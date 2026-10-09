# OVERRIDE_PASSWORD — Bypass mật khẩu từ env cho run_oauth_s7_pipeline.py

## Mục đích
Override password của một account cụ thể mà không cần sửa DB, Excel, hay creds source.
Hữu ích khi password trong DB sai hoặc chưa cập nhật mà cần chạy thử ngay.

## Cách dùng

```bash
OVERRIDE_PASSWORD="n0spam@@" python "scripts/run_oauth_s7_pipeline.py" <email>
```

## Pattern code đã được áp dụng (line ~725)

```python
# TRƯỚC:
password = creds.get("password") or acc.get("password", "")

# SAU (patch đã apply):
password = os.environ.get("OVERRIDE_PASSWORD") or creds.get("password") or acc.get("password", "")
```

Priority chain: `OVERRIDE_PASSWORD` env → DB creds → acc dict fallback.
`import os` đã có sẵn ở đầu file (line 1) — không cần thêm import.

## Vị trí trong code
File: `D:/Taadaa/GPM auto/scripts/run_oauth_s7_pipeline.py`
Line: ~725 (sau `creds = get_creds(email)`)

## TIMEOUT sau patch — chẩn đoán

Nếu vẫn timeout với lặp "Điền mật khẩu cho <email>..." mỗi 5 giây:

1. **CAPTCHA block** — reCAPTCHA bframe detached trước khi đến password field. Password field không visible nên loop chờ mãi.
2. **Password sai** — field visible nhưng Google reject, redirect về.
3. **Profile bị lock** — GPM profile trước đó có session xấu.

**Check debug screenshot:**
```
D:/Taadaa/GPM auto/debug_screenshots/oauth_<email>_timeout_<timestamp>.png
```
Screenshot chụp tại thời điểm timeout — nhìn vào đó để biết Google đang hiện màn hình gì.

## Ví dụ chạy thực tế (Sep 21 2026)

- Email: `aliciaifrazier9vl5d@gmail.com`
- Password override: `n0spam@@`
- Kết quả: FAILED (TIMEOUT) — reCAPTCHA audio challenge bị detach trước đó, password field không load được. Không phải lỗi của patch.
- Profile tìm thấy OK: `DQEgnFdnIz-17092026` (M08 port 20008)
