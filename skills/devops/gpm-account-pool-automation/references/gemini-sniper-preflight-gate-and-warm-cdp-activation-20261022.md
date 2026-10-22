# Gemini Pro Flash Link Sniper: Preflight Session Gate & Warm CDP Instant Activation (2026-10-22)

## 1. Bối Cảnh & Cạm Bẫy Thực Tế (The 5-Minute Link Burn Trap)
- **Đặc thù sản phẩm:** Link nâng cấp Gemini Pro 18M / Google One AI Pro mua từ shop (SumiStore API: `SP-TY9J9GO9`) là link bảo hành ngắn hạn đúng **5 phút** kể từ thời điểm giao dịch (`time`/`checked_at`).
- **Cạm bẫy "Bấm link vào profile lỗi":**
  - Trong thiết kế cũ, script sniper chạy vòng lặp canh kho (`while True`), khi có hàng thì bắn lệnh mua HMAC-SHA256, nhận link rồi mới khởi động profile GPM.
  - Nếu profile GPM được chọn bị **hết hạn session Google** (bị văng ra màn hình đăng nhập `accounts.google.com/signin`), hoặc tài khoản bị kẹt xác minh 2FA/SĐT, hoặc dính giới hạn chuyển nhóm gia đình Google Family:
    - Quá trình xử lý đăng nhập, nhập pass, giải mã TOTP và khôi phục mất từ 2 đến 5 phút.
    - Hết 5 phút, token trên link kích hoạt bị Google vô hiệu hóa hoặc quá hạn bảo hành của shop, link bị hủy, rơi vào landing page 15GB rác (`g1_landing_page=5`), dẫn đến mất trắng chi phí mua (9.000đ/acc) và làm cháy link mà không thể khiếu nại shop.

---

## 2. Invariant Cốt Lõi: Preflight Session Gate (Fail-Closed)
**CẤM TUYỆT ĐỐI BẮT ĐẦU VÒNG LẶP CANH KHO KHI CHƯA PASS PREFLIGHT PROFILE TRÊN MÀN HÌNH THỰC.**

Trước khi vào vòng lặp theo dõi kho sản phẩm, script BẮT BUỘC thực hiện hàm kiểm tra tiền bay `run_preflight()`:

```python
def run_preflight():
    # 1. Khởi động GPM Profile qua Local API
    start_url = f"{GPM_API_BASE}/api/v3/profiles/start/{GPM_PROFILE_ID}?skip_proxy_check=true"
    # Lấy remote_debugging_address (CDP port)
    
    # 2. Kết nối Playwright Chromium qua CDP
    p = sync_playwright().start()
    browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
    page = browser.contexts[0].pages[0]

    # 3. Điều hướng tới https://one.google.com/home
    page.goto("https://one.google.com/home", wait_until="domcontentloaded")
    
    # 4. CHỐT CHẶN: Kiểm tra redirect đăng nhập
    cur_url = page.url
    if "accounts.google.com/signin" in cur_url or "ServiceLogin" in cur_url:
        page.screenshot(path="D:/Taadaa/logs/sniper_preflight_fail.png")
        browser.close()
        raise SystemExit("[PREFLIGHT FAILED] Profile session is expired or requires login. Aborting sniper!")

    # 5. Kiểm tra trạng thái Family
    page.goto("https://families.google.com/families", wait_until="domcontentloaded")
    page.screenshot(path="D:/Taadaa/logs/sniper_family_preflight.png")
    
    # 6. Giữ browser sống cho pha kích hoạt tức thì (Warm Handover)
```

- **Quy tắc Fail-Closed:** Nếu trang bị chuyển hướng về form đăng nhập Google hoặc không mở được `one.google.com` $\rightarrow$ script lập tức chụp ảnh bằng chứng lỗi, dừng toàn bộ tiến trình và thoát ngay (`SystemExit`). Tuyệt đối không để sniper chạy ngầm thăm dò kho khi profile chưa sẵn sàng.

---

## 3. Cơ Chế Warm CDP Handover (Kích Hoạt 0 Giây)
- **Không tắt browser sau preflight:** Sau khi xác nhận session Google đang sống 100%, giữ nguyên instance `Playwright` và `page` đang kết nối trong bộ nhớ RAM (`_playwright_page`, `_playwright_browser`).
- **Bàn giao tức thì (Zero-Latency Claim):**
  1. Khi API shop báo mua thành công (`status == 200`) và trích xuất được `act_link`:
  2. `_playwright_page.goto(act_link, wait_until="domcontentloaded")` ngay lập tức (độ trễ < 0.5s).
  3. Quét và tự động click các nút kích hoạt:
     - `button:has-text("Kích hoạt gói")`
     - `button:has-text("Tham gia gia đình")`
     - `button:has-text("Activate")` / `button:has-text("Join family")`
  4. Đóng các dialog modal thông báo tính năng nếu bị che khuất (`button:has-text("Đóng")`).
  5. Chụp ảnh xác nhận kết quả `D:/Taadaa/logs/sniper_activated.png`.
  6. Phát còi hú liên tục sang máy Admin (`admin_ssh.py` gọi `admin_alarm.py` trên Admin-PC) để báo động cho operator.

---

## 4. Quy Trình Chọn Profile Khỏe (3-Tier Health Check)
Để chọn ra profile nạp vào sniper mà không bị lỗi:
1. **Tier 1 (Blacklist Filter):** Loại bỏ toàn bộ email xuất hiện trong `D:\OneDrive\TaadaaData\kibe\gmail_die_tong.txt`.
2. **Tier 2 (Credentials Audit):** Đối soát `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` hoặc `gmail_clean_v2.xlsx`, xác nhận tài khoản có đầy đủ mật khẩu, 2FA secret và recovery email.
3. **Tier 3 (Physical Cookie Audit):** Đọc file SQLite `Cookies` trong thư mục GPM profile (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<ProfilePath>\Default\Network\Cookies`), kiểm tra 3 cookie cốt lõi:
   - `SID`, `HSID`, `SSID` của host `google.com`.
   - Bắt buộc `expires_utc == 0` hoặc `expires_utc > now_chrome`.
   - Hồ sơ chỉ được chọn khi thỏa mãn đồng thời cả 3 tầng.
