# Samsung S7 Google Settings Intent & Security Code Dropdown Navigation

## 1. Direct Intent Khởi Động Cài Đặt Google Trên Samsung Galaxy S7 (Android 8)
Thay vì cuộn tìm "Google" trong cài đặt hệ thống Samsung (`android.settings.SETTINGS`), khởi động trực tiếp intent Google Play Services:

```bash
adb -s <SERIAL> shell am start -n com.google.android.gms/.app.settings.GoogleSettingsLink
```

- **Màn hình hiển thị:** Mở trực tiếp *Các dịch vụ của Google* (`GoogleSettingsLink`), hiển thị thông tin tài khoản đang chọn cùng nút *"Tất cả dịch vụ"* / *"Đề xuất"*.

---

## 2. Luồng Điều Hướng Đến Mã Bảo Mật 10 Số (Security Code)

### Bước 1: Mở Menu Tài Khoản Google
- Tap vào banner tài khoản: `[60, 758][960, 902]` (hoặc node có desc *"Tài khoản và các chế độ cài đặt"* / *"Quản lý Tài khoản Google của bạn"*).
- Menu bung ra danh sách các tài khoản Google đã đăng nhập trên máy.

### Bước 2: Chọn Tài Khoản & Mở "Tài khoản Google"
- Nếu tài khoản mục tiêu nằm trong danh sách: Tap chọn tài khoản mục tiêu.
- Tap nút **"Tài khoản Google"** (`android.widget.Button: text="Tài khoản Google"`).

### Bước 3: Mở Trang Mã Bảo Mật
- Màn hình tiếp theo hiển thị mục **"Mã bảo mật"** (`android.widget.TextView: text="Mã bảo mật"` / `"Nhận mã một lần để xác minh rằng đó là bạn"`).
- Tap vào "Mã bảo mật" $\rightarrow$ Chuyển sang màn hình hiển thị 2 mã số 10 chữ số:
  - **Mã 1:** 10 chữ số (VD: `2153 157 761` $\rightarrow$ `2153157761`).
  - **Mã 2:** 10 chữ số (VD: `3398 951 021` $\rightarrow$ `3398951021`).
  - Mã có hiệu lực trong **15 phút**.

---

## 3. Account Switcher Dropdown Trên Header Mã Bảo Mật
Khi màn hình "Mã bảo mật của bạn" đang hiển thị mã của một tài khoản khác:
- **Header Top Bar:** `android.widget.TextView: text="<current_email@gmail.com>" bounds=[216, 159][792, 224]`.
- Tap vào tọa độ header (VD: `x=504, y=191`) để bung dropdown danh sách toàn bộ các tài khoản Google trên máy.
- Tap vào email tài khoản mục tiêu trong danh sách dropdown $\rightarrow$ Google Play Services cập nhật và sinh ngay 2 mã bảo mật mới cho đúng tài khoản đó.

---

## 4. Xử Lý Khi Tài Khoản Bị "Yêu Cầu Đăng Nhập" (Action Required)
- Nếu tài khoản Google trên điện thoại S7 bị trạng thái *"Đã xảy ra lỗi và bạn cần đăng nhập lại"* (Action required):
  - Google Play Services sẽ tạm khóa tính năng sinh offline Security Code cho tài khoản đó.
  - Trên trình duyệt Chrome GPM, Google sẽ chuyển hướng sang `challenge/iap` (Phone SMS Checkpoint) yêu cầu số điện thoại nhận SMS.
  - Áp dụng **Fail-Closed Cleanup Protocol:** Đóng profile, xóa profile tạm (`mode=2`), ghi nhận `DIE` kèm ghi chú chi tiết vào `master_gmail_manager.xlsx`.
