# TikTok v46.9.3 Selector Drift & Missing Follow Button Recovery

## Hiện trường sự cố (Farm Alert Ca 2 Phiên 2 - Row 4)
- **Triệu chứng diện rộng (27 máy)**: M3, M10, M23, M26, M27, M29, M32, M33, M35, M40, M41, M42, M43, M45, M46, M48, M50, M51, M53, M54, M55, M58, M59, M60, M63, M65, M71.
- **Log lỗi**: `status: "MANUAL_REVIEW"`, `reason: "MANUAL_REVIEW: follower row không có nút follow semantic"`, `exit_code: 1`.
- **Màn hình**: Đang mở tab "Đã follow" / "Đang follow" của anchor profile, hiển thị đầy đủ danh sách follower và các nút bấm quan hệ, nhưng runner dừng phiên ngay ở hàng đầu tiên.

## Phân tích nguyên nhân gốc rễ (Root Cause)
1. **Đổi Resource ID nút Follow trên TikTok v46.9.3**:
   - Trên phiên bản TikTok 46.9.3, các nút quan hệ ("Follow", "Follow lại", "Bạn bè") trong hàng follower/following (`RecyclerView`) bị obfuscate đổi sang ID:
     `com.ss.android.ugc.trill:id/u68` (`:id/u68`, `id/u68`).
   - Danh sách trước đây trong `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` chỉ gồm: `id/tcj`, `id/thb`, `id/tvn`, `id/tum`, `id/u2f`.
2. **Cơ chế bắt lỗi layout fail-closed (`missing_button_rows`)**:
   - `_cluster_follower_rows` gom cụm `txt_user_name` và `txt_desc` thành hàng người dùng hợp lệ.
   - Do thiếu `id/u68`, `button_nodes` rỗng -> toàn bộ row hợp lệ bị gán `follow_button = None`.
   - Vòng lặp `run_mode2` kiểm tra `missing_button_rows`: phát hiện row không thuộc diện cắt biên (`_is_top_cutoff_row`, `_is_bottom_cutoff_row`) và chưa seen mà không có nút follow -> kích hoạt dừng an toàn `MANUAL_REVIEW: follower row không có nút follow semantic`.

## Quy tắc xử lý chuẩn (Selector Drift Contract)
1. **Cập nhật `follow_runner/core/selectors.py`**:
   - Bổ sung `com.ss.android.ugc.trill:id/u68`, `:id/u68`, `id/u68` vào `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`.
2. **Đồng bộ với các thay đổi khác của TikTok v46.9.3**:
   - Following tab labels tiếng Việt: `"Đang follow"`, `"Đang theo dõi"` trong `_FOLLOWER_HEADER_RE` và `_FOLLOWER_EMPTY_LABELS`.
   - Relation RecyclerView ID: `com.ss.android.ugc.trill:id/uzs` trong `FOLLOWER_LIST_RECYCLER_IDS`.
3. **Kiểm thử nghiệm thu focused (<30s)**:
   - `pytest follow_runner/tests/test_mode2_follow_followers.py -k "u68" -v`
