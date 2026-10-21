# SumiStore Gemini Pro 18M Instant Auto-Activation & Dual Pool Synchronization

## 1. Bối Cảnh & Kỷ Luật Vận Hành
- **Sản phẩm:** Link kích hoạt Google AI Pro 18M (Jio entitlement / Google One 5TB) mua từ API SumiStore (`https://sumistore.me/api/tele-product/buy`) bằng chữ ký HMAC-SHA256 (`X-Tele-API-ID`, `X-Timestamp`, `X-Nonce`, `X-Signature`).
- **Rủi ro cốt tử:** Gói chỉ bảo hành trong vòng **5 - 10 phút** kể từ lúc phát hành.
- **Kỷ luật "Zero-Touch Auto-Activation" (Chống để user bấm tay):** Khi cam kết "kích hoạt trên profile", agent BẮT BUỘC phải tự động lái CDP click hoàn tất nút kích hoạt trên trang Google One, không được dừng lại ở bước "mở sẵn tab" rồi ném link cho user tự bấm (tránh bị phàn nàn *"sao mày nói mày kích hoạt luôn trên profile cho tao"*).

---

## 2. Quy Trình Tự Động Kích Hoạt Qua GPM CDP (Playwright CDP)

1. **Khởi chạy profile GPM sống qua Local API:**
   ```text
   GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?skip_proxy_check=true
   ```
   Lấy `data.remote_debugging_address` (ví dụ `127.0.0.1:58108`).

2. **Kết nối Playwright qua CDP và điều hướng tới Activation Link:**
   ```python
   browser = playwright.chromium.connect_over_cdp(f"http://{cdp_address}")
   page = browser.contexts[0].new_page()
   page.goto(activation_url, timeout=30000)
   ```

3. **Cạm bẫy Modal Thông Tin ("Nhận tổng bộ nhớ 5 TB" vs "Kích hoạt gói"):**
   - Trang landing `one.google.com/activate-plan/subscription/new/...` có nút hành động chính là `<button>Kích hoạt gói</button>`.
   - Tuy nhiên, nếu click nhầm vào các khối lợi ích (như `"Nhận tổng bộ nhớ 5 TB..."`), Google One sẽ bung một dialog modal với nút `<button>Đóng</button>`, che phủ toàn bộ viewport và làm nghẽn/timeout khi click nút kích hoạt.
   - **Xử lý chuẩn:**
     ```python
     # 1. Đóng modal nếu có popup che
     try:
         close_btn = page.locator("button:has-text('Đóng')").first
         if close_btn.is_visible(timeout=1000):
             close_btn.click()
             time.sleep(1)
     except Exception:
         pass

     # 2. Click nút Kích hoạt gói chính chủ
     act_btn = page.locator("button:has-text('Kích hoạt gói')").first
     if act_btn.is_visible(timeout=3000):
         act_btn.click()
     else:
         page.evaluate('''() => {
             const btns = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Kích hoạt'));
             if (btns.length > 0) btns[0].click();
         }''')
     ```

4. **Kiểm chứng trang Celebration (Bằng chứng hoàn tất):**
   - Khi kích hoạt thành công, URL chuyển sang `https://one.google.com/celebration?from=/activate-plan/...` với tiêu đề `Google One Confirmation Page`.
   - Body chứa thông điệp: `"Bạn là thành viên gói Google AI Pro"` kèm quyền lợi 5TB và nút `"Chuyển đến Gemini"`.
   - Chụp ảnh màn hình, gọi `browser_vision` kiểm chứng không có lỗi/popup trước khi gửi `MEDIA:` cho user.

---

## 3. Quy Trình Nạp Tài Khoản Pro Mới Vào Dual Pool (OmniRoute + AGY CLI)

Khi một tài khoản Gmail trong farm được nâng cấp lên Pro, BẮT BUỘC phải nạp đồng bộ vào cả 2 pool:

### Tầng 1: OmniRoute Pool (Port 20129)
1. **Cập nhật SQLite `storage.sqlite`:**
   ```sql
   UPDATE provider_connections
   SET provider_specific_data = json_set(
       provider_specific_data,
       '$.tier', 'g1-pro-tier',
       '$.subscriptionTier', 'Google AI Pro 18M',
       '$.plan', 'Pro 18M'
   ),
   updated_at = CURRENT_TIMESTAMP
   WHERE id = '<connection_id>';
   ```
2. **Nạp vào Combo `ag-gemini-pool-3`:**
   - Lấy danh sách combo qua `GET http://127.0.0.1:20129/api/combos`.
   - Tìm combo `ag-gemini-pool-3`, thêm entry model mới:
     ```json
     {
       "id": "ag-gemini-pro-<N>-<conn_id_prefix>",
       "kind": "model",
       "model": "antigravity/gemini-3.8-flash-tiered",
       "providerId": "antigravity",
       "connectionId": "<connection_id>",
       "weight": 0,
       "label": "pro-<email_username>"
     }
     ```
   - Gửi `PUT http://127.0.0.1:20129/api/combos/<combo_id>` để cập nhật.

### Tầng 2: AGY CLI Pool (`D:/Taadaa/agy_profiles`)
1. **Khởi tạo Sandbox Profile:**
   ```bash
   python D:/Taadaa/tools/ag_cli.py init-profile acc_<N> --proxy "http://<user>:<pass>@test.taadaa.click:<port>"
   ```
   Lệnh này tự động tạo cấu trúc thư mục sandbox và ghi nhận profile vào `profiles_config.json`.

2. **Xuất Credentials từ OmniRoute sang Sandbox:**
   - Đăng ký mapping trong `D:/Taadaa/tools/setup_agy_profile_creds.py`:
     ```python
     PROFILES_MAP = {
         ...
         "acc_<N>": "<email>@gmail.com",
     }
     ```
   - Chạy lệnh: `python D:/Taadaa/tools/setup_agy_profile_creds.py`.
   - Script tự động đọc `access_token`, `refresh_token`, `scope` từ `storage.sqlite` và ghi các file cấu hình `.gemini/`:
     * `google_accounts.json` (`{"active": "<email>", "old": []}`)
     * `oauth_creds.json`
     * `settings.json`, `projects.json`, `state.json`.

3. **Hậu kiểm trạng thái:**
   ```bash
   python D:/Taadaa/tools/ag_cli.py pool-status
   ```
   Xác nhận profile `acc_<N>` hiển thị trạng thái `READY` với proxy tương ứng.
