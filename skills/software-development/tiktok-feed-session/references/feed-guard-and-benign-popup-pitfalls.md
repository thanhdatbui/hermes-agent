# TikTok Main Feed Guard & Benign Popup Pitfalls

## 1. Pitfall: False-Positive Popup Detection Trên Main Feed
- **Nguyên nhân**: Trong `benign_popup.py` và `benign_popup_registry.py`, các detector (như `detect_follow_friends_suggestion_popup`, `_detect_follow_friends`) sử dụng danh sách keyword/marker ngắn như `"Follow lại"`, `"Follow bạn"`, `"Bạn bè với"`, `"Mời bạn bè"`.
- **Hệ quả trên feed thật**:
  - Khi lướt feed, nếu gặp video của tài khoản đang follow lại ta, nút bên cạnh hiển thị `"Follow lại"`.
  - Caption video có thể chứa `"Bạn bè với"`.
  - Thanh header trên cùng chứa tab `"Bạn bè"` nằm ngang hàng với `"Đề xuất"` (cùng dải tọa độ $y_1 \approx 72, y_2 \approx 246$).
  - Detector text đơn thuần kích hoạt nhầm $\rightarrow$ script gọi dismisser (`_dismiss_follow_friends`), bấm nhầm nút follow hoặc back thoát khỏi feed.

## 2. Chuẩn Thiết Kế: Feed Guard Pattern
Mọi hàm detect popup dễ lẫn với feed phải tuân thủ Feed Guard:
1. **Nhận diện Main Feed**:
   - Tab feed: Text/desc chứa `"Đề xuất"`, `"Dành cho bạn"`, `"For You"`.
   - Bottom navigation bar: Chứa `"Trang chủ"`, `"Hồ sơ"`.
   - Interaction controls: `"Đăng lại cho follower"`, `"Thêm bình luận"`, `"Bóc tem"`.
2. **Kiểm tra Container Popup Thực Sự**:
   - Nếu màn hình là Main Feed, BẮT BUỘC phải có container/modal thực sự:
     - `android.app.Dialog` hoặc modal container.
     - Popup card có nút đóng X / Đóng / 'Không quan tâm' (xác thực qua semantic close control).
     - Text đặc trưng subpage/popup kết bạn: `"Tìm bạn bè trong danh bạ"`, `"Sử dụng mã QR"`, `"Tìm bạn bè trên Facebook"`.
   - Nếu là Main Feed và KHÔNG có container/nút đóng popup thực sự $\rightarrow$ `return False`.
3. **Quy tắc Top Tab "Bạn bè"**:
   - Kiểm tra bounds của element chứa `"Bạn bè"`: Nếu nằm ở khu vực top bar ($y_1 < 350$, cùng hàng với `"Đề xuất"`) $\rightarrow$ bỏ qua, không coi là popup.

## 3. Kỷ Luật Canary Test (Chống Quá Nhiệt Tool Budget)
- Khi nhận yêu cầu sửa popup và chạy canary test:
  1. Mở trực tiếp hàm mục tiêu trong `benign_popup.py` / `benign_popup_registry.py`.
  2. Patch logic tối thiểu.
  3. Kiểm tra cú pháp bằng `python -m py_compile`.
  4. Chạy ngay canary script (ví dụ: `run-feed-session.ps1 -Machines <N> -RecoveryTestSwipes 2 ...`).
  5. Tuyệt đối không tiêu tốn tool iterations vào grep diện rộng hay đọc lặp lại các file XML dump mẫu.
