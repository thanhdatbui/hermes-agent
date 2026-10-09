# Account Switcher & UIElement Pitfalls (Taadaa Farm)

## 1. UIElement Contract & Instantiation
- `UIElement` trong `automation_core.ui` được định nghĩa là `@dataclass(frozen=True)` với các trường:
  - `text: str`
  - `content_desc: str`
  - `resource_id: str`
  - `bounds: Bounds | None`
  - `attrib: dict[str, str]`
- `center` là một `@property` được tính toán tự động: `((left + right) // 2, (top + bottom) // 2)` từ `bounds`.
- **Pitfall:** Tuyệt đối KHÔNG truyền `center=...` vào `UIElement(...)` làm keyword argument. Việc này gây crash tức thì: `TypeError: UIElement.__init__() got an unexpected keyword argument 'center'`.
- **Cách fix chuẩn:** Nếu cần điều chỉnh điểm tap (center), hãy thu hẹp hoặc dịch chuyển tuple `bounds=(left, top, right, bottom)` trước khi khởi tạo `UIElement`.

## 2. Account Switcher Fallback Matching Rules
- Khi tìm kiếm dòng tài khoản mục tiêu trong account switcher XML (`_find_account_switch_option`):
  - Luôn kiểm tra `_is_login_or_add_account_option_text(expected_clean)`. Nếu chuỗi cần tìm là action text ("Thêm tài khoản", "Log in", "Đăng nhập"), trả về `None` ngay lập tức.
  - Khi duyệt qua các node con (`_nodes(xml_text)`), BẮT BUỘC bỏ qua các node thỏa mãn `_is_login_or_add_account_option_text(val)` để tránh nhận diện nhầm nút "Thêm tài khoản" hoặc "Log in" là dòng tài khoản hợp lệ.
  - Khi node cha là container full-width (`w >= 600px`), tìm node con cụ thể của username/avatar để lấy `bounds` chính xác thay vì tap vào khoảng trống bên phải.
