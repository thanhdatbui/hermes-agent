# Proxy Rotation, Feed Trust Rehydration & AI Recovery Hardening (20/08/2026)

## 1. Chiến Lược Đổi Dàn Proxy Mới & Rửa IP (Rehydrate Trust Score)
- **Bối cảnh**: Khi phát hiện dàn máy bị leak direct IP hoặc chạy dính chung dải IP bị cắm cờ (Flagged IP), việc tiếp tục đăng video hoặc bấm Follow sẽ kích hoạt bộ lọc spam cụ thể:
  - Tỉ lệ nhả follow tăng vọt lên ~98% sau vài giờ khi IP cạn hạn mức tin cậy (trust budget).
  - Video đăng mới dễ bị 0 view hoặc shadowban theo cụm.
- **Quy tắc vận hành khi đổi Proxy mới**:
  - **Giai đoạn 1 (1–2 ngày đầu)**: **CHỈ LƯỚT FEED FYP THUẦN TÚY** (tắt hoàn toàn hook follow & upload hook). Lướt tự nhiên để TikTok ghi nhận thiết bị đổi IP hợp lệ và tái tạo điểm uy tín (Trust Score).
  - **Giai đoạn 2 (Từ ngày thứ 3)**: Mở lại tính năng Follow cho Row 1 & Row 2 (giữ hạn mức an toàn 4 sáng / 4 tối).
  - **Giai đoạn 3 (Sau khi Follow ổn định)**: Mở lại ca Upload video phiên cuối.

## 2. Khắc Phục Triệt Để 2 Điểm Nghẽn AI Auto-Recovery
1. **Lỗi `WinError 2` khi Commit Git trong Subprocess**:
   - Khi process AI Auto-Recovery được spawn ngầm, biến môi trường `PATH` có thể bị thiếu thư mục Git.
   - **Khắc phục**: Khóa cứng đường dẫn tuyệt đối chuẩn `_GIT_EXE = r"C:\Program Files\Git\cmd\git.EXE"` trong `code_patcher.py`.
2. **Lỗi Pytest Collection do Xung Đột Môi Trường**:
   - Pytest trong `code_patcher.py` bắt buộc chạy qua Python automation env (`D:\Taadaa\python-envs\automation\Scripts\python.exe`) và loại bỏ `PYTHONPATH` của Hermes venv để tránh lỗi import `_imaging` từ Pillow.

## 3. Khóa Cứng Xoay Dọc Mọi Phiên Feed (`lock_portrait_rotation`)
- Bắt buộc gọi `lock_portrait_rotation(ctx)` (Dual-layer: `settings put` + `content insert` vào Content Provider) ngay tại đầu hàm `_feed_session_flow` (`feed_swipe_smoke.py`) để ngăn chặn tình trạng cảm biến gia tốc trên Samsung tự động xoay ngang màn hình khi lướt video tỷ lệ lạ.
