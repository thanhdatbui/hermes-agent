# Mode 2 Anchor Open Following Tab Retry & Ladder Semantics

## Cơ chế Thử lại (2 Lần) & Recovery Ladder
Trong `follow_runner/flows/mode2_follow_followers.py` (`run_mode2`):
1. **Lần 1 (`_open_following_tab`)**: Runner tìm kiếm UID anchor (ví dụ `quyphuoc056`), vào Profile, xác thực identity, sau đó tap vào tab **"Đã follow"** (Following).
   - Chờ tối đa 10s để xác nhận bề mặt danh sách qua `_on_follower_list(nodes)`.
   - Nếu không nhận diện được danh sách hợp lệ (`_classify_follower_surface` trả về `invalid`), lần 1 thất bại.

2. **Chạy Recovery Ladder**:
   - Khi lần 1 fail, runner gọi `engine.recover_ui()` (ATX kill, force stop/relaunch app TikTok).
   - Kiểm tra và đưa máy quay về Feed (`_back_to_feed(engine)`).

3. **Lần 2 (`_open_following_tab`)**:
   - Runner thực hiện lại toàn bộ luồng tìm kiếm anchor và tap tab "Đã follow".
   - Nếu lần 2 tiếp tục không xác nhận được bề mặt danh sách hợp lệ, runner dừng phiên:
     `MANUAL_REVIEW: mở tab Đã follow fail cho <uid> sau ladder (lần 2)`
   - Trạng thái phiên chuyển sang `MANUAL_REVIEW`, kích hoạt cơ chế giữ nguyên hiện trường cho Hermes Agent/Admin kiểm tra.

## Chẩn đoán Hiện trường
- Nếu trên màn hình thiết bị thực tế đã mở đúng tab "Đã follow" (có header "Đã follow X", hiển thị danh sách nick và nút Follow):
  - Nguyên nhân chính: TikTok render RecyclerView hoặc text header chậm quá deadline 10s, hoặc resource ID / format header của phiên bản TikTok bị lệch khiến `_classify_follower_surface` đánh giá là `invalid`.
  - Cần kiểm tra XML dump thực tế (`mX_after_tap_following_tab.xml`) để kiểm tra `android:id/text1`, `selected=true`, và các node con trong ViewPager.
