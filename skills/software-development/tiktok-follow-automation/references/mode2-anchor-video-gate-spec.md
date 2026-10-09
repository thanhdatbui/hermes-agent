# Mode 2 Anchor Selection & Video Gate Specification

## 1. Điều Kiện Lọc Anchor (Anchor Gating)
- **Quy tắc**: Chỉ các tài khoản thuộc Tik1/Tik2 (Row 1 hoặc Row 2 trong `taikhoan_run_safe.xlsx`) **VÀ** có số lượng video đã đăng `video_count >= 5` mới được chọn làm Anchor cho Mode 2.
- **Mục đích**:
  - Tránh lãng phí lượt search đối với các nick mới reg/chưa có video.
  - Ngăn ngừa việc tài khoản farm đi follow các anchor trống video, dẫn đến rủi ro bị TikTok coi là bot follow trần hoặc bị nhả follow ngay lập tức.
- **Fallback an toàn**: Nếu toàn bộ pool không có tài khoản nào đạt `>= 5` video (ví dụ môi trường test mock không cấp `video_count`), engine fallback về điều kiện `Row <= 2` để không làm crash pipeline test.

## 2. Nhận Diện Video Cover Trên Profile TikTok (UI Selector Drift)
- Trên các bản TikTok hiện đại (v46.x trên Samsung S7):
  - Khung hình / cover của video trong lưới cá nhân không còn cố định ID `cover`.
  - Các resource ID thực tế đại diện cho video item gồm: `com.ss.android.ugc.trill:id/exx` (FrameLayout chứa video item), `com.ss.android.ugc.trill:id/tv_play_count` (lượt xem video), hoặc các node chứa `aweme`.
  - Grid chứa video thường là `com.ss.android.ugc.trill:id/i3s` hoặc `com.ss.android.ugc.trill:id/uva` (ViewPager).
- **Bộ selector chuẩn**:
  ```python
  video_covers = [
      n for n in profile_nodes
      if any(k in str(n.get("resource_id", "")).lower() for k in ("cover", "tv_play_count", "exx", "aweme"))
      and n.get("bounds")
      and n["bounds"][1] >= 400
  ]
  ```

## 3. Cơ Chế Safe-Skip Khi Anchor Không Có Video
- Khi runner mở profile Anchor và kiểm tra không có video cover nào (kể cả sau 1 lần cuộn nhẹ):
  1. Ghi nhận trạng thái: `engine._last_anchor_follow_outcome = "no_video"`.
  2. Bấm back quay về Feed an toàn (`_back_to_feed`).
  3. Bỏ qua anchor này và duyệt tiếp Anchor kế tiếp trong danh sách (tối đa 3 anchor).
  4. Nếu hết toàn bộ 3 anchor mà không thể follow (do `no_video` hoặc `zero_following`), kết quả phiên trả về là:
     - `status: "SKIPPED"`
     - `reason: "anchors_skipped_safe"`
     - `exit_code: 0`
     - `failed: 0`
  5. **CẤM TUYỆT ĐỐI** trả về `MANUAL_REVIEW` hay `exit_code: 1` cho trường hợp này, vì đây là hành vi bypass an toàn chuẩn mực của farm, không phải lỗi kỹ thuật của script.
