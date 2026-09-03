# SystemUI Package Filtering & Gmail Warehouse Rules

## 1. SystemUI Notification Isolation (Android XML Dumps)
- **Vấn đề:** Trên thiết bị Android (đặc biệt Samsung S7), `uiautomator dump` trả về XML chứa toàn bộ cây View, bao gồm cả thanh thông báo hệ thống (`com.android.systemui`). Các notification như *"Google Play: Yêu cầu đăng nhập"* hoặc *"Không có điện thoại nào"* thường xuyên kích hoạt false-positive ở các bộ lọc tìm text đăng nhập (`dang nhap`, `so dien thoai`, `log in`).
- **Quy tắc:**
  - Mọi hàm kiểm tra modal đăng nhập, form email, button submit, hoặc edittext của TikTok BẮT BUỘC phải lọc theo package `com.ss.android.ugc.trill` (sử dụng `_iter_package_nodes(root, APP_PACKAGE)` hoặc `_tiktok_flat_xml(xml)`).
  - Không dùng `strip_accents(xml)` toàn bộ cây XML khi phân loại trạng thái màn hình TikTok.

## 2. Quy Tắc Kho Mail `gmail_clean_v2.xlsx` & Tracking `taikhoan_dat_v2_updated .xlsx`
- **Bản chất `gmail_clean_v2.xlsx`:** Là kho mail LIVE của farm, KHÔNG PHẢI danh sách dùng 1 lần (reg xong KHÔNG được tự ý xóa khỏi `gmail_clean_v2.xlsx`).
- **Quy tắc Check-live / Dọn dẹp tài khoản:**
  - Khi quét check-live phát hiện tài khoản Gmail bị chết/mất khỏi máy:
    - Nếu Gmail đó **chưa có ID TikTok** trong tracking (`taikhoan_dat_v2_updated .xlsx`) ➔ **XÓA** khỏi `gmail_clean_v2.xlsx` để tool reg không bốc làm target nữa.
    - Nếu Gmail đó **đã có ID TikTok** trong tracking ➔ **GIỮ LẠI**, không được xóa.
- **Xác minh liên kết Email thực tế trên TikTok:**
  - Khi có nghi vấn lệch dữ liệu giữa Gmail/Hotmail trong tracking: vào trực tiếp TikTok app ➔ *Hồ sơ* ➔ *Menu 3 gạch* ➔ *Cài đặt và quyền riêng tư* ➔ *Tài khoản* ➔ *Thông tin tài khoản* ➔ Đọc trường *Email* liên kết thực tế để đối soát chính xác 100%.
