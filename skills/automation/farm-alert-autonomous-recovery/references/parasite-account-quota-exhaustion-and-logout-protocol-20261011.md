# Tài Khoản Ký Sinh (Parasite Account) Chiếm Trần 8 Slot TikTok & Quy Trình Logout

**Ngày ghi nhận:** 11/10/2026  
**Ngữ cảnh:** Nhận cảnh báo Farm Alert `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found`. Kiểm tra Switcher thấy đủ 8 nick nhưng nick cần chạy ca đó lại không có trong máy.

---

## 1. Cơ Chế Lỗi & Nguồn Gốc Nick Ký Sinh (Parasite Account Drift)

1. **Giới hạn cứng của TikTok App:**
   - Ứng dụng TikTok trên Android giới hạn tối đa **8 tài khoản** đăng nhập đồng thời trong Switcher.
2. **Nguyên nhân sinh ra nick ký sinh:**
   - Trong quá trình vận hành, một số slot nick bị die, đổi niche, hoặc được cấp bù tài khoản mới (ví dụ thay Row 3, Row 4).
   - Quá trình cập nhật bảng tính master (`taikhoan_dat_v2_updated .xlsx`) và database (`tiktok_tracker.db`) đã xóa nick cũ và nạp nick mới.
   - **Tuy nhiên trên máy thật, nick cũ chưa từng được đăng xuất (logout) khỏi app TikTok.**
3. **Hậu quả dây chuyền:**
   - Khi máy nạp đủ các slot mới, con ký sinh cũ vẫn nằm lì trong Switcher, chiếm mất 1 slot thứ 8.
   - Tài khoản chính chủ của slot khác (thường là Slot 1 hoặc slot đăng nhập sau cùng) không còn chỗ trên máy hoặc chưa được login vào.
   - Đến ca chạy slot đó (ví dụ Ca 1 - Slot 1), script tìm tài khoản trong Switcher -> vuốt 3 lần không thấy -> ném `ACCOUNT_MISSING` -> Watchdog báo P0 "Mất phiên / Văng account" giả.

---

## 2. Quy Trình Đối Soát Ký Sinh O(1)

1. **Soi mắt Switcher Snapshot:**
   - Chụp ảnh hoặc đọc ảnh Switcher `soft-reboot-account_switcher-before.png`.
   - Đếm số lượng nick: Nếu đủ **8 tài khoản** (1 active ngoài profile + 7 nick trong bottom sheet), lập tức nghi ngờ dính trần 8 slot do nick ký sinh.
2. **Đối chiếu với danh sách chuẩn của máy:**
   - Đọc 8 slot của máy trong `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` hoặc `taikhoan_dat_v2_updated .xlsx`.
   - Tìm ra username đang nằm trong app nhưng **không có tên trong 8 slot của máy**.
3. **Truy vết lịch sử (Session Search / SQLite):**
   - Tìm username lạ trong `account_boost_state` hoặc session cũ: Hầu hết các nick ký sinh chính là **nick cũ của chính máy đó** từng chạy ở các tuần trước.

---

## 3. Quy Trình Logout Nick Ký Sinh & Bẫy Onboarding Popup

Khi chạy flow đăng xuất nick ký sinh (qua `do_logout_account.py` hoặc script tự động):

### Cạm bẫy Onboarding Popup ("Thêm số điện thoại"):
- Nick ký sinh lâu ngày không hoạt động khi được switch vào thường bị TikTok kích hoạt popup nhắc nhở bảo mật:
  `Thêm số điện thoại / Thêm số điện thoại của bạn để tăng cường bảo mật...`
  kèm theo **bàn phím số (numeric keypad) nổi lên che toàn bộ nửa dưới màn hình**.
- Nếu script cố chấp tap vào tọa độ Tab Hồ sơ `(972, 1857)` hoặc Menu 3 gạch `(1005, 150)`, cú tap sẽ ăn vào bàn phím số và làm treo script (timeout).

### Thứ tự giải phóng bắt buộc:
1. **Dismiss bàn phím & popup:**
   - Gửi 2 nhịp Back (`input keyevent 4`) liên tiếp cách nhau 1 giây:
     - Nhịp 1: Đóng bàn phím số.
     - Nhịp 2: Đóng popup "Thêm số điện thoại", đưa màn hình về lại TikTok Feed/Home.
   - Hoặc tap vào nút `X` ở góc trên bên trái `(75, 150)`.
2. **Thực hiện Logout an toàn:**
   - Tap tab Hồ sơ: `(972, 1857)`.
   - Tap Menu 3 gạch: `(1005, 150)`.
   - Chọn Cài đặt và quyền riêng tư: `(540, 1248)`.
   - Cuộn xuống đáy trang cài đặt (5 lần swipe `540, 1600 -> 540, 400`).
   - Tìm và bấm nút `Đăng xuất` (hoặc fallback `(540, 1750)`).
   - Bấm xác nhận popup `Đăng xuất` (hoặc fallback `(750, 1100)`).
3. **Kiểm tra hậu kiểm (Verification Snapshot):**
   - Mở lại Switcher: Xác nhận danh sách chỉ còn 7 nick và nick ký sinh đã biến mất hoàn toàn.
   - Lúc này máy đã giải phóng 1 slot trống, sẵn sàng cho việc đăng nhập bù nick chính chủ.
