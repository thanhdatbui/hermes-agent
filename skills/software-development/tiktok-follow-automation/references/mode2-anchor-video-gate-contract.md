# Mode 2 Anchor Video Gate & Selection Contract

## 1. Anchor Selection Contract (follow_engine.py)
- **Tiêu chuẩn anchor chất lượng**:
  - `account_row_index <= 2` (Nick Tik1/Tik2 đã qua seed).
  - `video_count >= 5` (dựa trên mapping từ workbook/rows để đảm bảo profile có video và đủ tương tác).
  - Fallback: Nếu không tìm thấy anchor nào thỏa mãn `video_count >= 5`, fallback về anchor có `account_row_index <= 2` để đảm bảo tương thích mock unit test / dữ liệu chưa có trường `video_count`.

## 2. Anchor Profile Video Discovery & Outcome Handling (mode2_follow_followers.py)
- **Selector video covers**:
  - Ngoài check keyword `cover` trong `resource_id`, cần bao quát thêm:
    - `tv_play_count`
    - `exx`
    - `aweme`
  - Đảm bảo nhận diện đúng các node item video dạng grid trên profile TikTok phiên bản mới.
- **Handling khi Profile Anchor không có video (`no_video`)**:
  - Khi profile hoàn toàn không tìm thấy video cover sau khi swipe thử:
    - Gán `engine._last_anchor_follow_outcome = "no_video"`.
    - Ghi log cảnh báo và lưu lý do: `anchor @{uid} không có video — back ra bỏ qua`.
    - Gọi `adapter.back()` an toàn để quay về feed.
    - Tại vòng lặp điều phối `run_mode2`:
      - Bổ sung `"no_video"` vào tuple outcome skip an toàn: `("zero_following", "not_found", "no_video")`.
      - Khi gặp outcome `"no_video"`, thực hiện back feed và `continue` thử anchor kế tiếp, tuyệt đối không đánh trượt sang `MANUAL_REVIEW` hay `FOLLOW_FAILED`.
