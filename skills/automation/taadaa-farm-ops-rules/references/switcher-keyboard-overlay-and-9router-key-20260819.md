# Bài Học Vận Hành: Xử Lý Kẹt Bàn Phím Account Switcher, Modal Live & API Key 9Router (19/08/2026)

## 1. Xử Lý Kẹt Bàn Phím / Input Overlay Khi Mở Account Switcher (Máy 21)
- **Hiện tượng**: Khi script tap vào anchor tên tài khoản ở trang Profile để mở danh sách chuyển nick (Account Switcher), một số máy bị chạm nhầm vào ô comment/search hoặc app mở sẵn bàn phím ảo (`@f`), làm bàn phím che khuất danh sách tài khoản ➔ Script đọc XML thấy không có switcher và báo lỗi `account-switcher-not-open`.
- **Giải pháp đã chuẩn hóa vào `feed_swipe_smoke.py`**:
  1. Khi phát hiện switcher chưa mở sau lần tap đầu tiên.
  2. Tự động gửi phím `BACK` (`keyevent 4`) để hạ bàn phím ảo và đóng bất kỳ overlay nhập liệu nào.
  3. Chờ 1.0s rồi tự động tap lại vào `switch_anchor` một lần nữa.
  4. Capture lại XML ➔ switcher mở bình thường và tiếp tục luồng chuyển nick, không làm gián đoạn phiên nuôi.

## 2. Nguồn Trích Xuất API Key 9Router Local (`data.sqlite`)
- **Vấn đề**: Module Autonomous AI Recovery (`vision_client.py` & `plan_reviewer.py`) kết nối với 9Router qua port `20128`. Nếu file `C:\Users\Kibe\AppData\Local\hermes\.env` thiếu biến `NINEROUTER_API_KEY`, agent sẽ rơi vào fallback an toàn.
- **Nguồn lấy Key chuẩn**:
  - Truy vấn trực tiếp từ bảng `apiKeys` trong SQLite của 9Router:
    `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite` (cột `key` dạng `sk-2472cb5...`).
  - Ghi vào `.env` dưới biến `NINEROUTER_API_KEY=<key>`.

## 3. Thoát Popup Chính Sách Trong Phòng Live TikTok ("Đã hiểu")
- **Hiện tượng**: Lướt trúng phòng TikTok LIVE có thể xuất hiện popup thông báo lớn: *"Thông tin cập nhật Chính sách Phần thưởng và Chính sách vật phẩm ảo"* che kín màn hình.
- **Xử lý chuẩn**:
  1. Nhận diện nút *"Đã hiểu"* (hoặc gửi phím Back) để đóng modal thông báo.
  2. Tiếp tục gửi phím Back / tap nút X (`[990, 140]`) để thoát phòng Live về lại Feed Trang chủ lướt video bình thường.
