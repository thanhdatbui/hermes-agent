# Target-Bound Differential Canary & Safe Probe Matrix Operations (2026-10-25)

## 1. Triết Lý Cốt Lõi: Sửa Đâu — Canary Nhắm Trúng Đó
- **Chống Canary Generic Bừa Bãi:** Tuyệt đối không chạy full-flow toàn diện khi chỉ sửa một khâu kỹ thuật cục bộ (như device lock, media push, switcher).
- **Phân Loại Diff Theo Matrix (`canary_matrix.json` + `canary_plan.py`):**
  - **Miễn trừ tự động (Exempt):** Diff chỉ nằm trong test, docs, markdown, example yaml $\to$ không bắt thiết bị thật chạy Canary.
  - **Khâu Điều Phối / Khóa Máy (`batch-dispatch-lock`):** Chỉ chạy hook kiểm tra JIT lock & launch plan trên 1 máy test; cấm đi sâu vào quy trình biến đổi tài khoản.
  - **Khâu Giao Diện / Chuyển Nick (`account-switcher`):** Chỉ mở app $\to$ kiểm tra danh sách tài khoản $\to$ OCR xác nhận $\to$ thoát về Home.
  - **Khâu Bảo Mật / OTP / Mật Khẩu (`phase-b-security-ui`):** Chỉ mở đến form nhập $\to$ dừng lại, cấm submit đổi pass/2FA thật làm hỏng dữ liệu tài khoản.
  - **Khâu Tải / Đẩy Media (`media-push-manager`):** Chỉ kiểm tra đẩy file vào thẻ nhớ $\to$ mở picker $\to$ xóa file mẫu và về Home.

## 2. Xử Lý Khi Farm Đang Trong Ca Nuôi (Safe Probe / Dry-Run)
- Khi farm đang chạy ca (sáng, trưa, chiều), các máy đều có lịch trình gắt gao. Cướp máy chạy canary sẽ làm văng phiên nuôi hoặc gây deadlock lock.
- **Cơ chế Safe Probe / Dry-Run:**
  - Khi không có máy rảnh hợp lệ (`find_candidate_canary_devices` trả về rỗng):
  - `canary_runner.py --dry-run` tự động chạy test suite tập trung của repo tương ứng (như `pytest python_runner/tests/test_run_batch_live_2fa.py`, `pytest tests/test_adapter.py`, `pytest tests/test_shared_core_usage.py`).
  - Khi 100% tests PASS, hệ thống ký biên nhận Canary hợp lệ (`.canary_receipt.json`), mở khóa an toàn cho `safe_push` mà không làm gián đoạn ca nuôi.

## 3. Danh Mục Repo Đã Được Chuẩn Hóa Routing
- `tiktok-follow`
- `tiktok-luot nuoi acc`
- `tiktok-add-bao-mat-f2a`
- `Tiktok-video`
- `tiktok-log-in`
- `Tiktok_Reg`
