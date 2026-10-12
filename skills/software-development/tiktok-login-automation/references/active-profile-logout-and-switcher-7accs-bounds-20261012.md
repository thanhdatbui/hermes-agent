# QUY TẮC ĐĂNG XUẤT ACTIVE PROFILE & BẪY NÚT THÊM TÀI KHOẢN TRÊN MÀN HÌNH 1080x1920 (2026-10-12)

Đúc kết từ sự cố cơ cấu slot trên máy Samsung S7 (1080x1920): Đăng xuất nick non đang active và nạp nick mới khi danh sách Switcher đạt 7 tài khoản.

---

## 1. BẪY ĐĂNG XUẤT ACTIVE PROFILE TRÊN TIKTOK

### Cạm bẫy:
- Khi kiểm tra danh sách Switcher để tìm tài khoản cần đăng xuất, nếu tài khoản đó đang là **Active Profile** (đang mở trực tiếp), nó **HOÀN TOÀN KHÔNG XUẤT HIỆN TRONG DANH SÁCH SWITCHER** (Switcher chỉ hiển thị các tài khoản phụ còn lại, ví dụ 7 nick nếu máy có 8 nick).
- Khi script mở Switcher và không thấy nick, cố gắng đóng Switcher bằng cú tap `(540, 200)` sẽ thất bại vì trên màn hình 1080x1920, tọa độ `y=200` vẫn nằm bên trong dialog Switcher.
- Hậu quả: Các cú chạm Menu tiếp theo bị lệch vào màn hình phụ (ví dụ *Thời gian sử dụng màn hình - SparkActivity*) thay vì vào Menu Cài đặt, dẫn đến script báo thành công ảo hoặc không đăng xuất được nick.

### Quy trình chuẩn:
1. **Đóng Switcher an toàn:** BẮT BUỘC dùng phím **BACK (`input keyevent 4`)**, tuyệt đối không tap điểm mò trên đỉnh màn hình.
2. **Điều hướng vào Menu Cài đặt:**
   - Tap tab Hồ sơ: `(972, 1857)`.
   - Tap Menu 3 gạch góc trên phải: `(1005, 150)`.
   - Tap "Cài đặt và quyền riêng tư": fallback tọa độ chuẩn `(621, 1278)`.
3. **Bấm nút Đăng xuất:**
   - Cuộn xuống đáy cài đặt.
   - Dùng matcher đa thuộc tính (`text` + `content-desc` tìm `["đăng xuất", "dang xuat", "log out"]`), fallback tap `(300, 1640)`.
4. **Xác nhận Popup Đăng xuất:**
   - Quét popup tìm `resource-id` chứa `["a6d", "a6e", "button1"]` hoặc text "Đăng xuất" đi kèm bounds bắt đầu `[48,` hoặc `[0,`.
   - Fallback tap xác nhận: `(540, 1640)` và `(750, 1100)`.

---

## 2. BẪY NÚT "THÊM TÀI KHOẢN" BỊ ÉP MÉP ĐÁY TRÊN SAMSUNG S7 KHI CÓ 7 NICKS

### Cạm bẫy:
- Khi Switcher đã chứa 7 nick, nút "Thêm tài khoản" bị đẩy xuống sát mép dưới cùng của màn hình 1080x1920 (bounds `[0, 1788][1080, 1920]`).
- Phần text của nút nằm sát mép đáy khiến UIAutomator XML dumper không nhận diện được chuỗi text chuẩn (`"Thêm tài khoản"` / `"Add account"`). Script dùng `find_text_tap` sẽ lặp lại timeout và fail ở bước `[04_add_account]`.

### Giải pháp cơ học:
- Tăng biên độ cuộn Switcher: từ `(540, 1536)` vuốt lên `(540, 800)` trong `450ms` kèm sleep `2.0s`.
- Bổ sung fallback tap trực tiếp tọa độ mép đáy: `tap(device_id, 540, 1850)`.
- Kiểm tra ngay sự hiện diện của login modal qua `_tiktok_login_modal_present(get_ui_xml(device_id))` sau cú tap để tiếp tục luồng đăng nhập mà không bị kẹt vòng lặp text matcher.
