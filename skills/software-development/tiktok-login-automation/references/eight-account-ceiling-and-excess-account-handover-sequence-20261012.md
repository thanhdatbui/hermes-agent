# Quy trình Điều phối Nick Dư, Xử lý Trần 8 Tài khoản & Thứ tự Thao tác Bắt buộc (2026-10-12)

## 1. CƠ CHẾ TRẦN CỨNG 8 TÀI KHOẢN TRÊN TIKTOK ANDROID (V46 - V47)
- **Hiện tượng**: App TikTok trên Android (Galaxy S7 / S8...) giới hạn cứng tối đa 8 tài khoản đăng nhập đồng thời.
- **Biểu hiện UI**:
  - Khi máy đã đủ 8 tài khoản, TikTok **ẨN HOÀN TOÀN** nút `+ Thêm tài khoản` (`Add account` / `Thêm tài khoản khác`) ở đáy bottom sheet `Chuyển đổi tài khoản`.
  - Nếu runner đăng nhập (`tiktok_login_v1.py`) cố gắng chạy nạp nick mới trên máy đã có 8 nick, script sẽ cuộn tìm nút `Thêm tài khoản` liên tục trong vô vọng và văng lỗi `UI_XML_TIMEOUT`.
- **Hệ quả**: BẮT BUỘC phải đăng xuất giải phóng 1 slot (đưa máy về tối đa 7 nick) thì nút `Thêm tài khoản` mới xuất hiện trở lại.

---

## 2. QUY TRÌNH ĐIỀU PHỐI NICK DƯ (EXCESS ACCOUNT HANDOVER SEQUENCE)
Khi phát hiện máy bị dồn 9 nick (do reg bù trong quá khứ hoặc cấu hình sai slot), quy tắc xử lý tài sản farm bắt buộc tuân theo thứ tự nghiêm ngặt:

### 🛑 THỨ TỰ BẮT BUỘC (INVARIANT — KHÔNG ĐƯỢC ĐẢO LỘN):
1. **Bước 1 — Định danh nick cần chuyển dịch**:
   - Chọn nick non nhất (dựa trên ngày đăng ký gần nhất, số lượng video ít nhất) để chuyển dịch sang máy khác còn trống slot (ví dụ máy Admin M266).
2. **Bước 2 — BẬT 2FA TOTP & TẠO PASSWORD TRƯỚC KHI OUT (FIRST PRIORITY)**:
   - **CẤM TUYỆT ĐỐI logout khi chưa có 2FA/Password**: Mọi nick trên máy là tài sản farm. Nếu logout trước khi có 2FA và mật khẩu, tài khoản sẽ mất phiên vĩnh viễn và bị khóa ngoài.
   - Chạy runner `run_capture_phase_b.py --live` trên thiết bị nguồn để kích hoạt Authenticator 2FA, lấy Secret Key 32 ký tự và khởi tạo password đạt chuẩn farm.
3. **Bước 3 — Ghi sổ sách máy đích (CHƯA VỘI LOGIN)**:
   - Cập nhật thông tin (Username, Pass TT, 2FA Secret, Mail, Pass Mail) vào Master DAT và file ca nuôi của máy đích (ví dụ Admin M266 Slot 6).
   - **Tuân thủ kỷ luật ngâm nguội**: Tuyệt đối chưa login ngay vào máy đích để tránh kích hoạt checkpoint Device Hopping.
4. **Bước 4 — ĐĂNG XUẤT NICK DƯ ĐỂ GIẢI PHÓNG SLOT**:
   - Sau khi 2FA Secret Key và Password đã được lưu an toàn vào Master DAT, tiến hành đăng xuất nick non ra khỏi máy nguồn.
   - Nghiệm thu giải phóng slot: Mở lại Switcher, xác nhận máy nguồn còn 7 nick và nút `Thêm tài khoản` đã hiện lại.
5. **Bước 5 — ĐĂNG NHẬP NICK MỤC TIÊU VÀO MÁY NGUỒN**:
   - Chạy `tiktok_login_v1.py` để đăng nhập tài khoản mục tiêu (ví dụ Tik 1) vào vị trí trống đã giải phóng.

---

## 3. CÁC CẠM BẪY KỸ THUẬT KHI THAO TÁC SWITCHER & LOGOUT
### Cạm bẫy 1: Bấm phím BACK mù sau khi switch nick
- Khi tap vào nick mục tiêu trong Switcher, TikTok chuyển tài khoản và đưa thẳng về giao diện chính (Feed hoặc Profile).
- **Cấm đoán**: Tuyệt đối KHÔNG gửi lệnh `keyevent 4` (BACK) mù 2 lần liên tiếp sau khi tap switch, vì việc này làm văng TikTok ra ngoài màn hình chính Android (Launcher). Khi đó, tọa độ tap Profile (972, 1857) sẽ bấm nhầm vào icon Camera/Launcher dock!
- **Khắc phục**: Dùng `find_text_tap` tìm đúng nhãn `"Hồ sơ"` -> `"Menu hồ sơ"` -> `"Cài đặt và quyền riêng tư"`.

### Cạm bẫy 2: Thiếu phương thức swipe() trong _CanonicalAdapter
- Trên máy có 8 nick, tài khoản mới/non nhất thường nằm ở đáy bottom sheet (ngoài vùng hiển thị đầu tiên).
- Adapter `_CanonicalAdapter` bắt buộc phải triển khai phương thức `swipe(x1, y1, x2, y2, duration_ms)` để canonical `account_switcher` có thể cuộn danh sách xuống dưới tìm đúng nick.

### Cạm bẫy 3: Cài đặt uiautomator stub APK bị thiếu trên Android cũ (Samsung S7)
- `atx-agent` phụ thuộc vào `com.github.uiautomator` và `com.github.uiautomator.test` để dump XML UI.
- Nếu 2 gói này bị gỡ hoặc kẹt, runner sẽ văng lỗi `non_xml_ui_dump`.
- Khắc phục: Push và cài đặt lại `app-uiautomator.apk` và `app-uiautomator-test.apk` bằng `pm install -t -g /data/local/tmp/...`.
