# Google Sign-in Video Selfie Speedbump & GPM Proxy Circuit Breaker Separation

## 1. Google Video Selfie Speedbump & Anchor Tag `<a ...>Để sau</a>` Pitfall (2026-09-05)

### Triệu chứng
- Khi đăng nhập Google bằng tài khoản Gmail thật (đã nhập đúng email và password), Google không redirect thẳng về `myaccount.google.com` mà chuyển hướng qua màn hình onboarding hoặc speedbump:
  - URL: `https://gds.google.com/web/landing?...` hoặc `https://accounts.google.com/v3/signin/challenge/pwd?...`
  - Tiêu đề: *"Bảo vệ quyền truy cập vào tài khoản bằng video selfie"*
  - Nội dung: *"Việc lưu video selfie có thể giúp bạn đăng nhập vào Tài khoản Google nếu gặp sự cố đăng nhập..."*
- Kịch bản tự động chờ 15 bước (mỗi bước 5s) và báo `Login failed. Ended at URL: https://www.google.com/account/about/?hl=vi`.

### Nguyên nhân gốc rễ (DOM Inspection)
- Trên giao diện mới của Google (Material Design 3 / Glif), nút **"Để sau"** (hoặc *"Bỏ qua"*, *"Huỷ"*, *"Lúc khác"*) **KHÔNG PHẢI THẺ `<button>`** mà là thẻ liên kết `<a>` chứa thẻ con `<span>`:
  ```html
  <span jsname="V67aGc" class="VfPpkd-vQzf8d" aria-hidden="true">Để sau</span>
  <a class="WpHeLc VfPpkd-mRLv6 VfPpkd-RLmnJb" href="https://accounts.google.com/ServiceLogin?continue=https://myaccount.google.com/...">
    <!-- ripple & background -->
  </a>
  ```
- Bộ chọn cũ chỉ tìm `button:has-text("Để sau")` hoặc `button:has-text("Bỏ qua")` nên hoàn toàn không tìm thấy phần tử nào (`count() == 0`), khiến script bị bỏ qua bước dismiss và timeout.

### Khắc phục chuẩn trong Playwright
Bắt buộc mở rộng danh sách `dismiss_selectors` và `agree_selectors` quét đồng thời thẻ `a`, `button` và `span`:

```python
dismiss_selectors = [
    'a:has-text("Để sau")',
    'button:has-text("Để sau")',
    'span:has-text("Để sau")',
    'a:has-text("Không phải bây giờ")',
    'button:has-text("Không phải bây giờ")',
    'a:has-text("Not now")',
    'button:has-text("Not now")',
    'a:has-text("Bỏ qua")',
    'button:has-text("Bỏ qua")',
    'a:has-text("Skip")',
    'button:has-text("Skip")',
    'a:has-text("Hủy")',
    'button:has-text("Hủy")',
    'a:has-text("Huỷ")',
    'button:has-text("Huỷ")',
    'a:has-text("Lúc khác")',
    'button:has-text("Lúc khác")'
]

agree_selectors = [
    'a:has-text("Tôi đồng ý")',
    'button:has-text("Tôi đồng ý")',
    'a:has-text("I agree")',
    'button:has-text("I agree")',
    'a:has-text("Tiếp tục")',
    'button:has-text("Tiếp tục")',
    'a:has-text("Continue")',
    'button:has-text("Continue")'
]
```

---

## 2. Phân Tách Lỗi Hạ Tầng Proxy vs Lỗi Tài Khoản Trong Circuit Breaker (Fail-Safe)

### Vấn đề
- Khi chạy batch tự động nhiều tài khoản trên GPMLogin:
  - Một số cổng proxy 4G Mobi hoặc MikroTik có thể bị reset modem, mất sóng tạm thời hoặc chập chờn.
  - Khi gọi `GET /api/v3/profiles/start/{id}`, GPM pre-flight test proxy fail và trả về:
    ```json
    {"success": false, "data": null, "message": "Không thể kết nối tới proxy"}
    ```
- Nếu kịch bản xếp lỗi này chung vào nhóm lỗi tài khoản (`FAILED` / `ERROR`) và tăng biến đếm `consecutive_failures += 1`, thì chỉ cần 1 proxy cổng lẻ bị lag kết hợp với 2 tài khoản gặp thử thách bảo mật sẽ kích hoạt **Circuit Breaker** ngắt khẩn cấp toàn bộ batch, làm đình trệ các tài khoản khỏe mạnh phía sau.

### Quy tắc chuẩn xử lý
1. **Phân loại trạng thái trả về:**
   - Nếu GPM start profile fail do proxy: gán `outcome["status"] = "PROXY_ERROR"`.
   - Nếu Google báo sai mật khẩu hoặc checkpoint SMS: gán `outcome["status"] = "CHECKPOINT"` hoặc `"FAILED"`.
2. **Kỷ luật đếm Circuit Breaker:**
   - **CHỈ** tăng `consecutive_failures` khi gặp lỗi xuất phát từ Google (`CHECKPOINT`, `DIE`, `FAILED` do Google chặn).
   - Khi gặp `PROXY_ERROR`, ghi log cảnh báo và **BỎ QUA KHÔNG TĂNG `consecutive_failures`**:
     ```python
     if status in ["CHECKPOINT", "DIE", "FAILED"]:
         consecutive_failures += 1
         logger.warning(f"⚠️ Consecutive Google account failures: {consecutive_failures}/{CIRCUIT_BREAKER_LIMIT}")
         if consecutive_failures >= CIRCUIT_BREAKER_LIMIT:
             logger.critical("🛑 CIRCUIT BREAKER TRIGGERED! Halting batch immediately!")
             break
     elif status == "PROXY_ERROR":
         logger.warning(f"[M{acc['machine']:02d}] Proxy error encountered, skipping consecutive failure increment.")
     else:
         consecutive_failures = 0
     ```

---

## 3. Selector Chuẩn Cho Danh Sách Thử Thách `challenge/selection`

Trên màn hình `https://accounts.google.com/v3/signin/challenge/selection`:
- Các mục lựa chọn phương thức xác minh (Mã bảo mật, Email khôi phục, Authenticator) được render trong các thẻ `<li>` chứa `[role="link"]` và mã `data-challengetype`:
  - `data-challengetype="12"`: Gửi mã đến email khôi phục.
  - `data-challengetype="8"`: Nhận mã bảo mật trên thiết bị (S7).
  - `data-challengetype="6"`: Ứng dụng xác thực (Authenticator).
- **Tránh dùng selector broad:** Tránh dùng `div:has-text("mã bảo mật")` vì sẽ match vào thẻ container cha bao ngoài.
- **Selector chuẩn trong Playwright:**
  ```python
  rec_opt = page.locator('li:has-text("email khôi phục"), li:has-text("recovery email"), div[data-challengetype="12"]')
  sec_opt = page.locator('li:has-text("mã bảo mật"), li:has-text("security code"), div[data-challengetype="8"]')
  auth_opt = page.locator('li:has-text("Authenticator"), li:has-text("ứng dụng xác thực"), div[data-challengetype="6"]')
  ```
