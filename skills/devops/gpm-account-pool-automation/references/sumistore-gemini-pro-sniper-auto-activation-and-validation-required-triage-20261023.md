# SumiStore Gemini Pro 18M: Sniper, Auto-Activation, Proxy Alignment & Post-Buy Validation Triage (2026-10-23)

## 1. Tóm Tắt & Bối Cảnh Thực Chiến
- **Sản phẩm:** Link Google One / Gemini Pro 18M (`SP-TY9J9GO9`) trên bot SumiStore (giá thực tế biến động 9.000đ - 17.000đ, bảo hành ngắn hạn 5 phút).
- **Rủi ro sập luồng:**
  1. Profile GPM văng session / dính xác minh trước khi mua làm cháy link quá hạn 5 phút.
  2. Không gán proxy đầy đủ ở tầng OmniRoute dẫn đến lộ IP direct máy trạm khi gọi Google API.
  3. Cạm bẫy Stale Profile Watchdog: `gpm_stale_profile_watchdog.py` chạy mỗi 10 phút, tự động kill các profile GPM mở $\ge 1$ giờ (`age >= 3600s`). Nếu giữ warm tab quá 1h chờ kho, tiến trình Chrome bị dọn sạch và đứt kết nối CDP.
  4. Cạm bẫy ảo giác "Đã lên Pro là dùng được ngay": Sau khi trang Celebration hiển thị 5 TB thành công, Google Cloud Code API (`daily-cloudcode-pa.googleapis.com`) thường xuyên trả về `403 PERMISSION_DENIED` (`VALIDATION_REQUIRED`) đòi quét QR điện thoại để mở khóa hạn mức Pro.

---

## 2. Quy Trình Đối Soát Proxy 4 Tầng Bắt Buộc (Anti-Direct-Leak Invariant)
Tuyệt đối không để xảy ra tình trạng tài khoản đi qua IP khác nhau giữa farm và PC:
1. **Tầng S7 Phone Farm:** Tra cứu `PROXYgandienthoai.xlsx` theo số máy $M$ (ví dụ M18 -> Port `5122`).
2. **Tầng GPM Profile:** `raw_proxy` khớp định dạng `test.taadaa.click:51XX:mobiXX:Pass!`.
3. **Tầng OmniRoute (`storage.sqlite`):**
   - `provider_connections`: BẮT BUỘC đặt `proxy_enabled = 1`.
   - `proxy_assignments`: BẮT BUỘC gán cả 2 scope để phủ toàn bộ router:
     * `scope = 'account'` với `scope_id = <connection_id>` trỏ tới `proxy_id` có port `51XX`.
     * `scope = 'connection'` với `scope_id = <connection_id>` trỏ tới cùng `proxy_id`.
   - *Cảnh báo:* Chỉ bật `proxy_enabled = 1` mà thiếu entry `proxy_assignments` với `scope='account'` sẽ khiến OmniRoute fallback gửi request bằng IP direct của máy host!
4. **Tầng AGY CLI Sandbox (`D:/Taadaa/agy_profiles/acc_XX`):**
   - Khởi tạo qua: `python D:/Taadaa/tools/ag_cli.py init-profile acc_XX --proxy "http://mobiXX:Pass@test.taadaa.click:51XX"`.

---

## 3. Quản Trị Vòng Đời Warm Tab & Né Stale Profile Watchdog
- `gpm_stale_profile_watchdog.py` quét định kỳ mỗi 10 phút, kiểm tra `age = now - p.create_time()`. Nếu `age >= 3600`, watchdog gọi GPM API `/stop` và `p.terminate()`.
- **Giải pháp giữ warm tab an toàn khi chờ kho lâu:**
  - Trong vòng lặp sniper, theo dõi thời gian mở của GPM profile. Cứ mỗi **45 phút** (trước ngưỡng 60 phút của watchdog), sniper chủ động đóng và mở lại profile qua GPM Local API (`19995`), kết nối lại Playwright CDP mới.
  - Thao tác này reset `create_time` của tiến trình Chrome về 0, giữ profile luôn tươi mới, không ngốn RAM và không bao giờ bị watchdog dọn nhầm.

---

## 4. Triage Lỗi Upstream `VALIDATION_REQUIRED` Sau Khi Lên Pro
Sau khi kích hoạt link thành công (Celebration 5 TB xác nhận), BẮT BUỘC kiểm tra liveness thực tế qua `isolated_chat_test`:

### A. Chạy Isolated Chat Test (Phát hiện lỗi tươi):
```python
from vm_rescue_lib import isolated_chat_test, is_validation_required
res = isolated_chat_test('<connection_id>', model='antigravity/claude-sonnet-4-6')
if is_validation_required(res):
    print("Account requires phone/QR validation!")
```

### B. Trích xuất URL và Mở Màn hình QR trên GPM:
1. Đọc log `~/.omniroute/logs/application/app.log`, tìm entry lỗi 403 mới nhất:
   `"validation_url": "https://accounts.google.com/v3/signin/continue?plt=...&continue=.../auth_success_gemini..."`
2. Mở URL này trên chính profile GPM đang chạy qua Playwright CDP:
   `page.set_viewport_size({'width': 1280, 'height': 900})`
   `page.goto(validation_url, wait_until='domcontentloaded')`
3. Chờ 5 giây để Google render trang *"Xác minh thông tin để tiếp tục"*.
4. Chụp ảnh màn hình, OCR xác nhận đúng email mục tiêu và mã QR hiển thị trọn vẹn, sắc nét.

### C. Kỷ Luật Live Handshake:
- **CẤM ĐÓNG TRÌNH DUYỆT GPM:** Tab QR trên máy tính duy trì kết nối WebSocket/polling thời gian thực với server Google. Nếu đóng trình duyệt trước/trong khi user quét, điện thoại sẽ báo lỗi 500 và tài khoản không được gỡ cờ.
- Hướng dẫn User quét bằng **Camera mặc định của điện thoại** (iPhone / Samsung). Tuyệt đối **CẤM DÙNG APP ZALO** để quét.
- Sau khi User quét xong, chạy lại `isolated_chat_test` để nghiệm thu `200 OK` trước khi đóng profile.
