# Loại trừ Node Tiêu đề Đổi tên Hồ sơ khỏi Switcher Anchor (Case UI-11)

## Bối cảnh & Triệu chứng
- Khi chạy `multi-machine-feed-session` (hoặc `feed_swipe_smoke`), luồng `profile_preflight_switch` thực hiện tìm anchor để click mở danh sách chuyển đổi tài khoản (Account Switcher bottom sheet).
- Trên các tài khoản chưa thiết lập username `@...` (chỉ có Display Name như "Huy Mập") hoặc giao diện TikTok hiển thị thanh tiêu đề giữa, `find_switcher_anchor` (trong `automation_core.tiktok.account_switcher`) và `_find_sticky_profile_header` (trong `feed_swipe_smoke.py`) nhận diện nhầm node `com.ss.android.ugc.trill:id/pkh` / `pke` (tọa độ tâm `[540, 150]`) làm switch anchor.
- Việc tap trúng `pkh`/`pke` khiến TikTok mở trang "Đổi tên" (`tv_content_name` / "Thêm tên bạn mong muốn") và bật bàn phím ảo Samsung IME.
- Khi popup registry dismiss bằng nút Hủy/phím Back, script quay lại Profile root và tiếp tục tap lại `pkh` $\rightarrow$ lặp vô hạn và fail-closed dừng phiên với lỗi `known TikTok screen` / `account switcher blocked by manual-needed screen`.

## Quy tắc Loại trừ Chuẩn (Negative Exclusions)
Trong cả `automation_core.tiktok.account_switcher` và consumer `feed_swipe_smoke.py`:
1. Tuyệt đối không chọn các node có resource-id thuộc cụm sửa tên hồ sơ làm switch anchor:
   - `com.ss.android.ugc.trill:id/pkh`
   - `com.ss.android.ugc.trill:id/pke`
   - `com.ss.android.ugc.trill:id/pau`
   - `com.ss.android.ugc.trill:id/s9b`
   - `tv_content_name`
2. Trong `generic_candidates` của `find_switcher_anchor`:
   - Phải kiểm tra và loại trừ mọi node có resource-id kết thúc bằng các suffix trên trước khi thêm vào danh sách ứng viên header.
3. Trong `_find_sticky_profile_header` của consumer:
   - Thêm guard loại trừ tương tự ở cả nhánh `display_name_anchor_element`, `display_name_element` và generic header fallback.
