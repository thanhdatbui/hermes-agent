# SumiStore Gemini Pro 18M Sniper, Auto-Activation & Dual-Pool Ingestion

## 1. Bối Cảnh & Mục Tiêu
Các gói "Link Gemini Pro 18M (Phải dùng ngay)" trên shop Telegram (SumiStore) có đặc điểm:
- **Giá cực rẻ:** 9,000đ (thay vì 24,000đ - 60,000đ).
- **Số lượng có hạn (Flash Drop):** Shop nhồi nhỏ giọt từng đợt (1–3 link), hết hàng trong vòng 5–15 giây.
- **Thời hạn bảo hành ngắn:** Bắt buộc kích hoạt trong vòng 5–10 phút kể từ lúc mua.
- **Kỳ vọng của User (Anti-Passive / Zero-Human Intervention):** Không chỉ mở tab trình duyệt để user tự bấm; hệ thống BẮT BUỘC tự động bấm nút "Kích hoạt gói" trên Google One và nạp ngay tài khoản vào cả 2 pool (OmniRoute + AGY CLI).

---

## 2. API SumiStore & Cơ Chế Ký Chữ Ký HMAC-SHA256

- **Endpoint kiểm tra tồn kho:** `GET https://sumistore.me/api/tele-products/SP-TY9J9GO9`
  - Header: `X-Tele-API-ID: <API_ID>`
  - Tần suất poll an toàn & cực nhạy: 0.6s – 0.8s (tránh Cloudflare 429).
- **Endpoint mua hàng:** `POST https://sumistore.me/api/tele-product/buy`
  - Body: `{"id": "SP-TY9J9GO9", "quantity": 1}` (lưu ý dùng separator chuẩn `separators=(',', ':')` để khớp chữ ký).
  - Thuật toán chữ ký HMAC-SHA256:
    ```python
    t_str = str(int(time.time()))
    nonce = uuid.uuid4().hex
    raw_sig = f"{t_str}|{nonce}|{body_str}"
    sig = hmac.new(api_id.encode("utf-8"), raw_sig.encode("utf-8"), hashlib.sha256).hexdigest().lower()
    ```
  - Headers bắt buộc:
    ```python
    headers = {
        "Content-Type": "application/json",
        "X-Tele-API-ID": api_id,
        "X-Timestamp": t_str,
        "X-Nonce": nonce,
        "X-Signature": sig,
        "User-Agent": "Mozilla/5.0"
    }
    ```

---

## 3. Khởi Chạy GPM & Tự Động Kích Hoạt Qua CDP (Zero-Human Activation)

Sau khi API trả về URL kích hoạt (dạng `https://gemini-activation.st-editvision.workers.dev/...`), script thực hiện:
1. **Khởi chạy profile GPM chứa Gmail sống qua Local API:**
   `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?skip_proxy_check=true`
   Lấy `remote_debugging_address` (ví dụ `127.0.0.1:52177`).
2. **Kết nối Playwright CDP:**
   `browser = playwright.chromium.connect_over_cdp(f"http://{remote_debugging_address}")`
3. **Mở URL kích hoạt và chờ redirect:**
   Trang worker sẽ chuyển hướng sang `https://one.google.com/activate-plan/subscription/new/...`.
4. **Cạm bẫy Modal Thông Tin Che Khuất Nút Kích Hoạt (Modal Backdrop Trap):**
   Nếu DOM vô tình kích hoạt popup giới thiệu bộ nhớ ("Sử dụng tổng bộ nhớ 5 TB"), nút "Đóng" sẽ che màn hình khiến click vào "Kích hoạt gói" bị timeout hoặc no-op.
   - **Xử lý:** Kiểm tra `button:has-text('Đóng')`, nếu visible thì click đóng trước.
   - **Click Kích hoạt:** Tìm `button:has-text('Kích hoạt gói')` hoặc evaluate click trên button có innerText chứa `Kích hoạt`.
5. **Xác nhận hoàn tất (Celebration URL):**
   URL chuyển sang `https://one.google.com/celebration?from=/activate-plan/subscription/entitle/ai...` với tiêu đề "Bạn là thành viên gói Google AI Pro". Chụp ảnh lưu vào `logs/` và soi mắt qua Vision / WinRT OCR trước khi gửi `MEDIA:`.

---

## 4. Báo Động Khẩn Cấp Từ Xa Qua Máy Admin (Admin-PC Alarm)

Để người vận hành nhận biết tức thì:
1. **Kích hoạt còi hú liên tục trên Admin-PC:**
   Dùng `admin_ssh.py` gọi PowerShell khởi chạy nền `admin_alarm.py`:
   ```bash
   python D:/Taadaa/tools/admin_ssh.py --powershell "Start-Process python -ArgumentList 'D:\Taadaa\tools\admin_alarm.py' -WindowStyle Hidden"
   ```
   `admin_alarm.py` chạy vòng lặp vô tận `winsound.Beep(1200, 250); winsound.Beep(1800, 300)` cho tới khi thấy file cờ dừng.
2. **Dập tắt còi sau khi hoàn tất:**
   Ghi file cờ `D:\Taadaa\tools\stop_alarm.flag` và gọi `pkill -f admin_alarm.py` qua `admin_ssh.py`.

---

## 5. Quy Trình Nạp Tài Khoản Mới Nâng Cấp Vào Cả 2 Pool (Dual-Pool Ingestion)

Khi user yêu cầu "ném acc đó vào pool":
### A. Pool 1: OmniRoute (Port 20129)
1. Cập nhật hạng mức tài khoản trong SQLite `~/.omniroute/storage.sqlite`:
   ```sql
   UPDATE provider_connections 
   SET provider_specific_data = json_set(provider_specific_data, '$.tier', 'g1-pro-tier', '$.subscriptionTier', 'Google AI Pro 18M')
   WHERE id = '<connection_id>';
   ```
2. Thêm connection vào combo **`ag-gemini-pool-3`**:
   - `GET http://127.0.0.1:20129/api/combos` -> lấy combo `ag-gemini-pool-3`.
   - Nối thêm model object:
     ```json
     {
       "id": "ag-gemini-pro-XX-<conn_prefix>",
       "kind": "model",
       "model": "antigravity/gemini-3.8-flash-tiered",
       "providerId": "antigravity",
       "connectionId": "<connection_id>",
       "weight": 0,
       "label": "pro-<email_prefix>"
     }
     ```
   - `PUT http://127.0.0.1:20129/api/combos/<combo_id>` với payload cập nhật.
3. Đồng bộ models: `POST http://127.0.0.1:20129/api/providers/<connection_id>/sync-models`.

### B. Pool 2: AGY CLI (`D:/Taadaa/agy_profiles`)
1. **Khởi tạo sandbox profile mới:**
   ```bash
   python D:/Taadaa/tools/ag_cli.py init-profile acc_XX --proxy "http://mobiXX:Pass@test.taadaa.click:51XX"
   ```
2. **Sao chép cấu hình cơ sở:**
   Copy `settings.json`, `projects.json`, `state.json` từ `acc_22/.gemini/` sang `acc_XX/.gemini/`.
3. **Cập nhật và chạy credentials generator:**
   Thêm `acc_XX: email` vào `PROFILES_MAP` của `D:/Taadaa/tools/setup_agy_profile_creds.py` và chạy script. Script sẽ tự đọc `access_token`, `refresh_token`, `scope` từ OmniRoute SQLite và ghi ra `oauth_creds.json` + `google_accounts.json`.
4. **Kiểm tra trạng thái pool:**
   `python D:/Taadaa/tools/ag_cli.py pool-status` -> Xác nhận profile `acc_XX` ở trạng thái **`READY`**.

---

## 6. Đối Soát Proxy Chuẩn 1:1 Giữa S7 ↔ GPM ↔ OmniRoute ↔ AGY CLI
- Khi cấp tài khoản Pro cho farm/agent, BẮT BUỘC đối soát 4 tầng khớp 100% cổng proxy:
  1. `PROXYgandienthoai.xlsx`: Cổng proxy gán cho S7 máy `M` (ví dụ `5102` cho M02, `5118` cho M16).
  2. GPM profile: `raw_proxy` khớp cổng `51XX`.
  3. OmniRoute: `assignments` trỏ đúng Proxy Registry item có port `51XX`.
  4. AGY CLI: `profiles_config.json` cấu hình đúng URL proxy cổng `51XX`.
- Tuyệt đối không để xảy ra tình trạng cùng 1 tài khoản nhưng trên PC đi qua IP khác với thiết bị di động S7.
