# Checklive-First & Lifecycle Synchronization Cho GPM Login & OmniRoute (2026-09-20)

## 1. Bài Học Cốt Lõi: Checklive-First Trước Mọi Thao Tác Đăng Nhập
- **Nguyên tắc**: Tuyệt đối không tự động thử đăng nhập, re-auth hay mở profile GPM cho tài khoản chưa được kiểm chứng trạng thái LIVE gần nhất.
- **Rủi ro**: Việc mở browser cố đăng nhập vào tài khoản đã bị Google khóa backend (`challenge/iap` / Phone Checkpoint) sẽ làm nghẽn proxy 4G, kích hoạt thêm cảnh báo an ninh và gây lãng phí chu kỳ xử lý của watchdog.
- **Quy trình chuẩn**:
  1. Chạy `run_checkmail_kibe_farm.py` (checkmail.live) qua mobile proxy để cập nhật trạng thái LIVE vs DIE trong `master_gmail_manager.xlsx`.
  2. Kích hoạt `sync_gpm_lifecycle.py` để xóa sạch profile GPM của các tài khoản DIE và gỡ bỏ session tài khoản DIE trên máy S7 rảnh.
  3. Chỉ đưa các tài khoản `LIVE` có tuổi ngâm thỏa mãn vào hàng đợi candidate của `post_evening_gpm_login_watchdog.py`.

---

## 2. Bẫy Tính Tuổi Tài Khoản Ngâm (Account Age Divergence)
- **Bẫy**: Trong `master_gmail_manager.xlsx`, cột 15 là `Cập Nhật` (lưu ngày gần nhất script checklive chạy ghi nhận, ví dụ `2026-09-20`). Nếu script watchdog đọc cột này để tính `(d_today - d_created).days < 7`, tất cả tài khoản LIVE đều bị tính là 0 ngày tuổi và bị loại bỏ toàn bộ.
- **Giải pháp**:
  - Tra cứu ngày tạo gốc từ file nguồn `gmail_clean_v2.xlsx` (cột 7 / index 6 `ngày tạo`).
  - Toàn bộ kho clean_v2 được nhập từ tháng 2–6/2026 (tuổi > 80 ngày). Nếu tài khoản có trong `clean_v2` nhưng không ghi rõ ngày tạo, mặc định coi như đủ điều kiện ngâm an toàn.

---

## 3. Quy Tắc Chống Xung Đột Cron Khi Mở Rộng Khung Giờ Ban Ngày
Khi cấu hình watchdog login/OAuth chạy vào khung giờ ban ngày (Sáng 07:15–08:45, Trưa 12:00–13:45), bắt buộc phải tuân thủ 2 chốt chặn:
1. **Device Lock Chặt Chẽ**: Sử dụng `acquire_device_lock` từ `automation-core`, tự động bỏ qua nếu máy đang có tiến trình khác chiếm giữ.
2. **Buffer Thời Gian Nuôi Feed (45 Phút)**:
   - Đọc manifest `manifests/assignment-v1-*.json`.
   - Nếu máy S7 đang trong slot nuôi feed hoặc **sắp đến giờ nuôi feed trong vòng 45 phút tới** (`MIN_IDLE_BUFFER_MIN = 45`), watchdog lập tức bỏ qua máy đó để bảo vệ lịch trình nuôi tài khoản TikTok.
