# Avatar Local SSD Staging & Device-Lock Reconciliation (07/10/2026)

## 1. Tránh chạy ffmpeg trực tiếp trên ổ HDD / External Drive D:
- **Hiện tượng:** Khi gọi `ffmpeg` hoặc OpenCV trích xuất frame (`-ss <sec> -i "D:\..."`) trực tiếp trên `D:\TIKTOK-videonuoinick\<folder>` hoặc `D:\video goc\<folder>`, tiến trình dễ bị kẹt đọc I/O / seek chậm dẫn đến timeout 15s - 30s.
- **Giải pháp tối ưu:** 
  - Copy file video mục tiêu (thường chỉ 3MB - 10MB) về thư mục tạm trên ổ SSD cục bộ (`C:\Users\Kibe\AppData\Local\Temp\...`).
  - Sau đó gọi `ffmpeg` hoặc OpenCV đọc từ SSD cục bộ: hoàn thành trích xuất frame chỉ trong < 0.1 giây.
  - Sau khi hoàn tất và tạo xong avatar 512x512, dọn dẹp các video tạm trên ổ C.

## 2. Kiểm tra Device-Lock kép (Machine ID & Serial)
- Thư mục lock `~/.codex/device-locks/` quản lý cả 2 loại tên file lock:
  1. `machine_<N>.lock.json`
  2. `serial_<DEVICE_SERIAL>.lock.json`
- Khi kiểm tra máy có rảnh hay không trước khi chạy `run_tiktok_upload_avatar.ps1`, BẮT BUỘC kiểm tra cả 2 định dạng file lock trên.
- Nếu phát hiện tiến trình đang chạy (ví dụ `phase-b-live` của `tiktok-add-bao-mat-f2a`):
  - Tra cứu PID và kiểm tra xem máy đang chạy đến hàng nào (qua workbook).
  - Nếu đang ở hàng cuối cùng (hoặc sắp hoàn thành), tuyệt đối KHÔNG kill tiến trình ngang xương.
  - Chờ tiến trình kết thúc sạch sẽ (graceful exit), lock tự giải phóng, rồi mới kích hoạt runner avatar.

## 3. Quy trình trích xuất Avatar chuẩn Niche cho kênh thú cưng / chó mèo
1. **Tìm video có khuôn mặt rõ nét:** Không chỉ lấy video `1.mp4` (dễ dính tư thế nằm lộn ngược hoặc quay lưng). Duyệt qua các video `5.mp4`, `7.mp4`, `8.mp4`...
2. **Đánh giá qua Vision API:** Soi độ nét chi tiết (mắt, mũi, tai, biểu cảm tươi tắn, không bị bệt lông đen).
3. **Crop & Padding:** Căn chỉnh bounding box sao cho đầu và tai cún nằm trọn 100% trong vòng tròn 512x512, không bị lẹm viền TikTok.
4. **Tạo ảnh đối chiếu Composite:** Ghép ảnh màn hình kênh cũ (lệch niche) và ảnh avatar mới (chuẩn niche có viền tròn TikTok) để gửi `MEDIA:` kèm lời xác nhận rõ ràng.
