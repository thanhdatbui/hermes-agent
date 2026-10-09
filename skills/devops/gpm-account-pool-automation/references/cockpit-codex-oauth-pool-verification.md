# Cockpit Codex OAuth pool verification

Use this reference when importing OpenAI/Codex accounts from GPM into Cockpit Tools.

## State model

Keep these counts separate:

- candidate roster from farm/GPM/OmniRoute
- OAuth attempts
- successful Cockpit imports
- `codex_accounts.json` entries
- sidecar `manifest.json` members
- API-routable members

A candidate, a decrypted token, or an OmniRoute database row is not a Cockpit import.

## Safe sequence

1. Select one target email and its intended GPM profile/proxy.
2. In Cockpit, open "Add Account" -> "OAuth Authorization" (Browser auth) to start the single-flight callback listener (`localhost:1455`) and get the fresh authorization link.
3. Start the matching GPM profile via GPM Local API (`/api/v3/profiles/start/{id}`). GPM profiles retain live ChatGPT web sessions.
4. Navigate GPM browser to the Cockpit authorization URL -> ChatGPT automatically detects active session -> Click account / "Tiếp tục" / consent.
5. Capture callback hit to `http://localhost:1455/auth/callback?code=...&state=...` and verify Cockpit accepts it.
6. Close the GPM profile.
7. CRITICAL COCKPIT STEP: On the new account card in Cockpit, click "Add to API Service" so the account joins the Instance Gateways / Local API pool.
8. Bind/verify the isolated per-account egress proxy node in Cockpit.
9. Fresh-read Cockpit account store and sidecar manifest; verify email, count, and proxy binding.
10. Call `/v1/models` and one minimal chat completion through the shared API key (`agt_codex_...`).
11. Only after evidence passes, proceed to the next account.

## Anti-patterns & User Pitfalls

- CẤM TỰ Ý TRÍCH XUẤT TOKEN TỪ OMNIROUTE SQLITE: Khi User yêu cầu OAuth vào Cockpit bằng GPM, tuyệt đối KHÔNG mò vào `storage.sqlite` của OmniRoute để giải mã hay test refresh token cũ. Token cũ trong database thường đã hết hạn (`token_expired` 401). Flow chuẩn là mở GPM profile (đã có session ChatGPT) để OAuth mới trực tiếp.
- CẤM NẠP SONG SONG NHIỀU ACC: Cockpit chỉ lắng nghe 1 callback listener (`localhost:1455`) với 1 state duy nhất tại một thời điểm. Mở nhiều OAuth cùng lúc sẽ gây đè state, lỗi `state_mismatch` hoặc nạp nhầm token chéo giữa các account. BẮT BUỘC tuần tự 1:1.
- MỘT POOL KHÔNG PHẢI MỘT IP: Cockpit cung cấp 1 API Key chung cho Hermes gọi vào Local API (`http://127.0.0.1:60818/v1`), nhưng phía OpenAI mỗi account BẮT BUỘC đi qua node proxy riêng (M1 -> 5101, M2 -> 5102...). Tuyệt đối không để chung IP kẻo ban chùm.
- QUÊN BẤM "ADD TO API SERVICE": Tài khoản OAuth thành công mới chỉ nằm ở danh sách account, CHƯA vào pool API. Phải bấm "Add to API Service" trên card của account đó thì sidecar manifest mới cập nhật `accountIds` và route được request.
- COCKPIT MINIMIZE GÂY CHẾT LISTENER 1455 ([WinError 10061]): Khi cửa sổ Cockpit Tools bị thu nhỏ (minimize) hoặc trôi tọa độ ngoài màn hình (-31976), tiến trình nội bộ có thể đóng hoặc từ chối kết nối cổng `1455`. Phải Restore cửa sổ hoặc restart Cockpit nếu `netstat -ano | grep 1455` không thấy LISTENING.
- COCKPIT RESTART VỀ TAB DEFAULT TẮT LISTENER: Khi Cockpit Tools restart, app mặc định mở tab Antigravity/Dashboard, KHÔNG tự giữ listener 1455. BẮT BUỘC điều hướng lại tab Codex -> bấm "Add Account" -> "OAuth Authorization" để kích hoạt lại listener 1455 trước khi Playwright gửi callback.
- QUÉT PROFILE GPM BẰNG COOKIE TRỰC TIẾP (O(1)): Đừng mở từng profile bằng Playwright rồi điều hướng https://chatgpt.com (rất chậm và dễ timeout 55s). Thay vào đó, đọc thẳng file SQLite `Default\Network\Cookies` của từng profile folder (copy ra file tạm để tránh lock): tìm domain `chatgpt.com` có cookie `__Secure-next-auth.session-token` hoặc `session-manifest` để lọc ngay các profile đang có session sống chỉ trong <1s.
- CẤM IM LẶNG KHI TOOL/SUBPROCESS TIMEOUT: Khi bất kỳ script OAuth hay Playwright CDP bị timeout (>45s-55s), BẮT BUỘC báo cáo ngay lập tức cho User với error log cụ thể và nguyên nhân. TUYỆT ĐỐI CẤM im lặng chờ đợi nhiều giờ làm đóng băng phiên.
- PRE-SCREEN SESSION SỐNG TRƯỚC KHI OAUTH: Không duyệt mò các profile GPM chưa rõ trạng thái đăng nhập. Dùng script Playwright/CDP đọc nhanh cookie của profile: nếu có `unified_session_manifest` hoặc `__Secure-next-auth.session-token` thì mới tiến hành lấy link OAuth, tránh làm timeout vòng xoay Cockpit.
- KHÔNG DỪNG ĐỨNG PHIÊN KHI 1 ACC LỖI: Khi 1 account dính `Authentication timed out` hoặc callback timeout, đánh dấu account đó cần reauth, đóng profile GPM cũ, refresh lại Auth Link mới trên Cockpit và chuyển sang nick sống kế tiếp trong danh sách thay vì dừng toàn bộ tiến trình.

Cockpit's OAuth callback listener/state is single-flight (commonly `localhost:1455`), so OAuth submissions to one Cockpit instance must be serialized. GPM profiles may be open concurrently for unrelated work, but do not run multiple Cockpit OAuth transactions concurrently.

## Pool and IP semantics

One shared Cockpit API key is an ingress credential. It does not prove that accounts share an upstream IP, nor does it prove that every account has been imported. Each account must have an independently verified proxy/node binding. Never report a 10-account pool from a candidate list; report `N/10` from fresh Cockpit/manifest state only.

## Failure classification

- `401 token_revoked` or `token_expired`: stale credential; preserve the account and perform a new OAuth authorization. Do not treat a decrypted refresh token as live.
- `PROXY_ENGINE_TIMEOUT`: stop the affected account flow, repair/restart the proxy engine, then retry with a fresh OAuth state.
- Old callback/state: discard it and generate a new authorization transaction.

Do not synthesize Cockpit account/manifest files to bypass native import. Do not run a hidden multi-account batch loop. Capture UI evidence before and after each mutation; isolate failed accounts and reconcile state before proceeding.
