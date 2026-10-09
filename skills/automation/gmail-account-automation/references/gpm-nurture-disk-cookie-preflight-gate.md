# Disk-Level SQLite Cookie Preflight Gate Prior to GPM Profile Launch

Đúc kết bài học kỹ thuật và quy tắc kiến trúc sống còn từ phản ánh của User ngày 2026-10-02:
*"Ủa sao k check đc acc có cookies google hay k mà đã chạy nuôi v"*

---

## 1. Bản Chất Sự Cố & Bẫy "Kiểm Tra Session Muộn Trong Browser" (Late Session Verification Trap)

### A. Giả định sai lầm (Faulty Assumption)
- Khi phân vùng hồ sơ GPMLogin theo nhóm `GroupId = 10` (`Google_Live_Ready`), hệ thống giả định rằng: *"Toàn bộ 76 profile nằm trong Group 10 đều là profile đã đăng nhập Google sống"*.
- Do giả định đó, bước tiền kiểm tra file SQLite cookies trên đĩa (`get_emails_with_session()`) đã bị gỡ bỏ khỏi vòng lặp chọn ứng viên (`filter_nurture_candidates`), chuyển sang kiểm tra cookie muộn bên trong hàm `nurture_profile()` qua Playwright (`context.cookies()`).

### B. Hậu quả thực tế (Starvation Trap & Resource Waste)
1. **Lệch thực tế 35%**: Đối soát thực tế trong 76 profile Group 10 cho thấy chỉ có **49 profile** có cookie Google sống ($\ge 2$ token `SID`, `SSID`, `HSID`, `SAPISID`), còn tới **27 profile (35.5%)** hoàn toàn không có cookie Google (0 token do hết hạn, văng phiên, hoặc chưa login xong).
2. **Bẫy chiếm quyền ưu tiên (Priority Inversion / Starvation)**:
   - Thuật toán chọn ứng viên ưu tiên profile chưa nuôi bao giờ (`last_nurtured = 0`).
   - Các profile mất phiên / chưa đăng nhập luôn có `last_nurtured = 0` $\rightarrow$ chúng độc chiếm toàn bộ slot đầu của batch nuôi.
3. **Lãng phí tài nguyên cực nặng**:
   - Ở mỗi profile chết: Script gọi GPM API `/profiles/start` $\rightarrow$ GPM cấp port $\rightarrow$ khởi động Chromium $\rightarrow$ kết nối Playwright CDP (mất 10–15s).
   - Đến khi Playwright đọc `context.cookies()`, phát hiện 0 token mới log cảnh báo `NEEDS_LOGIN` và gọi teardown/kill process.
   - Một batch 6 profile mất gần **8 phút** chạy mở/tắt browser liên tục nhưng tỷ lệ thành công là **0% (0/6)**, gây nghẽn Chromium, giật lag PC và nghẽn kết nối proxy 4G.

---

## 2. Quy Tắc Bắt Buộc: Disk-Level SQLite Cookie Preflight Gate ($O(1)$)

### Nguyên tắc tối cao:
```
ZERO BROWSER LAUNCH WITHOUT PRIOR DISK-LEVEL COOKIE PROOF
(Tuyệt đối CẤM khởi động GPM profile hoặc Chromium khi chưa có bằng chứng cookie sống trên đĩa)
```

### Kiến trúc kiểm tra 2 tầng (Dual-Gate Validation):
1. **Gate 0 (Disk Preflight - Bắt buộc trước khi chọn Candidate)**:
   - Đọc trực tiếp file SQLite cookie của profile trên ổ cứng trong chế độ Read-Only (`mode=ro`) hoặc copy nhanh sang file tạm.
   - Thời gian thực thi: **~0.001s / profile** (quét toàn bộ 76 profile chỉ mất **0.05 giây** thay vì 8 phút).
   - Hồ sơ có $< 2$ token session Google BẮT BUỘC bị loại ngay lập tức (`skipped_no_cookie`) và ghi nhận trạng thái `NEEDS_LOGIN` vào state file mà **KHÔNG ĐƯỢC PHÉP GỌI API START GPM**.
2. **Gate 1 (In-Browser Verification - Phòng thủ thứ cấp)**:
   - Sau khi Playwright kết nối CDP, kiểm tra lại `context.cookies()`. Đây chỉ là lớp bảo vệ dự phòng cuối cùng chống trường hợp cookie bị hỏng trong RAM.

---

## 3. Pattern Triển Khai Chuẩn Hóa (Canonical Pattern)

```python
import sqlite3
import shutil
import tempfile
from pathlib import Path

CRITICAL_GOOGLE_COOKIES = ('SID', 'SSID', 'HSID', 'SAPISID')

def check_gpm_profile_google_cookies_on_disk(profile_dir: Path) -> Tuple[bool, int]:
    """
    Kiểm tra nhanh O(1) session Google của profile GPM trực tiếp trên đĩa.
    Trả về: (has_session: bool, cookie_count: int)
    """
    cookie_paths = [
        profile_dir / "Default" / "Network" / "Cookies",
        profile_dir / "Default" / "Cookies"
    ]
    
    target_path = None
    for p in cookie_paths:
        if p.exists() and p.stat().st_size > 0:
            target_path = p
            break
            
    if not target_path:
        return False, 0

    count = 0
    # Dùng tempfile copy để chống xung đột SQLite database locked khi Chrome đang chạy
    tmp_db = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db = Path(tmp.name)
        shutil.copyfile(target_path, tmp_db)
        
        conn = sqlite3.connect(f"file:{tmp_db}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM cookies WHERE host_key LIKE '%google.com' "
            "AND name IN ('SID', 'SSID', 'HSID', 'SAPISID')"
        )
        row = cur.fetchone()
        count = row[0] if row else 0
        conn.close()
    except Exception as e:
        # Fallback query trực tiếp nếu không copy được
        try:
            conn = sqlite3.connect(f"file:{target_path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute(
                "SELECT count(*) FROM cookies WHERE host_key LIKE '%google.com' "
                "AND name IN ('SID', 'SSID', 'HSID', 'SAPISID')"
            )
            row = cur.fetchone()
            count = row[0] if row else 0
            conn.close()
        except Exception:
            count = 0
    finally:
        if tmp_db and tmp_db.exists():
            try:
                tmp_db.unlink(missing_ok=True)
            except Exception:
                pass

    return (count >= 2), count
```

---

## 4. Tích Hợp Vào Vòng Lặp Lọc Ứng Viên (`filter_nurture_candidates`)

Khi lọc profile hợp lệ để đưa vào hàng đợi nuôi:
1. Bóc tách `ProfilePath` từ thông tin profile GPM.
2. Gọi `check_gpm_profile_google_cookies_on_disk(base_gpm_dir / ppath)`.
3. Nếu `not has_session`:
   - Ghi nhận metric: `skipped_no_cookie += 1`.
   - Cập nhật state file: Đánh dấu `status = "NEEDS_LOGIN"`, `last_checked = now`.
   - Bỏ qua profile, nhường tài nguyên cho các tài khoản có session sống.
4. Tài khoản bị đánh dấu `NEEDS_LOGIN` sẽ được watchdog chuyên trách (`post_evening_gpm_login_watchdog.py`) xử lý đăng nhập lại trong ca tối, phục hồi session trước khi quay trở lại hàng đợi nuôi.
