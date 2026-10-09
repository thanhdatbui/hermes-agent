# Case UI-63: TikTok 46.9.3 Action Selector Drift (id/fm9) & Audit Đếm Profile Follower/Following

## 1. Hiện Tượng & Nguyên Nhân
- **Phiên bản TikTok:** 46.9.3 (trên các dòng máy như Samsung Galaxy S7 / Máy 38).
- **Hiện tượng 1:** Search nick chưa từng follow (ví dụ: `hunh.m.linh571`, `kimm.ngnn614`), script vào profile đối phương nhưng không bấm nút Follow, tự động back ra ngoài và ghi vào state `skipped`.
- **Hiện tượng 2:** Vào Anchor chưa follow (vẫn hiện nút Follow đỏ), nhưng script vẫn nhảy vào danh sách Following của Anchor để cào tiếp nick bên trong.
- **Hiện tượng 3:** Sau khi bấm Follow nick trong danh sách Following, mở profile kiểm tra (Path B) thấy nút vẫn đỏ (bị server nhả follow) nhưng script không phanh dừng mà tiếp tục back ra follow nick tiếp theo.

### Root Cause Cốt Lõi:
1. **Selector Drift `id/fm9`:**
   TikTok 46.9.3 đã đổi resource ID của cặp nút hành động trên header profile sang `id/fm9` (ví dụ: nút Follow có ID `id/fm9`, nút Nhắn tin có ID `id/fm9`).
   Trong `verify_follow.py`, `_ACTION_BUTTON_SUFFIXES` chỉ chứa các ID cũ (`id/fds`, `id/ff8`, `id/fij`, `id/fi6`, `id/flo`, `id/flp`). Do thiếu `id/fm9`:
   - Node "Follow" (chưa follow) bị `_is_profile_action_node()` đánh giá là `False`.
   - Node "Nhắn tin" lại được nhận diện qua fallback `message_markers` (`has_message = True`).
   - Hàm `classify_button()` thấy có nút message và không có nút follow (do nút follow bị lọc bỏ vì không khớp whitelist ID) -> **kết luận nhầm profile đã `followed` 100%!**
   - Hậu quả: Mode 1 tưởng nick đã follow -> skip. Anchor tưởng đã follow -> mở Following tab.
2. **Anchor Gate Lỏng Lẻo:**
   Trong `_ensure_anchor_followed()`, nếu `classification != "not_followed"` (ví dụ do lỗi parse ra `unknown`/`manual`), hàm trả về `profile_xml` ban đầu khiến `_open_following_tab()` coi như Anchor đã OK và tiếp tục mở danh sách.
3. **Path B Fail-Closed:**
   Khi mở profile nick con kiểm tra Path B, nếu không nhận diện được `followed` rõ ràng (nút vẫn đỏ hoặc unknown), runner phải lập tức gọi `state.set_follow_failed()` và dừng toàn bộ session thay vì trả về `manual` để vòng lặp bỏ qua tiếp tục.

---

## 2. Giải Pháp Khắc Phục (Patch Contract)

### 2.1 Cập nhật Selector Whitelist trong `verify_follow.py`
Thêm `:id/fm9` và `id/fm9` vào `_ACTION_BUTTON_SUFFIXES`:
```python
_ACTION_BUTTON_SUFFIXES = (
    ":id/fds", ":id/ff8", ":id/fij", ":id/fi6", ":id/flo", ":id/flp", ":id/fm9", ":id/follow_button",
    "id/fds", "id/ff8", "id/fij", "id/fi6", "id/flo", "id/flp", "id/fm9", "id/follow_button",
)
```

### 2.2 Siết Chặt Anchor Follow Gate trong `mode2_follow_followers.py`
- Chỉ cho phép tiếp tục vào Following list nếu và chỉ nếu Anchor đã được chứng minh là `followed`.
- Nếu trạng thái ban đầu không phải `followed`, bắt buộc thực hiện luồng xem video + follow. Nếu sau reload trạng thái vẫn không phải `followed`, lập tức set `FOLLOW_FAILED` và abort, cấm trả về `profile_xml` để mở list.

### 2.3 Siết Chặt Path B trong `mode2_follow_followers.py`
- Mọi trường hợp mở profile con trong `_path_b_verify` mà trạng thái không chuyển sang `followed` (hoặc là `not_followed`) đều phải kích hoạt `state.set_follow_failed()` và trả về `"failed"` để ngắt session ngay lập tức.

---

## 3. Quy Trình Đối Soát Dữ Liệu Thực Tế (Ground Truth Verification)
Để ngăn chặn tình trạng script báo cáo "láo" hoặc bị Optimistic UI của TikTok đánh lừa:
1. **Trước Phiên Chạy:**
   Vào Profile tài khoản hiện tại trên máy, cào chỉ số `Đang follow: N` lưu vào preflight snapshot.
2. **Sau Phiên Chạy:**
   Vào lại Profile tài khoản, đọc lại chỉ số `Đang follow: M`.
3. **Đối Soát:**
   - Số follow tăng thực tế = `M - N`.
   - Nếu script báo cáo `len(res.followed) > 0` nhưng `M - N == 0` (hoặc chênh lệch lớn): Đánh dấu ngay vi phạm nhả follow âm thầm (`shadow_rollback_detected`), kích hoạt Cooldown cho nick và tạo Farm Alert để rà soát selector.
