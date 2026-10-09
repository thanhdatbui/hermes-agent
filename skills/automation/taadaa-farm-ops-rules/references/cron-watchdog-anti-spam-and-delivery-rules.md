# Cron Watchdog Anti-Spam & Delivery Rules (Taadaa Farm Operations)

## 1. Bối cảnh & Phân loại sự cố Spam Telegram

Trong quá trình vận hành Phone Farm, có hai nguồn chính gây bão tin nhắn / spam alert trên Telegram:

### A. Tác vụ Dọn dẹp ngầm (Janitor / Reaper / Auto-healer) gán nhầm kênh Telegram
- **Triệu chứng:** Cứ mỗi 5–10 phút, Telegram lại nhận được thông báo dọn dẹp profile, kill lock chết, sửa wifi... dù đây là các hoạt động định kỳ bình thường.
- **Ví dụ điển hình:** `gpm-stale-profile-watchdog` (quét profile GPM > 1h) được gán `deliver: telegram:...`. Khi có profile quá hạn, script in danh sách ra stdout, khiến Hermes tự động chuyển tiếp toàn bộ tin nhắn vào nhóm điều hành.
- **Lỗi nhân bản PID (Chrome Sub-process Spawning):** Mỗi profile Chrome khi mở sẽ kéo theo 5–10 tiến trình con (`--type=renderer`, `--type=gpu-process`, `--type=utility`, `crashpad`). Khi watchdog quét thô toàn bộ tiến trình không lọc `--type=`, 2 profile sẽ bị in thành 13–15 dòng PID riêng biệt, gây tràn màn hình chat.

### B. Vòng lặp báo lỗi thất bại (Cron Failure Alert Loop)
- **Triệu chứng:** Một cron job tự động thử lại (Recovery / Retry Watchdog, ví dụ: nạp OTP M40) chạy mỗi 5 phút nhưng bị lỗi liên tục (timeout 480s, exception).
- **Cơ chế:** Khi script thoát với mã lỗi khác 0 hoặc dội exception, Hermes mặc định gửi cảnh báo kèm ảnh chụp `MEDIA:` về kênh `deliver` (thường là `origin` - DM của User). Với chu kỳ 5 phút, User liên tục nhận thông báo lỗi kèm ảnh chụp lặp đi lặp lại.

---

## 2. Invariant Quy tắc Giao tiếp Cronjob (Delivery Matrix)

| Loại Cronjob | Mục đích & Tần suất | Cấu hình `deliver` bắt buộc | Hành vi khi có output / lỗi |
| :--- | :--- | :--- | :--- |
| **Janitor / Reaper** | Dọn dẹp profile treo, kill lock chết (`*/5m`, `*/10m`, `*/15m`) | **`deliver: "local"`** | Chỉ lưu file local `~/AppData/Local/hermes/cron/output/<job_id>/`. Tuyệt đối CẤM gửi Telegram. |
| **Auto-Healer / Sync** | Sửa Wi-Fi, heal proxy, sync workbook (`*/5m`, `*/15m`) | **`deliver: "local"`** | Chỉ lưu log local. Im lặng khi không có sự cố (Silent Watchdog). |
| **Retry / Recovery** | Thử lại nạp nick, giải phóng tài khoản treo | **`deliver: "local"`** hoặc chặn exception | CẤM `deliver: origin` trong vòng lặp thử lại ngắn (<= 15m). Dùng cờ `max_retries` và chỉ báo cáo khi thành công. |
| **Session Watchdog** | Báo cáo hoàn thành phiên nuôi acc (1.5h), tổng kết ngày | **`deliver: "telegram:..."`** | Cho phép gửi Telegram vì đây là báo cáo tiến độ kinh doanh quan trọng của Farm. |

---

## 3. Quy chuẩn Kỹ thuật khi viết Script Watchdog

### A. Khử trùng lặp tiến trình Chromium / Chrome / GPM
Mọi watchdog quét tiến trình Chromium bắt buộc lọc bỏ các sub-processes để không đếm trùng PID:
```python
# 1. Bỏ qua các tiến trình con của Chrome (renderer, gpu, utility...)
if any(arg.startswith("--type=") for arg in cmdline):
    continue

# 2. Khử trùng lặp theo profile key
prof_key = prof_id or profile_path or str(pid)
if prof_key in seen_profiles:
    continue
seen_profiles.add(prof_key)
```

### B. Nhận diện đúng form 'Đặt lại mật khẩu' trong TikTok Login OTP
- Màn hình "Đặt lại mật khẩu" trên TikTok có câu phụ: *"Bạn sẽ nhận được mã xác minh qua email"*.
- Cụm từ *"mã xác minh"* tuyệt đối **KHÔNG ĐƯỢC** kích hoạt `OTP_HINTS` trên màn hình này, vì đây thực chất là form yêu cầu người dùng điền lại địa chỉ Email để TikTok gửi mã.
- Nếu kích hoạt nhầm, script sẽ lấy mã OTP cũ/chưa gửi từ hộp thư để điền vào ô email -> TikTok báo *"Nhập địa chỉ email hợp lệ"* và gây timeout 480s làm văng vòng lặp spam lỗi.
