# Gmail OTP App Flow: Skip Account Switcher When Target Already Selected

## Triệu chứng
Trong luồng lấy OTP qua ứng dụng Gmail (`_try_get_otp_gmail_app` trong `social_reg_v1.py`), runner luôn thực hiện tap avatar để mở panel chuyển đổi tài khoản (Account Switcher), ngay cả khi tài khoản Gmail đích đã là tài khoản đang hiển thị hiện tại trong ứng dụng.
Hậu quả:
- Mất thêm 10-30s cho các bước mở panel, retry tìm kiếm account, hoặc xử lý nút "Chuyển đổi tài khoản" bị thu gọn.
- Dễ chạm trúng các lỗi phụ: tap nhầm vào dòng tài khoản active gây mở cài đặt Google Account, match nhầm vào thông báo bảo mật nền, hoặc timeout CLI (300s) / OTP timeout (150s).

## Nguyên nhân gốc rễ
Hàm `_try_get_otp_gmail_app` sau khi mở Gmail chỉ kiểm tra sơ bộ inbox mà không kiểm tra xem tài khoản đang active trong mailbox đã đúng là `email` đích chưa trước khi gọi tap avatar.
Trong khi đó, hàm helper `_gmail_mailbox_state(xml, email)` đã có sẵn cờ `target_selected` để nhận diện xem tài khoản hiện tại có khớp với `email` hay không.

## Giải pháp chuẩn
Trước khi thực hiện tap avatar mở switcher:
```python
    current_state = _gmail_mailbox_state(xml, email)
    if current_state.get("target_selected"):
        log(f"   [otp-gmail] {email} đã là tài khoản hiện tại trong Gmail -> bỏ qua mở switcher")
        xml_mailbox = xml
    else:
        # Chỉ tap avatar và mở switcher khi target chưa được active
        ...
        xml_mailbox = _ensure_gmail_mailbox("after account switcher", save_proof=True)
        if not xml_mailbox:
            return None
```
Khi `target_selected` là `True`, bỏ qua hoàn toàn bước mở avatar, tận dụng luôn `xml` mailbox hiện tại để đi thẳng vào kiểm tra tab Promotions hoặc kéo refresh lấy mã OTP.
