# Case UI-65: TikTok 47.0.3 ID/FMP Selector Drift (Máy 37)

## 1. Hiện Tượng & Root Cause
- **TikTok 47.0.3 Selector Drift (Máy 37)**:
  - Trên máy 37 chạy TikTok phiên bản 47.0.3, resource-id nút Follow/Follow lại và nút Nhắn tin trên header profile đổi sang `id/fmp` (`com.ss.android.ugc.trill:id/fmp`).
  - Tương tự như case `id/fm9` (TikTok 46.9.3 trên máy 38), cả nút Follow và nút Nhắn tin đều mang chung resource-id `id/fmp`.
  - Nếu `_ACTION_BUTTON_SUFFIXES` trong `follow_runner/flows/verify_follow.py` thiếu `:id/fmp` và `id/fmp`:
    - Hàm `_is_profile_action_node` sẽ bỏ qua node Follow mang id `fmp`.
    - Trong khi đó, node Nhắn tin mang text khớp `message_markers` vẫn được match -> dẫn đến false positive (profile chưa follow bị classify nhầm thành `"followed"`).
    - Hậu quả: Script tưởng đã follow nên skip không tap nút (Mode 1), hoặc cào nhầm list của anchor chưa follow (Mode 2), báo cáo thành công giả.

## 2. Giải Pháp & Invariant
1. **Cập nhật Whitelist Action Suffixes**:
   - Thêm `:id/fmp` và `id/fmp` vào `_ACTION_BUTTON_SUFFIXES` trong `verify_follow.py`:
     ```python
     _ACTION_BUTTON_SUFFIXES = (
         ":id/fds", ":id/ff8", ":id/fij", ":id/fi6", ":id/flo", ":id/flp", ":id/fm9", ":id/fmp", ":id/follow_button",
         "id/fds", "id/ff8", "id/fij", "id/fi6", "id/flo", "id/flp", "id/fm9", "id/fmp", "id/follow_button",
     )
     ```
2. **Quy Tắc Quản Lý Selector Drift Trên Farm**:
   - Danh sách selector action button theo phiên bản TikTok / Máy:
     - Máy 1 (46.3.3): `id/fds`
     - Máy 2: `id/ff8`
     - Máy 6: `id/fij`
     - Máy 16: `id/fi6`
     - Máy 50: `id/flo`
     - Máy 38 (46.9.3): `id/fm9`
     - Máy 37 (47.0.3): `id/fmp`
   - Bất kỳ khi nào farm nâng cấp hoặc phát hiện phiên bản TikTok mới có selector lạ, phải bổ sung cả dạng `:id/<suffix>` và `id/<suffix>` vào tuple và chạy lại bộ test `test_verify_follow.py`.
