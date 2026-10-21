# Case Study: Account Switcher 7-Account Bottom Cutoff & Profile vs Home Feed Collision (2026-10-21)

## 1. Hiện Tượng & Bối Cảnh
Khi một máy farm (ví dụ Máy 24) gặp lỗi `ACCOUNT_MISSING` / `account-switcher-missing-expected` do nick mục tiêu (`trinhgiang7694`) chưa có trên thiết bị, hệ thống tự động kích hoạt canonical login runner:
```bash
python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py 24 --email trinhgiang7694 --ss
```
Quá trình đăng nhập bị văng lỗi:
```
[10:18:09] ✓ tap Add account safe row point (540, 1832) bounds=[0,1788][1080,1920]
[10:18:13] [5] Add another account (if shown)
[10:18:32] → bỏ qua bước 5 (không có màn này)
[10:18:32] [6] Choose email login method
[10:18:46] [6] Màn home feed (chưa login) → tap tab Hồ sơ mở login sheet
...
STOPPED: [06] Không thấy màn chọn phương thức đăng nhập
```

## 2. Root Cause Trực Tiếp Trong Script

### Lỗi 1: Nút "Thêm tài khoản" ở mép dưới bị nuốt cảm ứng (`tap_add_account` trong `social_reg_v1.py`)
- Khi thiết bị đã đăng nhập 7 tài khoản, khay Account Switcher bị chiếm trọn chiều cao màn hình (Samsung S7 1080x1920).
- Nút `Thêm tài khoản` bị dồn xuống đáy: `bounds=[0,1788][1080,1920]`, phần TextView chữ chỉ còn từ `y=1866` đến `y=1920` (54px ở đáy).
- Công thức tính tọa độ an toàn `safe_y = y1 + (y2 - y1) // 3 = 1832` nằm ngoài vùng bấm chữ và chạm vào vùng viền gesture/navigation bar của Android.
- Cũ: script thấy node là tap ngay `(540, 1832)` rồi return ngay mà không kiểm tra hậu điều kiện modal login đã mở hay chưa.

### Lỗi 2: Nhận diện nhầm Profile thành Anonymous Home Feed (`choose_email_login` trong `social_reg_v1.py`)
- Khi `tap_add_account` không mở được modal đăng nhập, app vẫn giữ nguyên ở màn hình Profile của nick cũ.
- Tại bước 6 (`choose_email_login`), script dùng danh sách marker:
  `_home_markers = ["cong dong", "ban be", "trang chu", "de xuat", "ho so"]`
  để phát hiện máy anonymous chưa login đang ở feed.
- Màn hình Profile của tài khoản đã đăng nhập cũng chứa 2 tab điều hướng đáy: `Trang chủ` và `Hồ sơ`.
- Điều kiện `sum(1 for k in _home_markers if k in flat_0) >= 2` bị kích hoạt sai (True). Script tự động bấm vào tab `Hồ sơ` (972, 1857).
- Vì đang ở sẵn màn hình Profile, việc bấm tab Hồ sơ không làm thay đổi giao diện. Script chờ 20s không thấy nút "Đăng nhập" / "Dùng SĐT/Email" và văng lỗi `[06]`.

## 3. Bản Vá Kỹ Thuật (Remediation)

1. **Auto-Scroll Khay Switcher Khi Nút Bị Cắt Mép (`tap_add_account`):**
   ```python
   if y1 > 1650 or y2 >= 1880:
       log(f"   [add-account] Nút ở sát mép dưới ({y1}-{y2}), cuộn lên trước khi tap")
       swipe(device_id, 540, 1600, 540, 1100, 300)
       time.sleep(1.0)
       continue
   ```
2. **Kiểm Chứng Hậu Điều Kiện Tap Modal:**
   Sau khi tap tọa độ an toàn, không return ngay mà kiểm tra `_tiktok_login_modal_present` hoặc màn auth landing. Nếu sau 3 nhịp vẫn chưa mở thì tiếp tục vòng lặp retry.
3. **Loại Trừ Profile Đã Login Trong `choose_email_login`:**
   ```python
   _home_markers = ["cong dong", "ban be", "trang chu", "de xuat", "ho so"]
   _is_logged_in_prof = any(k in flat_0 for k in ["follower", "dang follow", "da follow", "sua ho so", "them tieu su"])
   if not _is_logged_in_prof and not _tiktok_login_modal_present(xml_0) and sum(1 for k in _home_markers if k in flat_0) >= 2:
   ```
