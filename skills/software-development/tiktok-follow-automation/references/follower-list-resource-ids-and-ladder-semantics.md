# Follower / Following List Resource IDs & Ladder Semantics (TikTok 46.x+)

## 1. Resource IDs trên màn Following / Follower List
- **RecyclerView ID (`FOLLOWER_LIST_RECYCLER_IDS`)**:
  - Các biến thể đã ghi nhận: `id/u5r`, `id/u_q`, `id/uoc`, `id/uo1` (`com.ss.android.ugc.trill:id/uo1`).
  - **Triệu chứng lỗi nếu thiếu ID**: Hàm `_classify_follower_surface` kiểm tra header tab (ví dụ: `Đã follow 1`), `selected_count = 1` nhưng `has_recycler = False` -> trả về `"invalid"`. Khi đó `_open_following_tab` bị timeout sau 10s dù màn hình máy thật đã mở đúng danh sách.
- **Nút Follow / Follow lại trong Row (`FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`)**:
  - Các biến thể đã ghi nhận: `id/tcj`, `id/thb`, `id/tvn`, `id/tum` (`com.ss.android.ugc.trill:id/tum`).

## 2. Cơ chế lỗi "sau ladder (lần 2)"
- **Lần 1**: Runner tìm kiếm anchor, vào profile, bấm tab "Đã follow" (`_open_following_tab`). Nếu timeout hoặc không nhận diện được bề mặt list hợp lệ -> `open_ok = False`.
- **Recovery Ladder**: Kích hoạt ladder UI chuẩn (ATX kill, force-stop/relaunch nếu cần) để phục hồi app và đưa về Feed (`_back_to_feed`).
- **Lần 2**: Runner lặp lại toàn bộ luồng tìm kiếm và mở tab lần 2. Nếu lần 2 vẫn `open_ok = False`, runner mới dừng phiên, ghi nhận `(lần 2)` và chuyển trạng thái `MANUAL_REVIEW` để giữ hiện trường.
