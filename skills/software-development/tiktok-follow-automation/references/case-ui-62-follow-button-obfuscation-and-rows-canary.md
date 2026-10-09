# Case UI-62: TikTok v46.9.3 Follow Button Obfuscation & Dynamic Rows Canary Recovery

## 1. Hiện trường sự cố (Farm Alert Ca 2 Row 4 - 27 Máy)
- **Triệu chứng**: 27 máy dừng phiên đồng loạt trong Ca 2 - Phiên 2 (Row 4) với lỗi:
  `MANUAL_REVIEW: follower row không có nút follow semantic`
- **Môi trường**: TikTok v46.9.3 trên Samsung S7 (Android 7).

## 2. Nguyên nhân gốc rễ (Root Cause)
- Trên TikTok v46.9.3, ngoài việc danh sách quan hệ đổi sang RecyclerView `id/uzs`, các nút quan hệ ("Follow" và "Bạn bè") trong follower/following list đã đổi resource-id thành `com.ss.android.ugc.trill:id/u68` (trước đó là `id/u2f`, `id/tum`, `id/tcj`...).
- Danh sách `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` trong `follow_runner/core/selectors.py` thiếu `id/u68`.
- Hàm `_cluster_follower_rows` không gán được button cho row (`r["follow_button"] is None`).
- Bộ lọc `missing_button_rows` phát hiện hàng hiển thị đầy đủ nhưng không có nút semantic hợp lệ nên fail-closed, ngắt phiên và chuyển sang trạng thái `MANUAL_REVIEW`.

## 3. Giải pháp chuẩn (Case Fix)
1. **Bổ sung Selector**:
   Thêm `com.ss.android.ugc.trill:id/u68`, `:id/u68`, `id/u68` vào bộ tuple `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` trong `follow_runner/core/selectors.py`.
2. **Targeted Canary Hook**:
   Thêm canary hook `inspect_following_rows` vào CLI entrypoint `run_follow.py`:
   - Mở tab following của target anchor qua `_open_following_tab`.
   - Dump UI qua `adapter.dump_ui()` và parse nodes.
   - Gọi `_collect_follower_rows(nodes)` để xác nhận trực tiếp số hàng và số nút bấm `id/u68` nhận diện được trên màn hình thiết bị thật (<60s) thay vì chạy cả pipeline.
3. **Cơ chế Import trong CLI**:
   Khi `run_follow.py` được thực thi trực tiếp dạng top-level script (`python run_follow.py`), các import bên trong nhánh canary bắt buộc dùng absolute import (`from follow_runner.flows...`), tuyệt đối không dùng relative import (`from .flows...`) gây `ImportError: attempted relative import with no known parent package`.
