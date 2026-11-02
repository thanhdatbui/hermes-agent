# TikTok 2FA Deletion vs Phone Requirement & Switcher OCR Pitfalls

## 1. Cơ Chế Tắt 2FA Email Trên TikTok (Yêu Cầu Số Điện Thoại Bắt Buộc)
- **Hành vi thực tế:** Trong menu `Cài đặt và quyền riêng tư` -> `Bảo mật & quyền` -> `Xác minh 2 bước`:
  - Khi người dùng/agent bấm vào dòng `Email` (đang ở trạng thái `Bật`) để tắt hoặc xóa phương thức nhận mã qua Email:
  - TikTok sẽ hiển thị modal xác nhận: `Xóa email? - Bạn sẽ không còn dùng tùy chọn này làm phương thức xác minh 2 bước nữa` kèm nút đỏ `Xác nhận`.
  - **BẪY BẢO MẬT BẮT BUỘC:** Ngay khi bấm `Xác nhận`, TikTok **KHÔNG CHO PHÉP TẮT EMAIL** nếu tài khoản chưa có số điện thoại. App lập tức cưỡng chế chuyển sang màn hình **`Thêm điện thoại`** (`VN +84, Bạn sẽ nhận được mã xác minh qua SMS...`).
  - **Quy tắc bảo mật TikTok:** Để duy trì tính năng Xác minh 2 bước, tài khoản bắt buộc phải có tối thiểu 2 phương thức bảo mật khả dụng. Nếu tài khoản chỉ có Mật khẩu + Authenticator App, việc gỡ Email sẽ vi phạm điều kiện này, do đó TikTok bắt buộc phải bổ sung SMS trước khi lưu thay đổi gỡ Email.
  - **Kết luận vận hành:** Không thể dùng mẹo "tắt 2FA Email trước rồi mới đổi mail" trên các nick chưa liên kết SĐT.

## 2. Popup Xác Nhận 2 Lớp Khi Đổi Email ("Thay Đổi Email?")
- **Hiện tượng:** Sau khi vào `Thông tin tài khoản` -> bấm dòng `Email` -> bấm nút `Thay đổi email` ở modal đầu tiên, TikTok tiếp tục bật lên một dialog cảnh báo lớp thứ 2:
  - Text: `Thay đổi email? / Thay d6i email? Email mới của bạn cũng sẽ được dùng cho xác minh 2 bước.`
  - Nút bấm: `Quay lại` (bên trái) và `Tiếp tục / Tiép tvc` (bên phải, màu đỏ tại tọa độ khoảng `750, 1285`).
- **Xử lý tự động:**
  - Bắt buộc kiểm tra OCR sau khi tap nút `Thay đổi email`: nếu xuất hiện dialog chứa `thay` + `email` và có nút `tiếp tục` / `tiép tvc`, phải tap vào tâm nút `Tiếp tục` (tọa độ `750, 1285` trên màn 1080x1920) rồi mới tiến hành nhập Hotmail mới.

## 3. Lỗi OCR Nhầm Lẫn Tên Tài Khoản Trong Switcher (Fuzzy Normalization)
- **Hiện tượng:** Trên màn hình Switcher danh sách nick của TikTok (đặc biệt các máy Samsung S7):
  - Ký tự `l` thường bị OCR nhận diện thành chữ `I` hoa hoặc số `1` (ví dụ: `l.thanh.ngn311` -> `I.thanh.ngn311`, `phungloan0138` -> `phungIoan0138`).
  - Dấu chấm `.` hoặc gạch dưới `_` đôi khi bị mất hoặc nhận diện thành khoảng trắng.
- **Giải pháp chuẩn hóa bắt buộc:**
  ```python
  def norm_name(s):
      return s.lower().replace('l', 'i').replace('1', 'i').replace('.', '').replace('_', '').strip()

  u_norm = norm_name(username)
  for text_item, bounds in sw_boxes:
      t_norm = norm_name(text_item)
      if username.lower() in text_item.lower() or u_norm in t_norm:
          # Match thành công! Tap vào tâm bounds
          cx = (bounds[0] + bounds[2]) // 2
          cy = (bounds[1] + bounds[3]) // 2
          tap(cx, cy)
          break
  ```
