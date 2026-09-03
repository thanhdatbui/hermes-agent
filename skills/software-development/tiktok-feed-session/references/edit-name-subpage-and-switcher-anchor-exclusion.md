# Case 67: Màn hình "Thêm tên bạn mong muốn" (Edit Name Subpage Overlay) & Loại trừ Display Name khỏi Switcher Anchor

## Hiện tượng & Nguy cơ
1. Khi tài khoản chưa đặt display name hoặc có tên hiển thị trên header tab Hồ sơ (Profile), runner quét tìm `find_switcher_anchor` có thể nhận nhầm node display name (`:id/pkh`, `:id/pke`, `:id/pau`, `:id/s9b`, `tv_content_name`).
2. Tapping vào anchor sai mở ra subpage "Thêm tên bạn mong muốn" (Edit Name Subpage) kèm bàn phím ảo.
3. Mặc dù runner có thể xử lý điền tên hoặc dismiss qua registry (`_dismiss_edit_name`), nếu kết quả trả về `PopupDismissResult` không được normalize đầy đủ `selector` và `popup_type`, hàm `_apply_popup_dismiss_result` sẽ gán `row["popup_type"] = None`.
4. Khi `row["popup_type"]` là `None`, `_is_allowed_popup_retry_allowed` trả về `False`, khiến `_maybe_handle_profile_add_phone_guard` coi là `manual-needed` và dừng phiên với alert `known TikTok screen`.

## Quy tắc xử lý chuẩn (Case 67)
1. **Loại trừ Display Name khỏi Switcher Candidates (Refined Case 70):**
   - Trong `find_switcher_anchor` (automation-core) và `_find_sticky_profile_header` (`feed_swipe_smoke.py`), loại trừ các resource-id container/unwanted:
     `(":id/pkh", ":id/pau", ":id/s9b", "tv_content_name")`.
   - *Lưu ý*: `:id/pke` là ID profile header TextView hợp lệ chứa username (Case 70), KHÔNG được loại trừ cứng. Phân biệt bằng text marker `{"thêm tên", "add name", "thêm tiểu sử", "add bio"}`.
2. **Normalize Popup Dismiss Result:**
   - Trong `dismiss_allowed_generic_popup` và `dismiss_any_popup`, luôn đảm bảo `selector` được khởi tạo và chứa `popup_type`:
     `selector = {"action": "allowlist_dismiss", "popup_type": matching_entry.name}` nếu handler trả về `selector=None` hoặc thiếu `popup_type`.
   - Trong `_apply_popup_dismiss_result`, luôn thực hiện fallback an toàn: nếu `dismissed=True` và `popup_type` rỗng, fallback sang `"allowlist_popup"`.
3. **Retry an toàn sau khi dismiss subpage:**
   - Khi popup hoặc subpage được dismiss thành công (`status == "dismissed"`), cho phép retry thao tác mở account switcher thay vì dừng phiên `manual-needed`.
