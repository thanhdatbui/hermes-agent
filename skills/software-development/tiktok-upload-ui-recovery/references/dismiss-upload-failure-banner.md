# Dismiss Banner Upload Thất Bại ("Không thể tải video lên. Đã lưu bản nháp")

## 1. Hiện tượng & Ngữ cảnh
- Khi thực hiện upload video trên TikTok, có trường hợp mạng yếu hoặc vi phạm tạm thời khiến TikTok hiện banner: `"Không thể tải video lên. Đã lưu bản nháp."` (hoặc tiếng Anh: `"Couldn't upload video"` / `"Could not upload video"`).
- Banner này có thể chứa nút `"Không quan tâm"`, `"Hủy"`, `"Cancel"`, `"Đóng"`, che khuất view hoặc làm kẹt các bước kiểm tra tiếp theo trong StateMachine.

## 2. Giải pháp Code-Surgery chuẩn trong StateMachine (`scripts/tiktok_workflow/state_machine.py`)
1. **Thêm phương thức tĩnh `_dismiss_upload_failure_banner`**:
   - Quét XML text (casefold).
   - Markers: `"không thể tải video lên"`, `"couldn't upload video"`, `"could not upload video"`, `"tải lên không thành công"`.
   - Action buttons: `"Không quan tâm"`, `"Hủy"`, `"Cancel"`, `"Đóng"`, `"Close"`, `"Bỏ qua"`, `"Dismiss"`. Thử cả `_tap_if_found(text=label)` lẫn `_tap_if_found(text_contains=label)`.
   - Fallback: Nếu không tìm thấy button, gọi `adapter.back()` (nếu callable).
2. **Gắn vào các điểm chặn popup**:
   - `_handle_dismiss_popups`: kiểm tra trước hoặc song song với `_dismiss_add_to_home_popup`. Nếu dismiss thành công, sleep 1s và re-dump UI.
   - `_wait_for_post_submission`: trong vòng lặp 15 lần chờ upload kết thúc, gọi `_dismiss_upload_failure_banner` tương tự như `_dismiss_add_to_home_popup` để tránh kẹt loop.

## 3. Unit Test Regression (`tests/test_tiktok_workflow.py`)
- Mock một adapter đơn giản chứa `_tap_if_found` và kiểm tra với XML sample:
  ```python
  def test_dismiss_upload_failure_banner(self):
      from tiktok_workflow.state_machine import StateMachine

      class Adapter:
          def __init__(self):
              self.labels = []
          def _tap_if_found(self, _xml, **kwargs):
              text = kwargs.get("text") or kwargs.get("text_contains")
              self.labels.append(text)
              return text == "Không quan tâm"

      adapter = Adapter()
      xml = '<hierarchy><node text="Không thể tải video lên. Đã lưu bản nháp."/><node text="Không quan tâm"/></hierarchy>'
      assert StateMachine._dismiss_upload_failure_banner(adapter, xml) is True
      assert "Không quan tâm" in adapter.labels
  ```
