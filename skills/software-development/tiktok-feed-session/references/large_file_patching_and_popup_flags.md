# Pitfalls: Patching Large Flow Files & Benign Popup Flags

## 1. Cạm bẫy khi patch `feed_swipe_smoke.py` (>22k dòng)
- **Đặc thù file**: File `feed_swipe_smoke.py` cực lớn (>22,000 dòng) và có rất nhiều dòng trống phân cách (double-spaced lines trong một số block).
- **Nguy cơ**: Công cụ fuzzy patch rất dễ match nhầm vào các khối hàm kiểm tra trạng thái ở phía trên (ví dụ: `_is_feed_confirmed` tại dòng ~1950 thay vì `_maybe_dismiss_add_phone_row` tại dòng ~8200) do cấu trúc `if / return` tương đồng và cảnh báo pagination view.
- **Quy tắc bắt buộc**:
  1. Bao gồm context dòng định danh duy nhất (tên hàm `def ...`, biến đặc thù) trong `old_string`.
  2. Ngay sau khi patch, **luôn chạy `git diff <file>`** qua terminal để kiểm tra chính xác diff trước khi chạy test.
  3. Nếu patch bị lệch vị trí, lập tức `git checkout <file>` để phục hồi nguyên trạng.

## 2. Quy tắc cờ an toàn `allow_benign_popup_dismiss`
- **Mục đích**: Tự động đóng các popup không độc hại (như popup "Thêm số điện thoại / Add phone", quyền vị trí) mà không dừng phiên báo `MANUAL_NEEDED`.
- **Trong `feed_swipe_smoke.py` (`_maybe_dismiss_add_phone_row`)**:
  - Phải dùng default `True` khi lấy cờ:
    `allow_dismiss = ctx.config.get("safety", {}).get("allow_benign_popup_dismiss", True)`
  - Không được default `False`, nếu không các flow chạy không kèm flag tường minh sẽ bị dừng oan với lý do `benign Add phone popup detected; dismiss requires explicit flag`.
- **Trong `multi_machine_feed_session.py`**:
  - Khởi tạo `child_safety["allow_benign_popup_dismiss"] = True`.
  - Khi sao chép config từ `parent_safety`, tránh đè mất giá trị `True` nếu parent không đặt tường minh `False`.

## 3. Mocking `_row_from_attempt` trong Unit Test
- Khi viết unit test cho `_maybe_dismiss_add_phone_row`:
  - `_maybe_dismiss_add_phone_row` gọi `_row_from_attempt(...).as_dict()`.
  - Do đó, mock của `_row_from_attempt` **phải** có method `as_dict()`:
    `mock_row = Mock(); mock_row.as_dict.return_value = {"status": "success", ...}`
  - Trả về plain `dict` sẽ gây lỗi `AttributeError: 'dict' object has no attribute 'as_dict'`.
