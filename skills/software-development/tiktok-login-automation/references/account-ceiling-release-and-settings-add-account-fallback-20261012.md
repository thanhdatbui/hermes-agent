# Luân Chuyển Nick Trần 8 Acc, Kỷ Luật 2FA Trước Logout & Fallback Cài Đặt Thêm Tài Khoản (2026-10-12)

## 1. TỔNG QUAN & USER INVARIANT BẮT BUỘC
- **Quy tắc trần cứng TikTok**: App TikTok trên Android chỉ cho phép lưu tối đa 8 tài khoản đăng nhập đồng thời. Khi đạt đủ 8 nick, nút `+ Thêm tài khoản` (`Add account`) trong Switcher bị **ẨN HOÀN TOÀN**.
- **User Invariant tối cao (Chấn chỉnh 12/10/2026)**:
  * "Ủa t ns rõ ràng add 2fa acc đó xong out ra r mà"
  * Khi luân chuyển tài khoản (đẩy nick non sang máy thiếu slot, đưa nick chính chủ cũ vào máy):
    **BẮT BUỘC BẬT 2FA TOTP & TẠO MẬT KHẨU CHO NICK NON TRÊN MÁY NGUỒN TRƯỚC KHI LOGOUT**.
  * CẤM TUYỆT ĐỐI logout nick khi chưa có 2FA và mật khẩu lưu trên Master DAT (nguy cơ mất quyền truy cập tài sản farm).
  * CẤM TUYỆT ĐỐI nhảy cóc sang chạy login nick mới khi chưa hoàn thành trọn vẹn cả 2 bước (add 2FA và logout nick non).

---

## 2. QUY TRÌNH 4 BƯỚC ĐIỀU PHỐI BẤT DI BẤT DỊCH
Khi xử lý máy bị đụng trần 8 nick do reg bù hoặc dồn nick:
1. **Bước 1 — Định vị & Gán sổ sách máy nhận**:
   - Chọn nick non nhất (reg gần nhất, 0-1 video, ít fl) trên máy nguồn (ví dụ M74).
   - Điền thông tin nick vào các file Excel máy nhận (ví dụ M266: `admin/Tik6.xlsx`, `taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`).
   - 🔒 **Kỷ luật**: Tuyệt đối CHƯA login lên máy nhận.
2. **Bước 2 — Kích hoạt 2FA TOTP + Tạo Pass ngay trên máy nguồn**:
   - Chạy `run_capture_phase_b.py --machine <máy_nguồn> --live` nhắm vào nick non.
   - Trích xuất Secret Key 32 ký tự và Password mới vào Master DAT.
   - *Cứu hộ*: Nếu runner văng `UI_TARGET_AMBIGUOUS:Next:0` ở bước đổi pass cuối cùng, đọc ngay file audit để lấy secret:
     `tail -n 5 C:\Users\Kibe\AppData\Local\tiktok-add-bao-mat-f2a\logs\2fa_audit.log`
     Ghi thủ công secret vào Excel, CẤM chạy lại từ đầu làm đè mã.
3. **Bước 3 — Đăng xuất nick non khỏi máy nguồn (Giải phóng slot)**:
   - Điều hướng: Hồ sơ -> Menu 3 gạch `(1005, 150)` -> Cài đặt và quyền riêng tư -> Cuộn xuống đáy -> Đăng xuất -> Xác nhận popup.
   - *Bẫy tránh*: Tránh bấm `keyevent 4` mù quáng sau khi switch nick làm văng app ra ngoài Launcher.
   - Chụp ảnh Switcher nghiệm thu: Soi mắt kiểm tra danh sách còn đúng 7 nick, nick non đã biến mất hoàn toàn.
4. **Bước 4 — Đăng nhập nick mới vào slot vừa giải phóng**:
   - Chạy `tiktok_login_v1.py <máy_nguồn> --email <nick_mới> --ss`.
   - Máy còn 7 nick -> Nút `Thêm tài khoản` xuất hiện -> Điền thông tin và bypass 2FA TOTP.

---

## 3. CẠM BẪY SWIPE OVERSHOOT VĂNG BOTTOM SHEET KHI CÓ 7 NICK
### 3.1. Hiện tượng
- Máy đã logout nick non, còn đúng 7 nick trong Switcher.
- Chạy `tiktok_login_v1.py` để nạp nick mới nhưng bị timeout với lỗi:
  `STOPPED: [04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account', ...)`
- Kiểm tra ảnh/XML thấy app bị văng về Trang chủ (Feed) hoặc trang Tìm kiếm (Search).

### 3.2. Căn nguyên kỹ thuật
- Khi có 7 nick, danh sách chiếm gần hết chiều cao bottom sheet (từ `y ≈ 600` đến `y ≈ 1800`), nút "Thêm tài khoản" bị đẩy xuống dưới fold.
- Lệnh cuộn cũ trong `tap_add_account()`:
  `swipe(device_id, 540, 1500, 540, 800, 400)`
- Trên màn hình 1080x1920 (Samsung S7), mép trên của bottom sheet nằm ở `y ≈ 1050-1100`. Điểm kết thúc `y = 800` nằm **HOÀN TOÀN NGOÀI VÙNG BOTTOM SHEET** (vùng mờ phía trên).
- Khi điểm chạm/nhấc tay xảy ra ngoài vùng bottom sheet, Android kích hoạt sự kiện `TOUCH_OUTSIDE` và đóng ngay dialog bottom sheet, đẩy app về màn hình nền trước đó!

### 3.3. Giải pháp chuẩn 2 lớp đã áp dụng vào `social_reg_v1.py`
1. **Lớp 1 — Giới hạn biên độ vuốt trong lòng bottom sheet**:
   Chuyển tọa độ vuốt thành:
   `swipe(device_id, 540, 1500, 540, 1100, 400)` (không vượt qua mép `y=1100`).
2. **Lớp 2 — Fallback bất bại qua Menu Cài đặt (`_open_account_dropdown_via_settings`)**:
   Nếu sau các lần cuộn bottom sheet vẫn không thấy nút:
   ```python
   if _open_account_dropdown_via_settings(device_id):
       return
   ```
   Trong `_open_account_dropdown_via_settings`:
   - Bấm `keyevent(device_id, 4)` để đóng triệt để mọi bottom sheet đang mở.
   - Gọi `go_to_profile(device_id)` đảm bảo chắc chắn đứng ở màn hình Hồ sơ chính.
   - Tap Menu 3 gạch `(1005, 150)` -> chọn "Cài đặt và quyền riêng tư".
   - Cuộn 8 lần xuống đáy trang Cài đặt -> Tap trực tiếp nút "Thêm tài khoản" (`Add account`).
   - *Ưu thế*: Màn hình Cài đặt là Activity toàn màn hình, không bao giờ bị văng dialog do vuốt nhầm tọa độ!

---

## 4. BẪY ADAPTER THIẾU `swipe()` TRONG PHASE B 2FA
- Khi chạy `run_capture_phase_b.py`, module `account_preflight.py` wrap adapter để gọi hàm chuẩn `automation_core.tiktok.account_switcher.select_exact_account`.
- Khi tài khoản cần switch (ví dụ nick non ở slot 8) nằm ở đáy Switcher (ngoài viewport 5-6 nick đầu), `account_switcher` cần cuộn để tìm nick.
- Nếu `_CanonicalAdapter` thiếu phương thức `swipe()`, `account_switcher` không thể cuộn và văng lỗi `ACCOUNT_NOT_IN_SWITCHER` giả.
- **Bắt buộc**: Luôn khai báo `swipe()` trong `_CanonicalAdapter`:
  ```python
  def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
      self.adb.shell(["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)], check=False)
  ```
