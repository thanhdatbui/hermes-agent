# Windows OpenSSH Job Object Breakaway, ADB Transport Reconnect & TikTok Auth-Blocked Triage (25/10/2026)

## 1. Hiện Tượng & Bẫy Chết Tiến Trình Con Qua Windows OpenSSH (Admin Host)
- **Bối cảnh:** Khi điều phối từ xa từ máy Kibe tới Admin PC (`192.168.110.119`) qua `admin_ssh.py`, ta cần spawn một tiến trình Python dài hạn (ví dụ: `tiktok_login_v1.py` chạy 60-120s) chạy nền hoàn toàn để không nghẽn SSH session hoặc không bị timeout SSH.
- **Bẫy kỹ thuật (Root Cause):**
  * Trên Windows, dịch vụ OpenSSH Server bọc mỗi phiên SSH người dùng vào một **Windows Job Object**.
  * Nếu dùng `subprocess.Popen(..., creationflags=subprocess.DETACHED_PROCESS)` (giá trị `0x00000008`), tiến trình con bị tách console nhưng **vẫn nằm trong Job Object của OpenSSH**.
  * Ngay khi kênh SSH kết thúc và đóng phiên, OpenSSH Server dọn dẹp Job Object, tự động **terminate toàn bộ các tiến trình con** mà không để lại log crash!
- **Giải pháp Đột phá (Breakaway Flag):**
  * BẮT BUỘC kết hợp cờ `CREATE_BREAKAWAY_FROM_JOB` (`0x01000000`) cùng với `DETACHED_PROCESS` (`0x00000008`):
    ```python
    creationflags = 0x01000000 | 0x00000008  # 0x01000008
    p = subprocess.Popen(cmd, cwd=workdir, stdout=log_file, stderr=subprocess.STDOUT, creationflags=creationflags)
    ```
  * Nhờ cờ này, tiến trình con thoát hoàn toàn khỏi sự quản lý vòng đời của phiên SSH, tiếp tục thực thi độc lập trên host Admin ngay cả khi SSH ngắt kết nối.

---

## 2. Remote ADB Transport Contention & Phục Hồi Bằng `adb reconnect`
- **Sự cố:** Sau khi các batch lớn (như batch 2FA 15 workers hoặc ca nuôi XiaoWei) chạy xong hoặc xảy ra timeout bus USB, thiết bị có thể rơi vào trạng thái treo I/O (`device offline or ADB/USB disconnected`, `socket read timed out`).
- **Phản xạ sai:** Vội vàng báo cáo đứt cáp USB thật, đòi khởi động lại máy điện thoại hoặc rút cắm lại cáp.
- **Quy trình cứu hộ O(1):**
  1. Kiểm tra trạng thái ADB:
     ```bash
     python D:/Taadaa/tools/remote_admin_adb.py devices
     ```
  2. Nếu thiết bị có trong danh sách nhưng lệnh shell bị timeout, thực thi ngay lệnh tái đàm phán transport:
     ```bash
     python D:/Taadaa/tools/remote_admin_adb.py -s <serial> reconnect
     ```
  3. Lệnh này tái khởi tạo handshake kết nối giữa ADB server và adbd trên điện thoại trong < 1 giây, đưa thiết bị về lại trạng thái `device` hoạt động bình thường mà không làm mất phiên ứng dụng.

---

## 3. Tích Hợp Popup Solver Từ `automation-core` Vào Runner Độc Lập
- **Nguyên tắc kế thừa:** Các script độc lập cũ (như `tiktok_login_v1.py`) khi gặp popup TikTok (ví dụ: bottom-sheet "Thêm số điện thoại của bạn để tăng cường bảo mật...") TUYỆT ĐỐI KHÔNG tự viết parser regex hoặc toạ độ tay rời rạc.
- **Cách tích hợp chuẩn:**
  1. Bootstrapping sys.path an toàn cho môi trường đa venv:
     ```python
     _c = r"D:\Taadaa\automation-core\src"
     if _c not in sys.path and os.path.isdir(_c):
         sys.path.insert(0, _c)
     ```
  2. Sử dụng trực tiếp bộ rules và button finder chuẩn:
     ```python
     from automation_core.tiktok_popup import _detect_tiktok_popup, _find_button, TIKTOK_POPUP_RULES
     match = _detect_tiktok_popup(xml_text, TIKTOK_POPUP_RULES)
     if match:
         btn = _find_button(xml_text, match.rule)
         if btn and btn.center:
             tap(device_id, btn.center[0], btn.center[1], wait=D_LONG)
     ```

---

## 4. Xử Lý Sai Pass Tài Khoản Hotmail & Cơ Chế Chuyển Sang OTP-Only
- **Hiện tượng:** Nick TikTok lưu trong workbook báo lỗi `⚠️ Mật khẩu sai` khi submit password.
- **Nguyên nhân gốc:** Các tài khoản reg qua luồng Hotmail/Outlook trước đây thường đăng ký bằng mã OTP email và người dùng/tool có thể đã bỏ qua bước "Tạo mật khẩu" (Skip Password), hoặc mật khẩu trong cột `PASS` bị lệch với mật khẩu thực tế.
- **Kỷ luật chống khóa tài khoản (`[AUTH_BLOCKED]`):**
  * CẤM TUYỆT ĐỐI thử lại mật khẩu lần 2 nếu màn hình vẫn đứng ở ô password và báo lỗi sai pass.
  * Phải dừng ngay lập tức để bảo vệ tài khoản khỏi bị checkpoint khóa vĩnh viễn.
  * Chuyển hướng sang cờ `--otp-only`: Chọn "Quên mật khẩu?" hoặc "Đăng nhập bằng mã xác minh" gửi về hòm thư Hotmail/Outlook, trích xuất OTP 6 số để đăng nhập và thiết lập lại mật khẩu đồng bộ vào workbook.
