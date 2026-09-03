# Quy tắc Vận hành Đăng ký TikTok & Quản lý Kho Mail (Cập nhật 2026-08-23)

## 1. Quy tắc Đặt Tên Hiển Thị (Display Name / Biệt danh)
- Sau khi reg nick TikTok thành công (màn hình "Tên" / "Tạo tên" / "Tạo biệt danh"):
- **BẮT BUỘC đặt tên tiếng Việt** (viết hoa chữ đầu, theo bộ mapping hoặc chọn từ danh sách tên tiếng Việt phổ biến `_VI_NAME_FALLBACK`).
- Không đặt tên tiếng Anh, chuỗi vô nghĩa hoặc tên không dấu khó đọc.

## 2. Quy tắc Quản lý Kho Mail Live (`gmail_clean_v2.xlsx`)
- `gmail_clean_v2.xlsx` là **KHO MAIL LIVE** của hệ thống.
- **Tuyệt đối không tự ý xóa mail sau khi vừa reg xong TikTok**.
- Khi chạy quét check-live / dọn mail:
  - Nếu mail bị die/quarantine VÀ **chưa có ID TikTok** trong `taikhoan_dat_v2_updated .xlsx` -> **XÓA KHỎI KHO**.
  - Nếu mail **đã có ID TikTok** trong `taikhoan_dat_v2_updated .xlsx` -> **BẮT BUỘC GIỮ LẠI** trong kho để phục vụ nuôi acc và login sau này.
- Khi một mail đăng ký thành công TikTok -> **BẮT BUỘC ghi ID TikTok cùng hàng với Email đó trong `taikhoan_dat_v2_updated .xlsx`**, không được ghi lệch sang email khác.

## 3. Quy tắc Device Lock và Cron Nuôi Acc
- Khi chạy batch reg TikTok: luôn bật `DEVICE_LOCK_ENABLED=1`.
- Cron nuôi acc (`hermes_cron_runner`) có cơ chế Lock-Aware kiểm tra thư mục lock trước khi spawn.
- Nếu một máy đang bị lock do tiến trình reg đang chạy, cron nuôi sẽ ghi log `SKIPPED_DEVICE_LOCKED` và chỉ **bỏ qua duy nhất 1 phiên nuôi của máy đó** trong khung giờ đó, không bao giờ can thiệp hay chạy đè lên nhau gây xung đột.
