# Đối soát tài khoản từ Huanwei & Quy trình đổi Biệt danh (Display Name) TikTok an toàn

## 1. Đối soát tài khoản từ ảnh chụp màn hình Huanwei (Screen Mirroring)

### Bẫy ngộ nhận: Máy hiển thị vs Máy sở hữu
Khi user gửi ảnh chụp từ phần mềm Huanwei (`欢卫安卓投屏`):
- **Hiện tượng:** Một máy được phóng to (ví dụ: Máy 39) đang hiển thị một trang cá nhân TikTok (ví dụ: `@sadoudqbv2e`, biệt danh `8`).
- **Dấu hiệu nhận biết:**
  - Nếu profile có nút màu đỏ **"Follow"** (hoặc "Follow lại") và nút xám **"Nhắn tin"** $\rightarrow$ Máy phóng to đó **KHÔNG PHẢI** là máy sở hữu nick, mà chỉ đang mở xem profile để chạy tương tác chéo / follow chéo (`tiktok-follow`).
  - Nếu profile có nút **"Sửa hồ sơ"** (Edit profile) hoặc nút chia sẻ/cây bút $\rightarrow$ Đây mới là máy đang đăng nhập chính chủ nick đó.
- **Cách tra cứu O(1) xác định máy chủ thể:**
  - Đọc file `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` (hoặc cụm `admin/`): Tìm username không có dấu `@`.
  - Cột `May` cho biết chính xác máy nào trong farm (1–80 hoặc 201–280) sở hữu tài khoản này.
  - Đối soát tiếp trong `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx` để lấy mật khẩu, email đăng ký và khóa bảo mật 2FA TOTP.

---

## 2. Quy trình đổi Biệt danh (Display Name / Nickname) TikTok

### Lưu ý sống còn về chính sách TikTok:
- TikTok áp dụng chính sách **giới hạn đổi biệt danh 7 ngày một lần** (`"Đặt biệt danh? Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần"`).
- Khi đã bấm Lưu & Xác nhận, tài khoản sẽ bị **khóa cứng tên mới trong vòng 7 ngày**, không thể hoàn tác ngay.
- Vì vậy, nếu user chỉ yêu cầu chung chung: *"Đổi biệt danh cho nick đó cho tao"*, Coordinator **BẮT BUỘC** dùng công cụ `clarify` đưa ra 2–3 phương án tên nữ/nam tự nhiên tiếng Việt (hoặc theo prefix email) để user quyết định trước khi can thiệp thiết bị.

### Kỹ thuật gõ tiếng Việt có dấu qua ADB:
- Android S7 trên farm dùng **AdbKeyboard**.
- Để gõ chuỗi tiếng Việt có dấu (ví dụ: `"Hải Sa"`), mã hóa Base64 chuỗi UTF-8:
  ```python
  import base64
  raw_text = "Hải Sa"
  b64_text = base64.b64encode(raw_text.encode("utf-8")).decode("ascii")
  # Kết quả: "SOG6o2kgU2E="
  ```
- Phát broadcast ADB:
  ```bash
  adb -s <serial> shell am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text "SOG6o2kgU2E="
  ```

### Các bước thao tác UI chuẩn:
1. Mở TikTok: `am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`
2. Vào tab Hồ sơ (Profile tab ở góc dưới bên phải).
3. Kiểm tra đúng tài khoản cần đổi (nếu đang ở nick khác thì mở Switcher chuyển sang).
4. Chụp ảnh hiện trường TRƯỚC KHI ĐỔI: `before_rename.png`.
5. Bấm nút **"Sửa hồ sơ"** (Edit profile).
6. Bấm vào mục **"Tên"** (hiện đang chứa tên cũ, ví dụ `"8"`).
7. Xóa text cũ, gõ tên mới qua AdbKeyboard Base64.
8. Bấm **"Lưu"** (Save) ở góc trên bên phải.
9. Bấm **"Xác nhận"** trên dialog cảnh báo giới hạn 7 ngày.
10. Quay lại màn hình Profile chính, chụp ảnh nghiệm thu: `after_rename.png`.
11. Báo cáo nghiệm thu kèm `MEDIA:<path>` theo Invariant Gate 6.
12. Đưa máy về HOME an toàn và giải phóng lock.

---

## 3. Quy chuẩn điều phối Subagent Worker (Coordinator Guard Invariants)

Khi Coordinator gọi `delegate_task` để thực hiện can thiệp farm:
1. **Bắt buộc khai báo `TASK_KIND`:**
   - Context bắt buộc phải có dòng `TASK_KIND: INVESTIGATE` (nếu là task đọc/thao tác hiện trường) hoặc `TASK_KIND: EDIT` (nếu là task sửa code/repo).
   - Nếu thiếu `TASK_KIND`, Coordinator Guard sẽ chặn dispatch ngay lập tức với lỗi: `MISSING_TASK_KIND`.
2. **Device Lock độc quyền:**
   - Tuyệt đối không để Worker can thiệp máy trần mà không có lock.
   - Lệnh bọc ngoài bắt buộc:
     ```bash
     python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command>
     ```
     hoặc sử dụng context manager `operator_device_lock` từ `automation_core.device_lock`.
