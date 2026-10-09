# Codex OAuth (start-callback-server) vs ChatGPT-Web (import-token) Architecture

## 1. Khác biệt kiến trúc cốt lõi

| Đặc tính | Luồng ăn trộm Web (`import-token`) | Luồng OAuth chính thức (`start-callback-server`) |
| :--- | :--- | :--- |
| **Bản chất Token** | JWT web session ngắn hạn (`accessToken` từ `/api/auth/session`) | Mã định danh OAuth 2.0 PKCE Developer Token |
| **Refresh Token** | **KHÔNG CÓ** (chỉ có session cookie `__Secure-next-auth.session-token`) | **CÓ** `refresh_token` (`rt.1...`), cấp quyền `offline_access` |
| **Vòng đời token** | Hết hạn sau **1-2 giờ** -> báo lỗi `[401] Unauthorized / Token invalid or revoked` | **VĨNH VIỄN** -> OmniRoute tự động dùng `refresh_token` gia hạn access token ngầm |
| **Endpoint OmniRoute** | `POST /api/oauth/codex/import-token` | `GET /api/oauth/codex/start-callback-server` + `POST /api/oauth/codex/poll-callback` |
| **Mô hình hỗ trợ** | Bị giới hạn hoặc giả lập reverse proxy | Toàn quyền gọi dòng model cao cấp: `gpt-5.6-terra-high`, `gpt-5.6-sol`, `gpt-5.5` |
| **Vị trí trong Combo** | Chỉ dùng cho fallback chat thông thường (dễ dính 413 nếu payload lớn) | **Tier 1 đứng đầu combo `review`** (`codex/gpt-5.6-terra-high`), chịu tải context lớn |

## 2. Quy trình thực thi OAuth Codex qua GPMLogin (5 Bước chuẩn)

### Bước 1: Khởi tạo Callback Server trên OmniRoute
Gửi request lấy URL ủy quyền PKCE:
```python
res = requests.get("http://127.0.0.1:20129/api/oauth/codex/start-callback-server", timeout=15).json()
auth_url = res.get("authUrl")
# auth_url dạng: https://auth.openai.com/oauth/authorize?response_type=code&client_id=app_EMoamEEZ73f0CkXaXp7hrann&redirect_uri=http%3A%2F%2Flocalhost%3A1455%2Fauth%2Fcallback&scope=openid%20profile%20email%20offline_access...
```

### Bước 2: Khởi động Profile GPMLogin & Kết nối CDP
- Bắt buộc kiểm tra null-safe khi đọc `data`:
```python
r = requests.get(f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?win_scale=0.8", timeout=30).json()
data = r.get("data") or {}
cdp_addr = data.get("remote_debugging_address")
```

### Bước 3: Forward Callback Request về Loopback
Khi trình duyệt chuyển hướng về `http://localhost:1455/auth/callback?code=...`:
- Chặn sự kiện mạng và forward thẳng về `http://127.0.0.1:1455/...` để OmniRoute bắt được mã `code`:
```python
def on_req(req):
    url = req.url
    if "1455" in url and ("callback" in url or "code=" in url):
        try:
            local_url = url.replace("localhost", "127.0.0.1")
            requests.get(local_url, timeout=5)
        except Exception:
            pass
page.on("request", on_req)
```

### Bước 4: Tự động hóa UI (Cloudflare + Google SSO + Consent)
1. **Cloudflare "Just a moment..."**: Chờ 10-15s cho tiêu đề trang thoát khỏi `Just a moment...` và đạt `Welcome back - OpenAI`.
2. **Nút Google**: Click `button:has-text("Continue with Google")`.
3. **Google Account Chooser**: Nhận diện tài khoản qua `div[role="link"][data-identifier*="{email}"]`, lấy bounding box và click chuột vật lý. Sau đó dùng JS evaluate click nút "Tiếp tục" / "Continue" nếu Google hiện trang consent.
4. **Codex Authorize**: Click `button:has-text("Authorize")` hoặc `button:has-text("Cho phép")`.

### Bước 5: Polling Callback và Lưu trữ Connection
Lặp polling mỗi 2-3s (timeout 90-120s):
```python
poll = requests.post("http://127.0.0.1:20129/api/oauth/codex/poll-callback", json={}, timeout=5).json()
if poll.get("success") or "connection" in poll or "connectionId" in poll:
    # Thành công, token đã lưu kèm refresh_token vào database OmniRoute
```

## 3. Các cạm bẫy thực tế (Pitfalls & Auto-healing)

1. **PermissionError khi đọc file Cookies của GPMLogin**:
   - Khi có tiến trình Chrome renderer chạy ngầm giữ file `Cookies`, mở trực tiếp bằng `sqlite3.connect` sẽ bị `PermissionError: [Errno 13] Permission denied`.
   - **Cách fix**: Bắt buộc dùng `shutil.copyfile(src, temp_path)` ra thư mục tạm (`%TEMP%`), đọc xong xóa file tạm trong khối `finally`.

2. **Tiến trình Chrome mồ côi làm nghẽn tài nguyên**:
   - Khi profile GPM bị crash hoặc script tắt ngang, tiến trình `gpm_browser_chromium_core_.../chrome.exe` vẫn chạy ngầm (có thể lên tới hàng trăm tiến trình).
   - **Cách fix**: Dùng `psutil` quét và kill toàn bộ tiến trình có đường dẫn chứa `gpm_browser` trước khi bắt đầu batch mới.

3. **Xung đột Playwright Sync API trong ThreadPool**:
   - Tránh chạy `sync_playwright()` trực tiếp lồng sâu trong các vòng lặp asyncio hoặc đa luồng phức tạp dễ gây `It looks like you are using Playwright Sync API inside the asyncio loop`.
   - **Cách fix**: Tách runner của từng profile thành subprocess độc lập (`subprocess.run(["python", "run_single_codex_worker.py", pid, email])`), cô lập hoàn toàn môi trường thực thi.

4. **Trần Payload HTTP 413 trên ChatGPT-Web vs Codex CLI**:
   - `chatgpt-web` bị trần body ~500KB-1MB từ Cloudflare WAF. Không đặt `chatgpt-web-pool` làm tầng hứng tải trực tiếp sau Flash trong `omni-worker` vì request mang vác agentic context/tool schemas sẽ dội về 413 hàng loạt.
   - Luôn ưu tiên `ag-claude` hoặc `codex` lên trên `chatgpt-web` trong các combo worker.

5. **Cổng kiểm tra số điện thoại bắt buộc (Phone Gate / `add-phone`) khi OAuth Codex**:
   - Mặc dù tài khoản Google/Gmail đã đăng nhập và dùng bình thường trên ChatGPT Web (`chatgpt.com`), việc gọi OAuth cấp quyền Codex CLI (`offline_access`) là luồng Developer API, OpenAI bắt buộc phải verify số điện thoại (`https://auth.openai.com/add-phone`).
   - Cấm agent click lặp vô tận tại trang `choose-an-account`: nếu sau khi click tài khoản mà URL chuyển thành `/add-phone`, phải dừng ngay và báo cáo user nhập OTP SMS, hoặc chuyển sang dùng tài khoản đã verify phone trước đó.
