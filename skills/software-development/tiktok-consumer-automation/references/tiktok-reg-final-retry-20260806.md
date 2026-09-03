# Tiktok_Reg retry cuối (2026-08-06) — blocker nghiệp vụ sau khi hết bug code

## Bối cảnh

Sau 3 vòng fix code (draft-dialog, mail-die guard ALIVE/UNKNOWN/BLOCKED, OTP
marker-node, swipe refresh + Chrome foreground, hotmail recovery wrapper,
BLOCKED-mail guard), chạy retry 31/34/54/57/66 → **5/5 FINAL_BLOCKED**, 0
success mới. Nhưng mọi signature giờ là blocker **nghiệp vụ/môi trường** —
bằng chứng fix hoạt động đầy đủ trong run thật:

- STT 54: `[7c] Hotmail inbox status=BLOCKED; giữ mail, không cleanup` — BLOCKED
  guard hoạt động (trước đây mail bị xóa 2 lần).
- STT 66: `giữ mail (status=ALIVE)` + lấy được code MỚI (`Fresh code found in
  preview`) + swipe refresh chạy (`đã vuốt refresh Outlook inbox`).
- STT 30 đã SUCCESS từ run trước (draft-dialog fix live-proven).

## Phân loại blocker còn lại

### 1. TikTok reject OTP dù code ĐÚNG và MỚI (STT 57/66)

Log: `[otp-browser] Fresh code found in preview` → `[otp-enter] type <code>` →
`OTP screen still visible after bounded submit verification` → reject. Code
không phải cũ (lấy được code mới) nhưng TikTok vẫn từ chối. Nguyên nhân:
**TikTok chặn device/IP fingerprint** — máy reg quá nhiều lần cùng proxy trong
ngày. Retry thêm cùng proxy = kết quả giống nhau. Hướng: đổi proxy/fingerprint
cho 2 máy rồi mới retry; không retry code.

### 2. CDP sau swipe vẫn trả code cũ (`refusing reuse`) (STT 57/66)

Sau swipe refresh + đọc lại CDP vẫn trả code cũ. Không phải bug swipe (đã
verify swipe chạy: `[otp-refresh] đã vuốt refresh Outlook inbox; đọc lại code
mới`). Lý do thật: **mail TikTok mới chưa tới inbox** trong cửa sổ chờ — CDP
reload tab cũ không đủ, Outlook cần thời gian nhận mail mới. Khi code mới
chưa tới, CDP trả đúng code cũ duy nhất nó thấy. Hướng: chờ lâu hơn hoặc đổi
proxy (nếu mail chậm do proxy). Mail vẫn ALIVE → giữ (guard đúng).

### 3. Gmail `target_account_unverified` dù account CÓ trong AccountManager (STT 31/34)

Account `macthuong1905200031@gmail.com` / `truongthuy111034@gmail.com` đều CÓ
trong `dumpsys account`, nhưng Gmail app không verify được — Gmail đang hiện
**account khác** (multi-account trên máy), account switcher trong Gmail không
chọn đúng target. Hướng: dọn account thừa trên Gmail app / chọn đúng account
trước retry. Đây là trạng thái máy, không phải code.

### 4. `RECOVERY_OTP_SCREEN_NOT_IDENTIFIED` (STT 54)

`recover_account` (repo Hotmail) chạy khi gặp Protect account nhưng không nhận
diện được màn hình OTP recovery trên máy 54. Flow recovery-email trong repo
Hotmail chưa cover UI variant máy này. Hướng: xử lý thủ công màn hình Protect
hoặc cấp mail mới. Mail giữ (BLOCKED guard đúng).

### 5. `[otp-enter] TikTok OTP screen unavailable after Recents recovery` (STT 34)

Máy rời khỏi OTP screen giữa recovery (Recents) → không nhập được. Hướng:
retry khi máy về đúng surface (SignUpOrLoginActivity).

## Kết luận / rule

Khi đã hết bug code (guard + test + live-proven):
1. Đọc từng signature blocker — phân loại nghiệp vụ (proxy/fingerprint) vs
   trạng thái máy (multi-account Gmail, surface kẹt) vs code còn thiếu.
2. KHÔNG retry mù cùng signature ≥2 lần — đổi proxy, dọn máy, hoặc xử lý thủ
   công tùy loại.
3. Mail bị xóa nhầm (trước guard): restore từ backup + xóa Audit Pending
   (pattern `scripts/restore_sttXX_source.py` / `remove_audit_sttXX.py`).
4. Kiểm tra trạng thái mail cuối: source workbook phản ánh đúng — mail sống
   CÓ, mail CAPTCHA-confirmed die KHÔNG CÓ.
