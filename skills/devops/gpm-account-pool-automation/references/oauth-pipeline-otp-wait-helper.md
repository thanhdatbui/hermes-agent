# wait_for_otp_or_code Architecture & Contract

## Background
Trong pipeline OAuth (`scripts/run_oauth_s7_pipeline.py`), khi gặp challenge SMS / OTP và alert Telegram được bắn ra, hệ thống bước vào vòng chờ nhận mã từ user (qua file `otp_code.txt`) hoặc bắt được Authorization Code nếu user tự thao tác trên browser hoặc màn hình thiết bị (`captured_code`).

Trước đây, logic này nằm trực tiếp dạng vòng lặp lồng trong `process_account`, gây khó khăn cho việc viết unit test độc lập và tạo ra duplication khi cần tái sử dụng.

## Signature & Interface
```python
def wait_for_otp_or_code(mid: int, otp_file: str, waiting_file: str, get_captured_code, timeout: int = 180):
    """
    Chờ nhận OTP từ otp_file hoặc nhận captured_code từ callback `get_captured_code()`.
    Trả về: (captured_code, otp_code)
    - Nếu captured_code xuất hiện: trả về (captured_code, None) và tự động dọn dẹp otp_file, waiting_file.
    - Nếu otp_file có 6 chữ số: trả về (None, otp_code).
    - Nếu hết timeout: trả về (None, None).
    """
```

## Caller Invariant Trong `process_account`
Thay vì để vòng lặp inline, caller gọi:
```python
captured_code_res, otp_code = wait_for_otp_or_code(
    mid, otp_file, waiting_file, lambda: captured_code, timeout=180
)
if captured_code_res:
    continue
elif otp_code:
    sms_code_inp.fill(otp_code)
    time.sleep(1)
    page.keyboard.press("Enter")
    try:
        if os.path.exists(otp_file): os.remove(otp_file)
        if os.path.exists(waiting_file): os.remove(waiting_file)
    except Exception:
        pass
    time.sleep(4)
    continue
```

## Testing Protocol
- Không test simulation loop qua sleep giả lập mà import trực tiếp `wait_for_otp_or_code` từ `scripts.run_oauth_s7_pipeline`.
- Test cả 2 nhánh:
  1. `get_captured_code()` trả về code -> kiểm tra early break, cleanup file chờ.
  2. `otp_file` có OTP 6 chữ số hợp lệ -> kiểm tra parsed code chính xác.
- Khi chạy pytest trong repo `GPM auto`, luôn bảo đảm `PYTHONPATH=.` (hoặc `python -m pytest tests`) để tránh lỗi `ModuleNotFoundError: No module named 'src'`.
