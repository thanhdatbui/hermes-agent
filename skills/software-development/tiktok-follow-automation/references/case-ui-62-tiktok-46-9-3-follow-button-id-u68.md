# Case UI-62: TikTok 46.9.3 Follow Button Obfuscation (`id/u68`) & Targeted Canary Verification

## 1. Hiện trường sự cố (Farm Alert 27 Máy Ca 2 Phiên 2 - Row 4)
- **Triệu chứng**: 27 máy dừng phiên đồng loạt với cảnh báo:
  `MANUAL_REVIEW: follower row không có nút follow semantic`
- **Các máy bị ảnh hưởng**: 3, 10, 23, 26, 27, 29, 32, 33, 35, 40, 41, 42, 43, 45, 46, 48, 50, 51, 53, 54, 55, 58, 59, 60, 63, 65, 71.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **TikTok v46.9.3 Obfuscation Resource-ID nút quan hệ**:
   - Bên cạnh việc đổi `RecyclerView` danh sách quan hệ sang `id/uzs` (Case UI-61), TikTok 46.9.3 đổi toàn bộ resource-id của các nút bấm hành động ("Follow", "Follow lại", "Bạn bè") trong hàng follower/following thành `com.ss.android.ugc.trill:id/u68` (trước đó là `id/u2f`, `id/tcj`, `id/tum`, `id/tvn`).
2. **Thiếu id trong selector tuple**:
   - Trong `follow_runner/core/selectors.py`, `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` thiếu `id/u68`.
   - Kết quả: `_cluster_follower_rows` duyệt qua các hàng nhưng không gán được `follow_button` (`r["follow_button"] is None`).
   - Hàm `run_mode2` lọc `missing_button_rows`: thấy hàng người dùng hợp lệ nằm giữa màn hình nhưng không có nút semantic -> kích hoạt dừng phiên fail-closed sang `MANUAL_REVIEW`.

## 3. Quy tắc khắc phục (Case UI-62 Invariant)
1. **Mở rộng Selector**:
   - Bổ sung `com.ss.android.ugc.trill:id/u68`, `:id/u68`, `id/u68` vào tuple `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` trong `follow_runner/core/selectors.py`.
2. **Kỷ luật Targeted Canary (TARGETED-CANARY-GATE)**:
   - Khi sửa selector cho hàng/nút, BẮT BUỘC kiểm chứng thực tế qua targeted canary hook thay vì chỉ chạy unit test hoặc chỉ chụp ảnh Home.
   - Entrypoint targeted canary trong `run_follow.py` cần hỗ trợ hook kiểm tra nội hàm (`inspect_following_rows`) để verify trực tiếp tỷ lệ `valid_buttons / total_rows >= 1` trên màn hình live của máy thật trong <60s trước khi báo hoàn tất cho operator.
