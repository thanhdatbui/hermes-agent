# Feed Main Guard: Tránh nhận diện nhầm Feed chính thành Follow Friends Suggestion Popup

## 1. Hiện tượng & Bối cảnh
- Khi chạy Feed session trên dàn máy TikTok (ví dụ Máy 9), detector benign popup nhận diện nhầm màn hình Feed chính (For You / Đề xuất) thành popup gợi ý kết bạn `follow_friends_suggestion_popup`.
- Hậu quả: Hệ thống kích hoạt handler dismiss popup cho Feed chính, cố gắng tìm nút Đóng/X hoặc bấm nhầm nút Follow trên avatar creator, gây lỗi hoặc abort session lướt feed.

## 2. Nguyên nhân kỹ thuật (Root Cause)
- Cả `detect_follow_friends_suggestion_popup` (`flows/benign_popup.py`) và `_detect_follow_friends` (`flows/benign_popup_registry.py`) đều duyệt danh sách `markers`:
  `["Follow bạn bè của bạn", "Follow your friends", "Gợi ý follow", "Follow lại", "Follow back", "Theo dõi lại", "Follow bạn", "Bạn bè với", "Mời Bạn bè", "Tìm Bạn bè", ...]`
- Trên màn hình Feed chuẩn của TikTok:
  1. Top tab bar có mục `"Bạn bè"` đứng ngang hàng với `"Đề xuất"` (hoặc `"For You"`).
  2. Giao diện Feed có nút `"Đăng lại"` (Repost), video engagement bar (tim, comment, bookmark, share), caption video hoặc avatar có nút Follow.
  3. Khi quét XML hoặc OCR text, các cụm từ trong caption/tab như `"Bạn bè"`, `"Follow bạn"` dễ làm khớp nhầm marker nếu thiếu guard loại trừ màn hình Feed chính.

## 3. Quy tắc Feed Guard (Negative Exclusion) chuẩn
Trước khi kết luận màn hình là popup/card gợi ý kết bạn:
1. **Kiểm tra dấu hiệu Feed chính:**
   - Text hoặc content-desc chứa `"Đề xuất"`, `"Dành cho bạn"`, `"For You"`.
   - Hoặc có tab bottom `"Trang chủ"` / `"Home"` đi kèm video engagement bar / nút `"Đăng lại"` / `"Repost"`.
2. **Kiểm tra vị trí tab "Bạn bè":**
   - Nếu text `"Bạn bè"` chỉ xuất hiện ở thanh tab top (cùng tọa độ $y$ ngang hàng với `"Đề xuất"`, thường ở $y < 350$), đó là tab điều hướng của TikTok, KHÔNG phải popup.
3. **Kiểm tra Modal / Card thực tế:**
   - Một modal/card gợi ý kết bạn thực sự phải có container riêng kèm:
     - Tiêu đề modal rõ ràng: `"Follow bạn bè của bạn"`, `"Gợi ý follow"`, `"Người bạn có thể biết"`, `"Tìm bạn bè"`.
     - Hoặc có các action row mời bạn bè chuyên biệt: `"Sử dụng mã QR"`, `"Tìm bạn bè trong danh bạ"`, `"Tìm bạn bè trên Facebook"`, `"Mời bạn bè"`.
     - Hoặc có nút đóng modal ngữ nghĩa riêng: `"Không quan tâm"`, `"Đóng"`, `"✕"` (resource-id `:id/c3t`, `:id/e63`, `:id/e8c`).
4. **Quyết định:**
   - Nếu màn hình là Feed chính và KHÔNG có modal/card chứa các hành động kết bạn / mời bạn bè thực sự, HOẶC nếu text `"Bạn bè"` chỉ là tab top bar: **BẮT BUỘC trả về `False`**.

## 4. Kỷ luật vận hành & Anti-Disk-Scan
- Tuyệt đối không dùng `os.walk`, `find` hoặc quét đĩa diện rộng để tìm file/log (dễ gây timeout shell).
- Trỏ thẳng vào file đích:
  - `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/benign_popup.py`
  - `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/benign_popup_registry.py`
- Luôn kiểm tra cú pháp bằng `python -m py_compile` và chạy canary test trên máy chỉ định (ví dụ Máy 9).
