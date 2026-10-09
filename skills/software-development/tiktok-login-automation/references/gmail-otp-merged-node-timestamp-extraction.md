# Gmail OTP Preview List: Merged-Node Timestamp Extraction Pitfall

## Triệu chứng
Khi TikTok gửi mã xác minh email (6 chữ số) đến tài khoản Gmail, app Gmail trên thiết bị đã nhận được thư và hiển thị ngay trên màn hình danh sách thư (`ConversationListActivityGmail`), nhưng runner vẫn không lấy mã, liên tục báo:
```text
[otp-gmail] Bo qua code preview cu <OTP_CODE> (timestamp='')
```
Sau đó tiếp tục refresh / search trong vô vọng cho đến khi timeout (`BLOCKED_GMAIL_OTP_TIMEOUT`).

## Nguyên nhân gốc rễ
Trong `social_reg_v1.py`, hàm `extract_recent_tiktok_otp_from_gmail_list` trích xuất thông tin từng thư từ XML:
- Logic cũ giả định layout Gmail chia nhỏ hàng thư thành nhiều node riêng biệt: node text nội dung và node timestamp nằm ở góc phải (`nearby["coord"][0] >= 780`, `len(nearby["text"]) <= 16`).
- Trên nhiều phiên bản Gmail của máy farm (Samsung Galaxy S7), toàn bộ hàng thư được render thành **1 node duy nhất**, gộp cả trạng thái đọc, người gửi, tiêu đề, mã số và thời gian:
  ```text
  "Chưa đọc, , , TikTok, , 072296 là mã gồm 6 chữ số của bạn, , Sử dụng mã này để đăng nhập vào TikTok và không chia sẻ mã với bất kỳ ai. Mã gồm 6 chữ số của TikTok Xin chào ninhy05100, Mã gồm 6 chữ số của bạn là: 072296 Hãy sử dụng mã này hoặc nhấn vào liên kết, , ,  lúc 14:33"
  ```
- Do không có node lân cận thỏa mãn điều kiện tọa độ, `timestamp` bị gán rỗng `""`.
- Khi `timestamp == ""`, hàm `_gmail_timestamp_looks_recent("")` trả về `False`.
- Runner kết luận mã OTP này là mã cũ từ trước và bỏ qua (`preview_meta and preview_meta.get("code")` trigger log "Bỏ qua code preview cũ").

## Giải pháp chuẩn
Trong `social_reg_v1.py` tại vòng lặp duyệt `entries` của `extract_recent_tiktok_otp_from_gmail_list`:
Nếu không tìm thấy node lân cận chứa timestamp (`if not timestamp:`), trích xuất trực tiếp thời gian từ chuỗi `entry["text"]` bằng regex:
```python
        if not timestamp:
            time_m = re.search(r'(?:lúc\s+|at\s+)?(\b\d{1,2}:\d{2}\b)', entry["text"], re.IGNORECASE)
            if time_m:
                timestamp = time_m.group(1)
```
Điều này đảm bảo timestamp dạng `14:33` hoặc `lúc 14:33` được bóc tách chính xác, giúp `_gmail_timestamp_looks_recent` và `_gmail_timestamp_is_after` xác thực mã OTP tươi thành công ngay từ màn hình preview mà không cần click mở chi tiết thư.
