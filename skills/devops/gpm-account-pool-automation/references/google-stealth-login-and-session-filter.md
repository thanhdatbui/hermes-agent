# Google Stealth Login & Session Filtering Runbook

## 1. Nguyên tắc cốt lõi (User Policy)
1. **Kiểm tra Session trước tiên (Skip if already logged in):**
   - Không đăng nhập lại các profile đã có session hợp lệ.
   - Luôn load `https://myaccount.google.com` để kiểm tra. Nếu URL là `myaccount.google.com` và không chứa `signin` hay `about`: **BỎ QUA NGAY**, không điền thông tin để tránh làm bẩn / đè session cũ.
2. **Chỉ xử lý đúng danh sách chưa login:**
   - Khi chạy batch, chỉ tập trung vào các profile/account chưa có session hoặc nằm trong danh sách cần khắc phục (ví dụ: cụm 28 Admin accounts trên port MikroTik `10008..10035`).
3. **Phân biệt Profile Sạch vs Profile Kibe:**
   - 15 Profile Kibe (`01_Rua`, `02..15` trong Group `cheat`): CẤM đổi proxy, CẤM đưa vào batch test tài khoản khác.
   - Khi cần profile trắng để nạp acc Admin / acc mới: Chỉ lấy từ kho 240 profile ẩn (`GroupId = 0` trong `profile_data.db` / `gpm_hidden_240profiles_*.zip`).

---

## 2. Kỹ thuật Stealth Launch vượt "Trình duyệt không an toàn" của Google

### Launch Arguments chuẩn:
```python
args = [
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-blink-features=AutomationControlled",
    "--lang=vi-VN,vi"
]
```

### Khởi tạo Playwright Persistent Context:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=profile_path,
        executable_path=CHROME_EXE,
        proxy={"server": f"http://192.168.110.2:{20000 + machine_num}"},
        locale="vi-VN",
        headless=False,
        args=args
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.set_default_timeout(35000)
```

---

## 3. Xử lý chuỗi Popup Onboarding sau Password

Google thường hiển thị các màn hình Onboarding:
- *"Thêm video selfie dùng để đăng nhập"*
- *"Tạo mã khóa (Passkey)"*
- *"Thêm số điện thoại khôi phục"*

### Vòng lặp giải phóng liên hoàn:
```python
for _ in range(4):
    time.sleep(2)
    dismiss_btn = page.locator('button:has-text("Bỏ qua"), button:has-text("Để sau"), button:has-text("Not now"), button:has-text("Hủy"), button:has-text("Skip")')
    if dismiss_btn.count() > 0:
        try:
            dismiss_btn.first.click()
            time.sleep(3)
        except Exception:
            pass
    else:
        break
```
