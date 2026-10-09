# TikTok Follow Mode 2: Anchor Gating & Safe-Skip Protocol

Tài liệu chuẩn hoá cơ chế bốc Anchor và xử lý khi Anchor không có video trên farm TikTok (Case 153 - 13/09/2026).

## 1. Ngăn chặn Anchor chưa đủ video (Anchor Gating)
- **Vấn đề thực tế**: Trong Mode 2, `anchor_uids()` bốc ngẫu nhiên 3 nick từ danh sách Row 1 & Row 2 làm seed anchor. Tuy nhiên, một số máy mới reg hoặc chưa đăng đủ video (như M80: 2 video, M30: 2 video, M65: 4 video) dẫn đến runner bốc trúng nick không có hoặc chưa đủ video.
- **Giải pháp**:
  - `anchor_uids(self)` BẮT BUỘC lọc thêm điều kiện `row_video_counts.get(uid, 0) >= 5`.
  - Chỉ cho phép các tài khoản Row 1/2 có từ 5 video trở lên làm seed anchor.
  - Fallback an toàn: Nếu tập dữ liệu hoặc mock unit test không có `video_count`, mới fallback về điều kiện Row <= 2 gốc.

## 2. Selector nhận diện Video Cover Grid trên TikTok 46.x (Samsung S7)
- **Triệu chứng**: Anchor đã đăng 19-21 video (như M18, M26, M58...) nhưng runner vẫn kết luận `anchor không có video`.
- **Nguyên nhân**: Bản cập nhật TikTok mới trên Samsung S7 không còn đặt chuỗi `cover` trong `resource-id` của các ô video trên trang cá nhân. Thay vào đó, layout sử dụng:
  - `id/exx`: FrameLayout bao quanh mỗi item video trong GridView `id/i3s`.
  - `id/tv_play_count`: TextView hiển thị lượt xem ở góc dưới mỗi thumbnail.
  - `id/aweme` / `cover`: Dự phòng cho các phiên bản giao diện khác.
- **Quy tắc Selector**:
  ```python
  video_covers = [
      n for n in profile_nodes
      if any(k in str(n.get("resource_id", "")).lower() for k in ("cover", "tv_play_count", "exx", "aweme"))
      and n.get("bounds")
      and isinstance(n["bounds"], (list, tuple))
      and len(n["bounds"]) == 4
      and n["bounds"][1] >= 400
  ]
  ```

## 3. Safe-Skip Protocol (Chống False Alarm "Lỗi script/xác minh")
- **Anti-pattern**: Khi Anchor không có video, runner trả về `MANUAL_REVIEW` với `exit_code: 1`. Kết quả là Watchdog farm gom toàn bộ các máy này vào nhóm "Lỗi script/xác minh" (gây hoang mang báo động giả 22 máy lỗi).
- **Pattern chuẩn**:
  - Khi Anchor thực sự không có video sau khi kiểm tra grid và swipe nhẹ:
    - Đặt `engine._last_anchor_follow_outcome = "no_video"`.
    - Back về feed an toàn và chuyển sang Anchor tiếp theo trong vòng lặp (`run_mode2`).
    - Nếu hết cả 3 anchor mà đều bị `no_video` / `zero_following`, phiên kết thúc với trạng thái `status: "SKIPPED"` và lý do rõ ràng `anchors_all_skipped_safe`.
    - TUYỆT ĐỐI KHÔNG ném lỗi `MANUAL_REVIEW` hay crash exit code khi chỉ đơn thuần là anchor được bốc không đủ điều kiện video.
