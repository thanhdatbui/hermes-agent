# Cron Deployment Drift & Preflight Auto-Reg Playbook

Tài liệu đúc kết từ sự cố Farm Alert Batch 80 máy (Row 6 trống 11 máy: `M11, M18, M19, M57, M62, M63, M69, M71, M74, M75, M80`) ngày 12/09/2026.

---

## I. CƠ CHẾ ON-DEMAND AUTO-REG BÙ TÀI KHOẢN THEO CA (`ensure_row_accounts.py`)

1. **Kiến trúc vận hành:**
   - Hệ thống Taadaa Phone Farm CÓ cơ chế tự động bù tài khoản theo ca trước khi chạy lướt feed.
   - Trong `tiktok_runner.py`, trước khi spawn `multi_machine_feed_session.py`, runner gọi hàm preflight:
     ```python
     _preflight_ensure_accounts(row)
     ```
   - Hàm này kích hoạt `python D:\Taadaa\tools\ensure_row_accounts.py <row>`.

2. **Các bước xử lý của `ensure_row_accounts.py`:**
   - **Bước 1 - Quét máy thiếu:** Đọc `taikhoan_run_safe.xlsx` ở Row chỉ định. Lọc ra các máy đang có giá trị trống (`expected_username is None`).
   - **Bước 2 - Kiểm tra kho mail:** So khớp với `gmail_clean_v2.xlsx`. Nếu máy nào chưa có mail hợp lệ, tự động gọi `buy_hotmail.py` để mua Hotmail OAuth2 và nạp vào máy.
   - **Bước 3 - Kích hoạt Reg TikTok:** Chạy `_run_all_targets.py` (trong `D:\Taadaa\Tiktok_Reg`) giới hạn riêng cho danh sách máy bị thiếu acc.
   - **Bước 4 - Merge & Đồng bộ:** Gọi `apply_deferred_tracking_results.py` nạp nick mới vào `taikhoan_dat_v2_updated .xlsx`, sau đó chạy `sync-safe-workbook.py` để xuất ra `taikhoan_run_safe.xlsx` mới nhất.

3. **Kỷ luật điều phối:**
   - CẤM TUYỆT ĐỐI võ đoán lý thuyết "hệ thống không tự reg vì sợ xung đột device_lock" khi chưa kiểm tra codebase và git log của runner.

---

## II. CRON DEPLOYMENT DRIFT TRAP (GIT REPO VS LIVE RUNTIME)

1. **Hiện tượng Stale Deploy:**
   - Mã nguồn phát triển & git track nằm tại: `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`.
   - Nhưng Hermes Cron runtime thực thi trực tiếp các script từ thư mục: `C:\Users\Kibe\AppData\Local\hermes\scripts\`.
   - Khi commit/pull mã nguồn mới trên `D:\Taadaa\Hermes` mà quên đồng bộ sang `AppData\Local\hermes\scripts\`, cron runner sẽ tiếp tục chạy code cũ (stale code), gây ra lỗi ngầm dù code đã được fix trên git.

2. **Quy trình kiểm tra O(1) khi nhận Batch Alert Cron:**
   - Khi có alert về lỗi runner hoặc cron (ví dụ: `script-blocker: account row X is empty`):
     1. Kiểm tra `git log -n 5` trên repo script (`D:\Taadaa\Hermes` hoặc repo liên quan) để xem các commit mới nhất.
     2. So sánh `diff` giữa file trên repo deploy và file trên live runtime:
        ```bash
        diff -u "D:/Taadaa/Hermes/deploy/hermes-home/scripts/<script>.py" "C:/Users/Kibe/AppData/Local/hermes/scripts/<script>.py"
        ```
     3. Nếu phát hiện lệch code: đồng bộ ngay và giải thích rõ nguyên nhân do stale runtime copy.

---

## III. PYTHON ENVIRONMENT TRAP TRONG CRON SCRIPTS

1. **Nguyên nhân:**
   - Hermes chạy bằng môi trường venv riêng (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\`). Môi trường này chỉ chứa dependencies của Hermes core, KHÔNG có `openpyxl`, `uiautomator2`, hay thư viện điều khiển farm.
   - Nếu script trong cron gọi subprocess bằng `sys.executable`, subprocess sẽ thừa hưởng Python của Hermes venv và crash ngay lập tức do thiếu module (`ModuleNotFoundError: No module named 'openpyxl'`), sau đó bị nuốt lỗi trong các khối `try...except`.

2. **Quy tắc bắt buộc:**
   - Mọi lệnh gọi subprocess trong cron scripts liên quan đến Farm BẮT BUỘC dùng helper phân giải Python chuyên dụng:
     ```python
     def target_python() -> str:
         p = Path(r"D:\Taadaa\python-envs\automation\Scripts\python.exe")
         return str(p) if p.is_file() else sys.executable
     ```
