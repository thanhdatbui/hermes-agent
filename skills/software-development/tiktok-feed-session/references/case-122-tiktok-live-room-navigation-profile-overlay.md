# Case 122: TikTok LIVE Room Overlay Che Khuất Navigation Profile Tại Bước Verify Profile (Sự Cố Máy 77 - Nick rudysbhzx4h)

## 1. Hiện Tượng & Dấu Hiệu Nhận Diện
- **Farm Alert:**
  ```text
  Máy M77: profile verification navigation-failed: navigation target profile not found in XML
  ```
- **Triệu chứng tại hiện trường:**
  - Phiên nuôi acc hoàn thành trọn vẹn số lượt swipe (ví dụ 21/21 swipes).
  - Khi chuyển sang bước `verify_profile` sau phiên, runner gọi `tap_navigation_target(target="profile")`.
  - Thiết bị đang kẹt trong màn hình livestream / phòng LIVE TikTok (do người dùng bị điều hướng vào luồng LIVE stream hoặc chia sẻ phiên LIVE).
  - Không có thanh điều hướng đáy (`Hồ sơ` / `Profile`, `Trang chủ` / `Home`), dẫn đến lỗi `navigation target profile not found in XML`.
  - Classifier nhận diện nhầm màn hình LIVE là `for-you` do có các nút tương tác chia sẻ (`chia sẻ video`, `repost`, `follow`).
  - Runner bỏ qua phím BACK vì logic an toàn tưởng app đang ở Home/Feed (`navigation_back_recovery_skipped_at_home_feed`), khiến thiết bị không thoát khỏi phòng LIVE.

## 2. Nguyên Nhân Kỹ Thuật
- Trong `benign_popup_registry.py`, hàm `_detect_tiktok_live_room` quét danh sách `live_markers`.
- TikTok cập nhật các biến thể UI LIVE mới:
  - Text tiếng Việt: `"đã chia sẻ phiên LIVE"` -> chứa cụm `"phiên live"`.
  - Banner/Widget sự kiện: `"Thử thách LIVE lân cận"`, `"14–28/9 Nhận thưởng tiền mặt"`.
  - Các biến thể này thiếu trong `live_markers` của `_detect_tiktok_live_room`, khiến `find_matching_handler` trả về `None`, không kích hoạt `_dismiss_tiktok_live_room`.

## 3. Giải Pháp Kỹ Thuật Chuẩn
1. **Bổ sung marker vào `_detect_tiktok_live_room`:**
   Thêm các cụm từ nhận diện đặc trưng vào `live_markers`:
   - `"phiên live"`
   - `"thử thách live lân cận"`
   - `"thu thach live lan can"`
2. **Xác lập Test Coverage:**
   Bổ sung unit test trong `tests/test_benign_popup_registry.py` kiểm tra dump XML thực tế từ phòng LIVE (chứa banner thử thách và chia sẻ phiên LIVE) phải khớp `_detect_tiktok_live_room`.
3. **Quy tắc điều phối Coordinator (Gate 2 & Gate 4):**
   - Xác định file UI XML thực tế tại `artifacts/.../swipe_N_after/attempt_1/ui.xml`.
   - Trích xuất text/id gây cản trở và đối soát với detector registry.
   - Soạn Patch Contract đóng với exact `old_string` -> `new_string`, cấp cho worker subagent kèm lệnh test focused <30s.
