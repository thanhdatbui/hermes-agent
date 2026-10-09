# TikTok Feed Session: Account Switcher 8-Roster, Draft Banner & Cold-Start Network Recovery (2026-10-05)

## 1. Bẫy Account Switcher trên dàn 8 nick (Standard Roster)
- **Hiện tượng**: Màn hình Switcher hiện đầy đủ 8 tài khoản nhưng script báo `manual-needed: account switcher requires manual review`.
- **Nguyên nhân 1 (Nút "Thêm tài khoản" bị đẩy off-screen)**:
  * Khi thiết bị nạp đủ 8 nick, danh sách tài khoản chiếm trọn chiều cao màn hình.
  * Nút "Thêm tài khoản" bị cuộn xuống đáy màn hình (off-screen, không có trong dump XML ban đầu).
  * Hàm nhận diện `_is_profile_account_switcher_xml` nếu bắt buộc đồng thời `has_title` và `has_add_account` sẽ fail-closed oan.
  * **Giải pháp**: Nhận diện Switcher hợp lệ khi có `has_title` ("Chuyển đổi tài khoản") VÀ `account_rows` chứa danh sách username, không bắt buộc phải nhìn thấy nút "Thêm tài khoản".
- **Nguyên nhân 2 (Tap tâm `x=540` rơi vào khoảng trống)**:
  * Trên Samsung S7 Android 8, mỗi hàng tài khoản trong Switcher là 1 container rộng 1080px (`[0, y1][1080, y2]`).
  * Tên tài khoản và avatar nằm ở nửa bên trái (`x=0..600`).
  * Nếu tính tâm `x = (0 + 1080) / 2 = 540`, tọa độ rơi vào khoảng trống giữa username và mép phải màn hình, UI Samsung không bắt sự kiện click item.
  * **Giải pháp**: Giới hạn bề rộng hàng (`clamp` max x = 700px), dịch tọa độ tap sang bên trái (`x=350`) để rơi trúng chữ và avatar tài khoản.

## 2. Bẫy Banner Lỗi Upload / Bản Nháp Che Khuất Header Profile
- **Hiện tượng**: Bot vào trang Profile nhưng không đọc được username / display name, báo `profile account mismatch and profile username/display name anchor is unavailable`.
- **Nguyên nhân**:
  * Banner lỗi upload cũ: *"Không thể tải video lên. Đã lưu bản nháp. Chạm để thử lại"* (resource-id `tv_tips`, nút đóng `ea5` tại `[960,138][1008,186]`) che phủ toàn bộ header phía trên.
  * Mục danh mục "Bản nháp: 1" bị bắt nhầm thành display name.
- **Giải pháp**:
  * Tự động phát hiện banner `tv_tips` / *"Không thể tải video lên"* và bấm nút đóng `ea5` để giải phóng header.
  * Thêm tiền tố `"bản nháp"`, `"draft"` vào `profile_placeholder_texts` để không bao giờ nhận vơ tab nháp làm tên nick.

## 3. Bẫy Cold-Start Network Error & Swipe Recovery Vô Ích
- **Hiện tượng**: Khi TikTok vừa bật lên, mạng chưa nạp kịp nên app hiện màn hình: *"Không có kết nối Internet. Hãy nhấn để thử lại."* kèm nút *"Thử lại"* (`dd9`). Script cố vuốt màn hình (`swipe_recovery`) nhưng vô hiệu, dẫn đến kẹt và dừng phiên.
- **Nguyên nhân cốt lõi**:
  * Proxy và Wi-Fi hoàn toàn sống 100%, nhưng delay khởi động cold-start của TikTok kích hoạt fallback mạng tạm thời.
  * Bấm thử lại nhưng không chờ đủ thời gian nạp lại socket, post-condition kiểm tra lại ngay vẫn thấy marker mạng.
  * Script kích hoạt `swipe_recovery_on_stuck` trên màn hình lỗi mạng: Thao tác vuốt feed trên màn hình lỗi mạng là **hoàn toàn vô ích** (không trigger reload).
- **Giải pháp dứt điểm**:
  1. Trong `benign_popup_registry.py`: Bấm chính xác nút retry `dd9`, hậu kiểm XML sau delay; nếu còn marker mạng trả `network_retry_postcondition_failed` rõ ràng, cấm tap mù giữa màn hình.
  2. Trong `feed_swipe_smoke.py`: Loại trừ `NETWORK_RETRY_SCREENS` khỏi `_swipe_recovery_on_stuck`. Tuyệt đối không vuốt màn hình khi đang ở màn hình lỗi mạng.
  3. Kích hoạt `_network_force_stop_recovery`: Nếu thử lại không hết, tự động force-stop và relaunch app sạch với `allow_network_force_stop_recovery = True` để nạp lại phiên TikTok mới.
