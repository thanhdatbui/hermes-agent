# Bẫy Chọn Avatar Góc Nghiêng & Quy Trình Mosaic Trình Duyệt 6 Frame Ứng Viên

## 1. Bài học kinh nghiệm: Tránh vội vàng nạp góc chụp nghiêng / biểu cảm gượng gạo
- Khi trích xuất tự động bằng Haar Cascade / Face detector, thuật toán thường bắt trúng các frame đầu tiên có khuôn mặt (ví dụ khuôn mặt to ở góc nghiêng, góc ngửa cằm tập yoga, hoặc lúc đang thở/gồng cơ mặt).
- Mặc dù tỷ lệ kỹ thuật thỏa mãn (đủ 512x512, không cụt đỉnh đầu, mặt ở tâm tròn), về mặt thị giác người dùng sẽ thấy "xấu / gượng gạo / không tự nhiên" và yêu cầu "Đổi ảnh khác".
- **Quy chuẩn mới**:
  1. Tuyệt đối không chọn duy nhất 1 frame đầu tiên rồi nạp ngay vào thiết bị.
  2. BẮT BUỘC ghép **bảng mosaic 6 frame ứng viên** (`mosaic_frames.py`) lấy từ các clip khác nhau trong folder nguồn (`v00`, `v01`, `v03`, `v04`, `v05`, `v07`...).
  3. Dùng `browser_vision` soi mắt thẩm mỹ: Ưu tiên góc nhìn **trực diện, nụ cười tươi, thần thái tự nhiên, ánh sáng trong trẻo** trước khi crop và nạp.
  4. Gửi bảng mosaic hoặc bản preview tròn cho User xem hoặc tự chọn phương án tối ưu nhất.

## 2. Xử lý Lock Tranh chấp giữa Batch 2FA và Avatar Runner
- Khi chạy nạp avatar độc lập qua `run_avatar_batch_3accs.py`, nếu gặp `SKIPPED_LOCKED` (`device lock active`):
  * Kiểm tra `machine_<M>.lock.json` xem ai đang giữ lock.
  * Nếu là batch dài hạn như `run_batch_live_2fa.py` (PID còn sống, trạng thái `queued_v2`), TUYỆT ĐỐI CẤM cướp lock hay xóa file lock thô bạo.
  * Có 2 hướng giải quyết:
    a) Đợi batch 2FA hoàn tất nhả lock hoặc hoàn thành máy đó (PID kết thúc / lock file bị xóa).
    b) Đã cập nhật đầy đủ Excel (`Avatar = PENDING`), marker `.manual_avatar_locked` và SQLite `avatar_replace_queue`. Cron watchdog `post-evening-avatar-watchdog` sẽ tự động cuốn chiếu nạp ngay khi máy rảnh.
