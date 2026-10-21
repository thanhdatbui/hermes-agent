# Gemini Pro 18M Auto-Sniper, CDP Activation & 1:1 Proxy Dual-Pool Provisioning (2026-10-21)

## 1. Bối cảnh & Mục tiêu
Khi săn mua các gói nâng cấp Google One / Gemini Pro thời hạn ngắn (gói kích hoạt link bảo hành 5-10 phút từ SumiStore hoặc các chợ số), thao tác mở link tay là điểm nghẽn nghiêm trọng (Human-Latency Failure). Yêu cầu kỹ thuật cốt lõi:
1. Tự động hóa mua hàng qua API ký HMAC-SHA256 (`X-Timestamp`, `X-Nonce`, `X-Signature`).
2. Tự động mở GPM profile tương ứng và click kích hoạt trực tiếp qua Playwright CDP (Zero-Manual-Click Invariant).
3. Đảm bảo bảo toàn tuyệt đối nguyên tắc **Proxy 1:1 Đa Tầng (Parity Invariant)** giữa máy S7 vật lý, profile GPM, OmniRoute connection, và AGY CLI profile sandbox.
4. Tự động hóa nạp tài khoản Pro vừa kích hoạt vào đồng thời cả 2 pool: **OmniRoute Combo (`ag-gemini-pool-3`)** và **AGY CLI (`D:/Taadaa/agy_profiles/acc_XX`)**.

---

## 2. Luồng Tự Động Kích Hoạt CDP Trên Google One (Zero-Manual-Click Invariant)

### A. Cạm bẫy Giao diện & Modal Bị Che (Dialog Trap)
Khi link kích hoạt (`https://gemini-activation.../subscription/new/...`) chuyển hướng vào `https://one.google.com/activate-plan/...`:
- Trang Google One thường mở sẵn một modal dialog thông báo dung lượng: `"Sử dụng tổng bộ nhớ 5 TB"`.
- Modal này che phủ nút chính, khiến các lệnh click trực tiếp vào nút `"Kích hoạt gói"` bị timeout hoặc rơi vào trạng thái không tương tác được.

### B. Bộ Chọn & Thứ Tự Thao Tác Chuẩn
```python
from playwright.sync_api import sync_playwright
import time

def auto_activate_google_one(cdp_addr, activation_url):
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
        page = browser.contexts[0].new_page()
        page.goto(activation_url, timeout=30000)

        # 1. Đợi redirect vào trang Google One
        for _ in range(15):
            time.sleep(1)
            if "one.google.com" in page.url:
                break
        time.sleep(2)

        # 2. Đóng modal che phủ nếu có
        try:
            close_btn = page.locator("button:has-text('Đóng')").first
            if close_btn.is_visible(timeout=1000):
                close_btn.click()
                time.sleep(1)
        except Exception:
            pass

        # 3. Click nút Kích hoạt gói
        btn = page.locator("button:has-text('Kích hoạt gói')").first
        if btn.is_visible(timeout=3000):
            btn.click()
        else:
            page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Kích hoạt'));
                if (btns.length > 0) btns[0].click();
            }''')

        # 4. Chờ trang Celebration & chụp ảnh nghiệm thu
        time.sleep(5)
        page.screenshot(path="activation_after_click.png")
```

### C. Tiêu Chuẩn Thẩm Định Thành Công
- URL đích: Chứa `/celebration?from=/activate-plan/...`.
- Tiêu đề & Nội dung: Header `"Bạn là thành viên gói Google AI Pro"`, nút `"Chuyển đến Gemini"`.
- Bắt buộc kiểm tra bằng `browser_vision` xác nhận không lỗi hiển thị trước khi báo cáo.

---

## 3. Kỷ Luật Proxy 1:1 Đa Tầng (S7 ↔ GPM ↔ OmniRoute ↔ AGY CLI)

Khi một tài khoản Farm được nâng cấp và đưa vào pool phục vụ inference/coding, **CẤM TUYỆT ĐỐI** dùng proxy ngẫu nhiên hoặc IP trực tiếp:
1. **Tầng 1 - S7 Hardware:** Tra cứu số máy của email trong `gmail_clean_v2.xlsx`, lấy cổng proxy từ `PROXYgandienthoai.xlsx` (ví dụ: M02 -> port `5102`, M16 -> port `5118`).
2. **Tầng 2 - GPM Profile:** `raw_proxy` trong GPM Profile (`/api/v3/profiles/{id}`) bắt buộc khớp đúng `test.taadaa.click:51xx:user:pass`.
3. **Tầng 3 - OmniRoute:** 
   - Tìm connection ID trong `/api/providers`.
   - Tìm Proxy ID khớp với cổng `51xx` trong `/api/settings/proxies`.
   - Gán assignment vào `/api/settings/proxies/assignments` với scope `"account"`.
4. **Tầng 4 - AGY CLI Profile:**
   - Khởi tạo profile sandbox: `python D:/Taadaa/tools/ag_cli.py init-profile acc_XX --proxy "http://mobiX:...@test.taadaa.click:51xx"`.
   - Đảm bảo traffic ra ngoài hiển thị đúng IP di động 4G của đúng cổng farm đó (e.g. `116.98.195.183`).

---

## 4. Quy Trình Nạp Kép Đa Pool (Dual-Pool Provisioning)

### Bước 1: OmniRoute Ingestion & Tier Upgrade
1. Cập nhật `provider_specific_data` trong SQLite `storage.sqlite` hoặc qua API:
   ```json
   {
     "tier": "g1-pro-tier",
     "subscriptionTier": "Google AI Pro 18M",
     "plan": "Pro 18M"
   }
   ```
2. Cập nhật Combo `ag-gemini-pool-3`: Thêm entry model `antigravity/gemini-3.8-flash-tiered` trỏ tới `connectionId` của tài khoản, gắn nhãn `pro-<email>`.

### Bước 2: AGY CLI Profile Setup
1. Tạo thư mục sandbox `D:/Taadaa/agy_profiles/acc_XX/.gemini`.
2. Khởi tạo `installation_id` (UUID riêng biệt).
3. Đăng ký thông tin vào `setup_agy_profile_creds.py` và chạy script để copy access_token, refresh_token và scope từ OmniRoute sang `oauth_creds.json` và `google_accounts.json`.
4. Chạy `python D:/Taadaa/tools/ag_cli.py pool-status` để xác nhận trạng thái `READY`.

---

## 5. Báo Động Khẩn Cấp Đa Trạm (Cross-Host Continuous Alarm)
- Khi hoàn tất mua và kích hoạt gói khẩn cấp, để đảm bảo người vận hành nghe thấy từ các phòng máy khác, kích hoạt còi hú ngầm trên `admin-farm` (`Admin-PC`):
  ```bash
  python D:/Taadaa/tools/admin_ssh.py --powershell "Start-Process python -ArgumentList 'D:\Taadaa\tools\admin_alarm.py' -WindowStyle Hidden"
  ```
- Dừng còi qua cờ dừng file / `pkill`: `python D:/Taadaa/tools/stop_admin_alarm.py`.
