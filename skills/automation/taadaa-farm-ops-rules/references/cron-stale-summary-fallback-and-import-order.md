# Pitfall: Cron Stale Summary Fallback & Import Order Preflight

## 1. Triệu chứng & Bản chất (Ghost Summary Trap)
- Cron pipeline (như `run_night_chain_pipeline.py`) chạy batch qua subprocess.
- Khi subprocess crash ngay từ giây đầu tiên (ví dụ do lỗi `NameError`, cú pháp import, v.v.) và không xuất ra đường dẫn `Summary JSON: ...` trên stdout.
- Logic parser fallback lại tìm thư mục `logs_parallel_*` có timestamp mới nhất trong thư mục runtime/logs.
- **Hậu quả ma ám**: Thư mục log mới nhất thực ra là của phiên chạy thành công/thất bại từ nhiều ngày trước (ví dụ 4 ngày trước). Parser đọc file summary cũ đó và báo cáo về Telegram với các số liệu cũ y như thật, che giấu hoàn toàn việc code runner đang crash 100%.

## 2. Quy tắc phòng chống (Stale Summary Guard)
1. **Freshness Check bắt buộc**:
   - Khi fallback tìm file log/summary mới nhất, BẮT BUỘC kiểm tra `mtime` của file summary.
   - Nếu file được tạo > 2 giờ trước (hoặc trước thời điểm bắt đầu batch hiện tại `start_time`): **CẤM ĐỌC**, lập tức phân loại kết quả là `RUNNER_CRASHED` hoặc `RUNNER_FAILED_NO_FRESH_SUMMARY`.
2. **Import-Order Dependency Gate**:
   - Trong các script monolith Python (như `gmail_reg_v10.py`), hằng số đường dẫn root dự án (`PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))`) PHẢI được định nghĩa ngay sau phần import chuẩn (`import os, sys`).
   - CẤM gọi `os.path.join(os.path.dirname(PROJECT_ROOT), ...)` ở đầu file trước khi biến `PROJECT_ROOT` được gán.
   - Khi review/test một commit mới vào runner: BẮT BUỘC test import smoke (`python -c "import <module>"`) trước khi kết luận pass.
