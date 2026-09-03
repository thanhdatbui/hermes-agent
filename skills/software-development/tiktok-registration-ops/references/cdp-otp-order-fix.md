# CDP OTP order fix (Outlook DOM)

## Triệu chứng
Máy Hotmail/Outlook reg TikTok FAILED với `OTP_REJECTED_AFTER_FRESH_RETRY` — TikTok reject mã 2 lần (lần đầu + sau resend). Log:
```
[otp-cdp] Fresh Outlook code found in background tab: [REDACTED]
[otp-enter] Quay lại TikTok, nhập OTP: [REDACTED]
[otp-enter] TikTok rejected or expired the submitted email OTP
```

## Root cause
`_try_get_otp_outlook_cdp()` trong `social_reg_v1.py` quét DOM Outlook tab nền qua CDP,
thu candidates là các số 6 chữ số trong node text chứa "tiktok", rồi:
```python
for code in reversed(candidates):   # BUG: giả định mail mới nhất NẰM CUỐI conversation
```
**Thực tế (probe máy 57, 2026-08-11):** Outlook DOM liệt kê mail TikTok **MỚI NHẤT TRƯỚC, cũ sau**:
```
310726 | T TikTok 1:07 AM ... 310726 là mã TikTok của bạn   <- mới nhất
630427 | T TikTok 1:05 AM ... 630427 là mã TikTok của bạn   <- cũ
```
`reversed()` lấy `630427` (mail 1:05 cũ) → TikTok reject vì mã cũ/expired.

## Fix
```python
for code in candidates:   # lấy candidate ĐẦU = mail mới nhất
    if re.fullmatch(r"\d{6}", code):
        return code
```
Kèm sửa comment JS trong expression: "DOM liệt kê mail mới nhất trước".

## Chẩn đoán (probe thực tế, không đoán)
Dùng `scripts/probe_cdp_otp.py` để in DOM Outlook hiện tại:
```
adb forward tcp:9224 localabstract:chrome_devtools_remote
GET http://127.0.0.1:9224/json → tìm tab outlook.live.com/mail
_evaluate JS quét node chứa /tiktok/i, regex (\d{6}), trả {code, sample}
```
Thấy thứ tự thật của mail (timestamp AM/PM) rồi mới sửa hướng scan.

## Lưu ý
- `websocket` (pip package) KHÔNG có sẵn — dùng `_cdp_evaluate()` của chính `social_reg_v1.py` (import module, nó tự implement websocket handshake).
- Sau fix, máy 30 qua được OTP (không còn reject) — chứng minh đúng hướng.
- "reader returned a previously rejected code; refusing reuse" = CDP trả mã cũ đã reject — dấu hiệu vẫn còn lấy nhầm thứ tự hoặc mail mới chưa về.
