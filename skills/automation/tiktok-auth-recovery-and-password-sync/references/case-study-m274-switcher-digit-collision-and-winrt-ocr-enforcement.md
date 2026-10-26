# Case Study & Technical Analysis: Account Switcher Digit Collision & WinRT OCR Enforcement (M274 - 2026-10-26)

## 1. Context & Incident
- **Thiết bị:** Máy M274 (Serial: `ad0a160368c5d7120a`, Cụm Admin Remote `192.168.110.119:5037`).
- **Tài khoản chỉ định trong Workbook:** Row 1 (`khanhthu1609`).
- **Tài khoản thực tế trên máy:** Đang có 7 nick lưu sẵn trong switcher (gồm `khanhthu2275`, `chicun0910`, `oduong2438`...). Hoàn toàn vắng mặt `khanhthu1609`.
- **Hiện tượng lỗi:**
  - Ca chạy sáng và chiều đều ghi nhận máy 274 kết thúc với trạng thái:
    `manual-needed: profile verification mismatch: profile account mismatch`.
  - Máy lướt xong toàn bộ 16 video nhưng đến cuối phiên đối soát Profile thì bị chặn fail-closed vì tài khoản đang mở là `khanhthu22751` chứ không phải `khanhthu1609`.

---

## 2. Root Cause Analysis

### A. Lỗ hổng Fuzzy Matching trong Account Switcher (`matches_switcher_identity`)
- Trong `automation_core.tiktok.account_switcher`:
  ```python
  def matches_switcher_identity(node_value: str, target_value: str) -> bool:
      ...
      if v1.rstrip("0123456789+ ") == v2.rstrip("0123456789+ "):
          return True
  ```
- **Bản chất lỗi:** Hàm cắt bỏ toàn bộ chữ số đuôi để so khớp phần tên cơ sở.
  - Khi tìm `khanhthu1609` (target): chuỗi rút gọn là `khanhthu`.
  - Trên giao diện Switcher có dòng `khanhthu2275`: chuỗi rút gọn cũng là `khanhthu`.
  - `khanhthu == khanhthu` $\rightarrow$ Matcher kết luận đây là cùng 1 tài khoản!
  - Script tap vào `khanhthu2275`, tưởng rằng đã chuyển đúng nick `khanhthu1609`.
- **Hậu quả:** Kịch bản bỏ qua bước nạp bù tài khoản (vì tưởng đã có nick trên máy), cày feed 16 video trên nick cũ, dẫn tới mismatch ở cuối ca.

### B. Spam XML Dump làm sập ADB Transport trên Samsung S7
- Kịch bản đăng nhập legacy (`social_reg_v1.py` / `tiktok_login_v1.py`) chứa hơn 100 lần gọi `get_ui_xml()`.
- Mỗi lần gọi `get_ui_xml()` kích hoạt daemon `uiautomator` Java bên trong thiết bị Android.
- Chip Exynos 8890 trên Samsung S7 bị đẩy lên 100% CPU khi vừa gánh TikTok vừa gánh XML dump, dẫn tới tiến trình Java bị kernel kill (`Killed 137`), làm treo daemon `adbd` và đẩy thiết bị sang trạng thái `offline` hoặc ngắt kết nối USB.

---

## 3. Engineering Fixes & Verification

1. **Khắc phục Switcher Digit Collision:**
   - Trong cả `automation_core.tiktok.account_switcher` và `flows/feed_swipe_smoke.py`:
     ```python
     m1 = re.search(r"\d+$", v1)
     m2 = re.search(r"\d+$", v2)
     if m1 and m2 and m1.group() != m2.group():
         return False
     ```
   - Nếu cả hai tên đều kết thúc bằng số mà số đuôi khác nhau (`1609` vs `2275`), bắt buộc từ chối khớp để runner nhận diện đúng tài khoản bị thiếu và kích hoạt auto-login bù.
   - Toàn bộ 46/46 unit tests trong `automation-core/tests` pass 100%.

2. **Ép WinRT OCR Primary Cho Module Đăng Nhập (`social_reg_v1.py`):**
   - Nâng cấp `find_text_tap` và `text_exists`:
     - Chụp ảnh màn hình `screencap` về PC trong 0.1s.
     - Chạy `automation_core.ocr.ocr_screen_boxes` qua WinRT OCR trên CPU máy tính Windows trong 0.2s–0.5s.
     - Tìm thấy tọa độ nút $\rightarrow$ tap trực tiếp `(cx, cy)`.
     - Chỉ fallback sang XML khi OCR thật sự không tìm thấy chữ.
   - Vượt qua kiểm tra tĩnh của Hard Gate `python D:/Taadaa/tools/ui_policy_check.py` (Exit code 0).

3. **Fallback GPM Profile Khi Graph API Token Hết Hạn (`AADSTS70000`):**
   - Giảm timeout chờ Graph API xuống 15s.
   - Khi token hết hạn, tự động gọi `read_tiktok_otp_from_gpm_profile` khởi động profile GPM qua CDP và bóc OTP từ hộp thư `outlook.live.com` kèm danh sách `exclude_codes` mã cũ.

4. **Bẫy OCR Méo Chữ Tiếng Việt & Header Title Tap (`Tiép tvc` vs `Tiếp tục`):**
   - WinRT OCR đọc chữ "Tiếp tục" ở chân màn hình ($y=1808$) thành `'Tiép tvc'` (chữ `u` thành `v`). Trong khi đó, đỉnh màn hình ($y=154$) mang tiêu đề "Đăng nhập" (`'Däng nhäp'`).
   - Do `'Tiép tvc'` miss norm_text, script tap nhầm vào tiêu đề $y=154$ vì `"Đăng nhập"` có trong danh sách tìm kiếm của `tap_next`.
   - Đã xử lý: Chuẩn hóa `.replace("tvc", "tuc")`, loại trừ tuyệt đối vùng $y_2 < 220$ khi tìm nút bấm hành động, và ưu tiên các từ khóa submit cụ thể trước từ khóa tiêu đề chung.

5. **Chống Lỗi Rỗng Góc Xoay Khi Đánh Thức Màn Hình Qua Remote ADB (`user_rotation` empty):**
   - Khi remote ADB qua mạng LAN sang host Admin (`192.168.110.119`), lệnh `settings get system user_rotation` có thể bị trễ một nhịp và trả về rỗng.
   - Đã xử lý: Thêm vòng lặp thử lại 2 lần với `time.sleep(0.4)` trong `device_prepare.py` để không fail-closed vô cớ.

6. **Forward Đầy Đủ Tham Số `exclude_codes` Trong `hotmail_provider.py`:**
   - Khi luồng OTP chuyển sang GPM profile, hàm gọi truyền tập hợp các mã OTP đã cũ trong hộp thư (`exclude_codes`).
   - Hàm wrapper trong `D:/Taadaa/Tiktok_Reg/hotmail_provider.py` thiếu tham số này dẫn đến `TypeError: unexpected keyword argument 'exclude_codes'`.
   - Đã xử lý: Bổ sung `exclude_codes=None` và truyền trực tiếp xuống `read_otp_gpm.py`, đảm bảo Playwright CDP chỉ bóc tách mã OTP mới tinh vừa được gửi về hòm thư Hotmail.
