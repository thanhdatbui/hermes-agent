# UIElement Constructor & Device Lock Management

## 1. UIElement Constructor Pitfall (`center` parameter)
- Trong `automation_core.ui:UIElement`, `center` là một `@property` được tính toán tự động từ `bounds: tuple[int, int, int, int] | None`:
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
- **Lỗi thường gặp:** Truyền `center=...` vào `UIElement(...)` dẫn đến lỗi `TypeError: UIElement.__init__() got an unexpected keyword argument 'center'`.
- **Cách xử lý chuẩn:** Khi muốn tinh chỉnh tọa độ tap cho row container rộng (ví dụ full-width account row trong switcher), hãy gán thu hẹp `bounds` (ví dụ `best_bounds = (x1, y1, x1 + 600, y2)` hoặc lấy `inner.bounds`) để `@property center` tự động tính đúng tọa độ tâm.

## 2. Multi-Machine Device Lock Handling during Canary Tests
- Khi tiến trình `multi-machine-feed-session` chạy nền (ví dụ cron job), tất cả máy được gán trong batch sẽ bị khóa bởi file lock tại `C:\Users\<user>\.codex\device-locks\machine_<N>.lock.json`.
- Nếu canary test cho 1 máy trả về `skipped-device-locked`, kiểm tra PID trong file lock. Nếu batch đang chạy, kiểm tra tiến độ của máy đó trong batch artifacts hoặc đợi toàn bộ batch hoàn tất để lock được tự động giải phóng trước khi chạy canary test riêng.
