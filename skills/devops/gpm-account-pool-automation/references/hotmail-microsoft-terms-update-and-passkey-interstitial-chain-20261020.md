# Microsoft Hotmail Terms Update ("We're updating our terms") & Passkey Interstitial Chain

## 1. Hiện Tượng Hiện Trường
Khi đăng nhập tài khoản Hotmail/Microsoft qua GPMLogin v3 (`batch_gpm_hotmail_password_login.py`):
1. Nhập email ➔ Bấm "Use your password" ➔ Nhập password ➔ Bấm Sign in.
2. Trình duyệt chuyển hướng sang trang cập nhật điều khoản dịch vụ của Microsoft:
   `https://account.live.com/tou/accrue?mkt=EN-US&uiflavor=web&id=38936...`
   Màn hình hiển thị: `"We're updating our terms"` kèm nút xanh lớn **`Next`**.
3. **Lỗi quan sát được:** Script dừng lại tại màn hình này, lưu ảnh chụp nghiệm thu `post_login_...png`, báo `LOGIN SUCCESS! (exit code 0)` và tự đóng trình duyệt mà **hoàn toàn không bấm Next**!

## 2. Nguyên Nhân Kỹ Thuật (Hai Bẫy Tử Huyệt)

### Bẫy 1: Thiếu Selector Tiếng Anh Trong Interstitial Handlers
Trong script đăng nhập cũ, bộ selector của màn hình điều khoản (`term_sel`) chỉ chứa các từ khóa tiếng Việt hoặc class giao diện cũ:
```python
# CODE CŨ THIẾU SELECTOR TIẾNG ANH:
term_sel = ["input[value*='Tiếp']", "button:has-text('Tiếp')", ".btn-primary", "input[type='submit']", "#iNext"]
```
Khi profile chạy với locale tiếng Anh (`mkt=EN-US`), nút bấm có text là **`Next`**:
- Nút là thẻ `<button>` với Fluent UI classes hiện đại, không dùng class Bootstrap `.btn-primary`.
- Không phải thẻ `<input type="submit">`.
- Không mang ID `#iNext`.
➔ Tất cả selector tiếng Việt đều timeout 1500ms, vòng lặp interstitial (10 loops) trôi qua trong im lặng mà không click được nút Next.

### Bẫy 2: Ngộ Nhận Đăng Nhập Thành Công Sớm (False-Done Early Exit)
Trong hàm kiểm tra trạng thái đăng nhập cuối cùng:
```python
# CODE CŨ BỊ BẪY URL:
if netloc in ["account.microsoft.com", "outlook.live.com"] or (netloc == "account.live.com" and path not in ["/", "/login.srf"]):
    logged_in = True
```
- Trang Terms nằm trên domain `account.live.com` với path `/tou/accrue`.
- Biểu thức `path not in ["/", "/login.srf"]` trả về `True`, khiến script ngộ nhận rằng tài khoản đã vào trang chủ Microsoft!
- Hậu quả: Script lưu ảnh chụp màn hình đang kẹt ở Terms, đánh dấu `status: SUCCESS`, rồi gọi API đóng trình duyệt. Phiên đăng nhập chưa được xác nhận điều khoản sẽ bị kẹt lại khi chạy ChatGPT OAuth hoặc lần login kế tiếp.

## 3. Chuỗi Interstitial Liên Hoàn Cần Xử Lý (Cascade Chain)
Khi bấm `Next` vượt qua màn hình Terms, Microsoft **không chuyển ngay về Account Home** mà kích hoạt chuỗi màn hình kế tiếp:
1. **Bước 1 — Điều khoản (`/tou/accrue`):**
   - Tiêu đề: `"We're updating our terms"` / `"Chúng tôi đang cập nhật các điều khoản"`.
   - Action: Bấm nút `Next` / `Tiếp theo`.
   - Selectors chuẩn:
     ```python
     [
         "button:has-text('Next')", "button:has-text('next')",
         "button:has-text('Tiếp theo')", "button:has-text('Tiếp tục')",
         "button:has-text('Tiếp')", "input[value*='Next']", "input[value*='Tiếp']",
         "#iNext", "button[id*='Next']", "a:has-text('Next')",
         ".btn-primary", "input[type='submit']", "button[type='submit']"
     ]
     ```
2. **Bước 2 — Gợi ý tạo Passkey / FIDO (`/consumers/fido/create`):**
   - Tiêu đề: `"Setting up your passkey..."` / `"Thiết lập khóa truy cập..."`.
   - Action: Bắt buộc bấm **`Cancel` / `Bỏ qua` / `Hủy`** (CẤM treo chờ Windows Security dialog vì môi trường farm headless không có thiết bị bảo mật phần cứng).
   - Selectors chuẩn:
     ```python
     [
         "#fido-cancel-button", "button:has-text('Cancel')", "a:has-text('Cancel')",
         "button:has-text('Hủy')", "a:has-text('Hủy')", "button:has-text('Skip')",
         "#iCancel", "button#iCancel", "#idBtn_Back",
         "a:has-text('No thanks')", "a:has-text('Không, cảm ơn')",
         "a:has-text('Skip for now')", "button:has-text('Not now')"
     ]
     ```
3. **Bước 3 — Duy trì đăng nhập KMSI (`login.live.com/login.srf?...`):**
   - Tiêu đề: `"Stay signed in?"` / `"Duy trì đăng nhập?"`.
   - Action: Bấm **`Yes` / `Có`** để lưu session cookie vào profile GPM vĩnh viễn.
   - Selectors chuẩn:
     ```python
     ["#idSIButton9", "input[type='submit']", "button[type='submit']", "input[value*='Có']", "input[value*='Yes']", "button:has-text('Có')", "button:has-text('Yes')"]
     ```
4. **Bước 4 — Kiểm tra trang đích thực thụ (Authenticated Account Home):**
   - Loại trừ dứt điểm `/tou/` và `/fido/` khỏi điều kiện thành công:
     ```python
     is_terms = "tou" in final_url.lower() or "terms" in page.title().lower()
     is_fido = "fido/create" in final_url.lower()
     if (netloc in ["account.microsoft.com", "outlook.live.com"] or (netloc == "account.live.com" and path not in ["/", "/login.srf"])) and not is_terms and not is_fido:
         logged_in = True
     ```
   - Xác nhận có các thành phần điều khiển người dùng: `#mectrl_headerPicture`, `button#mectrl_main_trigger`, `#meControl` hoặc text `"Microsoft account"`, `"Account"`, `"Security"`.
