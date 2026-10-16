# Hotmail ➔ GPM ➔ ChatGPT Lifecycle Supervisor Triage & Stagnation

## 1. Triệu chứng & Nguyên nhân Lệch Số Liệu Báo Cáo 6H

### Triệu chứng
- Báo cáo 6H (`hotmail-gpm-lifecycle-6h-report`) báo tỷ lệ đăng ký ChatGPT của Farm Kibe rất thấp (ví dụ: `4/409 ~ 0.9%`), trong khi Admin lên tới `442/626 ~ 70.6%`.
- Tiến độ đổi pass (`CHANGE_INFO` / `DONE`) của Admin là `0/626`, trong khi Kibe đã đạt `81/409`.
- Báo cáo ghi nhận hàng chục tài khoản (ví dụ 65 nick) rơi vào nhóm `BLOCKED` (Cooldown 48h / Cần cứu).

### Nguyên nhân Gốc Rễ
1. **Lệch Trường Dữ Liệu Báo Cáo (Timestamp vs Cờ Thực Tế):**
   - Trong `cron_hotmail_gpm_lifecycle_6h_report.py`, bộ đếm `chatgpt_ok` chỉ kiểm tra trường timestamp `chatgpt_registered_at` hợp lệ.
   - Tại Farm Kibe, hàng trăm tài khoản (392/409) đã có sẵn mật khẩu ChatGPT (`chatgpt_password` và `has_chatgpt = True`) từ Excel `taikhoan_dat_v2_updated .xlsx`, nhưng trường `chatgpt_registered_at` bị `None`. Watchdog đếm sót toàn bộ các tài khoản này.

2. **Kẹt State Machine ở `HOTMAIL_LOGIN` sau khi đã Reg ChatGPT:**
   - Tại Farm Admin, 442 tài khoản đã reg ChatGPT (`chatgpt_registered_at` có timestamp).
   - Tuy nhiên, 342 tài khoản trong số đó vẫn bị gán `stage: "HOTMAIL_LOGIN"` trong `batch_gpm_5profiles_supervisor_state.json`.
   - Vì không được nâng lên `stage: "WAIT_7D"`, hệ thống không tính chu kỳ ngâm 7 ngày để chuyển tiếp sang `CHANGE_INFO` (Đổi pass Hotmail & bảo mật), dẫn đến tỷ lệ đổi pass Admin mãi ở mức `0/626`.

3. **Cơ Chế Khóa Cooldown 48H Sau 1 Lần Lỗi (Deadlock):**
   - Khi `batch_gpm_hotmail_password_login.py` trả về `status: "FAILED"`, supervisor set `status: "BLOCKED"` và `login_retry_count += 1`.
   - Điều kiện gỡ khóa tự động: `(now - fail_time) >= 48 * 3600` (2 ngày). Nick bị đóng băng hoàn toàn trong 48h dù proxy hoặc mật khẩu có thể chỉ gặp sự cố tạm thời.

4. **Lệch Version Script Runner Giữa Local và OneDrive Sync:**
   - Wrapper cron `gpm_5profiles_supervisor_wrapper.py` gọi cứng đường dẫn `D:\Taadaa\GPM auto\scripts\batch_gpm_5profiles_supervisor.py`.
   - Nếu bản vá mới chỉ nằm ở `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`, cron vẫn chạy code cũ (chưa có bypass token, chưa đồng bộ pass mới từ Excel).

5. **Cron Nạp Pool ChatGPT Web Kẹt 0/10 Vì Google OAuth:**
   - `cron_auto_feed_chatgpt_pool.py` cố gắng trích xuất `__Secure-next-auth.session-token`. Khi session hết hạn, script ấn `Continue with Google` nhưng bị kẹt ở form đăng nhập Google (`accounts.google.com/v3/signin/...`), không có cookie mới để nạp vào OmniRoute (:20129).

---

## 2. Quy Trình Khắc Phục Chuẩn (Runbook Triage O(1))

### Bước 1: Đối soát sự đồng bộ của script runner
Kiểm tra kích thước và diff giữa bản local và OneDrive:
```bash
python -c "
import os
p1 = r'D:\Taadaa\GPM auto\scripts\batch_gpm_5profiles_supervisor.py'
p2 = r'D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\batch_gpm_5profiles_supervisor.py'
print('GPM auto size:', os.path.getsize(p1), 'OneDrive size:', os.path.getsize(p2))
"
```
Nếu khác biệt, đồng bộ bản mới nhất sang `D:\Taadaa\GPM auto\scripts\`.

### Bước 2: Tự động nâng stage cho các nick đã Reg ChatGPT
Script vá trạng thái O(1) chạy an toàn trên state JSON:
```python
import json, tempfile, os

def advance_registered_chatgpt_to_wait7d(state_path: str):
    if not os.path.exists(state_path):
        return 0
    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    profiles = data.get("profiles", {})
    count = 0
    for info in profiles.values():
        if info.get("chatgpt_registered_at") and info.get("stage") == "HOTMAIL_LOGIN":
            info["stage"] = "WAIT_7D"
            if info.get("status") in {"BLOCKED", "FAILED"}:
                info["status"] = "PENDING"
            count += 1
    if count > 0:
        dir_p = os.path.dirname(state_path)
        with tempfile.NamedTemporaryFile("w", dir=dir_p, delete=False, encoding="utf-8") as tf:
            json.dump(data, tf, indent=2, ensure_ascii=False)
            tmp = tf.name
        os.replace(tmp, state_path)
    return count
```

### Bước 3: Đồng bộ timestamp cho nick Kibe đã có mật khẩu ChatGPT
Với các nick đã có `chatgpt_password` hoặc `has_chatgpt: True` từ Excel, nếu thiếu `chatgpt_registered_at`, gán timestamp để báo cáo 6H phản ánh chính xác 100% năng lực tài khoản của Farm.

### Bước 4: Xử lý 65 nick BLOCKED
- Nếu đã qua 48h: Kiểm tra log `hotmail_login_cooldown_unblock` trong telemetry xem cron tự nhả chưa.
- Nếu cần can thiệp trước 48h: Chỉ reset `status: "PENDING"` cho các nick có mật khẩu hợp lệ trong Excel và proxy còn sống.

---

## 3. Cron Nạp Pool ChatGPT Web (`cron_auto_feed_chatgpt_pool.py`) & Dọn Dẹp Zombie

### Cạm bẫy tên tiến trình Chrome trên Windows (`chrome.exe` vs `gpm_browser`)
- **Lỗi:** Dùng `if 'gpm_browser' in (p.info.get('name') or '').lower()` để tìm và kill tiến trình GPM Chrome.
- **Thực tế:** Trên Windows, tên tiến trình luôn là `chrome.exe` (chỉ có đường dẫn binary nằm trong thư mục `gpm_browser_chromium_core_...`). Kiểm tra theo tên `gpm_browser` luôn trả về False, khiến sau mỗi lượt chạy bị rò rỉ hàng chục zombie Chrome processes làm nghẽn CPU/RAM.
- **Khắc phục chuẩn:**
```python
for p in psutil.process_iter(['name', 'cmdline']):
    try:
        if 'chrome' in (p.info.get('name') or '').lower():
            cmd = ' '.join(p.info.get('cmdline') or []).lower()
            if pid.lower() in cmd and 'google/chrome/user data' not in cmd.replace('\\', '/'):
                p.kill()
    except Exception:
        pass
```

### Phân vùng ưu tiên ứng viên (Candidate Partitioning)
- Tránh tình trạng các profile Gmail cũ bị hết hạn session (kẹt ở màn hình Google OAuth `accounts.google.com/v3/signin/...`) chiếm trọn slot nạp pool, khiến nạp 0/10 liên tục.
- BẮT BUỘC tách danh sách ứng viên và ưu tiên Hotmail trước:
```python
cand_h = []
cand_g = []
for pid, name in rows:
    # ... lọc email và port ...
    if email not in active_emails:
        item = {"pid": pid, "email": email, "port": port}
        if "hotmail" in email:
            cand_h.append(item)
        else:
            cand_g.append(item)
return (cand_h + cand_g)[:limit]
```

### Dọn dẹp profile GPM bị treo qua Watchdog
- Khi phát hiện rò rỉ Chrome, chạy ngay công cụ dọn dẹp chuyên dụng:
```bash
python "D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/gpm_stale_profile_watchdog.py" --threshold 900
```

---

## 4. Kỷ Luật Phản Hồi Báo Cáo Cron ("Kiểm Tra Lỗi")

### Chống báo cáo đối phó / "bình thường hóa" số liệu lỗi
- Khi người dùng gửi lệnh "Kiểm tra lỗi cho t" và nhận báo cáo định kỳ (như báo cáo 6H), **CẤM TUYỆT ĐỐI** đọc lướt rồi trả lời xã giao "hệ thống đang ổn định" hay "tiếp tục theo dõi".
- BẮT BUỘC soi ngay vào các chỉ số bất thường:
  1. **Tỷ lệ bất thường giữa các farm:** Tại sao Kibe chỉ 4/409 (0.9%) mà Admin là 442/626? ➔ Kiểm tra trường đếm trong script report có khớp với Excel/state không.
  2. **Tiến độ cuối phễu = 0:** Tại sao Admin đã reg 442 ChatGPT nhưng Đổi pass (`DONE`) lại bằng 0/626? ➔ Kiểm tra state machine có bị nghẽn ở stage trung gian không (ví dụ kẹt ở `HOTMAIL_LOGIN` chưa chuyển sang `WAIT_7D`).
  3. **Tài khoản BLOCKED / Cooldown:** Có bao nhiêu tài khoản đang bị khóa? Nguyên nhân lỗi là gì? Cần gỡ thủ công hay chờ cooldown?
  4. **ChatGPT Web Pool:** Có bao nhiêu acc active? Cron nạp pool 15p có sinh lỗi 0/10 không?
- Phản hồi người dùng phải đi thẳng vào **Root Cause** và đề xuất hành động cụ thể (Fix ngay / Chờ cooldown / Đồng bộ mã nguồn).
