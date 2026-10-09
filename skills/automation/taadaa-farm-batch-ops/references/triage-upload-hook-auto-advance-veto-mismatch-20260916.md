# Triage Sự Cố Post-Verification Failed Hàng Loạt Do Auto-Advance Video (2026-09-16)

## 1. Hiện Tượng & Triệu Chứng
- Báo cáo Watchdog nuôi acc (`feed_session_watchdog.py`) sau ca nuôi (Phiên 2/3 có hook đăng video) báo tỷ lệ lỗi upload cao bất thường (ví dụ: 69/80 máy dính `Lỗi script/xác minh`), chỉ có 2-3 máy thành công.
- Trong khi đó, kiểm tra thực tế:
  + Cột `Video Đã Đăng` trong file Excel (`TikN.xlsx`) vẫn tăng số đều đặn.
  + Thư mục runtime `D:/CodexRuntime/tiktok-video/runs` chứa các file `report.json` đều xác nhận `status: SUCCESS`, `post_verified: True`.
  + Tiến trình con kết thúc với mã thoát `exit_code: 0`.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
- **Cơ chế Auto-Advance của script upload:**
  Khi `tiktok_workflow` khởi chạy, nếu video được chỉ định bởi `--video-number <N>` đã từng được đăng và đã có fingerprint sha256 trong ledger, script sẽ tự động bỏ qua các video cũ và nhảy cóc lên video kế tiếp chưa đăng (ví dụ từ video 7 nhảy cóc lên video 10):
  `[AUTO-ADVANCE] Skipped 3 verified video(s); new video_number=10 (was 7)`.
  Khi upload video 10 thành công, `report.json` ghi nhận: `video_number: 10`, `status: SUCCESS`.
- **Bẫy VETO so khớp cứng trong Hook Feed Session (`multi_machine_feed_session.py`):**
  Khi tiến trình subprocess upload hoàn thành với `returncode == 0`, hook feed session đọc lại file `report.json` để xác minh và áp dụng logic phủ quyết:
  ```python
  if (
      rep_status == "SUCCESS"
      and rep_post_verified
      and rep_video_num is not None
      and int(rep_video_num) == int(next_video)  # <--- BẪY CỨNG Ở ĐÂY
      and ...
  ):
      verified_from_report = True
      report_veto_failed = False
  ```
  Khi `int(rep_video_num) != int(next_video)` (10 != 7):
  - `report_veto_failed = True` kích hoạt.
  - Hook ép `is_success = False` và gán nhãn tĩnh `reason: "post_verification_failed"`.
  - Hàng loạt máy thành công thật bị biến thành thất bại ảo trong `upload_result.json`.

## 3. Quy Chuẩn Khắc Phục Chuẩn
1. **Mở rộng điều kiện kiểm tra trong `multi_machine_feed_session.py`:**
   Cho phép `int(rep_video_num) >= int(next_video)` để chấp nhận các trường hợp auto-advance nhảy cóc video hợp lệ:
   ```python
   and int(rep_video_num) >= int(next_video)
   ```
2. **Cập nhật số video thực tế vào Ledger:**
   Khi ghi nhận hoàn tất upload thành công vào shift upload ledger, truyền đúng số video thực tế đã đăng (`actual_video_num = int(rep_video_num) if rep_video_num else next_video`) thay vì cố định `next_video` cũ.
