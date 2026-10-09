# Google Prompt & Security Code Automation trên Samsung Galaxy S7 (Android 7)

## 1. Hiện tượng & Vấn đề thực tế

Trong quy trình nạp OAuth Antigravity từ tài khoản Gmail chạy trên thiết bị Samsung Galaxy S7 qua pipeline GPMLogin Playwright:
1. **Daemon `atx-agent` bị tắt/chết đột ngột trên S7**: Khiến các cuộc gọi forward port (VD: `17000 + machine_id` -> `7912`) để dump UI XML hierarchy ném lỗi `RemoteDisconnected`.
2. **Biến thể Tiếng Việt của Google Prompt**: Google UI cập nhật thêm cụm từ **"Chạm vào Có trên điện thoại hoặc máy tính bảng của bạn"** thay vì chỉ có "Nhấn vào Có", khiến selector cũ bỏ sót và không nhận diện được challenge `dp`.
3. **Thanh tab ngang trong Google Settings che khuất tab "Bảo mật"**: Trên màn hình độ phân giải của S7, thanh tab của ứng dụng Google Account gồm: `[Trang chủ] [Thông tin cá nhân] [Dữ liệu và quyền riêng tư] [Bảo mật]`. Tab **"Bảo mật"** nằm lệch hoàn toàn về phía bên phải (ngoài viewport). Lệnh vuốt dọc thông thường không thể làm lộ tab này.
4. **SMS Checkpoint có số điện thoại ủy quyền**: Khi Google chuyển hướng sang màn hình SMS yêu cầu gửi mã xác minh đến số điện thoại, nếu có số điện thoại được ủy quyền từ user (VD: `0906746624`), pipeline cần tự động điền số vào `input[type="tel"]`, bấm Gửi và chụp ảnh màn hình chờ OTP.

---

## 2. Giải pháp kỹ thuật

### 2.1. Đảm bảo Daemon `atx-agent` luôn sống (`ensure_atx_agent`)
Trước khi thực hiện `adb forward tcp:<atx_port> tcp:7912` để thao tác UI, luôn kiểm tra tiến trình `atx-agent` và tự khởi động lại:

```python
def ensure_atx_agent(serial: str) -> None:
    try:
        check = subprocess.run([ADB_EXE, "-s", serial, "shell", "ps -A | grep atx-agent"], capture_output=True, text=True, timeout=5)
        if "atx-agent" not in check.stdout:
            logger.info(f"atx-agent not running on {serial}, starting daemon...")
            subprocess.run([ADB_EXE, "-s", serial, "shell", "/data/local/tmp/atx-agent server -d"], capture_output=True, timeout=8)
            time.sleep(1.0)
    except Exception as e:
        logger.warning(f"ensure_atx_agent warning on {serial}: {e}")
```

### 2.2. Nhận diện mở rộng Google Prompt (Tiếng Việt)
- Regex lấy PIN: `r'(?:nhấn vào|rồi nhấn vào|chạm vào|rồi chạm vào|chọn|tap|số|number)\s*(\d{1,2})'`
- Thêm điều kiện trigger: `"chạm vào có" in body_content`
- Selector cho tùy chọn Prompt:
  `div[data-challengetype="6"], li:has-text("Nhấn vào Có"), li:has-text("Chạm vào Có"), li:has-text("Tap Yes"), div[role="link"]:has-text("Nhấn vào Có"), div[role="link"]:has-text("Chạm vào Có"), div[role="button"]:has-text("Chạm vào Có")`

### 2.3. Vuốt ngang thanh tab để lộ mục "Bảo mật"
Trong Step 5 của hàm lấy Security Code (`get_s7_security_code`):
```python
# Vuốt ngang thanh tab (800, 280 -> 200, 280) để lộ tab 'Bảo mật' ở phía bên phải
subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "swipe", "800", "280", "200", "280"], capture_output=True, timeout=5)
subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "swipe", "500", "1400", "500", "600"], capture_output=True, timeout=5)
time.sleep(1.0)
```

### 2.4. Điền số điện thoại ủy quyền khi dính SMS Checkpoint
Nếu `phone_number` được truyền trong cấu hình account (`acc.get("phone_number")`):
- Điền vào `input[type="tel"], input#phoneNumberId, input[name="phoneNumber"]`
- Nhấn nút "Gửi" / "Tiếp theo"
- Chụp ảnh màn hình lưu vào `debug_screenshots`
- Chuyển trạng thái sang `AWAITING_SMS_OTP` để user nhập OTP hoàn tất nạp.
