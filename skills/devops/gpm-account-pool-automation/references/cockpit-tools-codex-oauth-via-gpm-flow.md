# Cockpit Tools Codex OAuth via GPM Profile Flow

## 1. Bối cảnh & Vấn đề
- Khi cần nạp tài khoản Codex (ChatGPT) từ dàn profile GPM vào **Cockpit Tools** (`cockpit-tools.exe`) để chạy Local API Gateway (port `60818`):
  + Không nên cố giải mã file storage của Cockpit hay ghi đè file token/manifest thủ công (Cockpit mã hóa AES-256-GCM với key riêng và sidecar sẽ xóa tài khoản không hợp lệ khi khởi động).
  + Cũng không được báo kẹt / BLOCKED với lý do thiếu proxy engine hay lo ngại xung đột callback cổng 1455 khi chưa thử luồng chuẩn.
  + **Giải pháp chuẩn O(1) do User chỉ đạo:** Lấy trực tiếp link OAuth từ Cockpit Tools, mở bằng GPM profile đã có phiên đăng nhập ChatGPT (đang gắn đúng proxy), bấm ủy quyền để callback tự động đổ về Cockpit.

## 2. Quy trình thao tác từng bước (End-to-End)

### Bước 1: Mở modal OAuth trong Cockpit Tools
1. Trên giao diện Cockpit Tools, vào mục **Codex** -> **Overview** (hoặc Account Pool).
2. Bấm nút **Add Account** (`+`).
3. Chọn tab **OAuth Authorization** (KHÔNG chọn Official Login hay Token/JSON).
4. Nhập email tài khoản cần nạp vào ô `Pending account` (ví dụ: `gilliara2011@hotmail.com`).
5. Cockpit sẽ tạo URL ủy quyền chuẩn có dạng:
   ```text
   https://chatgpt.com/codex/desktop-auth?authorize_url=https%3A%2F%2Fauth.openai.com%2Foauth%2Fauthorize...
   ```
   Đồng thời Cockpit tự động mở callback listener tại `http://localhost:1455/auth/callback`.
   *(Lưu ý: Nếu link bị timeout do để lâu, bấm nút "Refresh Auth Link" để Cockpit sinh URL + state mới).*

### Bước 2: Khởi động GPM Profile qua Local API
1. Gọi GPM API port 19995 để mở profile tương ứng (đã cấu hình proxy farm):
   ```python
   import urllib.request
   url = f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}"
   resp = urllib.request.urlopen(url).read()
   ```
2. Lấy port remote debugging CDP (ví dụ `127.0.0.1:60086`).

### Bước 3: Tự động hóa duyệt OAuth bằng Playwright qua CDP
1. Kết nối vào trình duyệt GPM qua Playwright CDP:
   ```python
   from playwright.async_api import async_playwright

   async with async_playwright() as p:
       browser = await p.chromium.connect_over_cdp("http://127.0.0.1:60086")
       page = browser.contexts[0].pages[0]
       await page.goto(auth_url, wait_until="domcontentloaded")
   ```
2. Thao tác xác thực trong GPM Chrome:
   - Nếu xuất hiện màn hình `Choose an account`: Click nút chọn đúng tài khoản email.
   - Khi xuất hiện màn hình `Đăng nhập vào Codex bằng ChatGPT` (Consent screen): Click nút `Tiếp tục` (Continue / Authorize).
3. Sau khi bấm `Tiếp tục`, trang web sẽ redirect về:
   ```text
   http://localhost:1455/auth/callback?code=ac_...&state=...
   ```
4. Cockpit Tools bắt được callback trên cổng 1455, tự động đổi token với OpenAI và hiển thị thông báo:
   ```text
   ✅ 授权成功 (Authorization Successful)
   ```
5. Đóng tab/profile GPM an toàn sau khi hoàn tất.

### Bước 4: Kích hoạt tài khoản vào Local API Service & Gán Proxy
1. Trên giao diện Cockpit, thẻ tài khoản vừa nạp sẽ xuất hiện với nhãn `FREE` (hoặc `PRO`), hiển thị Quota và thời gian reset (ví dụ: `89% 5 Week`).
2. Bấm nút **Add to API Service** trên thẻ tài khoản -> Trạng thái dịch vụ cập nhật thành `FREE (1) · All OK`.
3. Kiểm tra Local API hoàn tất:
   ```bash
   curl -H "Authorization: Bearer <COCKPIT_API_KEY>" http://127.0.0.1:60818/v1/models
   ```
   Kết quả trả về danh sách model (`gpt-6-astra`, `gpt-6-sol`, `gpt-5.6-luna`, `codex-auto-review`...).
4. **Proxy Engine Mihomo:**
   - Trong mục **Proxy management** -> tab **Proxies**, bấm **Download & install** để Cockpit tự tải engine `Mihomo 1.19.31` (`mihomo.exe`) vào `~/.antigravity_cockpit/proxy-engine/`.
   - Sau khi cài engine, có thể thêm proxy node (`Add proxy`) hoặc gán egress proxy riêng cho từng tài khoản (`Independent proxy`).

## 3. Pitfalls & Lưu ý sống còn
1. **Tránh can thiệp thủ công vào file encrypted:** Đừng cố inject token vào `codex_accounts/` hay chỉnh `manifest.json` bằng script vì Cockpit có logic checksum và sẽ tự wipe các file không khớp khi khởi động lại.
2. **OAuth Timeout Window:** State của Cockpit OAuth chỉ có hiệu lực khoảng 2-3 phút. Luôn lấy link mới hoặc bấm `Refresh Auth Link` ngay trước khi mở GPM để tránh lỗi `Authentication timed out`.
3. **Cổng 1455:** Cockpit mở server lắng nghe trên `localhost:1455`. Khi callback redirect về `1455`, Cockpit tự động xử lý. Nếu callback bị chặn hoặc không tự bắt, có thể copy full URL callback dán vào ô `Manual callback URL` trong Cockpit và bấm `I've authorized, continue`.
