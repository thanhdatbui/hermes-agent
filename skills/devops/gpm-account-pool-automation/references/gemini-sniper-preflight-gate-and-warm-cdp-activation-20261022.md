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

---

## 5. Giải Phẫu Lỗi "Link Đã Sử Dụng" vs Phản Ứng Của Shop (Seller False-Claim Trap)
- **Hiện tượng thực tế**: Đơn mua link Gemini Pro 18M lúc 8h sáng (`API-TELE-5NORQ6Q4GYWM6XDO`), khi mở lại link lúc 10h thì Google One hiện trang cảnh báo: *"Gói thuê bao này đã được sử dụng. Đường liên kết của gói thuê bao này đã được sử dụng."*
- **Nguyên nhân gốc rễ**: Profile GPM lúc 8h sáng bị văng phiên Google và dính màn hình bảo mật *"Đảm bảo rằng bạn luôn có thể đăng nhập - Thêm SĐT / Email khôi phục"*, khiến link kích hoạt bị treo quá thời hạn bảo hành 5-8 phút của shop. Khi quá hạn, link bị Google vô hiệu hóa hoặc bị claim.
- **Cạm bẫy từ chối bảo hành của Shop**:
  - Người bán nhìn vào thông báo *"Gói thuê bao này đã được sử dụng"* sẽ lập tức quy kết là *"Tài khoản đã lên Pro rồi kìa"* (cho rằng người mua đã nhận gói thành công).
  - Kết hợp với việc người mua phản hồi sau 8 phút, shop vin vào cớ này để từ chối bảo hành hoàn toàn, trong khi thực tế tài khoản đích vẫn là `free-tier` (Starter Quota) và người mua chịu mất trắng tiền đơn hàng.
- **Quy tắc bắt buộc**: Preflight kiểm tra không chỉ URL `one.google.com/home` mà bắt buộc phải vào `myaccount.google.com/family/details` để chắc chắn không dính form khôi phục hay giới hạn nhóm gia đình; tab được giữ warm và kích hoạt trong vòng $\le 2$ giây kể từ khi API trả link.

---

## 6. Luồng Kích Hoạt 2 Chặng (Landing Page ➔ Nút "Kích Hoạt Gói" ➔ Celebration Page)
- **Cạm bẫy tưởng lầm đã kích hoạt (Landing Trap)**:
  - Link mua từ shop (`https://gemini-activation.st-editvision.workers.dev/subscription/new/...`) là link Cloudflare Worker chuyển hướng sang `https://one.google.com/activate-plan/subscription/new/<token>?g1_landing_page=5` (Title: *"Trang đích Google One"*).
  - **LƯU Ý CỐT LÕI:** Việc mở đến URL này **CHƯA ĐỒNG NGHĨA** với tài khoản đã được nâng cấp! Nếu chỉ mở tab rồi thoát tool, link vẫn ở trạng thái chờ và sẽ hết hạn trong 5 phút.
  - BẮT BUỘC script hoặc operator phải click nút `button:has-text("Kích hoạt gói")`.
  - **Dấu hiệu thành công duy nhất:** Trình duyệt chuyển hướng sang URL chúc mừng:
    `https://one.google.com/celebration?from=/activate-plan/subscription/entitle/ai&g1_landing_page=5` (Title: *"Google One Confirmation Page"*), với tiêu đề lớn: **"Bạn là thành viên gói Google AI Pro"** kèm quyền lợi 5 TB bộ nhớ và nút *"Chuyển đến Gemini"*.
  - Mọi báo cáo hoàn tất bắt buộc chụp ảnh màn hình trang Celebration này và soi mắt qua `browser_vision` trước khi kết luận.

---

## 7. Cạm Bẫy Nhận Diện Avatar Google Tiếng Việt (Tên Thay Vì Họ)
- **Thực tế giao diện**: Trong vòng tròn avatar Google ở góc trên bên phải, Google hiển thị chữ cái đầu tiên của **Tên chính (First Name)**, KHÔNG hiển thị chữ cái của Họ hay Tên đệm.
- **Ví dụ**:
  - `quyphuoc090565@gmail.com` (Tên: Quy Phước $\rightarrow$ Tên gọi là Phước) $\rightarrow$ Avatar hiển thị chữ **"P"** màu xanh.
  - `nguyenkhoi14031998@gmail.com` (Tên: Khôi) $\rightarrow$ Avatar hiển thị chữ **"K"**.
  - `taquynh06011998@gmail.com` (Tên: Quỳnh) $\rightarrow$ Avatar hiển thị chữ **"Q"**.
- Khi operator hoặc reviewer nhìn thấy avatar chữ "P" thường nghi ngờ bị nhầm profile (`quyphuoc` tưởng phải chữ "Q" hay "N"). BẮT BUỘC kiểm tra thuộc tính `aria-label` của nút tài khoản qua DOM (`document.querySelector('a[aria-label*="Google Account"]')`) hoặc nội dung trang `myaccount.google.com/family/details` để xác nhận chuẩn xác 100% email đang đăng nhập.

---

## 8. Bẫy EPIPE Playwright Node Driver & Cơ Chế Khôi Phục Nút Bấm Qua CDP
- Khi chạy script Python Playwright kết nối CDP trong tiến trình ngầm lâu (polling kéo dài nhiều chục phút), các thao tác gọi subprocess bên ngoài (như còi báo `admin_ssh.py` hoặc ngắt pipe) có thể gây ra lỗi `EPIPE: broken pipe, write` trên Node driver của Playwright.
- Nếu Playwright crash trước khi click được nút "Kích hoạt gói", tab trình duyệt GPM vẫn được CDP mở sẵn ở trang landing.
- **Hành động phục hồi tức thì:** Coordinator ngay lập tức kết nối lại cổng CDP (`127.0.0.1:<port>`), tìm tab chứa `activate-plan`, click nút `button:has-text("Kích hoạt gói")`, đợi chuyển sang `celebration` rồi mới dập còi Admin qua `python D:/Taadaa/tools/stop_admin_alarm.py`.

---

## 9. Giám Định Bằng Chứng Thực Tế: Google One Pro vs Free / Starter (Anti-False-Pro Triage)
- Khi bên bán vin vào thông báo quá hạn link để tuyên bố *"tài khoản pro rồi kìa"* nhằm chối bỏ trách nhiệm, hoặc khi operator muốn kiểm tra lại nick cũ (ví dụ `nguyenkhoi14031998@gmail.com`):
- BẮT BUỘC mở profile GPM vào `https://one.google.com/home` và `https://one.google.com/storage`, kiểm tra 3 dấu hiệu phân định ranh giới:
  1. **Dung lượng hiển thị**: Nick Free chỉ có `0 GB / 5 GB` hoặc `0 GB / 15 GB`. Nick Pro 18M bắt buộc hiển thị `5 TB` (hoặc 2 TB).
  2. **Nút Nâng cấp / Mua thêm**: Nick Free vẫn hiện các nút xanh `Nâng cấp` và `Mua thêm bộ nhớ`. Nick Pro không có các nút này.
  3. **Thẻ GOOGLE AI PRO**: Nick Free hiện biểu tượng ổ khóa `lock` và nút `ĐĂNG KÝ GÓI GOOGLE AI PRO`. Nick Pro hiện thông báo `Bạn là thành viên gói Google AI Pro` kèm nút `Chuyển đến Gemini`.
- Chụp ảnh màn hình, soi mắt qua `browser_vision` xác nhận cả 3 điểm trước khi đối soát hoặc báo cáo user.

---

## 10. Quy Trình Onboarding Tài Khoản Pro Mới Vào Dual-Pool (OmniRoute + AGY CLI)
Ngay sau khi tài khoản hiển thị trang Celebration thành công:
1. **OmniRoute DB (`storage.sqlite`)**:
   - `UPDATE provider_connections SET is_active = 1, priority = 100, rate_limit_protection = 1, max_concurrent = 8, project_id = 'aicode-consumers', provider_specific_data = '{"clientProfile":"ide","projectId":"aicode-consumers","tier":"g1-pro-tier","apiKeyHealth":{},"subscriptionTier":"Google AI Pro","plan":"Pro"}' WHERE id = '<CONN_ID>'`
2. **Gán Proxy 1:1 Chuẩn Connection Scope**:
   - Xóa mapping cũ: `DELETE FROM proxy_assignments WHERE scope_id = '<CONN_ID>'`
   - Gán mới: `INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at) VALUES ('<PROXY_REGISTRY_ID>', 'connection', '<CONN_ID>', 0, datetime('now'), datetime('now'))`
3. **Thêm Vào Combo Pool (`ag-gemini-pool-3`)**:
   - Đọc JSON từ `combos WHERE name = 'ag-gemini-pool-3'`, chèn phần tử mới vào mảng `models`:
     ```json
     {
       "id": "ag-gemini-pool-3-model-<N>-antigravity-gemini-3-8-flash-tiered-<CONN_ID>",
       "kind": "model",
       "model": "antigravity/gemini-3.8-flash-tiered",
       "providerId": "antigravity",
       "connectionId": "<CONN_ID>",
       "weight": 0,
       "label": "<EMAIL>",
       "name": null
     }
     ```
4. **Khởi Tạo AGY CLI Sandbox (`D:\Taadaa\agy_profiles\acc_<N>`)**:
   - Tạo thư mục `.gemini/`
   - Xuất `oauth_creds.json`: bóc `access_token`, `refresh_token`, `scope` từ DB kèm `expiry_date` hợp lệ.
   - Xuất `settings.json`: `{"security": {"auth": {"selectedType": "oauth-personal"}}}`
   - Xuất `projects.json`: trỏ các project mapping `taadaa`, `kibe`, `automation-core`.
5. **Cập Nhật Registry AGY CLI (`profiles_config.json`)**:
   - Thêm entry vào list `profiles`:
     ```json
     {
       "name": "acc_<N>",
       "path": "D:/Taadaa/agy_profiles/acc_<N>",
       "proxy": "http://mobi<port-num>:TaadaaMobi%232026%21@test.taadaa.click:<port>",
       "enabled": true
     }
     ```
6. **Thử Thách Google Bot Verification (403 VALIDATION_REQUIRED)**:
   - Nếu upstream Antigravity trả lỗi 403 `VALIDATION_REQUIRED` kèm `validation_url`: Với các account farm nằm trên thiết bị S7 (`dumpsys account` có `com.google`), Google Play Services của máy S7 đã lưu trữ chứng chỉ thiết bị; mở URL xác minh trên GPM profile hoặc trên trình duyệt máy S7 để hoàn tất IAP validation một lần duy nhất.


