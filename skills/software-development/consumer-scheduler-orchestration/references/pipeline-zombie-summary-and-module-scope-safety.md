# Zombie Summary Prevention & Top-Level Module Scope Safety

## 1. Zombie / Stale Summary Detection in Orchestrator Pipelines
Trong các pipeline xâu chuỗi nhiều công đoạn (ví dụ: `run_night_chain_pipeline.py`, batch runners điều phối Gmail -> TikTok -> Follow):
- Khi một công đoạn kết thúc, orchestrator thường tìm file summary JSON mới nhất từ thư mục artifact/log (ví dụ `logs_parallel_* / summary.json` hoặc `social-batch-all / 20* / all_results.json`).
- **Nguy cơ Zombie Summary**: Nếu công đoạn hiện tại bị crash sớm, timeout, hoặc không sinh ra summary mới, logic tìm file mới nhất sẽ nhặt nhầm file summary cũ từ mẻ chạy trước đó (vài giờ hoặc ngày trước), dẫn đến báo cáo sai kết quả (false success/metrics).
- **Quy tắc phòng thủ**:
  - Luôn kiểm tra thời gian sửa đổi file (`st_mtime`) so với thời điểm hiện tại:
    ```python
    if summary_path and summary_path.is_file():
        # Chỉ chấp nhận file tạo trong vòng N giờ gần nhất (ví dụ: 3 giờ = 10800s)
        if time.time() - summary_path.stat().st_mtime > 10800:
            return {}
    ```
  - Trả về rỗng / unverified nếu file quá cũ thay vì parse dữ liệu cũ.

## 2. Top-Level Module Scope Ordering
Trong các script Python chạy automation dạng standalone hoặc import linh hoạt:
- **Biến môi trường / Đường dẫn gốc (`PROJECT_ROOT`)**: Phải được tính toán đầu tiên ngay sau import chuẩn (`os`, `sys`, `pathlib`). Tránh việc các khối tính đường dẫn phụ trợ (`GPM_SCRIPTS_DIR = ... os.path.dirname(PROJECT_ROOT) ...`) chạy trước khi `PROJECT_ROOT` được gán.
- **Bắt ngoại lệ tại top-level import**: Không gọi các hàm logger nội bộ (`log(...)`) khi logger chưa được định nghĩa hoặc chưa import xong. Dùng `sys.stderr.write(...)` để đảm bảo an toàn tuyệt đối.
