# Single-Machine On-Demand Avatar Replacement Workflow

## 1. Xác định máy và tài khoản mục tiêu
Khi nhận yêu cầu đổi avatar từ ảnh chụp màn hình hoặc username TikTok:
- Tra cứu username trong các workbook `D:/OneDrive/TaadaaData/kibe/Tik*.xlsx` (`Tik1.xlsx` đến `Tik8.xlsx`) và database `D:/Taadaa/data/tiktok_tracker.db` (`account_mapping`, `snapshots`, `avatar_replace_queue`).
- Lấy chính xác bộ 4 thông số: `máy`, `tik`, `folder_video` (kho render), `video_goc` (kho gốc).

## 2. Tiêu chuẩn trích xuất & Cắt crop Avatar đạt chuẩn Vision
- **Nguồn ảnh:** Trích xuất các frame rõ nét từ các video `.mp4` trong `D:/video goc/<folder>` hoặc `D:/TIKTOK-videonuoinick/<folder>`.
- **Quy tắc Crop tròn TikTok:**
  - Khung hình TikTok Profile là hình tròn. Tránh tuyệt đối lấy ảnh toàn thân ở góc xa (khi vào khung tròn mặt chủ thể sẽ bị nhỏ tí teo hoặc lệch góc).
  - Crop cận cảnh (tight zoom / portrait): Khuôn mặt chủ thể (người / thú cưng) phải nằm ngay trung tâm, chiếm 40%–60% diện tích khung hình vuông `512x512`.
  - Không dính watermark, phụ đề, thanh tiến trình hay viền đen.
- **Vision Pre-flight:** Mở ảnh qua `browser_vision` kiểm tra tận mắt độ nét, bố cục và xác nhận chủ thể đúng yêu cầu trước khi nạp vào hệ thống.

## 3. Đồng bộ kho ảnh 2 đầu (SSOT Dual-Sync)
- Copy file avatar thành phẩm `avatar.jpg` vào đồng thời cả hai kho:
  1. `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg` (Kho render trực tiếp)
  2. `D:/video goc/<folder>/avatar.jpg` (Kho gốc bảo toàn)
- Đảm bảo file có quyền đọc và kích thước hợp lệ (> 10KB, định dạng JPEG chuẩn).

## 4. Đồng bộ Workbook & Hàng đợi Database
- **Workbook `Tik<N>.xlsx`:**
  - Cập nhật cột `Avatar` của máy thành `PENDING` (để trigger runner nhận diện).
  - Kiểm tra và đồng bộ lại `Keyword Video` và `Hashtag Pool` cho chuẩn ngách nếu có sự sai lệch.
- **Database `D:/Taadaa/data/tiktok_tracker.db`:**
  - Cập nhật bảng `avatar_replace_queue`:
    ```sql
    UPDATE avatar_replace_queue
    SET status = 'PENDING', last_error = NULL, updated_at = datetime('now', 'localtime')
    WHERE username = '<username>' AND may = <may>;
    ```

## 5. Kích hoạt Runner Avatar chuyên biệt (Avatar-Only Mode)
- Sử dụng launcher `run_tiktok_upload_avatar.ps1` với `-ForceAvatarMachineList`:
  ```powershell
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 `
    -Tik <N> -MaxParallel 1 -HostConfigPath D:\Taadaa\machine-config\kibe.yaml `
    -ForceAvatarMachineList "<may>"
  ```
- **Kỷ luật Event-Driven:** Khởi chạy qua tiến trình nền `terminal(background=True, notify_on_complete=True, timeout=360)` để harness tự đánh thức khi runner kết thúc; CẤM TUYỆT ĐỐI polling vòng lặp sleep.

## 6. Nghiệm thu thực tế & Gửi ảnh bằng chứng (Gate 6)
- Sau khi runner báo thành công:
  1. Chụp ảnh màn hình Profile thực tế trên máy qua ADB (`screencap`).
  2. Dùng `browser_vision` (hoặc OCR) soi mắt kiểm tra: xác nhận avatar tròn trên profile đã cập nhật đúng hình mới, không bị lỗi hiển thị.
  3. Gửi ảnh nghiệm thu kèm thẻ `MEDIA:<path>` trong câu trả lời cho User kèm xác nhận trực quan nội dung đã thấy tận mắt.
