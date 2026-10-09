# Codex OAuth via GPM: pool verification runbook

## Trigger
Use when reauthenticating a Codex account from a GPM browser profile, checking why an OAuth test used the wrong provider, or reconciling duplicate GPM/OmniRoute records.

## Safe sequence

1. **Enumerate GPM profiles through the Local API, including pagination.** Do not infer the fleet size from page 1. Use `GET /api/v3/profiles?page=N&per_page=50`; read `pagination.total`, `page_size`, and `total_page`; fetch every declared page and fail closed if totals change, a page is empty/malformed, or fetched count differs from `total`.
2. **Retain duplicate Gmail candidates.** Map `email -> list[profiles]`, never `email -> profile` with silent overwrite. If multiple candidates exist, inspect each profile's live Gmail session via its GPM CDP endpoint. Metadata/name alone does not prove session identity.
3. **Use live identity evidence before destructive cleanup.** A matching Gmail title/body such as `Hộp thư đến ... - target@gmail.com - Gmail` proves the currently opened profile session. Stop the profile in `finally`. Delete a duplicate only after a verified live match and explicit operator instruction; preserve the verified profile.
   - **GPM Delete Contract**: GPM Local API bắt buộc query param `mode=1` (`GET /api/v3/profiles/delete/{id}?mode=1`). Gọi thiếu `mode` sẽ trả về `{"success": false, "message": "INVALID_MODE"}`. `mode=1` đảm bảo xóa sạch cả bản ghi SQLite lẫn thư mục dữ liệu trên disk.
   - **GPM Duplicate Triage Heuristic**: Khi gặp profile trùng tên/email (`AMBIGUOUS_GPM_PROFILE`), phân loại profile sống vs profile rác bằng 3 tiêu chí:
     * *Group ID & Group Name*: Profile nằm trong Group 10 (`Google_Live_Ready`) là profile chính chủ đang hoạt động; Profile trong Group 11 (`Google_Cooldown_Error`) hoặc nhóm demo/rác là bản sao lỗi cần dọn dẹp.
     * *Disk mtime & Cookie Count*: Profile sống có số lượng cookie lớn (thường >100 cookies, bao gồm Google và OpenAI cookies) và thư mục session `~/AppData/Local/Programs/GPMLogin/profile/<path>` có mtime gần nhất (trong ngày).
     * *Direct Session Extraction*: Profile sống trong Group 10 thường đã có sẵn session cookie hợp lệ (`__Secure-next-auth.session-token.0/.1`). Có thể trích xuất, ghép chunk và validate thẳng qua `/api/providers/validate` mà không cần re-login hay mở form đăng nhập. Xóa profile rác nhóm 11 bằng `mode=1` để giải phóng cờ `AMBIGUOUS_GPM_PROFILE` cho watchdog.
4. **Reconcile proxy identity.** Compare the GPM profile's `raw_proxy` host/port/user with OmniRoute `proxy_registry` and `proxy_assignments` (`scope=account`, `scope_id=<connection_id>`). Do not assume `proxy_enabled=true` means the correct proxy is assigned.
5. **Import OAuth narrowly.** Extract the access token only from the verified GPM profile's ChatGPT session and import through the Codex endpoint. Redact tokens; never report them.
6. **Do not verify an imported connection through a generic model name.** A newly imported connection may not belong to any combo and can fall through to OpenRouter. Verify through the existing pool combo and exact model, e.g. `codex/gpt-5.6-luna-medium`, with the intended `connectionId` header. If the response route/provider is `openrouter/*`, classify the verification as invalid route, not Codex quota failure.
7. **Keep pool and duplicate connection state separate.** After import, check `/api/combos` for the target connection. If the import created an unbound duplicate and the established pool connection is healthy, delete only the unbound duplicate through the documented provider-connection API after confirming it is not referenced by any combo.
   - **OmniRoute Connection Deletion**: Endpoint chuẩn để xóa connection là `DELETE /api/providers/{connection_id}` (không phải `/api/providers/connections/...`). Trước khi xóa, phải lọc bỏ `connectionId` khỏi mảng `models` trong bảng `combos` (`chatgpt-web-pool`, `gpt-web-sol`, `gpt-web-luna`, v.v.) qua `PUT /api/combos/{combo_id}` để tránh để lại dangling reference.
   - **Account Banned / Deleted Handling**: Khi ChatGPT Web trả về lỗi *"Bạn không có tài khoản vì tài khoản đã bị xóa hoặc vô hiệu hóa"* (Account deleted or disabled) hoặc redirect OAuth có query param `payload=<base64>` giải mã ra `{"kind": "AccountDeactivated"}`:
     * Cả `chatgpt-web` và `codex` của tài khoản này trên OpenAI đều đã chết vĩnh viễn.
     * Quy trình dọn dẹp: (1) Cập nhật các combo chứa connection này (lọc bỏ connectionId khỏi mảng `models`), (2) Gọi `DELETE /api/providers/{connection_id}` cho cả 2 connection `chatgpt-web` và `codex`.
     * **Decoupling Guard**: TUYỆT ĐỐI KHÔNG xóa hay tắt connection `antigravity` của email đó, vì Antigravity sử dụng Google Cloud Code / Gemini OAuth hoàn toàn độc lập với lệnh cấm của OpenAI.
   - **Dead Account Pruning**: Đối chiếu với `Gmail_DIE_Archive` trong `master_gmail_manager.xlsx`; nếu tài khoản đã DIE, gỡ dứt điểm khỏi OmniRoute để triệt tiêu false-alert rác.

## Evidence classifications

- `GMAIL_LIVE`: live Gmail page identifies the target address.
- `GPM_PROFILE_AMBIGUOUS`: multiple candidate profiles remain without unique live identity evidence.
- `OAUTH_IMPORTED`: OmniRoute accepted the token; not proof of model completion.
- `POOL_COMPLETION_PASS`: exact Codex pool model returns a successful completion.
- `WRONG_ROUTE`: response route/provider differs from the requested Codex provider; do not label as quota exhaustion.
- `QUOTA_OR_CREDITS`: only after the request is proven to have used the intended Codex pool route.
- `DUPLICATE_CONNECTION`: imported connection is active but unreferenced by the intended combo; reconcile before leaving it in rotation.
- `SOAKING_48H`: account is newly verified via 5sim (`batch_gpm_5profiles_supervisor_state.json`), set `is_active=0` to ngâm 48h an toàn. Probe test `/api/providers/{id}/test` returns `valid: true`. Auto-activated by cronjob `omni-activate-soaked-codex` once soak >= 48h.
- `TOKEN_REVOKED_401`: upstream OAuth token revoked/expired (`Token invalid or revoked`, HTTP 401). OmniRoute auto-disables toggle (`is_active=0`) after repeated failures (apiKeyHealth failure count >= 7). On Quota UI, card may still appear green (89%, 98%, 100% left) due to stale `quota_snapshots` cached before revocation. Cannot recover through soaking; MUST be re-authenticated via GPM OAuth.
- `OPENAI_ACCOUNT_DEACTIVATED`: upstream OpenAI login redirects to `https://auth.openai.com/error?payload=<base64>`. Decoded JSON reveals `{"kind": "AccountDeactivated"}`. Hard ban on OpenAI side. Must be marked banned (`is_active=0`, `test_status='banned'`) and pruned from combos to avoid retry churn.
- `GOOGLE_PHONE_CHECKPOINT`: Google OAuth login redirects to phone verification challenge ("Verify it's you - Enter a phone number"). Verified by WinRT OCR on `oauth_err_<user>.png`. Farm invariant: requires paid SMS, do NOT auto-order; keep `is_active=0` and report to operator.
- `STALE_QUOTA_SNAPSHOT`: Quota percentage displayed on UI does not prove token validity. Green quota with toggle OFF indicates either 48h soaking or 401 revocation.
- `UNSAFE_MANUAL_ACTIVATE`: Manually toggling `is_active=1` on an account in `TOKEN_REVOKED_401` state without re-auth immediately causes incoming requests to fail and triggers cascade failure across pools.
- `NO_SPONTANEOUS_TOKEN_RECOVERY`: Upstream 401 revoked tokens NEVER spontaneously recover or regenerate without an explicit GPM OAuth flow. If an inactive account tests `valid: true`, its token was NEVER revoked; it was disabled due to quota exhaustion or soaking.
- `CODEX_QUOTA_MONTHLY_WINDOW`: Codex Free Tier operates on a 30-day (monthly) rolling window (`next_reset_at` ~30 days out), NOT weekly. Quota exhaustion is tracked dynamically by OmniRoute (`is_exhausted=1`). Setting `is_active=0` for quota exhaustion is an anti-pattern because OmniRoute has NO automated cron to re-enable `is_active=1` upon quota reset.

## Automation & Watchdog Architecture Truths

1. **Unified 3-Provider Morning Watchdog (`cron_chatgpt_web_pool_watchdog.py`)**:
   - Chạy định kỳ lúc 05:00 sáng, tự động hồi sinh cả 3 nhà cung cấp chính qua GPM Profile:
     - `chatgpt-web`: Auto-heals qua GPM (Direct Google OAuth + Cookie extraction). Hễ validate cookie thất bại (HTTP 400 Bad Request, 401 hoặc văng session), BẮT BUỘC tự động chuyển sang luồng Auto-Relogin (`perform_auto_login_and_extract_cookies`) dùng `PASS CHATGPT` từ Cột L workbook `taikhoan_dat_v2_updated.xlsx` để đăng nhập lại và lấy cookie mới; TUYỆT ĐỐI CẤM dừng sớm báo lỗi khóc lóc khi chưa chạy auto-relogin.
       * *Bẫy Cookie Cũ Gây Lặp 400 Bad Request*: Trong Playwright CDP, nếu cookie session cũ đã chết mà không gọi `context.clear_cookies()`, trang `chatgpt.com` sẽ tiếp tục gửi cookie chết và không render form nhập `input#email-input`, dẫn đến việc cuối hàm lại trích xuất chính cookie cũ đó trả về và tiếp tục fail `400 Bad Request`. BẮT BUỘC phải `context.clear_cookies()` trước khi reload lại `https://chatgpt.com/auth/login` để điền email và password mới từ Cột L.
     - `antigravity`: Auto-heals qua GPM (Google OAuth consent + token exchange). Khi gặp Google challenge (Prompt / Security Code 10 số OOTP), BẮT BUỘC liên thông thiết bị Samsung S7 qua `run_oauth_s7_pipeline.py` / ATX-Agent port 7912 để duyệt prompt hoặc bốc mã 10 số offline; TUYỆT ĐỐI CẤM ngồi chờ 90s rồi timeout báo kẹt.
       * *Bẫy Timeout Thiếu Kết Nối S7 trong Watchdog*: Nếu watchdog trên PC chỉ xử lý form nhập Password/TOTP/Recovery Mail thông thường mà không tra cứu mapping máy S7 từ cả `taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`, cột 1 Máy, cột 6 Email, cột 10 Serial) lẫn `master_gmail_manager.xlsx` để gọi `approve_s7_google_prompt` (khi dính `challenge/dp`) hoặc `get_s7_security_code` (khi dính `challenge/ootp` hoặc `input#security-code-input`), Google sẽ giữ ở màn hình xác minh thiết bị đến khi hết timeout và ném lỗi `Timeout bắt OAuth code`. Bắt buộc `get_account_for_email` trong `run_oauth_s7_pipeline.py` phải ưu tiên tra cứu từ `taikhoan_dat_v2_updated .xlsx` (chú ý khoảng trắng đuôi file) trước khi fallback về `master_gmail_manager.xlsx` để tìm đủ serial máy thật cho các tài khoản farm.
     - `codex`: Auto-heals qua GPM khi phát hiện token 401 (`Token invalid or revoked` / `testStatus != 'active'`):
       * Khởi chạy callback server trên OmniRoute (`GET /api/oauth/codex/start-callback-server`).
       * Điều hướng GPM tới `authUrl`, forward cổng 1455 về `127.0.0.1`.
       * **BẮT BUỘC ẩn nút Google SSO** (`Continue with Google`), thực thi 100% Direct Email + Password từ `gmail_clean_v2.xlsx`.
       * Tự động giải TOTP 2FA nếu xuất hiện challenge.
       * Click Consent / Authorize và poll callback (`POST /api/oauth/codex/poll-callback`).
       * Cập nhật `is_active=1` và `test_status='active'` khi thành công; nếu thất bại mới kích hoạt `disable_codex_connection()` để giữ an toàn cho pool.
2. **Quota Reset vs `is_active` Toggle Discipline**:
   - **Tuyệt đối không tắt `is_active=0` khi tài khoản chỉ cạn quota (0% left)**: Combo router của OmniRoute đã tự động nhận diện và bỏ qua tài khoản hết quota qua cờ `is_exhausted=1` động. Nếu cố tình set `is_active=0` trong DB/UI, tài khoản sẽ bị kẹt tắt vĩnh viễn kể cả khi OpenAI reset quota hàng tháng, do hệ thống không có cron tự động bật lại `is_active` khi có quota mới (trừ cron 48h soak cho Hotmail).
   - **Chu kỳ Quota Codex Free**: Chu kỳ quota của OpenAI Codex Free là **30 ngày (chu kỳ tháng)**, không phải chu kỳ tuần.
3. **Soaked Account Activation**:
   - Các tài khoản Hotmail mới sau khi ver 5sim OTP (`WAIT_48H`) được bảo vệ riêng bởi cronjob `omni-activate-soaked-codex` (Job ID: `80c157b851d5`), tự động quét và bật `is_active=1` sau đủ 48 tiếng ngâm an toàn. Morning watchdog tự động bỏ qua các tài khoản `@hotmail.com` để không phá vỡ chu kỳ ngâm.
4. **Codex OAuth Concurrency vs Singleton TCP Port 1455 Constraint**:
   - **Bản chất kỹ thuật**: Không phải do máy yếu (CPU/RAM thừa sức gánh 10-20 browser). Nút thắt nằm ở giao thức OAuth của Codex CLI: redirect URI bị hardcode cố định là `http://localhost:1455/auth/callback`.
   - **Xung đột cổng TCP**: Ở tầng mạng OS, chỉ DUY NHẤT 1 socket được bind/listen trên cổng 1455 tại cùng một thời điểm.
   - **Singleton trong OmniRoute**: Backend OmniRoute (`route.ts`) lưu trạng thái callback vào `globalThis.__pkceCallbackStates['codex']`. Mỗi lệnh `start-callback-server` sẽ hủy `close()` server cũ và tạo mới `codeVerifier`. Nếu chạy song song, Worker sau sẽ giết chết server và xóa `codeVerifier` của Worker trước, gây ra lỗi `mismatch state / invalid_grant` hoặc nuốt nhầm token của nhau.
   - **Kỷ luật điều phối**: Trong khi Antigravity và ChatGPT-Web mở đa luồng song song thoải mái, riêng quy trình Codex OAuth qua GPM BẮT BUỘC phải xếp hàng chạy tuần tự (FIFO) trên cùng một máy host OmniRoute. Mọi kịch bản batch tự động phải giải thích rõ lý do kỹ thuật này để tránh hiểu lầm máy bị giới hạn phần cứng.
5. **So sánh Kiến trúc Giao thức: Antigravity OAuth (Song song) vs Codex OAuth (Bắt buộc tuần tự)**:
   - **Antigravity OAuth (Stateless Web Flow)**:
     * *Redirect URI*: `http://127.0.0.1:20129/callback` (dùng luôn Next.js HTTP server có sẵn của OmniRoute).
     * *Cơ chế*: Khi gọi `GET /api/oauth/antigravity/authorize`, OmniRoute trả về `{authUrl, state, codeVerifier}` trong payload HTTP response. Script Playwright tự lưu giữ bộ 3 này trong biến cục bộ của từng worker, tự lắng nghe URL chuyển hướng để chộp `code`, rồi tự gọi `POST /api/oauth/antigravity/exchange` kèm `{code, codeVerifier, state}` để đổi token.
     * *Tính song song*: Hoàn toàn **phi trạng thái (Stateless)**, không dựng listener mới, không dùng cổng cố định. Mở 10 hay 50 browser cùng lúc thì mỗi worker tự mang credential riêng, hoàn toàn độc lập, chạy song song tối đa công suất máy.
   - **Codex OAuth (Stateful Local Listener Flow)**:
     * *Redirect URI*: `http://localhost:1455/auth/callback` (OpenAI hardcode cố định trong Codex Client ID, không thể đổi sang cổng khác).
     * *Cơ chế*: Để nhận redirect từ browser, OmniRoute phải dùng `startLocalServer` chiếm giữ cổng TCP 1455 và lưu session vào bộ nhớ RAM dùng chung `globalThis.__pkceCallbackStates["codex"]`.
     * *Tính tuần tự*: Bắt buộc **tuần tự (FIFO)**. Nếu mở đồng thời 2 worker, lệnh gọi server thứ hai sẽ lập tức kill server 1455 thứ nhất và ghi đè `codeVerifier` trong RAM, dẫn tới lỗi lệch state / nuốt nhầm token chéo giữa các nick.
6. **Pipeline Combo Hotmail [Reg ChatGPT -> Ver Codex 5SIM]: Phân Tách Reg Song Song vs OAuth Mutex Tuần Tự**:
   - **Giai đoạn 1: Đăng ký ChatGPT (`CHATGPT_REG`)**:
     * Diễn ra 100% trên giao diện web `chatgpt.com` qua proxy riêng của từng profile, nhận OTP qua Microsoft Graph API.
     * Hoàn toàn không đụng chạm đến localhost hay cổng mạng nội bộ nào -> **Chạy song song đa luồng tối đa (5 workers)** trên 5 IP/proxy khác nhau để tận dụng tối đa CPU/RAM và tài nguyên proxy.
   - **Giai đoạn 2: Verify Codex OAuth & Thuê SIM (`CODEX_OAUTH`)**:
     * Trình duyệt chuyển hướng về `http://localhost:1455/auth/callback` và gọi `GET /api/oauth/codex/start-callback-server`.
     * Cả 5 browser đều nằm trên cùng 1 máy host Windows và trỏ về cùng cổng `1455` của OmniRoute.
     * **BẮT BUỘC dùng Mutex khóa tuần tự (FIFO Lock)**: Worker nào reg ChatGPT xong trước thì chiếm Mutex cổng 1455 để xin `authUrl`, mở callback server, nhận code và đổi token (chỉ mất ~15-20s). Xong xuôi nhả Mutex cho worker tiếp theo.
     * Không bao giờ cho phép 2 worker cùng lúc gọi `start-callback-server` trên cùng một máy host.
   - **Mã nguồn Chuẩn `CodexOAuth1455Lock` (Đã tích hợp trong `codex_5sim_auto_verify.py` & `cron_chatgpt_web_pool_watchdog.py`)**:
     ```python
     import msvcrt
     from pathlib import Path

     class CodexOAuth1455Lock:
         def __init__(self, lock_file=r"D:\Taadaa\runtime\kibe\cron-state\codex_oauth_1455.lock", timeout=900):
             self.lock_file = Path(lock_file)
             self.timeout = timeout
             self.handle = None

         def __enter__(self):
             self.lock_file.parent.mkdir(parents=True, exist_ok=True)
             start_t = time.time()
             self.handle = open(self.lock_file, "a+b")
             waited = False
             while True:
                 try:
                     self.handle.seek(0)
                     msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                     if waited:
                         print(f"[+] Đã lấy được khóa độc quyền 1455 sau {time.time()-start_t:.1f}s")
                     return self
                 except (OSError, IOError):
                     if not waited:
                         print("[*] Đang chờ nhả khóa độc quyền cổng 1455 (Codex OAuth Mutex)...")
                         waited = True
                     if time.time() - start_t > self.timeout:
                         raise TimeoutError(f"Timeout {self.timeout}s waiting for Codex OAuth 1455 lock")
                     time.sleep(2)

         def __exit__(self, *_):
             if self.handle:
                 try:
                     self.handle.seek(0)
                     msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
                 except Exception: pass
                 try:
                     self.handle.close()
                 except Exception: pass
                 self.handle = None
     ```
     Bọc toàn bộ logic OAuth của từng profile trong `with CodexOAuth1455Lock():` để bảo đảm các worker song song tự xếp hàng mà không bị đè cổng hoặc xóa mất `codeVerifier` trong OmniRoute.
7. **Độc Lập Tuyệt Đối Giữa Codex Provider (`codex-terra` / `codex-luna`) và ChatGPT Web Provider (`chatgpt-web-pool` / `gpt-web-sol` / `gpt-web-luna`)**:
   - **CẤM ném hoặc trông chờ cron ném connection Codex vào pool ChatGPT-Web**:
     * `codex`: Xác thực OAuth PKCE Bearer token qua cổng 1455, trỏ vào OpenAI Codex API (`/v1/responses`), gán cho các combo `codex-terra`, `codex-luna`.
     * `chatgpt-web`: Xác thực bằng Session Cookie (`__Secure-next-auth.session-token`), trỏ vào NextAuth Web backend (`/backend-api/conversation`), giải Turnstile/Sentinel, gán cho `chatgpt-web-pool`, `gpt-web-sol`, `gpt-web-luna`.
     * Ghép chéo connection (ném connection Codex vào pool Web hoặc ngược lại) sẽ gây gãy request ngay lập tức (lệch endpoint, thiếu cookie, sai request schema).
   - **Tồn tại song song độc lập (Dual-Provider Architecture)**: Một email/profile sở hữu 2 connection độc lập trong `provider_connections` (1 bản ghi `provider='codex'` và 1 bản ghi `provider='chatgpt-web'`) với 2 `connectionId` khác nhau, combo router gán đúng provider tương ứng.
8. **Quy Trình Khai Thác Kép (Dual-Harvest Pipeline) & Ngâm Kép Đồng Bộ 48H**:
   - **Bản chất**: Khi một profile vừa hoàn tất đăng ký ChatGPT (`CHATGPT_REG` trong `chatgpt_gpm_direct_reg.py`), trình duyệt đã có sẵn cookie `__Secure-next-auth.session-token` hợp lệ trước khi bước sang giai đoạn xác thực số điện thoại 5sim (`CODEX_OAUTH`).
   - **Trích xuất sớm & Chuẩn hóa Cookie Chunking (Early Session Extraction & Chunking Contract)**: 
     * Ngay tại màn hình chính sau reg thành công (có prompt textarea), script trích xuất ngay session token từ context browser và nạp connection `chatgpt-web` với trạng thái `is_active = 0` (`test_status = 'soaking'`).
     * **Pitfall Cookie Chunking**: Session cookie của ChatGPT Web (`__Secure-next-auth.session-token`) thường xuyên vượt ngưỡng 4KB và bị Chromium chia nhỏ thành các chunk (`__Secure-next-auth.session-token.0`, `.1`, ...). Kiểm tra đơn lẻ `name == '__Secure-next-auth.session-token'` sẽ trả về `None` trong im lặng. BẮT BUỘC: Lấy toàn bộ cookie, nếu không có cookie đơn thì lọc các cookie có tiền tố `__Secure-next-auth.session-token.`, sắp xếp theo index số (`key=lambda x: int(x['name'].split('.')[-1])`) và ghép chuỗi (`"".join(...)`) lại thành JWT hoàn chỉnh trước khi lưu vào DB.
   - **Quy Trình Kiểm Chứng Canary (Canary Verification Protocols)**:
     * *Canary Nhóm 1 (In-Profile Session Harvest & Auto-Activation)*: Với các profile đã có session (`chatgpt_registered_at` hoàn tất và đã ngâm $\ge$ 48h, ví dụ `murtaghshandy156@hotmail.com`): Khởi động profile GPM $\to$ trích xuất cookie chunked qua CDP $\to$ nạp bản ghi `chatgpt-web` (`is_active=0`) $\to$ kích hoạt script `cron_omni_activate_soaked_codex.py` để xác thực kích hoạt `is_active=1` và tự động gắn vào các combo `chatgpt-web-pool` và `gpt-web-sol`.
     * *Canary Nhóm 2 (Full Registration Pipeline)*: Với các profile mới tinh chưa reg ChatGPT: chạy trọn vẹn `chatgpt_gpm_direct_reg.py` từ nhận OTP qua Microsoft Graph API đến nạp session tự động vào OmniRoute.
   - **Ngâm tĩnh kép 48h (Dual Soaking Protection)**:
     * Cả 2 connection (`chatgpt-web` và `codex`) BẮT BUỘC giữ `is_active = 0` trong suốt 48h đầu (`WAIT_48H` / `SOAKING_48H`).
     * Không cho phép ChatGPT-Web nhận request sớm nhằm tránh Cloudflare Sentinel / Turnstile bot detection quét làm chết tài khoản non và kéo theo mất luôn OAuth token Codex.
   - **Kích hoạt đồng bộ & Nạp combo tự động**:
     * Cronjob `omni-activate-soaked-codex` (`cron_omni_activate_soaked_codex.py`) quét các email ngâm đủ 48h và kích hoạt `is_active = 1` đồng thời cho CẢ HAI provider (`codex` và `chatgpt-web`).
     * Tự động nạp connection `chatgpt-web` vào các combo Web (`chatgpt-web-pool`, `gpt-web-sol`) và nạp connection `codex` vào các combo Codex (`codex-terra`, `codex-luna`).
     * Tối ưu hóa 100% tài nguyên: 1 tài khoản đăng ký phục vụ đồng thời cả Agentic Coding (Codex CLI) lẫn Web Inference mà không tốn thêm chi phí proxy hay mua SIM phụ.
9. **Reconciliation & Backfill cho các đợt tài khoản cũ bị lệch Pool (Historic Account Pool Balancing)**:
   - **Bối cảnh**: Khi hệ thống nâng cấp lên kiến trúc Dual-Harvest, các tài khoản Hotmail ở các batch cũ đã có connection `codex` nhưng chưa có bản ghi `chatgpt-web` tương ứng trên OmniRoute, dẫn đến mất cân bằng quy mô giữa 2 pool.
   - **Runbook xử lý lệch pool dứt điểm**:
     1. *Quét đối soát (Cross-Audit)*: Lấy danh sách connection `codex`, đối chiếu tập email với bảng `provider_connections` (`provider='chatgpt-web'`) để lọc danh sách tài khoản bị khuyết.
     2. *Trích xuất session an toàn qua GPM CDP*:
        - Khởi chạy profile GPM tương ứng qua `/api/v3/profiles/start/{id}`.
        - Kết nối Playwright Chromium CDP, lấy cookies từ `https://chatgpt.com`.
        - Bắt buộc kiểm tra cả cookie đơn `__Secure-next-auth.session-token` và cookie chunked `.0`, `.1` (nối chuỗi hoàn chỉnh).
        - Đóng profile qua `/api/v3/profiles/stop/{id}`.
     3. *Nạp OmniRoute phân tầng*:
        - Nạp bản ghi mới `provider='chatgpt-web'`, `auth_type='apikey'`, `is_active=0` (`test_status='soaking'`).
     4. *Phân nhánh kích hoạt theo tuổi ngâm*:
        - Kiểm tra mốc `codex_oauth_at` trong `batch_gpm_5profiles_supervisor_state.json`:
        - Nếu $\ge 48h$: Chạy `cron_omni_activate_soaked_codex.py` $\to$ tự động lật `is_active=1` và nạp vào các combo `chatgpt-web-pool` và `gpt-web-sol`.
        - Nếu $< 48h$: Giữ nguyên `is_active=0` (soaking) để cronjob định kỳ tự động bật khi đủ thời gian.
     5. *Cân bằng Combo Codex*:
        - Đối chiếu các connection Codex đang `is_active=1` nhưng chưa nằm trong combo $\to$ đồng bộ bù vào `codex-terra` và `codex-luna` để khai thác triệt để quota.
10. **GPM Chromium CDP Socket Bind Race Condition & Retry Pattern**:
   - Khi khởi chạy profile GPM qua `GET /api/v3/profiles/start/{id}?win_scale=0.8`, GPM Local API trả về `remote_debugging_address` (ví dụ `127.0.0.1:53001`) ngay khi vừa tạo process Chrome.
   - Trên môi trường Windows (đặc biệt khi chạy song song 5 workers trong morning watchdog), Chromium có thể mất 1-3 giây để khởi động toàn bộ tiến trình con và bind socket lắng nghe CDP.
   - Việc gọi ngay `p.chromium.connect_over_cdp(...)` sẽ gặp lỗi `BrowserType.connect_over_cdp: connect ECONNREFUSED`.
   - **Quy tắc bắt buộc**: Phải bọc `connect_over_cdp` trong vòng lặp thử lại 3 lần kèm linear-exponential backoff (1.5s, 3.0s, 4.5s) và structured warning log:
     ```python
     browser = None
     for attempt in range(1, 4):
         try:
             browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
             break
         except Exception as e:
             log(f"[{email}] CDP retry {attempt}/3 fail: {e}")
             time.sleep(attempt * 1.5)
     if not browser:
         log(f"[{email}] Kết nối CDP thất bại sau 3 lần thử")
         return None
     ```
   - Cơ chế này loại bỏ hoàn toàn các lỗi false-positive `ECONNREFUSED` trong quá trình watchdog tự động kiểm tra và phục hồi session.
   - **Zero Dangling Reference Integrity Check**: Sau mọi thao tác xóa connection hoặc chỉnh sửa combo, bắt buộc chạy kiểm chứng toàn vẹn SQLite để đảm bảo không để lại `connectionId` mồ côi trong bất kỳ combo nào:
     ```python
     # Query kiểm tra connectionId mồ côi trong combos
     cur.execute("SELECT id, name, data FROM combos")
     dangling = [
         (cname, m['connectionId'])
         for cid, cname, cdata in cur.fetchall()
         for m in json.loads(cdata).get('models', [])
         if m.get('connectionId') and not cur.execute(
             "SELECT 1 FROM provider_connections WHERE id=?", (m['connectionId'],)
         ).fetchone()
     ]
     assert len(dangling) == 0, f"Dangling references detected: {dangling}"
     ```

## Inactive (is_active = 0) & Stale Quota Card Triage Runbook

When triaging disabled Codex connection cards on OmniRoute Quota Dashboard (`/dashboard/quota`):
1. **Never trust UI quota color alone**: The Quota UI displays cached data from `quota_snapshots`. An account with a revoked token will still display green (e.g. 89% or 100% left) if it had unused quota before revocation.
2. **Execute live probe test**: Call `POST http://127.0.0.1:20129/api/providers/{id}/test` with payload `{}`:
   - If `valid: true` and account is Hotmail in `batch_gpm_5profiles_supervisor_state.json` (`stage: WAIT_24_48H`) -> `SOAKING_48H`. Check `created_at` or `codex_oauth_at`. Let cronjob `omni-activate-soaked-codex` auto-activate after 48h.
   - If `valid: false` with `error: "Token invalid or revoked"` (HTTP 401) -> `TOKEN_REVOKED_401`. Do NOT toggle `is_active=1` manually. Schedule GPM profile re-authentication.
   - If `valid: true` and not soaking (e.g. recovered/refreshed) -> Safe to re-enable.
3. **Inspect SQLite audit logs**:
   ```sql
   SELECT timestamp, action, target, details 
   FROM audit_log 
   WHERE target LIKE 'codex:%' 
   ORDER BY timestamp DESC LIMIT 20;
   ```
   Check exact timestamp and error payload when `isActive` changed to identify whether it was auto-disabled by upstream 401 or an intentional policy change.

## Common failure that must not recur

A first-page-only GPM lookup reported "no profile" even though the API held 192 profiles across four pages. A generic post-import ping (`gpt-5.5`/`gpt-5.6-luna`) on an unbound connection fell through to `openrouter/openai/*` and returned 402. Both are routing/lookup errors, not evidence that Gmail or Codex OAuth is dead.

## Reporting template

Report: target email; all candidate profile IDs/paths; live identity evidence; selected/deleted profile and API response; proxy registry ID and account assignment; imported connection ID; combo/model/connection ID used for verification; HTTP status, route, latency; final active state. Never claim Codex quota exhaustion from an OpenRouter response.
