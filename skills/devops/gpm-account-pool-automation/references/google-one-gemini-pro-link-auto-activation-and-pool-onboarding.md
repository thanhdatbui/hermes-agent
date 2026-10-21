# Google One / Gemini Pro Auto-Activation via GPM CDP & OmniRoute Pool Onboarding

## 1. Bối cảnh & Yêu cầu vận hành
- Các gói link nâng cấp Google AI Pro (Jio/Family 18 tháng) mua qua Telegram API shop (`sumistore.me`) có thời hạn bảo hành kích hoạt cực ngắn (5–10 phút từ lúc mua).
- **Quy tắc bất biến:** Tự động hóa 100% (End-to-End Zero-Manual). CẤM chỉ mở tab trình duyệt rồi để user tự bấm tay. Khi mua thành công, script bắt buộc điều khiển CDP để click hoàn tất kích hoạt trong vòng <= 10 giây.

---

## 2. Quy trình kích hoạt tự động trên Profile GPM qua Playwright CDP

### A. Khởi chạy Profile GPM & Bắt CDP Address
1. Chọn tài khoản Gmail khỏe (đã xác thực 3 tầng: Master Excel active, Google Cookies `SID/HSID/SSID` còn hạn trong SQLite `Default/Network/Cookies`, loại trừ `gmail_die_tong.txt`).
2. Khởi chạy profile qua GPM Local API:
   ```text
   GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?skip_proxy_check=true
   ```
3. Lấy `remote_debugging_address` (ví dụ `127.0.0.1:58108`).

### B. Mở Link Kích Hoạt & Cạm bẫy Modal Che Khuất Nút Action
1. Kết nối Playwright CDP: `browser = playwright.chromium.connect_over_cdp(f"http://{cdp_addr}")`.
2. Mở tab mới tới link kích hoạt:
   - Link mua về thường là URL chuyển tiếp Cloudflare Worker (`https://gemini-activation.st-editvision.workers.dev/subscription/new/...`).
   - Trang sẽ tự động redirect sang Google One: `https://one.google.com/activate-plan/subscription/new/...`.
3. **Cạm bẫy Modal Card Tính năng (Modal Backdrop Block Trap):**
   - Trên trang `activate-plan`, các thẻ tính năng (ví dụ *"Nhận tổng bộ nhớ 5 TB..."*) có vai trò interactive. Nếu script hoặc click nhầm vào các thẻ này, Google One sẽ mở một popup dialog mô tả (`role="dialog"`).
   - Backdrop của modal này sẽ che mờ toàn màn hình và vô hiệu hóa các click vào nút action chính.
   - **Xử lý dứt điểm:**
     * Trước khi click kích hoạt, kiểm tra nếu có nút `button:has-text('Đóng')` đang hiển thị (`visible: True`), click đóng modal ngay.
4. **Click Nút Kích Hoạt Chính:**
   - Nút hành động chuẩn trên Google One tiếng Việt: `<button>Kích hoạt gói</button>`.
   - Selector: `button:has-text('Kích hoạt gói')`.
   - Nếu click bằng locator bị trễ hoặc che, fallback bằng DOM evaluate:
     ```javascript
     const btns = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Kích hoạt'));
     if (btns.length > 0) btns[0].click();
     ```
5. **Xác thực kết quả thành công:**
   - URL chuyển về trang ăn mừng: `https://one.google.com/celebration?from=/activate-plan/...`.
   - Title: `Google One Confirmation Page`.
   - Text trên body: `"Bạn là thành viên gói Google AI Pro"`, kèm các checkmark mở rộng bộ nhớ 5 TB và nút `"Chuyển đến Gemini"`.
   - Chụp ảnh màn hình lưu vào `D:\Taadaa\logs\activation_after_click.png` để soi mắt kiểm chứng qua `browser_vision` / WinRT OCR trước khi báo cáo.

---

## 3. Quy trình nạp tài khoản vừa nâng cấp vào OmniRoute Pool

Sau khi tài khoản Gmail đã lên Pro 18M:

### A. Cập nhật Hạng mức trong OmniRoute Database
File SQLite: `~/.omniroute/storage.sqlite`
- Tìm connection ID của tài khoản trong bảng `provider_connections`:
  ```sql
  SELECT id, provider, provider_specific_data FROM provider_connections WHERE email = 'target_email@gmail.com';
  ```
- Cập nhật trường `provider_specific_data`:
  ```sql
  UPDATE provider_connections 
  SET provider_specific_data = json_set(provider_specific_data, '$.tier', 'g1-pro-tier', '$.subscriptionTier', 'Google AI Pro 18M', '$.plan', 'Pro 18M')
  WHERE id = '<connection_id>';
  ```

### B. Bổ sung vào Combo Pro (`ag-gemini-pool-3`)
- Combo `ag-gemini-pool-3` là pool Google AI Pro chính thức phục vụ cho `omni-worker` và các tác vụ nặng.
- Lấy combo hiện tại qua `GET http://127.0.0.1:20129/api/combos`.
- Bổ sung model entry vào mảng `models`:
  ```json
  {
    "id": "ag-gemini-pro-<N>-<conn_id_prefix>",
    "kind": "model",
    "model": "antigravity/gemini-3.8-flash-tiered",
    "providerId": "antigravity",
    "connectionId": "<connection_id>",
    "weight": 0,
    "label": "pro-<email_prefix>"
  }
  ```
- Gửi `PUT http://127.0.0.1:20129/api/combos/<combo_id>` với JSON vừa cập nhật.

---

## 4. Báo động Âm thanh Đa máy (Admin-PC Remote Alarm)

Khi mua hàng thành công và cần user chú ý ngay:
1. Phát chuỗi bíp cục bộ bằng `winsound.Beep`.
2. Đồng thời bắn lệnh SSH qua `admin_ssh.py` sang Admin-PC (`192.168.110.119`) để chạy vòng lặp hú còi vô tận:
   ```bash
   python D:/Taadaa/tools/admin_ssh.py --powershell "Start-Process python -ArgumentList 'D:\Taadaa\tools\admin_alarm.py' -WindowStyle Hidden"
   ```
3. Còi sẽ hú liên tục cho đến khi nhận được cờ dừng (`stop_alarm.flag` hoặc `pkill -f admin_alarm.py`).
