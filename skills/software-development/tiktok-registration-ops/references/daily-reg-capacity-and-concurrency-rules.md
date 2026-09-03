# Quy Tắc Giới Hạn Dung Lượng Máy & Điều Tiết Concurrency Reg TikTok

## 1. Giới hạn cứng 6 Tài Khoản / Máy
- **Nguyên tắc:** Mỗi thiết bị vật lý trong Farm chỉ chứa tối đa 6 tài khoản TikTok (`MAX_ACCOUNTS_PER_MACHINE = 6`).
- **Cơ chế Detector:** Quét `taikhoan_dat_v2_updated .xlsx`, đếm số lượng TikTok ID hiện có của từng máy (STT).
  - Nếu `count >= 6`: Loại vĩnh viễn khỏi mọi batch reg tiếp theo, tuyệt đối không cấp thêm mail thứ 7.
  - Tuyệt đối không reg dư trên máy cũ rồi logout mang sang máy mới (tránh checkpoint đổi thiết bị đột ngột trên acc non).

## 2. Điều kiện lọc Target kép (Dual Invariants)
Một máy chỉ được đưa vào danh sách đăng ký khi thỏa mãn đồng thời:
1. Số TikTok ID hiện có trên máy `< 6`.
2. Máy còn mail nguồn hợp lệ (Gmail/Hotmail có pass) trong `gmail_clean_v2.xlsx` mà chưa hề được đăng ký trong tracking.
3. Máy không bị chặn bởi `device_lock` (không có active lock hoặc cooldown 1 ngày).

## 3. Cơ chế Khóa Cooldown Đa Tiến Trình & Fail-Closed
- **Inter-process Kernel Lock:** Dùng `msvcrt.locking` (Windows) / `fcntl.flock` (POSIX) bảo vệ file `reg_daily_cooldowns.json`.
- **Check-and-Reserve Slot:** Khi bắt đầu đăng ký, gọi `reserve_machine_reg_slot(stt)` sinh token UUID độc nhất giữ chỗ, ngăn ngừa 2 tiến trình chạy trùng 1 máy.
- **Fail-Closed khi lỗi Schema:** Nếu file JSON hỏng hoặc thiếu trường `machines`, hệ thống tự động từ chối cấp slot mới và cấm ghi đè làm mất lịch sử máy đã thành công.
- **Release an toàn:** `release_machine_reg_reservation(stt, token=res_token)` bắt buộc token khớp chính xác mới được giải phóng slot khi có lỗi.

## 4. Điều tiết Concurrency & Ca Đêm (01:00 AM)
- **Cấu hình an toàn:** `--max-targets=30` và `--max-workers=6` (chạy cuốn chiếu từng đợt 6 máy, giãn cách 2–8s).
- **Tránh dính Rate-limit TikTok:** Không bao giờ dồn 40 máy mở app cùng lúc; chia nhỏ 30 máy/ca giúp lưu lượng mạng tự nhiên.
- **Tuần tự chuỗi đêm (Blocking):** Cron 01:00 AM chạy Phase 1 (Reg Gmail) $\rightarrow$ Đợi xong hoàn toàn 100% $\rightarrow$ Nghỉ 10s flush Excel $\rightarrow$ Mới chạy Phase 2 (Reg TikTok).
