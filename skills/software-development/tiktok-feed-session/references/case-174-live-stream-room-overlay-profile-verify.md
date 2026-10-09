# Case 174 (16/09/2026): TikTok LIVE Stream Room Che Navigation Bar Khi Verify Profile (Sự Cố Máy 77)

## 1. Hiện tượng & Triệu chứng thực tế
- Farm Alert `[MÁY 77]` báo lỗi tại bước cuối phiên nuôi acc / lướt feed:
  `feed-session-smoke blocked: profile verification navigation-failed: navigation target profile not found in XML`
- Quá trình swipe video diễn ra bình thường (đạt đủ số swipe yêu cầu, ví dụ 21/21 swipes).
- Khi kết thúc phiên chuyển sang bước `verify_profile`, runner gọi `tap_navigation_target(target="profile")` nhưng không tìm thấy tab Hồ sơ ở đáy màn hình.

## 2. Phân tích Hiện trường & Root Cause
- Trích xuất UI XML tại `swipe_21_after`: Màn hình đang hiển thị luồng TikTok LIVE stream (`com.ss.android.ugc.trill`).
- Toàn bộ thanh điều hướng đáy (Bottom Navigation Bar) bị che khuất bởi giao diện tương tác phòng LIVE:
  - Header/Banner: `Thử thách LIVE lân cận`, `14–28/9 Nhận thưởng tiền mặt`.
  - Chat/Activity feed: `‎Mắt 2 mí giao diện 1 mí đã chia sẻ phiên LIVE`.
  - Bottom bar bị thay bằng: ô nhập bình luận (`Nhập...`), nút chia sẻ video/live (`1.1K lượt chia sẻ`).
- **Anti-Pattern trong detector**:
  - Hàm `_detect_tiktok_live_room` trong `python_runner/flows/benign_popup_registry.py` chỉ kiểm tra các marker cũ như `"phòng live"`, `"chia sẻ live"`, `"nhập bình luận..."`, `"xếp hạng mua sắm"`, v.v.
  - Bỏ sót các biến thể thông báo mới của TikTok: `"phiên live"`, `"thử thách live lân cận"`, `"thu thach live lan can"`.
  - Do đó `find_matching_handler` trả về `None`, không nhận diện được màn hình LIVE để gửi phím BACK thoát về feed, dẫn đến fail-closed `navigation target profile not found in XML`.

## 3. Quy trình Xử lý & Patch Chuẩn
1. **Mở rộng marker nhận diện trong `benign_popup_registry.py`**:
   Bổ sung các chuỗi:
   - `"phiên live"`
   - `"thử thách live lân cận"`
   - `"thu thach live lan can"`
2. **Kiểm thử hồi quy (Unit Test)**:
   Thêm test case `test_detect_tiktok_live_room_session_share_and_challenge` trong `test_benign_popup_registry.py` với đoạn XML thực tế từ Máy 77.
3. **Kỷ luật Chốt phiên (Closeout Protocol)**:
   - Khi chạy `closeout_gate.py`, nếu có các thay đổi WIP khác trong working tree (ví dụ thử nghiệm swipe tốc độ cao trong `feed_swipe_smoke.py`), phải `git stash` để tách biệt, giữ candidate diff tinh gọn tập trung vào đúng phạm vi sửa lỗi popup.
   - Nhờ đó Sol Web (:20129) review model `review` pass ngay lập tức (`APPROVED`).
