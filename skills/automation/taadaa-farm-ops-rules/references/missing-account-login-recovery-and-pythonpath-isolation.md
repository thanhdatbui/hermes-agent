# Kỷ luật xử lý thiếu nick trong ca nuôi & Subprocess Reconcile Isolation

## 1. Bản chất ca nuôi nick: Tự động Login lại ngay khi thiếu nick
- **Nguyên tắc**: Tới ca nuôi acc nào thì chỉ duy nhất acc đó được tương tác.
- Nếu nick mục tiêu không có trên máy (không có trong Account Switcher):
  - **BẮT BUỘC** gọi luồng đăng nhập lại (`reconcile_tiktok_accounts.py` / `_maybe_recover_missing_account_via_login`).
  - Tuyệt đối không tự bịa lý do liên can đến acc khác trên máy để dừng máy hoặc đổ thừa.
  - **CHỈ ĐƯỢC BÁO LỖI / BẮN CẢNH BÁO KHI ĐĂNG NHẬP THẤT BẠI THỰC SỰ** (sau khi đã thử login lại mà fail, verify không thành công).

## 2. Pitfall chí mạng: PYTHONPATH leak khi spawn Subprocess giữa các Python Venvs
- **Hiện tượng**:
  - `feed_swipe_smoke.py` chạy trên môi trường chính hoặc từ Hermes session (Python 3.11).
  - Khi gọi subprocess sang script login:
    `D:\Taadaa\python-envs\tiktok-reg-recovery\Scripts\python.exe D:\Taadaa\tiktok-log-in\scripts\reconcile_tiktok_accounts.py` (Python 3.12).
  - Tiến trình con kế thừa biến môi trường `PYTHONPATH` trỏ vào venv của Hermes (`.../hermes-agent/venv/Lib/site-packages`).
  - Hậu quả: Venv con load nhầm thư viện C-extension (`PIL/_imaging`) của Python 3.11 vào Python 3.12, gây crash ngầm:
    `ImportError: cannot import name '_imaging' from 'PIL'`.
  - Subprocess bị treo ôm lệnh chờ đợi, gây kẹt máy đúng trần timeout (trước đây là 900 giây / 15 phút) làm chết đứng cả ca nuôi.

- **Giải pháp bắt buộc (Subprocess Environment Cleansing)**:
  Trước khi gọi bất kỳ subprocess Python venv chéo nào, BẮT BUỘC phải strip sạch `PYTHONPATH`:
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
- **Timeout Discipline**: Luôn cấu hình timeout hợp lý (300s thay vì 900s) để tránh treo vô tận.

## 3. Account Switcher Display Name vs Handle ID (Slot Elimination)
- Khi TikTok hiển thị Display Name (`Trang Le`) thay vì Handle ID (`@thu.trangg584`):
  - Dùng thuật toán **Slot Elimination** loại trừ 7 nick đã biết của các ca khác trên cùng máy để xác định slot mục tiêu.
  - Sau khi switch vào profile, đối soát lại ID thật.
