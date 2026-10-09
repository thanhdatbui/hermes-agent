# UIElement Constructor & Account Switcher Matching Invariants (Case 102)

## 1. UIElement Constructor Invariant (`automation_core.ui.UIElement`)
- `UIElement` trong `automation_core.ui` được định nghĩa là một `@dataclass(frozen=True)` nhận đúng 5 trường:
  ```python
  @dataclass(frozen=True)
  class UIElement:
      text: str
      content_desc: str
      resource_id: str
      bounds: Bounds | None
      attrib: dict[str, str]

      @property
      def center(self) -> tuple[int, int] | None:
          if self.bounds is None:
              return None
          left, top, right, bottom = self.bounds
          return ((left + right) // 2, (top + bottom) // 2)
  ```
- **Anti-Pattern:** Khởi tạo `UIElement(..., center=best_center)` sẽ gây crash ngay lập tức với lỗi `TypeError: UIElement.__init__() got an unexpected keyword argument 'center'`.
- **Chuẩn hóa (Fix):** 
  - KHÔNG truyền `center` vào `UIElement(...)`.
  - Nếu muốn điều chỉnh tọa độ tap của element (ví dụ thu hẹp vùng tap vào TextView bên trái thay vì container full-width), hãy tính toán và truyền `bounds=best_bounds` (ví dụ `(x1, y1, x1 + 700, y2)`), thuộc tính `center` sẽ tự động trả về tâm của vùng `bounds` mới.

## 2. Loại Trừ Add Account / Log In Khi Match Switcher
- **Anti-Pattern:** Trong hàm `_find_account_switch_option` hoặc các vòng lặp quét node fallback trên sheet Switcher, nếu so sánh trực tiếp `_normalize_account(val) == expected_clean` mà không loại trừ các nút hành động ("Thêm tài khoản", "Add account", "Log in", "Đăng nhập"), script sẽ match nhầm vào nút Add Account nếu `expected_account` bị rỗng hoặc trùng chuỗi.
- **Chuẩn hóa (Fix):**
  - Luôn kiểm tra `if _is_login_or_add_account_option_text(expected_clean): return None` ngay đầu hàm.
  - Trong vòng lặp duyệt `_nodes(xml_text)` fallback, thêm điều kiện `if val and not _is_login_or_add_account_option_text(val) and ...`.
  - Trong `_maybe_recover_missing_account_via_login`, chặn `if not expected or _is_login_or_add_account_option_text(expected): return False`.
