# Bẫy Ngộ Nhận Gmail DIE Giả Do Thừa Hưởng PYTHONPATH Gây Lỗi Greenlet / Playwright

## 1. Hiện Tượng (Symptom)
- Khi gọi `python D:/Taadaa/tools/recover_missing_tiktok_login.py --machine 3 --account annhubvqttr` hoặc `tiktok_login_v1.py 3 --email annhubvqttr`, tiến trình thoát ngay lập tức với Return Code = 2 (`RC: 2`).
- Trong log ghi nhận:
  ```text
  [login] account issues: missing_tiktok_pass
  [gmail-live] checker returned DIE for an.nhuan.work64541@gmail.com -> BLOCK
  [login] Gmail live gate blocked an.nhuan.work64541@gmail.com; no UI action will be attempted
  PENDING LOGIN: an.nhuan.work64541@gmail.com
  ```
- Tuy nhiên, khi kiểm tra độc lập thực tế, tài khoản Gmail này hoàn toàn đang hoạt động bình thường (LIVE).

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Thiết kế Fail-Closed của `_gmail_live_gate`**:
   Trong `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py`:
   ```python
   try:
       from check_gmail_live_fast import check_gmail_is_live
   except ImportError:
       try:
           ...
           _check_gmail_module = importlib.util.module_from_spec(_check_gmail_spec)
           _check_gmail_spec.loader.exec_module(_check_gmail_module)
           check_gmail_is_live = _check_gmail_module.check_gmail_is_live
       except Exception:
           def check_gmail_is_live(email):
               return False  # <--- FALLBACK DIE KHI CÓ EXCEPTION
   ```
2. **Nhiễm bẩn môi trường qua biến `PYTHONPATH`**:
   - Khi `recover_missing_tiktok_login.py` hoặc runner được kích hoạt từ tiến trình cha (Agent/Coordinator CLI/Gateway), biến môi trường `PYTHONPATH` được tự động kế thừa và trỏ về `site-packages` của tiến trình cha.
   - Trong `check_gmail_live_fast.py`, dòng `from playwright.sync_api import sync_playwright` nạp module `greenlet`. Do `site-packages` của môi trường cha bị thiếu hoặc xung đột binary C-extension, Python ném ra:
     ```text
     ModuleNotFoundError: No module named 'greenlet._greenlet'
     ```
   - Khối `except Exception` bên ngoài bắt ngoại lệ này và định nghĩa `check_gmail_is_live` luôn trả về `False` (tương đương kết luận tài khoản đã `DIE`).
   - Vì tài khoản TikTok không có mật khẩu tĩnh (`missing_tiktok_pass`), script từ chối thực hiện mọi thao tác UI để tránh checkpoint trên mail chết, dẫn đến toàn bộ quy trình nạp nick bị tê liệt.

## 3. Giải Pháp Khắc Phục Chuẩn (Standard Fix)
1. **Tách lập môi trường trong caller / runner**:
   Trong `D:/Taadaa/tools/recover_missing_tiktok_login.py` (và mọi script điều phối subprocess):
   ```python
   env = os.environ.copy()
   env.pop("PYTHONPATH", None)  # BẮT BUỘC: Khử ô nhiễm PYTHONPATH từ process cha
   env["PYTHONUNBUFFERED"] = "1"
   env["PYTHONUTF8"] = "1"
   ```
2. **Kiểm tra độc lập**:
   Khi chạy với môi trường sạch, `check_gmail_live_fast.py` sử dụng đúng `playwright` của virtualenv `automation` (`D:\Taadaa\python-envs\automation\Scripts\python.exe`) và trả về kết quả chính xác:
   ```text
   Result for an.nhuan.work64541@gmail.com: LIVE (RC: 0)
   ```
