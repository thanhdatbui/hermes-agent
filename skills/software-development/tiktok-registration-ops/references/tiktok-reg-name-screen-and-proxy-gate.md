# Quy trình Đăng Ký TikTok & Xử Lý Các Điểm Nghẽn Màn Hình Đặt Tên / Nickname

## 1. Live Proxy Gate Bắt Buộc Trước Khi Chạy Reg
- **Nguyên tắc:** BẮT BUỘC kiểm tra Live IP qua broadcast `ViChanger GET_IP` (`vn.vichanger.app/.AdbCaller`).
- **Điều kiện PASS:** `result=200` và IP hợp lệ khác `1.53.114.53` (Direct IP của farm).
- Nếu máy chết proxy hoặc không có proxy (như máy 36, 62, 63, 75) $\rightarrow$ LOẠI NGAY LẬP TỨC khỏi danh sách reg, tuyệt đối không chạy để tránh bị lộ dải IP farm.

## 2. Màn Hình "Tiếp tục với tên @nick" (Quick Login Prompt)
- **Hiện tượng:** Khi máy chưa có nick trong profile hoặc có session cũ trong cache app, TikTok hiện màn hình "Tiếp tục với tên @...".
- **Kiểm tra an toàn:** Các nick này thường là session rác, không nằm trong file tracking `taikhoan_dat_v2_updated .xlsx` của máy.
- **Xử lý:** Bấm liên kết dưới đáy **"Sử dụng tài khoản khác"** (`Sử dụng tài khoản khác` / `Use another account`) để điều hướng vào giao diện chọn phương thức đăng ký/đăng nhập.

## 3. Màn Hình "Tên" (Đổi biệt danh / 0/30) Sau Khi Nhập OTP Xong
- **Hiện tượng:** Sau khi nhập OTP và DOB thành công, TikTok chuyển sang màn hình **"Tên"** (input placeholder: "Thêm tên bạn mong muốn", đếm ký tự `0/30`, nút "Lưu" ở góc phải trên).
- **Quy tắc đặt tên (User Rule):** Đặt tên tiếng Việt chuẩn theo ngữ âm của email đăng ký (qua hàm `make_tiktok_name(email)`).
- **Thao tác:**
  1. Gõ tên tiếng Việt vào trường EditText.
  2. Bấm nút **"Lưu"** (hoặc tọa độ góc phải trên / `Tiếp tục` nếu là layout mới).
  3. Bấm **"Xác nhận"** nếu xuất hiện popup "Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần".
  4. Điều hướng vào tab Hồ sơ để lấy handle/ID TikTok và ghi nhận tracking.
