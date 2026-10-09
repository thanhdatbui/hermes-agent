# Triage Hiện Trường DPAPI Journal & Phân Định Điểm Nghẽn Phase B (21/09/2026)

## 1. Cú pháp đọc & Inspect DPAPI Journal chuẩn

Thư mục mặc định: `C:\Users\Kibe\AppData\Local\codex_gmail_debug-tiktok-add-bao-mat-f2a\journals`

```python
import sys, os, glob
from pathlib import Path
sys.path.insert(0, 'D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner')
from core.journal import JournalStore

journal_dir = Path('C:/Users/Kibe/AppData/Local/codex_gmail_debug-tiktok-add-bao-mat-f2a/journals')
store = JournalStore(root=journal_dir)

# PITFALL QUAN TRỌNG: store.load() nhận account_id (64-char SHA256 hex), KHÔNG nhận full path hay filename!
# fname = "8f565bd0a024bbbf12275ba3b697d82230b9c723b88083a2affc5ee48393b148.dpapi"
account_id = fname[:-6]
record = store.load(account_id)
# record.machine, record.source_row, record.username_normalized, record.state, record.secret
```
*Lưu ý:* Nếu truyền cả đường dẫn file hoặc chuỗi không đúng 64 ký tự hex vào `store.load()`, hàm sẽ ném ngoại lệ `ValueError("invalid account hash")`.

---

## 2. Ma trận Trạng thái Journal (`PhaseBState`) & Vị trí Điểm Nghẽn

Theo quy trình chuẩn trong `core/phase_b_runner.py`:
```python
# 1. Bắt Secret Key
secret = operations.enable_and_capture_secret()
journal.create(..., secret=secret)  # -> State: CAPTURED

# 2. Chuyển sang OTP & Submit
operations.advance_to_otp()
operations.check_clock()
otp = generate_totp(secret)
journal.transition(account_id, PhaseBState.CAPTURED, PhaseBState.OTP_SUBMITTED)
operations.submit_otp(otp)

# 3. Xác nhận Authenticator ổn định trên thiết bị
operations.confirm_authenticator_stable()
journal.transition(account_id, PhaseBState.OTP_SUBMITTED, PhaseBState.AUTHENTICATOR_CONFIRMED)

# 4. Ghi Workbook
operations.write_workbook(record, secret)
journal.transition(account_id, PhaseBState.AUTHENTICATOR_CONFIRMED, PhaseBState.WRITTEN)

# 5. Tắt Email / Lưu pass
operations.disable_email_and_confirm_stable()
journal.transition(account_id, PhaseBState.WRITTEN, PhaseBState.EMAIL_DISABLED)
operations.ensure_password_saved()
journal.purge(account_id)
```

### Phân định vị trí nghẽn theo State:
1. **`CAPTURED`**:
   - Đã bắt được chuỗi secret, dừng tại `advance_to_otp()` (không tìm thấy nút "Tiếp tục" / "Next").
   - *Kiểm tra bẫy Samsung Launcher:* Kiểm tra độ dài và giá trị secret. Nếu secret là `GALAXYESSENTIALS` (len 16), đó là bẫy widget Samsung Launcher khi TikTok bị văng về Home. Cần purge journal này.
   - Nếu secret hợp lệ (Base32 32 ký tự): kẹt UI nút bấm chuyển bước OTP trên TikTok.

2. **`OTP_SUBMITTED`**:
   - Đã sinh TOTP từ secret và bấm gửi OTP vào TikTok.
   - Điểm nghẽn: Kẹt tại `operations.submit_otp(otp)` hoặc đang chờ xác nhận UI ổn định tại `operations.confirm_authenticator_stable()`.

3. **`AUTHENTICATOR_CONFIRMED`** *(Sự cố Phase 2 thất bại hàng loạt 21/09/2026)*:
   - **Thực tế:** TikTok trên điện thoại **ĐÃ BẬT 2FA THÀNH CÔNG VÀ ỔN ĐỊNH**!
   - Điểm nghẽn: Bị chặn ngay tại bước `operations.write_workbook(record, secret)` trước khi chuyển sang state `WRITTEN` (nguyên nhân thường do file Excel đang bị mở/lock bởi tiến trình khác, lỗi API sheet hoặc lệch tham số hàm ghi).
   - **Ý nghĩa an toàn:** Trạng thái `AUTHENTICATOR_CONFIRMED` nằm trong `RESUMABLE_STATES` của journal. Toàn bộ secret 32 ký tự hợp lệ đã được mã hóa an toàn trong DPAPI. Không cần chạy lại flow UI trên máy, chỉ cần chạy recovery backfill ghi secret từ journal vào cột E workbook.
