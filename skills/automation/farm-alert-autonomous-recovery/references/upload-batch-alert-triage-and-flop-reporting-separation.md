# Upload Batch Alert Triage vs Flop Channel Reporting Separation

## 1. Phân Biệt Hai Luồng Báo Cáo Khác Nhau (Separation of Concerns)
- **Batch Run Alert (Alert Tức Thời Sau Ca Upload):**
  * Nguồn phát sinh: Runner batch upload sau khi hoàn tất phiên cày (ví dụ: `Run: row-0-060045` của Farm Admin).
  * Mục tiêu: Báo cáo trạng thái cơ học tức thì tại hiện trường (máy nào upload thành công, máy nào lỗi script, máy nào hết video).
  * Đặc điểm: KHÔNG chứa báo cáo phân tích tăng trưởng kênh flop vì lúc runner vừa post xong thì chưa có dữ liệu tương tác mới (views, hearts, followers).
- **Daily Stale Upload & Flop Channel Watchdog (Bản Tin Định Kỳ 07:15 Sáng):**
  * Nguồn: Cronjob `daily-stale-upload-accounts-watchdog` (`cron_stale_upload_watchdog.py`).
  * Mục tiêu: Quét dữ liệu tăng trưởng từ snapshot cào `tiktok_tracker.db` đối soát với Excel sổ cái (`Tik1..Tik8.xlsx`), gọi `flop_channel_scanner.py` để phân loại kênh khỏe / kênh flop và sinh sẵn lệnh xoay nguồn cào `swap_single_folder_pipeline.py`.
  * Không nhầm lẫn giữa hai loại báo cáo khi user hỏi về module kênh flop.

## 2. Quy Trình Bóc Tách O(1) Cho 12 Lỗi Script Upload Thường Gặp
Khi nhận alert có danh sách máy lỗi script (ví dụ: `207, 208, 213, 253, 261, 262, 264, 268, 272, 276, 278, 280`):
1. **Trích xuất Run Artifacts trực tiếp:**
   - Đọc trực tiếp file `D:/Taadaa/runtime/<cluster>/live/<date>/<run_id>/<timestamp>/machines/machine_<ID>/<timestamp>/upload_result.json`.
   - CẤM gọi live ADB commands vào các máy sau ca vì máy đã ngủ (`Post-Shift Sleeping Phones`).
2. **Phân loại lỗi chính xác:**
   - `Missing required fields: ID TikTok`: Thường do race condition khi đọc file Excel trong lúc OneDrive đang đồng bộ (`Tik*.xlsx`). Thử lại `AccountSource` sau khi sync hoàn tất; nếu đọc lại bình thường thì là lỗi tự phục hồi (`transient`).
   - `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`: Nút tạo clip `(+)` ở bottom nav không hiển thị hoặc bị che bởi popup (cập nhật, permission, thông báo).
   - `[POST_VERIFY_PROOF_INSUFFICIENT]`: Clip thực tế đã được đăng lên (generic success text), nhưng bot chưa bắt được sự gia tăng số video trên lưới profile.
   - `[PREFLIGHT_VPN_BLOCKED]`: Egress IP check timeout qua proxy port tương ứng.
   - `Đóng Recent chưa được xác nhận`: Lỗi thao tác dọn dẹp app sau khi upload hoặc máy bị ngắt kết nối USB đột ngột (`device offline`).
3. **Đối soát số lượng thiết bị Remote ADB:**
   - Nếu số máy online trên cổng `5037` Remote giảm mạnh (ví dụ chỉ còn 27/80 máy), đối chiếu ngay với hiện tượng Xiaowei bị nghẽn luồng `wait-for-device` hoặc ADB loopback binding để xử lý hạ tầng.
