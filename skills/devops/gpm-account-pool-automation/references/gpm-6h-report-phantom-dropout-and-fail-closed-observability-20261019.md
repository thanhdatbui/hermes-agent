# GPM 6H Report Phantom Dropout & Fail-Closed Observability Protocol

## 1. Bản chất sự cố Báo cáo Ảo 79 Acc Văng Cookie (Incident RCA 19/10/2026)

### 1.1. Hiện tượng thực tế
Bản tin định kỳ 06:00 sáng từ `gpm-gmail-nurture-6h-report` thông báo:
- `• Tổng số profile Group 10 (Google Live Ready): 77`
- `⚠️ Acc phát hiện văng cookie (79 acc, đã đẩy re-login miễn trừ cooldown)`
- Nghịch lý toán học: Cả Group 10 chỉ có 77 profile, nhưng script lại báo có tới 79 acc văng cookie, khiến Operator phản ứng gay gắt ("Fix lỗi đi").

### 1.2. Root Cause 1: Quét State Mù & Không Lọc Group ID
File trạng thái `gpm_gmail_nurture_state.json` lưu trữ tích lũy mọi tài khoản từng chạy từ quá khứ (bao gồm các nhóm cũ, nhóm rác hoặc acc đã xóa).
Khi script báo cáo duyệt qua `for em, info in state.items():`:
- Không đối chiếu danh sách email thuộc Group 10 trong cơ sở dữ liệu `profile_data.db`.
- Dẫn đến việc gom **29 tài khoản rác không thuộc Group 10** vào danh sách "văng cookie của Group 10".

### 1.3. Root Cause 2: Không Khóa Cửa Sổ Thời Gian (Time Window Leaks)
`status == "NEEDS_LOGIN"` được script kiểm tra mà **không lọc theo mốc thời gian** `(now_ts - last_checked) <= WINDOW_HOURS * 3600`:
- 50 tài khoản Group 10 đã bị đánh dấu `NEEDS_LOGIN` từ nhiều tuần trước (do các đợt chạy cũ) bị gom toàn bộ vào mục "Acc phát hiện văng cookie".
- Trong khi thực tế trong 6h qua: **0 tài khoản nào mới văng cookie** (toàn bộ 25 lượt nuôi đều thành công 100%).

### 1.4. Root Cause 3: Bẫy Nghẽn Nuôi Vĩnh Viễn (Selection Loop Choke)
Trong `cron_gpm_gmail_nurture.py`, vòng lặp chọn candidate nuôi thực hiện:
```python
if info.get("status") == "NEEDS_LOGIN":
    continue
```
Cú pháp `continue` vô điều kiện này biến `NEEDS_LOGIN` thành bản án "tù chung thân": các profile bị văng cookie không bao giờ được bốc lại để kiểm tra session hay nuôi nữa, kể cả khi session đã được watchdog login khôi phục thành công trên đĩa.

---

## 2. Chuẩn Hóa Kiến Trúc Báo Cáo 6H Fail-Closed

### 2.1. Truy vấn Danh tính Group 10 Độc quyền Read-Only
Tuyệt đối không mở SQLite ở chế độ ghi hay fallback mập mờ. Bắt buộc dùng `mode=ro` và giải phóng kết nối trong `try...finally`:
```python
def get_group10_emails(db_path: Optional[Path] = None) -> Set[str]:
    path = db_path or GPM_DB_PATH
    if not path.exists():
        return set()
    try:
        conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT Name FROM Profiles WHERE GroupId = ? OR GroupId = ?",
                (GROUP_ID, str(GROUP_ID))
            ).fetchall()
        finally:
            conn.close()
    except Exception as e:
        sys.stderr.write(f"Lỗi truy vấn GPM DB ({path}): {e}\n")
        return set()
    
    emails = set()
    for (name,) in rows:
        m = EMAIL_RE.search(name or "")
        if m:
            emails.add(m.group(1).lower())
    return emails
```

### 2.2. Nguyên tắc FAIL-CLOSED Tuyệt Đối (Anti-False-Health)
Khi DB GPM không tồn tại, kết nối lỗi, hoặc Group 10 rỗng:
- **Phân biệt Lỗi DB (`None`) và Group Rỗng (`set()`):**
  Hàm `get_group10_emails` trả về `None` khi file không tồn tại hoặc lỗi SQL, và trả về `set()` khi truy vấn thành công nhưng không có profile nào.
- **CẤM TUYỆT ĐỐI:** Bỏ qua bộ lọc và duyệt toàn bộ state, hoặc in khẩu hiệu giả tạo `"100% cookie sống tốt, không có acc văng"`.
- **BẮT BUỘC:** Cắt ngắn và báo lỗi rõ ràng ở đầu bản tin:
```python
if group10_emails is None:
    report.append("⚠️ LỖI DB: Không thể đọc danh sách Group 10 từ GPM DB (Fail-Closed)!")
    return report

if not group10_emails:
    report.append(f"⚠️ CẢNH BÁO: Group {GROUP_ID} rỗng, không có profile Gmail nào (Fail-Closed)!")
    return report

if not state:
    report.append("⚠️ CẢNH BÁO: State file rỗng hoặc chưa có dữ liệu nuôi!")
    return report
```

### 2.3. Bóc Tách Minh Bạch Hai Khái Niệm Quan Sát & Chặn Timestamp Tương Lai
Bản tin 6H bắt buộc:
1. **Acc mới phát hiện NEEDS_LOGIN trong 6h qua (`dropped_6h`):** Bắt buộc chặn cận dưới `0 <= (now_ts - last_checked) <= WINDOW_HOURS * 3600` để ngăn timestamp tương lai hoặc giá trị âm lọt vào cửa sổ thời gian.
2. **Kỷ luật từ ngữ (Claim Discipline):** Tuyệt đối không dùng các từ ngữ suy đoán vượt quá bằng chứng:
   - Dùng `"Gmail Group 10 (GPM DB)"` thay vì `"Google Live Ready"`.
   - Dùng `"Không có profile nào ghi nhận NEEDS_LOGIN trong state"` thay vì `"100% cookie sống tốt"`.
   - Dùng `"phát hiện NEEDS_LOGIN trong 6h qua"` thay vì `"văng cookie trong 6h qua"`.
```python
if pending_relogin:
    if dropped_6h:
        report.append(f"⚠️ Acc phát hiện NEEDS_LOGIN trong {WINDOW_HOURS}h qua: {len(dropped_6h)} acc")
        for em in dropped_6h[:5]:
            report.append(f"  - {em}")
        if len(dropped_6h) > 5:
            report.append(f"  ... và {len(dropped_6h) - 5} acc khác")
    else:
        report.append(f"• Trạng thái session {WINDOW_HOURS}h qua: ✓ Không có acc mới phát hiện NEEDS_LOGIN")
    report.append(f"⚠️ Tổng acc đang chờ re-login (Group {GROUP_ID}): {len(pending_relogin)} acc")
else:
    report.append("• Trạng thái session Google: ✓ Không có profile nào ghi nhận NEEDS_LOGIN trong state")
```

### 2.4. Tính Chính Xác Của Chỉ Số Nuôi (`nurtured_6h` & `warm_48h`)
- Chỉ đếm lượt nuôi thành công: bắt buộc kiểm tra `status == "success"` và `last_n > 0`.
- Đồng nhất đồng hồ thời gian: dùng `today_str = datetime.fromtimestamp(now_ts).strftime("%Y-%m-%d")` thay vì trộn lẫn `datetime.now()` để đảm bảo tính xác định (determinism) khi chạy test mô phỏng.

---

## 3. Cơ Chế Cooldown 24H Chống Nghẽn Nuôi (`is_profile_in_needs_login_cooldown`)

Trong `cron_gpm_gmail_nurture.py`:
- Thiết lập hằng số an toàn: `NEEDS_LOGIN_COOLDOWN_SECONDS = 86400` (24 giờ).
- Trích xuất thành hàm độc lập production để unit test có thể kiểm thử trực tiếp hành vi tại biên 24h:
```python
def is_profile_in_needs_login_cooldown(info: dict, now_ts: float, cooldown: int = NEEDS_LOGIN_COOLDOWN_SECONDS) -> bool:
    """Kiểm tra an toàn: chỉ coi là đang cooldown khi status=NEEDS_LOGIN, last_checked hợp lệ và không nằm trong tương lai."""
    if info.get("status") != "NEEDS_LOGIN":
        return False
    last_checked = info.get("last_checked", 0)
    return isinstance(last_checked, (int, float)) and 0 < last_checked <= now_ts and (now_ts - last_checked) < cooldown
```
- Trong bộ lọc `due_profiles`:
```python
if is_profile_in_needs_login_cooldown(info, now_ts):
    continue
```
- **Ý nghĩa:**
  + Trong vòng 24h kể từ khi phát hiện mất cookie: Profile được nhường trọn vẹn cho watchdog login xử lý, không bị cron nuôi đè ra mở lại vô ích.
  + Timestamp không hợp lệ (âm, rỗng, hoặc nằm ở tương lai `last_checked > now_ts`) sẽ không làm kẹt profile trong trạng thái cooldown vĩnh viễn.
  + Sau 24h hoặc khi được cập nhật `status: "LOGIN_RECOVERED"`: Profile tự động được đưa vào danh sách đánh giá lại để preflight cookie guard kiểm tra, không bị kẹt vĩnh viễn ngoài hàng đợi nuôi.
  + Test suite gọi trực tiếp `nurture_mod.is_profile_in_needs_login_cooldown` tại mốc đúng `now_ts - cooldown` để khẳng định hợp đồng `is False` tại biên mà không cần sao chép biểu thức logic vào test.
