# Quy Trình Tự Động Ghim Video Top View (TikTok Video Pinning) & Cạm Bẫy Đảo Lưới (Grid Reorder)

## 1. Bản Chất Nghiệp Vụ & Giới Hạn Của TikTok
- TikTok chỉ cho phép mỗi tài khoản ghim **tối đa 3 video** lên đầu trang cá nhân.
- Video được ghim sẽ hiển thị nhãn chữ nổi màu đỏ **"Đã ghim"** ở góc trên bên trái của thumbnail video.
- Thao tác ghim trên client Android:
  1. Mở video đích từ trang Profile.
  2. Bấm nút **Chia sẻ** (`...` hoặc icon Share ở thanh công cụ bên phải, tọa độ chuẩn S7 màn 1080x1920: `(999, 1556)`).
  3. Action Sheet trượt lên từ đáy màn hình chứa hàng công cụ quản trị video của chính chủ: tìm nút mang nhãn **"Ghim"** / **"Pin"** để click.
  4. Nếu video đã được ghim từ trước, nút đó sẽ mang nhãn **"Bỏ ghim"** / **"Unpin"**.

## 2. Bẫy Tử Huyệt: Đảo Lưới Khi Ghim Hàng Loạt (Grid Reorder Trap)
- **Hiện tượng:** Kênh có 3 video nổ view (ví dụ: Video A 19.5K ở Hàng 1 Cột 1; Video B 5K ở Hàng 3 Cột 3; Video C 1.4K ở Hàng 2 Cột 2). Sau khi ghim xong B và C, quay lại ghim A thì A lại không được ghim.
- **Nguyên nhân gốc rễ:**
  - Lưới video trên TikTok được sắp xếp ưu tiên: `[Toàn bộ video đã ghim]` đứng trước, theo sau mới là `[Video thường xếp theo thời gian mới nhất]`.
  - Ban đầu Video A chưa ghim nằm ở Ô 1 (Cột 1). Khi bot ghim B và C, TikTok tự động đẩy B và C lên chiếm Ô 1 và Ô 2.
  - Video A (chưa ghim) bị đẩy dạt sang **Ô 3 (Hàng 1, Cột 3)**.
  - Nếu bot lưu cache tọa độ hoặc danh sách index cũ mà không dump lại cây UI XML sau mỗi lần ghim: Bot sẽ bấm lại vào Ô 1 `(179, 1263)`.
  - Lúc này Ô 1 đã là video đã ghim, menu mở lên hiện **"Bỏ ghim" (UNPIN)**. Bot nhận diện nhãn UNPIN nên hủy thao tác, dẫn tới bỏ sót Video A nổ view cao nhất!
- **Kỷ luật giải quyết triệt để:**
  - BẮT BUỘC chụp/dump lại cây UI XML (`dump_profile_ui_atx`) **SAU MỖI LẦN GHIM THÀNH CÔNG** để tính lại bounding box thực tế của các candidate chưa ghim còn lại.
  - Hoặc ưu tiên ghim video có view cao nhất trước (Video A $\rightarrow$ Video B $\rightarrow$ Video C).

## 3. Kiến Trúc Tool `pin_top_videos.py` (`taadaa-farm-tools`)
- **Tập tin chính:** `D:\Taadaa\tools\pin_top_videos.py`
- **Bộ Unit Test:** `D:\Taadaa\tools\test_pin_top_videos.py`
- **Tích hợp `automation_core`:**
  - Mở profile chuẩn và an toàn qua `automation_core.tiktok.account_switcher.open_profile_root`.
  - Chuyển nick chính xác nếu máy có nhiều tài khoản qua `automation_core.tiktok.account_switcher.select_exact_account`.
  - Trích xuất UI XML qua ATX-agent (port 7912) bằng `automation_core.persistent_ui.capture_atx_session_ui`. CẤM dùng `shell uiautomator dump` gây treo máy S7.
- **Parser View Count Đa Dạng:**
  - Xử lý mượt mà: `"19,5K"`, `"19.5k"`, `"1.445"`, `"5.012"`, `"375"`, `"1,2M"`.
  - Loại bỏ các ô video mang nhãn Bản nháp (`"draft"` / `"bản nháp"`).
- **Quy tắc vận hành an toàn:**
  - Ghim video là tác vụ theo đợt khi có nick nổ view, KHÔNG gộp vào ca upload video thường ngày để tránh kéo dài thời gian chiếm máy và xung đột lịch nuôi ca.
