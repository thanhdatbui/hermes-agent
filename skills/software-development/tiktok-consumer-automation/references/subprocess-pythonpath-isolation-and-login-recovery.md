# Subprocess Python Venv Isolation & Auto-Login Recovery

## 1. Nguyên tắc cốt lõi: Tới ca nuôi acc nào thì tương tác acc đó
- Khi mở Account Switcher mà không thấy nick mục tiêu:
  - BẮT BUỘC gọi tiến trình login lại (`_maybe_recover_missing_account_via_login` -> `reconcile_tiktok_accounts.py`).
  - Không viện cớ ảnh hưởng nick khác để dừng máy báo `manual-needed` sớm.
  - **CHỈ ĐƯỢC BÁO LỖI / BẮN ALERT KHI ĐĂNG NHẬP THẬT SỰ THẤT BẠI**.

## 2. Pitfall chí mạng: PYTHONPATH Leak gây Crash C-Extensions & Treo Subprocess
- **Hiện tượng**:
  - Script cha chạy từ một môi trường Python (ví dụ Python 3.11 của Hermes hoặc main runner).
  - Khi spawn subprocess gọi script login chạy venv khác (ví dụ `tiktok-reg-recovery` dùng Python 3.12).
  - Biến môi trường `PYTHONPATH` bị leak kế thừa sang venv con.
  - Python 3.12 load nhầm package `PIL` (Pillow) của Python 3.11 -> văng lỗi `ImportError: cannot import name '_imaging' from 'PIL'`.
  - `subprocess.run` bị kẹt chờ đợi cho đến khi chạm trần timeout (mặc định cũ là 900s / 15 phút), làm cả máy bị treo chết đứng suốt ca.

- **Giải pháp bắt buộc**:
  Luôn tẩy sạch `PYTHONPATH` trước khi gọi `subprocess.run`:
  ```python
  clean_env = dict(os.environ)
  clean_env.pop("PYTHONPATH", None)
  proc = subprocess.run(
      cmd,
      capture_output=True,
      text=True,
      env=clean_env,
      timeout=timeout_sec,
  )
  ```
- Hạ trần `reconcile_timeout_seconds` xuống mức an toàn (ví dụ 300s).
