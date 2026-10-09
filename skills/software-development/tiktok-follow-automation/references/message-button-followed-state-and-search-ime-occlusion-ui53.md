# Case UI-53: TikTok 46.x Profile Action Button "Nhắn tin" & Search IME Focus Occlusion

## 1. Profile Action Button "Nhắn tin" / "Message" as `followed` State

### Triệu chứng & Bối cảnh
- Trên TikTok 46.x (ví dụ Máy 51 `ce0616063df1094004`, nick `duonguyen1202`), sau khi tap Follow thành công trên profile đối tượng (ví dụ `@yobi1965`):
  + TikTok chuyển nút chính từ "Follow" sang nút pill mang text/content-desc **"Nhắn tin"** / **"Message"** (hoặc "Gửi tin nhắn").
  + Đi kèm nút icon người có dấu tick (trạng thái bạn bè/đang follow) và nút tam giác xổ xuống ▼.
  + Không còn các nhãn truyền thống trong `FOLLOWED_TEXT` ("Đã follow", "Following", "Đang theo dõi").
- Flow xác minh `verify_follow.py`:
  + `_is_profile_action_node` trước đây whitelist cứng theo resource-id (`id/fds`, `id/ff8`, `id/fij`, `id/fi6`, `id/flo`, `id/follow_button`). Khi nút "Nhắn tin" có ID khác, node bị bỏ qua.
  + `classify_button` không tìm thấy nhãn follow hợp lệ nên trả về `unknown`.
  + `_confirm_not_released` kéo reload kiểm tra shadow drop/rate limit vẫn ra `unknown`, dẫn đến fail-closed: `MANUAL_REVIEW: trạng thái nút không xác định sau vuốt xác nhận`.

### Khắc phục chuẩn
1. **Mở rộng `_is_profile_action_node`**:
   - Chấp nhận các node thuộc package TikTok trong vùng header profile action (`bounds[1] < 1200`, ngoại trừ stat counters `_STAT_COUNTER_IDS`) có text hoặc content-desc chuẩn hóa thuộc nhóm `{"nhắn tin", "message", "gửi tin nhắn", "send message"}`.
2. **Cập nhật `classify_button`**:
   - Khi profile xuất hiện nút "Nhắn tin" / "Message" và hoàn toàn **không có** nút "Follow" / "Follow lại" / "Theo dõi", phân loại chính xác là `"followed"`.

---

## 2. Search Submit & KEYCODE_ENTER IME Focus Occlusion (Kẹt màn hình Search)

### Triệu chứng & Bối cảnh
- Khi tìm kiếm UID/anchor trong Mode 1 hoặc Mode 2 (`mode1_search_follow.py`):
  + Ô tìm kiếm nhập xong UID (ví dụ `tranngan8642`).
  + `_unique_search_submit` trước đây kiểm tra cứng `node.get("resource_id", "").endswith("id/tv_search_textview")`. Khi nút đỏ "Tìm kiếm" không có resource-id này hoặc id bị thay đổi, hàm trả về `None`.
  + Nhánh fallback gửi phím Enter (`KEYCODE_ENTER 66`) trong `_nav_search` yêu cầu `EditText` phải có `focused is True`. Tuy nhiên, khi bàn phím ảo Samsung/Gboard mở kèm dropdown autocomplete, focus của hệ thống chuyển sang IME window / candidate strip, khiến thuộc tính `focused` của `EditText` trong XML dump trả về `False`.
  + Hậu quả: Fallback Enter bị bỏ qua, runner không submit được tìm kiếm, app kẹt lại ở màn hình Search có bàn phím mở.

### Khắc phục chuẩn
1. **Mở rộng matcher `_unique_search_submit`**:
   - Chấp nhận node thuộc TikTok package có class `Button` hoặc `TextView`, text hoặc content-desc là "Tìm kiếm" / "Search", nằm ở đỉnh màn hình (`bounds[1] < 450`), không phụ thuộc cứng vào duy nhất resource-id `id/tv_search_textview`.
2. **Nới lỏng điều kiện KEYCODE_ENTER Fallback**:
   - Nếu không tìm thấy nút submit, chỉ cần XML dump có `EditText` thuộc TikTok chứa text/content-desc khớp với UID mục tiêu (sau khi chuẩn hóa `_clean_handle_text`), cho phép gửi `adapter.keyevent(66)` mà không bắt buộc `focused` phải là `True`.

---

## 3. Startup Feed Recovery chống `VERIFY_IDENTITY fail`

### Triệu chứng
- Khi app TikTok đang kẹt ở màn hình Search với bàn phím ảo mở (từ cữ chạy trước hoặc cron), cữ chạy kế tiếp gọi `run_session` -> `switch_account_and_verify` -> `open_profile_root`.
- Do bàn phím và màn hình Search che khuất toàn bộ thanh điều hướng dưới đáy (bottom nav), runner không tìm thấy tab "Hồ sơ" (`PROFILE_TARGET_NOT_FOUND`) -> ném ra lỗi giả `VERIFY_IDENTITY fail — nick không khớp @... (hoặc switcher fail)`.

### Khắc phục chuẩn
- Ở đầu `run_session` (hoặc trước `switch_account_and_verify`), luôn gọi cơ chế phục hồi Feed (`_back_to_feed` kết hợp `recover_ui`) để đóng bàn phím mềm và bấm Back thoát khỏi Search stack về Feed chính trước khi tìm tab Hồ sơ.

---

## 4. Stale Device Readiness (`proxy_pending` Timeout)

### Triệu chứng
- Canary preflight dừng fail-closed với lỗi: `BLOCKED: preflight device-lock/VPN fail-closed: proxy readiness timed out for <serial>`.
- Kiểm tra thực tế Wi-Fi và Sing-box proxy của thiết bị hoàn toàn thông suốt, egress IP hoạt động bình thường.
- Nguyên nhân: File marker trong `~/.codex/device-readiness/<serial>.json` bị kẹt trạng thái `"state": "proxy_pending"` từ phiên cũ (có thể từ nhiều ngày trước) mà chưa có tiến trình nào cập nhật lại.

### Khắc phục chuẩn
- Chạy lệnh cập nhật trạng thái readiness bằng Python:
  ```python
  from automation_core.readiness import mark_proxy_state
  mark_proxy_state("<serial>", "proxy_ready")
  ```
- Sau khi mark `proxy_ready`, preflight check `wait_for_proxy_ready()` sẽ pass ngay lập tức.
