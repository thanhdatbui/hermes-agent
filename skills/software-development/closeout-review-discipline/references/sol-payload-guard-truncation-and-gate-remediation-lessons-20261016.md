# Sol Payload Guard Truncation & Closeout Remediation Lessons (2026-10-16)

## 1. Cơ chế Truncation của sol_payload_guard (`SOL_TARGET_BYTES = 32768`)
- **Ngân sách Diff thực tế**: `split_budget(32768)` phân bổ `diff_b = int(32768 * 0.65) = 21,299 bytes (~20.8 KB)`.
- **Ngưỡng L0 vs L4 Truncation**:
  - Khi tổng diff của các file trong scope `> 21,299 bytes`, hệ thống tự động rơi vào `level=L4` và kích hoạt `TRUNCATION_MANIFEST`.
  - Sol Reviewer **tự động trừ điểm nặng** hoặc từ chối duyệt các đoạn code bị truncate: `"Phần bị lược KHÔNG được coi là đã review. Nếu cần xem để kết luận, trả về NEED_CONTEXT:<path>"`.
  - **Bài học cốt lõi**: Để đạt `level=L0 (omitted=[])`, tổng diff thô (`git diff`) của toàn bộ các file trong `--files` **bắt buộc phải <= 20,800 bytes (~20.3 KB)**.

## 2. Kỹ thuật nén Diff Test Suite chống phình Payload
- File test suite thường chiếm từ 50-60% dung lượng diff nếu viết dàn trải.
- **Biện pháp tinh gọn test**:
  1. Loại bỏ các test kiểm tra lại logic cơ bản đã được cover bởi integration test thật (ví dụ: test Win32 API trả 0.0, test helper độc lập).
  2. Gộp context manager: Dùng 1 khối `with patch(...)` chung cho nhiều assert thay vì lồng 4-5 tầng `with`.
  3. Sử dụng helper mock rút gọn (ví dụ `_proc(rc=0, out="", err="")`) thay vì khai báo `MagicMock` lặp đi lặp lại.
  4. Tránh các chuỗi assert dài dòng hoặc iterator trick phức tạp làm tăng số dòng diff vô ích.

## 3. Kiến trúc Fail-Closed 3 Trạng thái & Phòng thủ Race Condition
- **Fail-Closed Trạng thái**:
  - Hàm kiểm tra tiến trình `is_process_running()` khi gặp lỗi truy vấn (returncode != 0 hoặc exception) **bắt buộc trả về `True`** đối với logic đóng/hủy tiến trình (fail-safe không giết nhầm).
  - Đối với logic dọn dẹp tài nguyên phụ thuộc (`cleanup_orphan`), chỉ được chạy khi tiến trình chính **chắc chắn trả về `False`**. Nếu trả về `True` hoặc `None`, phải hủy dọn dẹp ngay.
- **Race Condition Guard 3 tầng**:
  - Tầng 1: Kiểm tra trước khi bắt đầu cleanup.
  - Tầng 2: Kiểm tra lại ngay trước khi thực thi `kill-server`.
  - Tầng 3: Kiểm tra lại trước khi gọi `CIM Terminate` (hoặc bọc lệnh kiểm tra nguyên tử trong cùng script PowerShell: `if (-not (Get-Process ...)) { ... }`).

## 4. Single Responsibility cho Concurrency Lock
- **Cấm gộp chung Lock (Lock Abuse)**:
  - `_METRICS_LOCK` chỉ chuyên trách bảo vệ dữ liệu đếm metric (`WATCHDOG_METRICS`).
  - `_CACHE_LOCK` phải được khai báo riêng biệt để bảo vệ cache trạng thái tiến trình (`_PROCESS_RUNNING_CACHE`).
  - Gộp chung một lock cho cả telemetry và nghiệp vụ logic là code smell bị Reviewer trừ điểm kiến trúc.

## 5. Chuẩn PEP 257 & Shebang Placement
- **Thứ tự bắt buộc ở đầu script Python thực thi**:
  1. Dòng 1: `#!/usr/bin/env python3` (Shebang tuyệt đối ở dòng 1 để cron/Linux có thể thực thi trực tiếp `./script.py`).
  2. Dòng 2 trở đi: Module Docstring `"""..."""`.
  3. Dòng tiếp theo: `from __future__ import annotations` và các import khác.
  - Đặt `from __future__ import annotations` trước shebang làm hỏng shebang trên Unix; đặt trước docstring làm hỏng `__doc__` của module theo chuẩn PEP 257.

## 6. Vận hành Farm: Emergency Kill-Switch (Dry-Run Mode)
- Mọi watchdog can thiệp tiến trình farm bắt buộc hỗ trợ cờ biến môi trường dry-run (ví dụ `WATCHDOG_DRY_RUN=1`).
- Khi bật dry-run, script ghi nhận event cảnh báo `DRY_RUN_ENABLED` và thoát ngay ở đầu `main()`, không can thiệp hệ thống. Điều này cho phép operator vô hiệu hóa khẩn cấp trên 80-280 máy mà không cần sửa code.
