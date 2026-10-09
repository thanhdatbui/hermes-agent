# Quy Tắc Bắt Buộc Khi Thiếu Nick Trong Ca Nuôi (Auto-Login Recovery)

*(User chốt chỉ đạo nghiêm ngặt ngày 2026-09-19)*

## 1. Nguyên Tắc Cốt Lõi
- **TỚI CA NUÔI KHÔNG CÓ ACC TRÊN MÁY: BẮT BUỘC CHẠY TỰ ĐỘNG LOGIN LẠI NICK ĐÓ**.
- Ca nuôi chỉ tương tác với duy nhất nick được chỉ định của ca đó, KHÔNG LIÊN QUAN gì tới các nick khác đang có trên máy.
- CẤM TUYỆT ĐỐI tự ý suy diễn hoặc viện cớ "dừng an toàn né login", "sợ ảnh hưởng nick khác" để dừng báo `manual-needed` ngay từ Switcher.
- **CHỈ KHI NÀO LUỒNG TỰ ĐỘNG LOGIN CHẠY XONG VÀ BÁO THẤT BẠI MỚI ĐƯỢC PHÉP BÁO MANUAL-NEEDED / FARM ALERT!**

## 2. Bẫy Kỹ Thuật Khi Gọi Subprocess Reconcile Login (`_maybe_recover_missing_account_via_login`)
- **Triệu chứng:** Máy thiếu nick bị treo đơ đúng 15 phút (900 giây) rồi mới văng lỗi `timed out after 900.0 seconds`.
- **Nguyên nhân gốc rễ:** 
  - Subprocess gọi script login (`D:\Taadaa\python-envs\tiktok-reg-recovery\Scripts\python.exe D:\Taadaa\tiktok-log-in\scripts\reconcile_tiktok_accounts.py`).
  - Môi trường kế thừa biến `PYTHONPATH` trỏ vào venv của `hermes-agent` (`Python 3.11 site-packages`).
  - Python 3.12 của venv `tiktok-reg-recovery` load nhầm module C-extension của `PIL` (`_imaging`) từ Python 3.11 $\rightarrow$ văng `ImportError: cannot import name '_imaging' from 'PIL'`.
  - Quá trình bị kẹt ở subprocess không trả về kịp, ôm trọn 900s timeout làm tê liệt ca nuôi.

## 3. Cách Khắc Phục Chuẩn
Trước khi gọi `subprocess.run(cmd)` trong `_maybe_recover_missing_account_via_login`:
```python
clean_env = dict(os.environ)
clean_env.pop("PYTHONPATH", None)
proc = subprocess.run(
    cmd,
    env=clean_env,
    capture_output=True,
    text=True,
    timeout=timeout_sec,
)
```
Tẩy sạch `PYTHONPATH` giúp script login chạy bằng đúng môi trường độc lập của nó, nạp tài khoản và khởi động ngay lập tức mà không bị xung đột thư viện.
