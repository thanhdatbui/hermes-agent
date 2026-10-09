# Kiến trúc Codex OAuth Phone Verification, 5sim API Automation & SumiStore API

## 1. Bản chất phân tầng giữa ChatGPT Web và Codex CLI
- **ChatGPT Web (`chatgpt.com/backend-api/conversation`)**:
  - Dùng session cookie từ Google OAuth thông thường. Không bắt buộc verify SĐT.
  - Nhược điểm: Bị giới hạn WAF/Reverse Proxy payload body (~500KB - 1MB). Khi dính request agent lớn (System Prompt, Tool schemas dài, conversation turns) sẽ dội ngay lỗi `HTTP 413 Payload Too Large`.
  - Không phù hợp làm tầng fallback chính cho agentic worker mang vác nặng.
- **Codex CLI / Official OpenAI API (`auth.openai.com/oauth/authorize` + scope `offline_access`)**:
  - Hỗ trợ full context window 128K - 200K tokens, payload dung lượng lớn, tool calls native.
  - **Rào cản bắt buộc**: OpenAI áp dụng chính sách chống abuse, khi user click chọn tài khoản Google để cấp quyền Codex, hệ thống tự động redirect sang `https://auth.openai.com/add-phone` đòi hỏi SMS Phone Verification 1 lần để sinh PKCE Developer Token.

## 2. Tự động hóa giải quyết Phone Verification bằng 5sim API

### 2.1. Bản chất cơ chế 5sim
- Header: `Authorization: Bearer <5SIM_API_TOKEN>`, `Accept: application/json`.
- Quét giá realtime: `GET https://5sim.net/v1/guest/prices?product=openai`.
- Cấp số: `GET https://5sim.net/v1/user/buy/activation/{country}/{operator}/openai`.
- Polling mã OTP: `GET https://5sim.net/v1/user/check/{order_id}` (`sms[0].code`).
- Cơ chế bảo toàn ví (Hold balance): Mua số chỉ tạm giữ tiền. Nếu không có SMS, gọi `GET https://5sim.net/v1/user/cancel/{order_id}` thì 5sim hoàn lại 100% tiền ngay lập tức. Chỉ bị trừ tiền khi nhận SMS và gọi `/finish/{order_id}`.

### 2.2. Sự thật về các dải số VoIP siêu rẻ và giải pháp thực nghiệm Argentina ($0.05)
- **Argentina (`virtual62`, $0.05 ~ 1.275 VNĐ)**:
  - Giá rẻ nhất hiện tại ($0.05/SIM), tỷ lệ nổ OTP đạt **~13%** (kho hơn 500 SIM), cao gấp 2.5 lần Philippines (`virtual58`, 5.08%).
  - Rẻ hơn 3.1 lần so với mua tài khoản tạo sẵn bên SumiStore (4.000 VNĐ) và rẻ hơn một nửa so với thuê SIM VN (2.500đ - 3.500đ), lại giữ được tài khoản chính chủ 100% trong GPM với Proxy tĩnh riêng.
- **Kỷ luật chống Spam / Phone Abuse & Quy Tắc 1 Nước 3 Lần, Max 3 Nước (CẤM TỰ PHÁ THIẾT KẾ WHATSAPP)**:
  - **Quy tắc 1 nước 3 lần, tối đa 3 nước (Trần 9 lần thử)**: Mỗi tài khoản được thử tối đa 3 số trên 1 quốc gia (`country_tries = 3`), và duyệt tối đa 3 quốc gia (`max_countries = 3`). Nước nào hết số (`no free phones`) tự động chuyển nước mà không tính mất slot.
  - **Thiết kế chuẩn xử lý WhatsApp của Sếp (CẤM TỰ Ý DỪNG SỚM)**:
    1. Khi form OpenAI đòi gửi OTP qua WhatsApp: Tìm và click chọn radio `Text Message (SMS)` nếu có.
    2. Nếu OpenAI ép 100% WhatsApp (không có nút SMS): Gọi ngay `GET /v1/user/cancel/{order_id}` hoàn tiền 100%, gọi `reset_to_add_phone(page)` để khôi phục form, và dùng `break` trượt ngay sang quốc gia tiếp theo. CẤM bấm submit mù gây văng phiên và CẤM dừng script khi chưa đi hết 3 nước.
    3. Phục hồi form khi văng: Khi submit lỗi hoặc bị mất form, bắt buộc điều hướng lại `https://auth.openai.com/add-phone` để nạp lại form nhập số sạch sẽ cho quốc gia tiếp theo.
  - **Auto-cancel / Refund 100%**: Nếu OpenAI từ chối số hoặc sau 45s không có OTP, gọi ngay `GET /v1/user/cancel/{order_id}` để hoàn lại tiền vào ví 5sim.
  - **Chỉ dừng chuyển ngâm 24h khi**: Đã đi hết cả 3 quốc gia (hoặc chạm trần 9 lần thử) mà không lấy được OTP, hoặc khi dính Cloudflare Turnstile/Captcha cứng. Tuyệt đối không dừng script chỉ vì 1 số điện thoại đầu tiên bị lỗi.
- **Xử lý dứt điểm Post-OTP Flow (Tránh mất tiền oan mà không nhận được Token)**:
  - Sau khi điền OTP 6 số, OpenAI thường chuyển hướng tới màn hình `about-you` (điền tên, tuổi) và màn hình cấp quyền `Continue / Authorize`.
  - BẮT BUỘC script phải tự động điền form `about-you` và click `Continue/Authorize` trước khi đóng trình duyệt để callback server trên port 1455 nhận PKCE OAuth token thành công.

### 2.4. Production Execution Gate & Anti-Blind Checkpoint Discipline
- **Exact Candidate Binding:**
  - Nhận `profile_id` và email chính xác từ request.
  - Phải paginate GPM profiles (`/api/v3/profiles?page=N&page_size=50`) để xác minh đúng profile ID và email/name trước khi thao tác.
  - Tuyệt đối KHÔNG dùng hardcoded `__main__` target (như `voha`) và KHÔNG sửa trực tiếp production script. Dùng explicit function call hoặc wrapper in-memory.
- **Bẫy Callback Forward Premature Collision (`on_req` check `:1455`):**
  - Khi bắt đầu OAuth, `auth_url` từ OmniRoute mang param `redirect_uri=http%3A%2F%2Flocalhost%3A1455%2Fauth%2Fcallback`.
  - Nếu listener Playwright `page.on("request", ...)` kiểm tra lỏng lẻo `"1455" in u and ("callback" in u or "code=" in u)`, chính request đầu tiên tới `auth.openai.com/authorize` sẽ bị bắt nhầm, in false-positive `Callback OAuth forwarded to OmniRoute` và GET nhầm endpoint.
  - **Bắt buộc:** Kiểm tra chặt chẽ host/origin callback: `u.startswith("http://localhost:1455") or u.startswith("http://127.0.0.1:1455")` hoặc `":1455/auth/callback" in u`.
- **Phân định DOM Gate Phone Verification vs Landing Log-in (`auth.openai.com/log-in`):**
  - Khi mở `auth_url`, OpenAI thường đáp ở `https://auth.openai.com/log-in` ("Welcome back" với nút "Continue with Google").
  - CẤM kiểm tra ngay `is_phone_verification_page` (`auth.openai.com/add-phone`) khi OAuth chưa tiến hành: phải chờ/vượt qua Cloudflare, click "Continue with Google" / chọn tài khoản Gmail, rồi mới phân loại:
    1. Trang `add-phone` -> Kích hoạt mua số 5SIM và điền OTP.
    2. Trang `Authorize` / callback xong trực tiếp -> Cấp quyền và poll OmniRoute (không tốn tiền SIM).
    3. Trang Captcha / mật khẩu / Blocked -> BẮT BUỘC chụp ảnh `codex_blocked_physical_*.png` TRƯỚC KHI dừng profile để có bằng chứng nghiệm thu vật lý.
- **Preflight Live Price & Operator Gating:**
  - Kiểm tra số dư 5SIM (`/v1/user/profile`) và giá live (`/v1/guest/prices?product=openai`).
  - Nếu user chỉ định operator cụ thể (ví dụ Vietnam `virtual34` trước, Colombia `virtual34` fallback), BẮT BUỘC tôn trọng đúng thứ tự ưu tiên và pool rate live, không tự ý chọn operator khác.
  - Giới hạn cứng tối đa 2 attempts tổng cộng (VN rồi Colombia).
- **GPM CDP Race Handling:**
  - Sau khi gọi `/api/v3/profiles/start/{id}`, Chrome cần vài giây để bind remote debugging port.
  - Phải loop poll `http://{cdp}/json/version` trước khi `browser.connect_over_cdp()`, tránh dội lỗi `ECONNREFUSED`.
- **Order Lifecycle & Immediate Refund:**
  - Mỗi attempt phải lưu `order_id`.
  - Nếu OpenAI báo lỗi từ chối số (`[role="alert"]`, `data-error`, số bị liên kết/không hỗ trợ) hoặc sau timeout không có OTP: BẮT BUỘC gọi `GET /v1/user/cancel/{order_id}` để hoàn tiền 100% ngay lập tức trước khi chuyển sang fallback attempt.
  - Chỉ gọi `GET /v1/user/finish/{order_id}` khi đã nhận OTP và hoàn tất cấp quyền.
- **Checkpoint Screenshots (Chống chạy mù):**
  - Chụp screenshot rõ ràng tại các checkpoint:
    1. Checkpoint 0: Landing OAuth / chọn tài khoản Google.
    2. Checkpoint 1: Điền số điện thoại xong, **trước khi submit**.
    3. Checkpoint 2: Kết quả **sau khi submit** (xác nhận chấp nhận số hay bị lỗi alert).
    4. Checkpoint 3: Sau khi điền OTP và click `Authorize` / hoàn tất UI.

### 2.5. Existing ChatGPT Session Only — Codex OAuth Gate (mandatory)

Khi người dùng yêu cầu dùng **chỉ session ChatGPT đã tồn tại**, đây là nhánh chuẩn và ghi đè mọi playbook SSO/đăng ký cũ:

1. **Inventory trước khi tương tác:** paginate GPM profiles; đối chiếu profile ID/name/email; dùng cookie evidence và OmniRoute `chatgpt-web` evidence chỉ để tạo ứng viên, không coi cookie đơn độc là proof. Profile phải được start live và kiểm tra bằng CDP/DOM/screenshot trên `https://chatgpt.com/`.
2. **Loại profile không hợp lệ:** loại ngay nếu ChatGPT hiển thị `Log in`, `Sign up`, guest mode, hoặc landing OAuth/OpenAI là login. Không click `Continue with Google`, Google chooser, SSO, password, CAPTCHA, hoặc tạo tài khoản. Nếu profile được chỉ định (ví dụ M16) không logged in, không force; chuyển sang ứng viên aged inventory khác và báo exact name/ID/evidence.
3. **Canonical existing-session flow:** mở OmniRoute `GET /api/oauth/codex/start-callback-server`, mở `authUrl` trong browser đã có session, chọn đúng **existing ChatGPT account** trên `/choose-an-account` nếu trang này hiển thị account đã đăng nhập, chọn workspace nếu cần, rồi click chỉ consent `Continue/Authorize`. Đây không phải Google SSO và không được thay bằng `run_codex_oauth_flow.py` login automation.
4. **Checkpoint/stop conditions:** chụp screenshot + DOM text trước OAuth, account chooser, consent, callback/add-phone. Nếu landing là login hoặc không có existing account choice thì dừng ngay; không mua SIM. Nếu callback trả về auth success thì poll `POST /api/oauth/codex/poll-callback` và verify connection bằng provider test.
5. **Phone gate:** chỉ khi authenticated existing-session flow reaches `auth.openai.com/add-phone` and live DOM contains `input[type="tel"]` plus phone/SMS verification text may 5SIM be used. Max 2 attempts total; cancel/refund every rejected, timed-out, or unused order; finish only after OTP + OAuth callback/connection ID. If existing session reaches callback directly, 5SIM orders must remain zero.
6. **Evidence report:** return exact profile name/ID/email, live URL and key OCR/DOM markers, screenshot paths, Codex connection ID/status, and each 5SIM order state/refund. Never claim success from cookie or stale OmniRoute evidence alone.

### 2.5a. Legacy OAuth Landing & Phone DOM Gate (only when user explicitly authorizes SSO)

- **Pitfall `phone_verification_dom_gate_failed` khi vừa mở authUrl:**
  - `auth_url` từ OmniRoute thường hạ cánh xuống trang **OpenAI Login / Welcome back** (`auth.openai.com/log-in` hoặc `/authorize`), hiển thị nút **"Continue with Google" / "Tiếp tục với Google"**, chưa phải Google Account Chooser hay `add-phone`.
  - Nếu script nhảy ngay vào gate kiểm tra `is_phone_verification_page(page)` hoặc chỉ tìm selector tài khoản Google mà không click `Continue with Google`, luồng sẽ đứt gãy và false alarm chặn mua SIM.
- **Quy trình chuẩn chuỗi chuyển tiếp (Transition Chain):**
  1. **OpenAI Landing Check:** Kiểm tra nếu có nút `Continue with Google` -> click để kích hoạt chuyển hướng sang Google SSO.
  2. **Google Account Selection:** Bắt selector `div[role="link"][data-identifier*="{email}"]` (fallback `div:has-text("{email}")` hoặc button), click chọn profile Gmail và bấm `Continue/Tiếp tục` nếu Google yêu cầu consent.
  3. **Wait for OAuth Session Transition:** Chờ redirect quay trở về domain `auth.openai.com` / `chatgpt.com`. Xác nhận trạng thái authenticated.
  4. **Canonical `add-phone` Resolution:** Chỉ khi đã authenticated vào OpenAI, nếu URL chưa tự động tới `https://auth.openai.com/add-phone` hoặc trang yêu cầu SMS, mới điều hướng tới canonical `https://auth.openai.com/add-phone`.
  5. **Phone DOM Gate Pre-check:** Chụp ảnh màn hình, kiểm tra `input[type="tel"]` và text yêu cầu SMS verification trước khi mở cổng gọi API 5SIM mua số. Không bao giờ mua số mù khi chưa qua verified DOM gate.
- **Success Criteria:**
  - Task chỉ được kết luận `SUCCESS` khi OmniRoute poll (`POST /api/oauth/codex/poll-callback`) trả về connection/id thực tế VÀ UI trình duyệt xác nhận OAuth hoàn tất.
  - Nếu chưa đạt, báo cáo `BLOCKED` kèm exact status, order state, và log/screenshot paths.

### 2.3. Quy tắc đồng bộ OmniRoute Combos & Proxy 1-1
- Khi tạo thành công Connection Codex qua OAuth callback:
  1. Gán Proxy 1-1 ngay lập tức qua API: `PUT /api/settings/proxies/assignments` (`{"scope": "account", "scopeId": cid, "proxyId": proxy_id}`).
  2. BẮT BUỘC nạp đồng bộ vào cả 4 combos Codex trên OmniRoute (:20129): `codex-terra-pool`, `codex-luna-pool`, `codex-terra`, `codex-luna`.

## 3. Kiến trúc API Đấu Kho Hàng SumiStore (`sumistore.me`)

### 3.1. Cấu trúc kết nối
- Base URL: `https://sumistore.me`
- Auth Header: `X-Tele-API-ID: <TAPI-...>` (lấy từ Bot Telegram của shop, không phải Telegram User ID dạng số).
- Endpoint đọc kho: `GET /api/tele-products`
- Endpoint chi tiết & tồn kho: `GET /api/tele-products/{product_id}`
- Endpoint số dư ví Telegram: `GET /api/tele-balance`
- Endpoint mua hàng (HMAC-SHA256): `POST /api/tele-product/buy`
  - Secret: `API ID`
  - Chuỗi ký: `timestamp|nonce|body`
  - Header: `X-Timestamp`, `X-Nonce`, `X-Signature`, `X-Idempotency-Key`, `Prefer: respond-async`

### 3.2. Phân định giữa Kho hàng Web API vs Bot Telegram
- **Web API kho hàng (`/api/tele-products`)**: Chỉ bán sản phẩm số có sẵn (tài khoản định dạng `mail|pass`, token, key API). KHÔNG có endpoint thuê số SIM OTP lẻ.
- **Sản phẩm tối ưu chi phí**: Shop bán tài khoản `CHAT GPT FREE ĐÃ VER PHONE CODEX` giá **4.000đ** (rẻ tương đương giá 1 SMS trên 5sim nhưng không cần chờ OTP, mua là có ngay account sạch đưa vào OmniRoute).
- **Thuê số trực tiếp**: Tích hợp riêng trong luồng chat Bot Telegram (Bee shop) dạng Mini-app/nút bấm (bán SIM ảo Mỹ 1.000đ, SIM vật lý Mỹ 7.000đ), không public qua REST API đấu kho.
