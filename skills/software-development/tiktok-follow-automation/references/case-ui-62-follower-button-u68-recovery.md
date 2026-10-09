# Case UI-62: TikTok v46.9.3 Follower List Button Obfuscation Recovery (`id/u68`)

## Hiện trường sự cố (Farm Alert Ca 2 Chiều 14/09/2026)
- **Cảnh báo diện rộng:** 27 máy dừng phiên Follow TikTok Mode 2 đồng loạt: M3, M10, M23, M26, M27, M29, M32, M33, M35, M40, M41, M42, M43, M45, M46, M48, M50, M51, M53, M54, M55, M58, M59, M60, M63, M65, M71.
- **Triệu chứng log:** `status: "MANUAL_REVIEW"`, `reason: "MANUAL_REVIEW: follower row không có nút follow semantic"`, `followed_count: 0`, `failed: 1`.

## Nguyên nhân gốc rễ (Root Cause)
1. Trên TikTok v46.9.3, song song với việc đổi `RecyclerView` danh sách quan hệ sang `id/uzs` (Case UI-61), TikTok tiếp tục làm rối (obfuscate) các nút bấm quan hệ trên mỗi dòng người dùng (`txt_user_name` / `txt_desc`):
   - Nút **"Follow"** và **"Bạn bè"** được đổi resource-id thành `com.ss.android.ugc.trill:id/u68` (trước đó là `id/u2f`, `id/tcj`, `id/tvn`...).
2. Danh sách selector `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` trong `follow_runner/core/selectors.py` thiếu `id/u68`:
   - Hàm `_cluster_follower_rows` không nhận diện được button để ghép cặp với hàng tương ứng (`r["follow_button"] is None`).
3. Bộ lọc `missing_button_rows` trong `run_mode2`:
   - Thấy hàng người dùng nằm giữa khung nhìn (không phải top/bottom cutoff) nhưng không có nút bấm follow semantic hợp lệ.
   - Kích hoạt cơ chế an toàn fail-closed: ngắt phiên lập tức và ném `MANUAL_REVIEW: follower row không có nút follow semantic` để bảo vệ tài khoản khỏi việc tap mù/sai tọa độ.

## Giải pháp chuẩn hóa (Case Fix)
1. **Mở rộng Selector:**
   Bổ sung `com.ss.android.ugc.trill:id/u68`, `:id/u68`, `id/u68` vào tuple `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` tại `follow_runner/core/selectors.py`:
   ```python
   FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS = (
       "com.ss.android.ugc.trill:id/tcj", "com.ss.android.ugc.trill:id/thb", "com.ss.android.ugc.trill:id/tvn",
       "com.ss.android.ugc.trill:id/tum", "com.ss.android.ugc.trill:id/u2f", "com.ss.android.ugc.trill:id/u68",
       ":id/tcj", ":id/thb", ":id/tvn", ":id/tum", ":id/u2f", ":id/u68",
       "id/tcj", "id/thb", "id/tvn", "id/tum", "id/u2f", "id/u68",
   )
   ```
2. **Unit Tests Hồi Quy (`test_mode2_follow_followers.py`):**
   - `test_follow_button_for_row_supports_id_u68`: Kiểm tra `_follow_button_for_row` tìm thấy nút `id/u68` theo y-overlap.
   - `test_cluster_follower_rows_supports_id_u68`: Kiểm tra `_cluster_follower_rows` gán đúng nút `id/u68` cho cả 2 trạng thái "Follow" và "Bạn bè".
3. **Live Canary Verification:**
   - Dùng file dump XML live từ máy thật (`canary_m10_live_dump.xml`) chạy kiểm chứng hàm `_collect_follower_rows`:
     Nhận diện chính xác 4/4 hàng và 4/4 nút bấm `id/u68` (Follow và Bạn bè), 0 hàng thiếu button.
