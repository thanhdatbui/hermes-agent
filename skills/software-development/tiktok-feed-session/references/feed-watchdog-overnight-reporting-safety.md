# Feed Session Watchdog & Overnight Session Reporting Safety

## 1. Bản chất sự cố chốt non (Premature Reporting)
- Các phiên nuôi TikTok cuối ngày (như **Ca 3 Phiên 3**: 21:45 - 23:59) chạy số lượng máy lớn (ví dụ 73-74 máy) thường kéo dài từ 22:30 đến 00:30 - 01:00 sáng hôm sau.
- Vào thời điểm 00:00:00, ngày chuyển sang ngày mới (`today` thay đổi), dẫn đến:
  - `is_today` đánh giá thành `False`.
  - Nếu hàm `can_report_session()` mặc định trả về `True` khi `not is_today` mà không kiểm tra runner process, watchdog sẽ chốt báo cáo ngay lập tức (chỉ mới có 2-3 máy hoàn tất) và ghi key vào `feed_session_reported.json`.
  - Kết quả: Báo cáo thiếu dữ liệu trầm trọng và các máy còn lại khi chạy xong sẽ không bao giờ được tổng hợp lại.

## 2. Nguyên tắc an toàn hai lớp (Double-Lock Safety)

### Khóa 1: Nhận diện tiến trình đang chạy (`is_feed_runner_active`)
- **Phải nhận diện cả cờ gạch nối và gạch dưới**:
  - Script có thể được gọi với `--mode multi-machine-feed-session` (dấu gạch nối) hoặc module name `multi_machine_feed_session` (dấu gạch dưới).
  - Phải kiểm tra đầy đủ các entry point và runner scripts:
    - `"multi_machine_feed_session"`
    - `"multi-machine-feed-session"`
    - `"run-feed-session.ps1"`
    - `"run_follow"`
    - `"run_tiktok.py"`
    - `"hermes_cron_runner.py"`
    - `"tiktok_runner.py"`
- **Loại trừ PID bản thân**: Luôn kiểm tra `if p.pid == os.getpid(): continue` để watchdog không tự nhận diện câu lệnh của chính nó khi quét `psutil`.

### Khóa 2: Điều kiện chốt báo cáo (`can_report_session`)
- **Quy tắc tuyệt đối**: Nếu `runner_busy == True`, **TUYỆT ĐỐI KHÔNG** cho phép report (`return False`), bất kể `is_today` là True hay False, bất kể số máy đã hoàn tất.
- **Khi phiên thuộc ngày hôm trước (`not is_today`)**:
  - Chỉ cho phép chốt report khi:
    1. `not runner_busy` (tiến trình runner đã kết thúc hoàn toàn), VÀ
    2. Một trong hai điều kiện sau thỏa mãn:
       - `completed_expected_count >= expected_count` (Tất cả máy dự kiến đã hoàn tất), HOẶC
       - `now_hm >= "02:00"` (Đã quá xa khung giờ Ca 3, sau 02:00 sáng, tránh chờ đợi vô tận nếu có máy bị drop vĩnh viễn).

## 3. Quy trình Reset State khi bị chốt non
Khi cần phát lại báo cáo đầy đủ sau khi đã sửa watchdog:
1. Mở file state: `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json`.
2. Xóa session key bị chốt non (ví dụ `"2026-09-05_ca3_phien3"`).
3. Đảm bảo runner đang chạy hoặc đã kết thúc. Khi watchdog chạy lại (hoặc chạy tay `python feed_session_watchdog.py`), nó sẽ tự động gom toàn bộ artifact của các máy (đầy đủ 73-74 máy), in báo cáo và ghi nhận lại state sạch.
