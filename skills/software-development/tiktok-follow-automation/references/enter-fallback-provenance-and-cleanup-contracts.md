# Enter Fallback, Identity Provenance, and Cleanup Strict Return Contracts

## 1. Mode 1 Enter Fallback Safety (`_nav_search`)
Khi ô submit Search bị che khuất bởi soft keyboard hoặc không match selector:
- Bắt buộc kiểm tra UI dump hiện tại:
  - Có node `android.widget.EditText`
  - Node thuộc `is_tiktok_package(n.get("package"))`
  - Node có thuộc tính focus hợp lệ: `n.get("focused") is True or str(n.get("focused", "")).lower() == "true"` (bảo vệ chống type divergence string vs bool từ XML parser).
  - `_normalize_search_value(n.get("text")) == _normalize_search_value(uid)`
- Nếu các điều kiện trên không thỏa, hoặc dump bị exception, hoặc `adapter.keyevent(66)` trả về `False`:
  - Phải ghi log cảnh báo / exception và `return False` ngay lập tức.
  - Tuyệt đối KHÔNG tiếp tục gọi `_wait_search_result()` vì có nguy cơ nhận nhầm kết quả cũ từ lần tìm kiếm trước (stale UI / race condition).

## 2. Mode 2 Path B Identity Provenance
Khi xác thực `identity_element` từ `profile_identity_from_xml`:
- Trích xuất package an toàn qua hàm chuẩn `_extract_identity_package(element)` xử lý 3 tầng:
  1. `element.attrib` dict: `attrib.get("package")`, `attrib.get("resource-id")`, `attrib.get("resource_id")`
  2. `element` là dict: `element.get("package")`, `element.get("resource_id")`, `element.get("resource-id")`
  3. `element` là object: `getattr(element, "package")`, `getattr(element, "resource_id")`
- Đặc biệt xử lý trường hợp `UIElement` có `attrib={}` (empty dict) nhưng có `resource_id` chứa package prefix (`com.ss.android.ugc.trill:id/...`).
- Tuyệt đối không mượn package của node khác (`handle_node`) gán cho `identity_element` nếu `identity_element` không tự chứng minh được package của chính nó.
- Nếu không chứng minh được package thuộc TikTok, coi như không xác thực được hồ sơ và trả về `manual`.

## 3. Strict Cleanup Ladder Contract (`_cleanup_follow_failed`)
- Mỗi bước trong cleanup ladder (`close_all_recent_apps` -> `close_all_apps` -> `home` -> `press_home`) coi là thành công khi `ok is not False` (để tương thích cả adapter trả `True` lẫn `None` void-return chuẩn Python).
- Bất kỳ bước nào trả `False`, thiếu method trên adapter, hoặc ném exception đều phải được ghi nhận chi tiết vào danh sách `cleanup_errors` (dạng `f"{method}: {ok!r}"` hoặc `f"{method}: {type(exc).__name__}: {exc}"`).
- `res.details["cleanup_errors"]` luôn được lưu lại nếu danh sách lỗi không rỗng, phục vụ chẩn đoán forensic.
- Nếu toàn bộ các bước trong ladder đều không thành công (`not cleanup_ok`), chuyển trạng thái thành `CLEANUP_FAILED` với `failed=True`, `follow_failed=True` và exit code 1 để kích hoạt Farm Alert và giữ nguyên hiện trường.

## 4. State Persistence Error Handling
- Khi `state.set_follow_failed()` gặp lỗi I/O hoặc ném exception:
  - Bắt exception bằng `logger.exception(...)`.
  - Giữ nguyên trạng thái kỹ thuật bẩn (`MANUAL_REVIEW`, `failed=True`, `follow_failed=True`).
  - Ghi chi tiết lỗi vào `res.details["state_error"]`.
  - Không bao giờ phát payload clean `FOLLOW_FAILED` (`failed=False`) khi chưa lưu được state.
