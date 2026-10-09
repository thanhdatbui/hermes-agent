# Quy Trình Warmup Gmail Mới Bằng Hook Đăng Ký ChatGPT (Google OAuth) Trên Thiết Bị S7

## 1. Bối cảnh & Mục đích
- Trước đây hệ thống dùng script `warmup_newsletter_services.py` để gửi request đăng ký nhận bản tin công nghệ (Node Weekly, Ruby Weekly...) nhằm kéo mail inbound tạo độ trust.
- **Thực trạng**: Các trang newsletter công khai hiện nay đều bật Cloudflare Bot Protection (Turnstile) chặn request HTTP POST. Gửi request trả về 200 thực chất là trang challenge Cloudflare, thư không bao giờ về hòm thư Gmail (kết quả ảo - false positive).
- **Giải pháp tối ưu**: Thay thế bằng việc đăng ký dịch vụ AI (ChatGPT) thông qua Google OAuth trực tiếp trên trình duyệt Chrome của chính thiết bị Samsung S7 vừa reg.
  - Mang lại email xác nhận / security notice chính thức từ Google & OpenAI (`openai.com`).
  - Google nhận diện hành vi người dùng thật (vừa tạo mail trên S7 đi đăng ký dịch vụ trên cùng IP Proxy 4G).
  - Khởi tạo sẵn tài khoản ChatGPT cho dàn nick.

---

## 2. Các Rào Cản Kỹ Thuật & Khắc Phục Trên Samsung S7 (Android 8.0)

### Pitfall 1: CustomTab / Account Chooser văng vào Settings máy
- **Hiện tượng**: Trên Chrome Android 8.0, bấm "Tiếp tục với Google", nếu hệ thống gọi Account Chooser của Google Play Services, intent redirect có thể bị văng ra màn hình `Settings$UserAndAccountDashboardActivity`.
- **Khắc phục**: Khi mở Google Signin trên Web, chọn tài khoản trực tiếp trong DOM web thay vì intent hệ thống. Nếu Google hỏi xác nhận mật khẩu, nhập mật khẩu chuẩn bằng `human_type`.

### Pitfall 2: Escape ký tự đặc biệt trong mật khẩu khi gõ qua ADB
- **Hiện tượng**: Mật khẩu chứa ký tự `!` (ví dụ `Kha!594Apex`), nếu bắn thô `input text Kha!594Apex` hoặc escape sai trong bash sẽ gõ thành `Kha\!594Apex` hoặc mất ký tự `!` khiến Google báo đỏ *"Mật khẩu không chính xác"*.
- **Khắc phục**: Bắt buộc dùng hàm `human_type` chuẩn (được định nghĩa trong `gmail_reg_v10.py`), escape ký tự đặc biệt theo shell escape set `r"\$&*();'\"<>|~^!?"` và gửi `\{ch}`.

### Pitfall 3: Lỗi OpenAI `client_id_not_found_in_session` do mất session
- **Hiện tượng**: Nếu quá trình xác thực bị ngắt quãng, tải lại nhiều lần hoặc mở nhiều tab Chrome thì session cookie của OpenAI bị mất, dẫn đến lỗi xác thực `client_id_not_found_in_session`.
- **Khắc phục**: Trước khi bắt đầu luồng, `force-stop com.android.chrome` để khởi tạo session sạch từ `https://chatgpt.com/auth/login`.

### Pitfall 4: Bàn phím ảo che mất nút "Tiếp tục" ở form About You
- **Hiện tượng**: Sau khi điền tuổi tại màn hình `auth.openai.com/about-you` ("Bạn bao nhiêu tuổi?"), bàn phím ảo của Samsung S7 không tự ẩn, che mất nút `Tiếp tục` bên dưới.
- **Khắc phục**: Sau khi gõ tuổi, gọi `hide_keyboard(device_id)` và gửi lệnh tap vào vùng header `(540, 200)` để ép ẩn bàn phím trước khi tìm/tap nút Tiếp tục.

---

## 3. Kiến Trúc Module & Điểm Nối Hook

### File thực thi độc lập:
`D:/Taadaa/register gmail/scripts/hook_chatgpt_register.py`

```python
from hook_chatgpt_register import register_chatgpt_on_device

# Gọi sau khi hàm register() trong gmail_reg_v10.py báo thành công:
res = register_chatgpt_on_device(
    device_id=device_id,
    email=email_target,
    password=pwd_target,
    dob=dob_target,
    timeout=180
)
# res: {"success": True/False, "status": "COMPLETED", "email": ..., "age": ...}
```

### Điểm tích hợp vào `gmail_reg_v10.py`:
Tại hàm `persist_success_result(acc, device_id=None)`:
1. Gọi `register_chatgpt_on_device(device_id, email, password, dob)` kích hoạt liên kết OAuth và nhận thư bảo mật.
2. Giữ fallback newsletter dự phòng.
3. Không làm gián đoạn luồng chính nếu hook gặp lỗi mạng ngoại vi.
