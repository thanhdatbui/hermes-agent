# TikTok Unhide Private Videos & Tab 2 Queue Shift Flow

## 1. Bản Chất Danh Mục Video Bị Ẩn / Riêng Tư Trên TikTok
- **Không chỉ nhìn Tab 1:** Trên giao diện Profile TikTok, lưới video công khai (Tab 1) chỉ có thể hiển thị một vài video riêng tư vừa đăng hoặc trong viewport đầu. Toàn bộ kho video bị ẩn/riêng tư được quản lý tập trung ở **Tab 2 ("Private videos" / "Video riêng tư" — icon ổ khóa 🔒)**.
- **Tránh kết luận vội:** Khi người dùng yêu cầu mở lại video bị ẩn, bắt buộc phải tap chuyển sang **Tab 2** (tọa độ fallback trên màn 1080x1920: `x = 417, y = 792`) để kiểm tra toàn bộ danh sách, không được nhìn vài video ở Tab 1 rồi báo chỉ có 5 video.

## 2. Quy Trình Đổi Quyền Riêng Tư O(1) (Privacy Settings Modal)
Từ màn hình xem video riêng tư (`DetailActivity`):
1. **Nút Cài đặt quyền riêng tư:** Nằm ở góc dưới cùng bên phải (`x = 900, y = 1850`, text: "Privacy settings" hoặc "Cài đặt quyền riêng tư").
2. **Bottom Sheet "Who can watch this video" / "Ai có thể xem video này":**
   - Hàng đầu tiên: **Everyone / Mọi người**.
   - **Vị trí Radio Button:** Nằm ở mép phải của hàng, tọa độ chính xác: `(950, 958)`.
   - **Nút đóng `x`:** Nằm ở góc trên bên phải sheet tại `(977, 633)` (hoặc tap outside tại `540, 300`).
3. **Thoát về lưới:** Bấm phím cứng Back (`adb shell input keyevent 4`) để quay lại lưới video.

## 3. Cơ Chế Tự Dịch Chuyển Hàng Đợi (Queue Shift Invariant)
- **Tự động biến mất khỏi Tab 2:** Ngay khi một video được chuyển sang `Everyone` (Công khai), TikTok tự động rút video đó ra khỏi Tab 2 và đưa sang Tab 1.
- **Vị trí cố định `(540, 1200)`:**
  - Ô (0, 0) góc trên bên trái luôn là thư mục `Stories archive`.
  - Ô (0, 1) ngay cạnh (`x = 540, y = 1200`) luôn là video riêng tư tiếp theo tự động trượt vào thay thế.
  - Nhờ cơ chế này, quá trình batch unhide không cần dump lại UI XML từng lần tốn 5-7s, mà chỉ cần chạy vòng lặp lặp lại thao tác tap tại `(540, 1200)` $\rightarrow$ đổi sang Everyone $\rightarrow$ Back. Mỗi video chỉ mất ~6 giây.
- **Dừng khi Tab 2 rỗng:** Khi toàn bộ video đã được mở công khai, Tab 2 sẽ trống hoàn toàn (chỉ còn lại `Stories archive`). Chuyển về Tab 1 (`tap 170 792`) để chụp ảnh nghiệm thu đối soát.
