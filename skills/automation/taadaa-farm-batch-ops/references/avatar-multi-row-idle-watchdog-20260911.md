# Avatar Multi-Row Idle Watchdog & Row Mapping Verification (2026-09-11)

## 1. Bản chất ca bệnh "Nãy bảo upload all nick r giờ lòi ra nick chưa up"
- Khi người dùng chụp màn hình tài khoản TikTok hiển thị 0 video / chưa up avatar (ví dụ `@leminhloc0523` trên Máy 73):
  - **Không kết luận vội là sót đơn lẻ hay lỗi code**: Phải tra ngay cấu trúc 8 Row / Slot trong `taikhoan_run_safe.xlsx` và `Tik1..Tik8.xlsx`.
  - Thực tế các đợt upload trước mới chạy hoàn tất cho **Row 1 ➔ Row 4** (Tik1..Tik4 đã đăng $\ge 1$ video).
  - Các tài khoản thuộc **Row 5 (`Tik5.xlsx`)** và **Row 6 (`Tik6.xlsx`)** toàn farm hiện tại đều đang ở trạng thái nguyên thủy `Video Đã Đăng = 0` và chưa chạy batch avatar riêng.
  - Ảnh thứ 2 (Account Switcher trên Máy 43): Kiểm tra kỹ danh sách nick (`songiang07`, `minh.minh.chu7`, ...) là các tài khoản thuộc các Row 1..6 của Máy 43, không phải Máy 73.

## 2. Quy trình "Canh rảnh thì up" (Idle-gated Multi-Row Avatar Watchdog)
Khi người dùng yêu cầu: *"Up ava luôn cho bno đi, canh rảnh thì up"*:
1. **Kiểm tra tính sẵn sàng của file avatar trên đĩa**:
   - Nguồn gốc: `D:\video goc\<video gốc>\avatar.jpg`
   - Nguồn render: `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`
   - Bắt buộc kiểm tra 100% các folder của Row cần up. Nếu thiếu folder nào thì bổ sung trước khi dispatch.
2. **Xây dựng Watchdog kiểm tra trạng thái Rảnh (3 Gate)**:
   - **Gate 1 - Tiến trình (Process Gate)**: Không có tiến trình nuôi feed (`run-feed-session.ps1`, `multi_machine_feed_session.py`), upload video (`run_post.py`, `run_tiktok_upload_batch.ps1`), hoặc chuỗi reg đêm (`run_all.ps1`, `night_chain_reg_pipeline`).
   - **Gate 2 - Device-Lock Gate**: Không có máy bị kẹt device lock (hoặc lock active $\le 3$ máy).
   - **Gate 3 - Giờ đổi ca (Shift Boundary Gate)**: Tránh khởi chạy sát giờ đổi ca nuôi feed (15 phút trước và sau các mốc 00:00, 06:00, 12:00, 18:00) và tránh giờ reg đêm lúc 01:00.
3. **Thứ tự thực thi tuần tự qua State File**:
   - `TARGET_TIKS = [5, 6, 3, 4]`.
   - Lưu trạng thái qua `avatar_idle_uploader_state.json`: ghi nhận `current_index` và `completed_tiks`.
   - Gọi canonical launcher:
     ```powershell
     powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1" -Tik <N> -MaxParallel 20 -HostConfigPath "D:\Taadaa\machine-config\kibe.yaml"
     ```
   - Sau khi hoàn thành hết toàn bộ danh sách `TARGET_TIKS`, cron job tự động thông báo và dọn dẹp.
