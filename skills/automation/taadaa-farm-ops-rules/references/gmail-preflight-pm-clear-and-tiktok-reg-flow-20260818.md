# Gmail Preflight PM-CLEAR & TikTok Reg Flow (2026-08-18)

## 1. Preflight `pm clear com.google.android.gm` & Welcome Tour Handling
- **Tác dụng**: Khử triệt để lỗi kẹt UI cũ (stale compose draft, popup lỗi phiên trước, cache cookie WebView xung đột).
- **Trạng thái tài khoản**: `pm clear com.google.android.gm` chỉ xóa dữ liệu app Gmail, KHÔNG làm mất tài khoản Google trên máy (vì tài khoản nằm ở `AccountManager` tầng Android OS).
- **Xử lý Welcome Screen**: Sau khi clear, app Gmail mở màn hình chào mừng ("Chào mừng bạn đến với Gmail"):
  - Nếu đã có tài khoản: tap nút *"ĐƯA TÔI TỚI GMAIL"* (`id/action_done` hoặc tọa độ chính giữa dưới cùng).
  - Nếu chưa có tài khoản: tap *"Thêm địa chỉ email"* -> chọn Google -> vào luồng GMS SetupWizard.

## 2. Quy trình Cleanup sau khi Gỡ Mail Die (User Rule 18/08)
- Sau khi gỡ tài khoản Google checkpoint qua `remove_blocked_google_account_from_device`:
  1. Đóng sạch Recent Apps: `keyevent 187` -> tap nút "Đóng tất cả" (tọa độ `540, 1600`) -> `keyevent 3` về HOME.
  2. Giải phóng device-lock: Xóa file lock của đúng máy đó (`machine_<N>.lock.json`, `serial_<S>.lock.json`) để đưa máy về trạng thái rảnh ngay.

## 3. Xử lý Popup Hệ thống "Cho phép gỡ lỗi USB?" (USB Debugging Dialog)
- **Hiện tượng**: Xuất hiện hộp thoại Android *"Cho phép gỡ lỗi USB? Dấu vân tay khóa RSA..."* đè lên chính giữa màn hình làm che khuất nút *"Tiếp tục với email"* / form đăng ký TikTok.
- **Xử lý**:
  - Tick chọn checkbox *"Luôn cho phép từ máy tính này"* (tọa độ khoảng `200, 1100`).
  - Tap nút **"OK"** (tọa độ khoảng `880, 1170`).
  - Nếu uiautomator stub bị nghẽn làm timeout dump XML: restart ATX-agent (`pkill -9 -f atx-agent`, `/data/local/tmp/atx-agent server -d`, `monkey -p com.github.uiautomator 1`).

## 4. Chuỗi Flow TikTok Reg chuẩn với Gmail OTP & DatePicker (Đã verify thành công Máy 07)
1. **Mở TikTok & Vào Hồ sơ**:
   - Nếu máy đang ở Feed video -> tap tab *Hồ sơ* (`972, 1857`).
2. **Mở danh sách tài khoản**:
   - Tap dropdown tên tài khoản (`540, 552`) -> popup "Chuyển đổi tài khoản" mở ra -> tap *"Thêm tài khoản"* (`540, 1788`).
3. **Chọn phương thức Email**:
   - Tap *"Tiếp tục với email"* (nút xám có icon lá thư).
4. **Điền Email**:
   - Nhập email (vd `huehoa2302fi@gmail.com`) -> tap *"Tiếp tục"*.
5. **Lấy & Nhập OTP từ Gmail**:
   - Mở Gmail -> switch sang đúng email vừa tạo -> swipe pull-to-refresh (`540,780` -> `540,1500`) -> mở email TikTok -> trích xuất mã 6 số -> quay lại TikTok nhập vào 6 ô OTP.
6. **Chọn Ngày sinh (DOB)**:
   - DatePicker wheel: cuộn ngày/tháng/năm theo DOB nguồn -> tap *"Tiếp tục"* (tọa độ tâm nút `540, 1788`).
7. **Tạo Mật khẩu & Biệt danh (Nickname)**:
   - Nhập mật khẩu chuẩn `@Ks` -> tap *"Tiếp tục"*.
   - Nhập nickname (vd `huehoafi23`) -> tap *"Tiếp tục"*.
8. **Đồng bộ Tracking & Cleanup**:
   - Ghi dữ liệu vào `taikhoan_dat_v2_updated .xlsx`.
   - Đóng Recent Apps -> về HOME -> giải phóng lock.
