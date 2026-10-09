# TikTok 46.9.3 Selector Drift (id/fm9) & Fail-Closed Anchor / Path B Verify

## 1. Selector Drift TikTok 46.9.3 (`id/fm9`)
- **Vấn đề phát hiện**:
  - Trên TikTok 46.9.3 (máy live), nút Action follow trên Profile Header chuyển sang dùng resource-id dạng `...:id/fm9` hoặc `id/fm9`.
  - Trong `follow_runner/flows/verify_follow.py`, `_ACTION_BUTTON_SUFFIXES` chỉ liệt kê các suffix cũ:
    `(":id/fds", ":id/ff8", ":id/fij", ":id/fi6", ":id/flo", ":id/flp", ":id/follow_button", ...)`
  - Do thiếu `":id/fm9"` và `"id/fm9"`, hàm `_is_profile_action_node` trả về `False` cho nút Follow đỏ / Follow lại.
  - Tuy nhiên, nút companion "Nhắn tin" vẫn được nhận diện (do text match `message_markers`).
  - Hệ quả nguy hiểm: `classify_button` chỉ nhìn thấy nút "Nhắn tin", không thấy nút Follow, dẫn đến đánh giá nhầm trạng thái là `followed` ngay cả khi tài khoản chưa hề follow!

- **Khắc phục**:
  - Bổ sung `":id/fm9"` và `"id/fm9"` vào `_ACTION_BUTTON_SUFFIXES` trong `verify_follow.py`.

## 2. Fail-Closed Anchor Follow (`_ensure_anchor_followed`)
- **Vấn đề**:
  - Trong `mode2_follow_followers.py`, logic cũ kiểm tra:
    ```python
    classification = _classify_profile_action(profile_xml)
    if classification == "followed":
        return profile_xml
    if classification != "not_followed":
        return profile_xml
    ```
  - Nếu `classification` trả về `"unknown"` (ví dụ do selector trôi hoặc layout lạ), nhánh `!= "not_followed"` lại return `profile_xml`! Điều này làm `_open_following_tab` lầm tưởng Anchor đã follow và tiếp tục mở Following list.
  - Ngoài ra, sau khi xem video, tap follow và pull-to-refresh reload, nếu `refreshed_classification` không phải `followed` (ví dụ `unknown`), code cũ vẫn `return refreshed_xml` thay vì ngắt session.

- **Khắc phục**:
  - CHỈ return `profile_xml` khi `classification == "followed"`. Mọi trạng thái khác đều phải thực hiện chu trình follow.
  - Sau khi tap follow và reload profile, nếu `refreshed_classification != "followed"`, BẮT BUỘC coi là lỗi nghiêm trọng:
    ```python
    engine._last_anchor_follow_outcome = "failed"
    engine.state.set_follow_failed()
    return None
    ```

## 3. Fail-Closed Path B Verify (`_path_b_verify`)
- **Vấn đề**:
  - Khi đã vào profile nick follower và xác nhận đúng identity (`dump_ok=True`, `back_ok=True`, `restored=True`):
  - Nếu `classification` trả về `"unknown"` hoặc không phải `"followed"`, code cũ trả về `"manual"`. Khi đó follow bị nhả nhưng session không fail-closed dừng lại.

- **Khắc phục**:
  - Khi màn hình đã nạp đúng profile nhưng `classification != "followed"` (bao gồm cả `unknown` lẫn `not_followed`), phải gọi `state.set_follow_failed()` và trả về `"failed"` để fail-closed dừng session ngay lập tức.
