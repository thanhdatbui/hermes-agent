# Quy Tắc Điều Phối Feed Session: Lịch 4 Ca x 2 Phiên, Upload Cả 2 Phiên, Gate Follow & Kỷ Luật Báo Cáo

## 1. Cơ chế Upload Video (4 Ca x 2 Phiên)
- **Mở Upload Hook ở cả Phiên 1 và Phiên 2:**
  - Phiên 1 (00h, 06h, 12h, 18h): Lướt feed xong kiểm tra và đăng video ngay (nếu có video tương ứng với row trong ca).
  - Phiên 2 (01h30, 08h, 14h, 20h): Lướt feed xong đăng bù nếu Phiên 1 chưa đăng hoặc đăng lỗi.
- **Khóa nguyên tử chống trùng (`_ShiftUploadLedger`):**
  - Mỗi tài khoản chỉ được đăng thành công tối đa 1 video / ca.
  - Nếu Phiên 1 đã đăng thành công: Phiên 2 tự động Safe-Skip ngay trong 0.1s (`reason: already_uploaded_in_shift`).

## 2. Quy tắc Gate Follow Chéo (Follow Hook)
- **Gỡ bỏ rule chặn cứng Row 3..6 (`tik{row}-warmup-feed-only`):**
  - Không còn phân biệt warmup row 3..6 đối với follow hook.
- **Duy trì duy nhất Gate an toàn số video:**
  - Bắt buộc nick có **tối thiểu 5 video (`video_count >= 5`)** mới được phép đi follow.
  - Nick có $< 5$ video (0..4 video) tự động safe-skip (`under-5-videos-follow-disabled`) để tránh bị TikTok nhả nút follow và dính action-block.

## 3. Kỷ luật Báo Cáo Chốt Phiên (Watchdog & Coordinator)
- **Bắt buộc đủ 3 trụ cột:** Báo cáo tổng kết phiên BẮT BUỘC phải thể hiện rõ:
  1. Lướt Feed (Success / Fail)
  2. Đăng Video (Success / Lỗi / Bỏ qua theo phiên thực tế `{win['phien']}/2`)
  3. Follow chéo (Success / Nhả follow / Lỗi / Bỏ qua)
- Cấm bỏ quên trụ cột Follow hoặc ghi hardcode `(Phiên 3)` trong template báo cáo.

## 4. Điều phối cấu hình giữa các máy Farm (Kibe ↔ Admin)
- Khi user yêu cầu cấu hình hay đồng bộ cron cho bot Hermes trên máy khác (ví dụ Admin):
  - **CẤM TUYỆT ĐỐI** đưa runbook hướng dẫn user làm thủ công từng bước.
  - **BẮT BUỘC:** Soạn sẵn script tự động hóa hoàn chỉnh và cung cấp duy nhất 1 câu lệnh (one-liner) để bot Hermes trên máy đó tự chạy và cấu hình.
