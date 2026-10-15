# ChatGPT-Web Pool Auto-Feed, Sentinel PoW, and Session Recovery

## 1. Sentinel Proof-of-Work (401) & DPL Live Asset Extraction
- **Nguyên nhân 401 Sentinel PoW**: OpenAI chuyển cấu trúc bundle từ Webpack script sang `<link rel="modulepreload" href="/cdn/assets/entry.client-*.js">`.
- **Vá executor `chatgpt-web.ts`**:
  - Cập nhật `OAI_CLIENT_VERSION` và `OAI_CLIENT_BUILD_NUMBER` live từ HTML `chatgpt.com`.
  - Thay regex cũ bằng regex bắt `entry.client-.*\.js`.
  - Bổ sung strip model prefix `chatgpt-web/` hoặc `cgpt-web/` trong `resolveChatGptWebModel` trước khi lookup `MODEL_MAP`.
  - Tài khoản Free chỉ hỗ trợ model `auto` / `gpt-5.6-luna-free`. Tuyệt đối cấm gọi model Pro/Plus `gpt-5.6-sol-high` trên tài khoản Free (OpenAI trả về HTTP 404).

## 2. Bẫy False Login & Trích Xuất Session Token Thật
- **Bẫy `eyJhbG`**: Khi ở màn hình đăng nhập hoặc dính challenge, OpenAI vẫn set các cookie tạm dạng JWT (`oai-did`, `auth0`, `__cf_bm`) có value bắt đầu bằng `eyJhbG`. Kiểm tra `value.startswith("eyJhbG")` sẽ lấy nhầm cookie rác khi chưa đăng nhập thật.
- **Quy chuẩn bắt buộc**:
  - Bắt buộc kiểm tra: `any("session-token" in (c.get("name") or "") for c in cookies)`.
  - Chuỗi cookie hợp lệ phải chứa `__Secure-next-auth.session-token` (hoặc `.0`, `.1` nếu chunked) và có độ dài > 2.000 ký tự.

## 3. Chốt An Toàn Proxy Mobi 1-1 & Triệt Tiêu Provider-Level Proxy Fast-Fail
- **Username theo port Mobi**: Dải Mobi `test.taadaa.click:5101..5138` có username tương ứng theo port: `mobi{port - 5100}` (e.g. 5101 là `mobi1`, 5104 là `mobi4`, 5128 là `mobi28`). Hardcode sai username gây `407 Proxy Authentication Required`.
- **Fast-Fail Isolation**: Xóa toàn bộ proxy cấp `scope='provider'` của `chatgpt-web` trong `proxy_assignments`. Chỉ gán proxy ở cấp `scope='account'` để 1 port lỗi không kích hoạt `[Proxy Fast-Fail]` giết chết cả pool.

## 4. Cuốn Chiếu Nạp Pool Tự Động (Cron 5 Workers)
- **Không bỏ sót Hotmail**: Kho GPM có cả Gmail lẫn Hotmail đã đăng nhập sẵn ChatGPT web. Cấm dùng regex cứng `re.search(r'@gmail\.com')` làm bỏ quên hàng trăm profile Hotmail.
- **Kỷ luật đóng profile**:
  - Chạy `ThreadPoolExecutor(max_workers=5)`.
  - Khối `finally` BẮT BUỘC gọi GPM API `/profiles/stop/{pid}` VÀ quét `psutil` kill sạch process `chrome.exe` mồ côi theo `profile_path`, không để rác chiếm RAM/CPU.

## 5. Cơ Chế Auto-Resume Sau Reboot Tay / Sập Nguồn
- Script `farm_preflight_daily_reset.py` chỉ bắt được reboot theo lịch 3 ca. Khi user reboot tay, tắt nguồn hoặc crash thì Windows không kích hoạt script này.
- **Giải pháp Startup Hook**: Tạo file `00_Hermes_AutoResume_Hook.vbs` trong thư mục `Startup` của Windows (`AppData\Roaming\...\Startup`).
  - Tiền tố `00_` đảm bảo thực thi đầu tiên khi boot.
  - Chạy script Python nhẹ quét bảng `gateway_routing` trong 60 phút gần nhất: nếu tin cuối là `user` hoặc `tool` thì gắn `resume_pending = true`.
  - Khi `Hermes_Gateway.vbs` bật lên sau đó, nó thấy cờ và tự động thức dậy nối tiếp công việc trong Telegram mà user không cần nhắc.
