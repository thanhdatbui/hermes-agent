# TikTok Password Preservation & Tracking Audit

## 1. Căn nguyên lỗi "Sai pass TikTok" sau khi reg bù / login OTP (Case M53)
- **Hiện tượng**: Tài khoản TikTok đã đăng ký thành công trước đó (ví dụ: `@mgpovhrgnnq`), nhưng sau này runner đăng nhập lại bị TikTok báo đỏ: *"Mật khẩu sai"*.
- **Root Cause phát hiện từ Artifact Tracing**:
  - Tại lần reg đầu tiên (`20260826-075147` lúc 08:13:30): Màn hình đăng ký yêu cầu nhập pass -> script sinh pass `kNXM@jTwq6e#` và tạo nick thành công. Pass thật trên TikTok server là `kNXM@jTwq6e#`.
  - Tại lần quét sau (`20260826-103903` lúc 10:51:02): Hệ thống nhập lại mail, TikTok chuyển thẳng sang OTP login (không qua form nhập pass). Script đọc OTP qua Graph API vào nick thành công.
  - **Bug ghi đè pass ảo**: Vì không có màn nhập pass (`tiktok_pw = ""`), code cũ có dòng fallback:
    `tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")`
    Dòng này tự sinh pass ngẫu nhiên mới (`xg2L&O74Zo&$s*o`) và lưu vào `tracking_result_*.json`, sau đó ghi đè thẳng vào Excel -> mất pass thật ban đầu!

---

## 2. Password Preservation Invariant (Bảo Toàn Mật Khẩu TikTok)
Bất kỳ script ghi nhận kết quả (deferred hoặc direct tracking write) đều phải tuân thủ 3 nguyên tắc:

### Quy tắc 1: Bảo toàn existing_pass trong Deferred Tracking Writer
Trong `scripts/deferred_tracking_writer.py` (hàm `apply_deferred_result`):
```python
# BẮT BUỘC giữ lại existing_pass nếu result["password"] rỗng/None (flow OTP/magic-link)
resolved_pass = result.get("password") or existing_pass or None
values = [
    int(result["stt"]),
    check.tik,
    result.get("tiktok_id") or "",
    resolved_pass,
    result.get("twofa") or None,
    result.get("email") or "",
    ...
]
```

### Quy tắc 2: Bảo toàn tracking pass trong Direct Writer
Trong `social_reg_v1.py` (`ensure_profile_completed_and_track` và `upsert_tracking_account`):
- Khi flow không nhập mật khẩu mới (`tiktok_pw` rỗng), BẮT BUỘC đọc lại mật khẩu cũ từ tracking workbook qua `get_tracking_account_meta(email)`.
- Trước khi ghi `ws.cell(target_row, 4)`: nếu `tiktok_pw` rỗng nhưng `ws.cell(target_row, 4)` đã có giá trị, giữ nguyên giá trị cũ.

### Quy tắc 3: Cấm sinh pass ngẫu nhiên khi tài khoản đã tồn tại
Trong Bước 8 của `social_reg_v1.py`:
- Khi `detect_after_continue == "registered"`: CẤM TUYỆT ĐỐI gọi `make_tiktok_password()` bốc pass ngẫu nhiên. Nếu tracking chưa có pass thì để rỗng để xử lý qua OTP/Reset, tuyệt đối không tạo pass ảo.

---

## 3. Quy trình Trace Artifact tìm lại mật khẩu gốc
Khi gặp tài khoản báo sai mật khẩu TikTok:
1. **Tìm file tracking JSON lịch sử**:
   Quét trong: `D:\Taadaa\runtime\<cluster>\artifacts\runs\social-batch-all\*\batch_*\stt_<STT>\tracking_result_stt<STT>_<email>.json`.
2. **So khớp các mốc thời gian**:
   - Mốc sớm nhất (lần đầu tiên có `proof_screenshot` tạo nick) thường chứa mật khẩu thật lúc submit form đăng ký ban đầu.
   - Thử đăng nhập lại bằng mật khẩu gốc này trước khi phải thực hiện Reset password tốn thời gian.
