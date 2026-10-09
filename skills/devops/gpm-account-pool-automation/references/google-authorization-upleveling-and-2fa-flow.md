# Google Authorization Upleveling, IAP QR Code & 2FA Automation Workflow

## 1. Cơ chế `AUTHORIZATION_UPLEVELING` của Google
Khi ứng dụng hoặc proxy yêu cầu quyền OAuth cấp cao cho Developer / Cloud Code API (`https://www.googleapis.com/auth/cloud-platform`, `experimentsandconfigs`, `cclog`) từ các môi trường anti-detect browser hoặc IP proxy datacenter, Google kích hoạt cơ chế `AUTHORIZATION_UPLEVELING`.

### Đặc điểm:
- **Mã lỗi API:** HTTP `403 Forbidden` / `PERMISSION_DENIED` với reason `VALIDATION_REQUIRED` và thông báo `"Verify your account to continue."`.
- **Giao diện chặn:** URL `https://accounts.google.com/v3/signin/challenge/iap/qrcode` hiển thị dòng chữ:
  > *"Verify your info to continue — Google needs to verify some info about your device or phone number before you can continue... Scan the QR code with your phone"*.
- **Tính chất bắt buộc:** Google **không cung cấp nút "Thử cách khác" (Try another way)** trên màn hình này. Đây là cơ chế anti-abuse bắt buộc có tương tác phần cứng thực tế.
- **Hành vi khi mở link trực tiếp trên máy không có Camera / SIM hoặc copy-paste URL vào Safari/Chrome:**
  Google phát hiện thiếu luồng quét phần cứng từ ứng dụng Camera thật và sẽ từ chối ngay lập tức:
  > *"We couldn't verify your info — Something went wrong and we couldn't verify your info. To complete verification, try going through the steps again."*
- **Giải pháp chuẩn:** 
  - Gửi ảnh chụp mã QR trực tiếp qua tin nhắn (`MEDIA:...png`) hoặc giữ Profile GPM hiển thị QR trên màn hình.
  - Bắt buộc người dùng dùng **ứng dụng Camera trên điện thoại/iPad thật** lia ống kính vào mã QR trên màn hình máy tính rồi chạm vào popup để hoàn tất, tuyệt đối không copy-paste đường link.

---

## 2. Trích xuất Link ẩn từ Base64 QR Code trong DOM
Để debug hoặc trích xuất link verification bên trong ảnh QR:

```python
import base64
import io
import zxingcpp
from PIL import Image

# Trích xuất từ selector img[alt*="QR"] trên trang challenge/iap/qrcode
# img_src có dạng "data:image/png;base64,iVBORw0KGgo..."
b64_data = img_src.split("base64,")[1]
img = Image.open(io.BytesIO(base64.b64decode(b64_data)))

# Giải mã barcode
results = zxingcpp.read_barcodes(img)
for r in results:
    qr_url = r.text
    print("Decoded URL:", qr_url)
    # Output: https://accounts.google.com/devicephoneverification/begin?flow=browser&plt=...
```

---

## 3. Tự động bật 2-Step Verification (2FA) qua GPM CDP
Khi tài khoản chưa bật 2FA, có thể tự động kích hoạt bảo vệ 2FA (kết hợp Phone + Google prompt + Passkey có sẵn) bằng Playwright CDP:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
    page = browser.contexts[0].new_page()
    
    # 1. Mở trang cài đặt 2FA
    page.goto("https://myaccount.google.com/signinoptions/two-step-verification", wait_until="domcontentloaded")
    
    # 2. Nhập mật khẩu xác thực nếu được hỏi
    pwd_input = page.locator('input[type="password"]').first
    if pwd_input.is_visible():
        pwd_input.fill(master_password)
        page.locator('button:has-text("Next"), [role="button"]:has-text("Next")').first.click()
        page.wait_for_timeout(4000)
        
    # 3. Bấm Turn on 2-Step Verification
    turn_on_btn = page.get_by_role("button", name="Turn on 2-Step Verification")
    if turn_on_btn.is_visible():
        turn_on_btn.click()
        page.wait_for_timeout(3000)
        
    # 4. Xác nhận Done trên popup hoàn tất
    done_btn = page.get_by_role("button", name="Done")
    if done_btn.is_visible():
        done_btn.click()
        print("2FA Enabled Successfully!")
```
