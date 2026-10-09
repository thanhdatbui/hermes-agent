# Case REG-14: False-Positive "Đã Có Tài Khoản TikTok" do Timeout Loading & Mở Rộng 8 Hàng Master Sheet (2026-09-13)

## 1. Bối cảnh sự cố
- Ca 0h ngày 13/09/2026 (ngày lẻ, Row 7): 58/80 máy thiếu account. Preflight `ensure_row_accounts.py`
  tự kích hoạt batch reg bù capped 20 máy lúc 00:05.
- Đợt 00:05 chỉ 2 máy thành công (M77 `@tunam03041`, M78 `@ohongthinh1126`); 9 máy báo lỗi:
  `RuntimeError: [07] Tat ca 1 email cua STT X da co TK TikTok`.
- User hỏi: "Ủa các mail đã sử dụng tại sao còn đem đi reg? Có 1 đống mail reg rồi mà không ghi info lại?"
- Bằng chứng đối chứng: đợt 01:22 cùng các email đó reg thành công 100% tài khoản mới
  (M1 `@beheo5746`, M2 `@maixinh075`, M8, M10, M12, M14, M15, M16, M17, M26, M29).

## 2. Nguyên nhân gốc rễ (Anti-Pattern)

### A. Timeout loading bị kết luận sai thành "đã có tài khoản"
1. Sau khi gõ email và bấm "Tiếp tục", mạng/TikTok lag, màn hình đứng yên ở form email.
2. `detect_after_continue(device_id, timeout=12)` trả `unknown` -> nhánh fallback:
   - kiểm tra lỗi mạng qua status-bar / flat XML: không thấy hint
   - secondary scan OTP/new/registered hints: không thấy -> `had_timeout_error` phải bật (trước fix thì không có cờ này)
   - bấm BACK, `continue` sang email tiếp theo, hết candidates.
3. Code cũ ở cuối `fill_email_and_next()`:
   ```python
   if had_form_error: raise ...
   if had_network_error: raise ...
   raise RuntimeError(f"[07] Tat ca {len(candidates)} email cua STT {stt} da co TK TikTok")
   ```
   -> mọi trường hợp còn lại (bao gồm timeout loading thực sự) đều rơi vào lỗi mặc định
   "đã có TK TikTok". Coordinator/user tưởng nhầm mail mới là mail cũ đã reg.

### B. Master sheet thiếu hàng vật lý Row 7/8
- 76 máy (1..75, 80) có đủ 8 hàng; riêng M76/M77/M78/M79 chỉ có 6 hàng (Row 1..6).
- `apply_results(row=7)` không map được slot thứ 7 -> 2 acc reg thành công (M77, M78) không ghi được vào master.

## 3. Fix đã áp dụng (Case REG-14, đã commit push `Tiktok_Reg` main)

### social_reg_v1.py — fill_email_and_next()
```python
had_network_error = False
had_form_error = False
had_timeout_error = False   # NEW
```
Nhánh unknown/timeout fallback:
```python
log(f"   → {em}: khong xac dinh (timeout loading), thu tiep theo")
had_timeout_error = True
```
Chốt chặn trước lỗi mặc định:
```python
if had_form_error: raise RuntimeError(...form validation...)
if had_network_error: raise RuntimeError(...'Khong co ket noi Internet'...)
if had_timeout_error:
    raise RuntimeError(f"[07] Khong the xac dinh trang thai email cho STT {stt} do timeout/mang cham khi bam Tiep tuc ('{em}')")
raise RuntimeError(f"[07] Tat ca {len(candidates)} email cua STT {stt} da co TK TikTok")
```
- Quy tắc: chỉ khi XML thực sự có `reg_fallback` ("da co tai khoan", "nhap mat khau")
  hoặc EditText password field mới được kết luận "đã có TikTok".

### Master sheet expansion (640 rows = 80 máy x 8 slots)
- M76: Slot7 Folder 608, Slot8 Folder 602, serial `9885b64d56305a3731`
- M77: Slot7 Folder 615 `@tunam03041`, Slot8 Folder 616, serial `ce05160595e7953b04`
- M78: Slot7 Folder 623 `@ohongthinh1126`, Slot8 Folder 624, serial `ce0916090a9d320a01`
- M79: Slot7 Folder 631, Slot8 Folder 632, serial `ce0516059d279f3e03`
- Sau đó: nạp 11 acc đợt 01:22 vào đúng `tracking_row` của từng máy + `sync-safe-workbook.py`
  (--source master --output safe). Row 7: 22 -> 35/80 máy.

## 4. Pitfalls cho lần sau
- Đừng tin chữ "da co TK TikTok" surface-level: luôn đọc `stdout.log` nhánh `[7]` + XML
  `fail_*_unknown_fallback_*` để phân biệt timeout-loading vs registered thật.
- Khi thấy 5+ máy cùng báo "đã có TK" trong 1 batch mà mail là lô mới mua -> nghi ngờ timeout/mạng trước,
  kiểm tra `detect timeout: unknown` trong log trước khi kết luận mail cũ.
- Trước mọi batch reg bù cho Row N: verify master sheet mỗi máy có đủ N hàng vật lý
  (read-only openpyxl count), thiếu -> chèn hàng trước rồi mới chạy reg/apply.
- `tracking_row`/`tik` trong JSON do `apply_results` enforce từ master; JSON cũ (trống) phải
  được cập nhật sau khi chèn hàng, nếu không `apply_deferred_tracking_results` ghi sai hàng.
