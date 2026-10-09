# Canary Patch Budget Exhaustion & TikTok Feed Guard Pattern

## 1. Sự Cố Chạm Trần Iteration Khi Nhận Task Patch + Canary (06/09/2026)
- **Bối cảnh**: Agent nhận chỉ thị rõ ràng:
  1. Patch feed guard vào `detect_follow_friends_suggestion_popup` (`benign_popup.py`) và `_detect_follow_friends` (`benign_popup_registry.py`).
  2. `python -m py_compile` cả 2 file.
  3. Chạy canary test trên Máy 9 (`run-feed-session.ps1 -Machines 9 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`).
- **Sai lầm gây kiệt quệ tool budget**:
  - Agent đọc nguyên file dump XML `m10_tiktok.xml` (trên 66.000 ký tự) để kiểm chứng cấu trúc feed.
  - Chạy nhiều lệnh tìm kiếm kiểm tra các hàm phụ trợ không cần thiết.
  - Chạm trần `max_iterations = 35` trước khi kịp ghi patch xuống đĩa và kích hoạt canary test.
- **Quy tắc đúc kết (Lean Execution)**:
  - Khi đã có file đích và số dòng hoặc tên hàm: đọc đúng hàm đó, patch ngay, chạy `py_compile`, và kích hoạt canary test ngay lập tức.
  - Tuyệt đối không đọc toàn bộ XML dump lớn chỉ để "xem cho biết" cấu trúc UI.

---

## 2. Bản Chất Lỗi: False-Positive Popup Detection Trên TikTok Main Feed
- Trong `benign_popup.py` và `benign_popup_registry.py`, các detector kết bạn (`detect_follow_friends_suggestion_popup`, `_detect_follow_friends`) sử dụng marker:
  `["Follow bạn bè của bạn", "Follow your friends", "Gợi ý follow", "Follow lại", "Follow back", "Theo dõi lại", "Follow bạn", "Bạn bè với", "Mời Bạn bè", "Tìm Bạn bè", "Sử dụng mã QR", "Tìm bạn bè trong danh bạ"]`.
- Khi tài khoản lướt feed video thông thường:
  1. Nếu gặp video của người theo dõi mình, nút bên phải hiển thị `"Follow lại"` hoặc `"Bạn bè với"`.
  2. Caption hoặc bình luận video có thể chứa `"Bạn bè với"` hoặc `"Mời bạn bè"`.
  3. Top tab bar có tab `"Bạn bè"` nằm cùng hàng với `"Đề xuất"` (cùng dải tọa độ $y_1 \approx 72, y_2 \approx 246$).
- Khi detector chỉ so khớp text đơn thuần:
  - Hệ thống nhận diện nhầm video feed là popup gợi ý kết bạn.
  - Dẫn đến việc kích hoạt dismisser (`_dismiss_follow_friends`), bấm nhầm nút follow tài khoản hoặc bấm phím Back thoát khỏi feed, làm gián đoạn phiên nuôi acc.

---

## 3. Kiến Trúc Chuẩn: 3 Lớp Feed Guard Cho Benign Popup
Khi viết detector cho popup dễ bị lẫn với feed (bạn bè, đề xuất follow, tương tác):

1. **Lớp 1 - Nhận diện Main Feed**:
   - Tab feed: Text hoặc `content-desc` chứa `"Đề xuất"`, `"Dành cho bạn"`, `"For You"`.
   - Bottom navigation bar: Chứa `"Trang chủ"`, `"Hồ sơ"`.
   - Video interaction controls: `"Đăng lại cho follower"`, `"Thêm bình luận"`, `"Bóc tem"`.
2. **Lớp 2 - Kiểm tra Container / Dialog Thực Sự**:
   - Nếu màn hình mang đặc trưng Main Feed, BẮT BUỘC phải tồn tại container/dialog thực sự:
     - Class `android.app.Dialog` hoặc modal container.
     - Popup card có nút đóng X / Đóng / 'Không quan tâm' (xác thực qua semantic close control).
     - Subpage kết bạn chuyên biệt: `"Tìm bạn bè trong danh bạ"`, `"Sử dụng mã QR"`, `"Tìm bạn bè trên Facebook"`.
   - Nếu là Main Feed và KHÔNG có container/nút đóng popup thực sự $\rightarrow$ Trả về `False`.
3. **Lớp 3 - Lọc Top Tab "Bạn bè"**:
   - Nếu từ khóa `"Bạn bè"` xuất hiện ở khu vực top tab ($y_1 < 350$, ngang hàng với `"Đề xuất"`): Bỏ qua, tuyệt đối không coi đó là dấu hiệu của popup bạn bè.
