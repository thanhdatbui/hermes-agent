# ChatGPT Batch Canary Triage + OmniRoute Inventory (2026-09-13)

## Khi nào dùng
- Batch login ChatGPT cho GPM profiles có Google account rồi OAuth vào OmniRoute `:20129`.
- BẮT BUỘC triage tồn kho trước khi chạy bulk, rồi chạy canary 3-5 accs LIVE nghiệm thu.

## 1. Triage tồn kho (GPM x Master x OmniRoute)
1. GPM API v3 phân trang: `GET /api/v3/profiles?page={n}&per_page=50` tới `pagination.total_page`, gom `data[]`.
2. Trích email: regex `([a-zA-Z0-9_.+-]+@gmail\.com)` trên `name`, dedup theo email lowercase (1 profile trùng có nhiều bản copy).
3. Đối chiếu `master_gmail_manager.xlsx` sheet `Master_All`: chỉ ưu tiên `Trạng Thái == LIVE`.
4. Đối chiếu OmniRoute: `GET http://127.0.0.1:20129/api/providers` → `connections[]`, lọc `provider == chatgpt-web/codex` + `testStatus == active`, lấy prefix email từ `name.split(' ')[0]`.
5. `unregistered = GPM_unique - OmniRoute_active` → danh sách chạy. Thực tế: 101 profiles → 84 Gmail unique → 81 chưa có ChatGPT/Codex.

## 2. Endpoint OmniRoute đúng (pitfall)
- SAI: `GET /api/connections` → `unknown_route`.
- ĐÚNG: `GET http://127.0.0.1:20129/api/providers` → `{connections: [{id, provider, name, authType, testStatus, isActive}]}`.
- Codex import: `POST /api/oauth/codex/import-token` với `{accessToken, name}`; body `{test:true}` trả 400 là bình thường (endpoint sống).
- AccessToken lấy từ `https://chatgpt.com/api/auth/session` (<pre> JSON, phải `startswith('ey')`, `len>50`).
- ChatGPT-web lấy cookie `__Secure-next-auth.session-token` (gộp chunk `.0/.1` nếu cần), sync theo `src/chatgpt_omniroute_hook.py` — không đoán endpoint.

## 3. Kỷ luật canary-first
- Trước bulk 60-97 accs, hỏi user scale: `canary 3-5 LIVE` vs `batch 10` vs `full`.
- Canary mẫu tốt: 1 acc/proxy khác nhau (VD 5105/5113/5133), đều LIVE trong Master.
- Dispatch worker Scope Lock tuyệt đối: đúng 3 profile_id, sequential (callback server Codex port `1455` single-thread — cấm song song), `finally: GET /profiles/stop/{id} + sleep 2s`.
- Onboarding ChatGPT: name từ prefix email, age 25, click Tiếp tục/Continue; check main chat (`Hôm nay bạn muốn làm gì`/`Đoạn chat mới`/`New chat` hoặc `#prompt-textarea`).
- Fail-fast: `account_deactivated`/đòi password ngoài scope/proxy timeout → ABORT acc đó, stop profile, báo anchor, cấm đốt budget mò file.
- Nghiệm thu: `debug_screenshots/chatgpt_<email>_verified.png` + bảng `email | login | codex conn_id | chatgpt-web | screenshot`.

## 4. Python toolchain
- Chạy bằng `python` (3.11 hệ thống), cấm `python3` (lỗi `greenlet._greenlet` khi import Playwright).
- CDP: `connect_over_cdp` + retry 5 lần + `sleep 2.5s`, lọc bỏ `chrome-extension://` pages.
