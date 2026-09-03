# Check-live sources chi tiết (session 2026-08-20, doravo.net)

## 1. TikTok — VPS direct check (GIẢI PHÁP CHÍNH, ~98% phủ)

Cách hoạt động: GET `https://www.tiktok.com/@<user>?lang=en` (header Chrome đầy đủ: UA, Sec-Fetch-*, Accept-Language en), parse `__UNIVERSAL_DATA_FOR_REHYDRATION__` script JSON:
- `__DEFAULT_SCOPE__.webapp.user-detail.statusCode == 0` + `userInfo` → **LIVE**
- `statusCode == 10221` → **DIE** (banned / không tồn tại)
- thiếu tag / len 12579 hoặc 1462 → **WAF block** → retry

Kết quả thực tế (385 acc, VPS IP 152.42.187.200):
- retry 4: 6 LIVE / 274 DIE / 105 UNKNOWN
- retry 8: +7 LIVE / +84 DIE / 20 UNKNOWN
- retry 12: +11 DIE / 9 UNKNOWN cuối
→ **2 vòng (8 rồi 12) cho UNKNOWN** để ép qua WAF. ~3-5s/acc.

Khác biệt môi trường:
- VPS (SGP DO): parse được đa số, TikTok trả JSON thật.
- GH Actions runner (datacenter US): 77% UNKNOWN — không dùng làm nguồn chính.
- request thuần python trên máy nhà (27.69.x): trả HTML nhưng pidName check cũ thường fail — dùng VPS.

## 2. GitHub Actions (`thanhdatbui/tiktok_check_live`) — FIX 401 artifact

Workflow: trigger `workflow_dispatch` với request_id (repo key trong DB settings: `tiktok_checklive_github_owner/repo/token`). Kết quả là artifact zip chứa `checklive-result.json`:
```json
[{"username": "sonaairhrk395682", "status": "UNKNOWN"}, ...]
```
Status: LIVE / DIE / UNKNOWN. Download artifact bị 401 vì 302 redirect drop Authorization; fix:
```python
class _NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        newreq = super().redirect_request(req, fp, code, msg, headers, newurl)
        if newreq is not None:
            newreq.headers = {k: v for k, v in req.headers.items() if k.lower() not in ("authorization",)}
        return newreq
opener = urllib.request.build_opener(_NoAuthRedirect)
```
Poll run: `GET /repos/{o}/{r}/actions/runs?per_page=10` lấy run mới nhất (có thể đụng run cũ — match theo request_id trong name artifact + created_at). **487 acc ~35 phút** → timeout poll 60 phút.

## 3. clonefbig.com/checklive (Instagram) — Playwright headful local

- CF Turnstile tự tick được (IP dân cư nhà), không cần giải manual. Token đọc từ `input[name="cf-turnstile-response"]`.
- Fill `#inputArea` (1 username/dòng) → `page.evaluate("startCheck()")` → đọc `#liveCount`/`#dieCount` + textarea `#liveOutput`/`#dieOutput`.
- Batch ≤500 để tránh timeout; mở headful (headless bị CF từ chối lâu hơn).
- Kết quả mẫu: 1.435 acc → 1.148 LIVE / 287 DIE (đã dọn, backup pre-tt-clean-die).

## 4. khommo247.com/cong-cu/check-tiktok — BỊ CHẶN ĐĂNG NHẬP

- CF: chỉ qua với **IP dân cư thật + browser có fingerprint** (Camoufox headful OK ở máy nhà). 
  - IP datacenter (VPS) hoặc proxy mobile farm → "Just a moment..." kể cả Camoufox headful.
- Selectors: textarea `#ttList` (mỗi dòng 1 username, hỗ trợ @user / link), button `#ttBtnStart` ("Check tất cả").
- **Login gate**: bấm check → modal `.tool-login-gate` "Yêu cầu đăng nhập". "Để sau" chỉ đóng UI — bấm check lại vẫn rỗng kết quả. Phải login thật: `/dang-nhap?return=%2Fcong-cu%2Fcheck-tiktok`, form `loginEmail` + `loginPass` (CSRF `_csrf` hidden).
- Nút "Check tất cả" query tool API — tài khoản free được dùng tool (chưa verify payload, cần đăng nhập session trước).
- Camoufox multi-tool page: textarea ẩn của tool khác có `id` riêng (vd `telegramOtpProxy`) — chỉ tool active mới visible; đừng fill textarea đầu tiên.

## 5. Camoufox (anti-detect Firefox, venv-core024 local / venv VPS)

- Cài: `pip install "camoufox[geoip]"` + `python -m camoufox fetch`; venv có sẵn: `D:/CodexRuntime/tiktok-video/venv-core024` (local), `/opt/camoufox-venv` (VPS 152.42.187.200, Ubuntu 22.04, cần `xvfb-run -a`).
- Trên VPS: `apt-get install xvfb` + `python3.10-venv` (thiếu ensurepip nếu chỉ có python3-venv).
- **Proxy bắt buộc dạng dict**: `Camoufox(headless=False, proxy={"server": "http://host:port", "username": "mobi1", "password": "TaadaaMobi#2026!"})`.
  - Nhét creds vào server URL (kể cả URL-encode) → `NS_ERROR_PROXY_CONNECTION_REFUSED` dù curl OK.
  - Pass chứa `#` phải URL-encode nếu ghép URL (`%23`).
- Headless → dễ bị CF chặn; headful (hoặc headful + Xvfb trên Linux) → qua được với IP tốt.

## 6. Gmail Check-Live Status & Architecture

- **Web tool `checkmail.live` (Đã kiểm chứng & hoạt động tốt 2026-08-31):**
  - **Cơ chế:** Web UI dùng CodeMirror editor (`editor.setValue(...)`) và hàm `CheckEmail()` gọi endpoint `./check/`.
  - **Yêu cầu phiên/Login:** Tài khoản Free bắt buộc phải đăng nhập trên Web UI mới có `api_key` (`$('#api-key').val()`) để chạy hàm `CheckEmail()`. Nếu gọi API trực tiếp không qua Web UI sẽ bị báo `"Free accounts do not have permission to execute"`.
  - **Vượt Cloudflare Turnstile:** Khi đăng ký/đăng nhập qua Chrome Headful CDP (port 9222, IP nhà), Cloudflare Turnstile tự tick giải mã token (`cf-turnstile-response` ~730 chars) sau 1 giây.
  - **Tốc độ & Độ chính xác:** ~1 - 2 giây cho một batch danh sách email; phân loại chuẩn xác `[Live]` vs `[die]` (đã test thực tế phân loại đúng cả mail die trong kho và mail ảo không tồn tại).
  - **Pitfall trích xuất định dạng mail thô (Raw email prefix parsing):** Một số nguồn mail (như `accphu.txt`, `accchinh.txt` của Rua) lưu theo định dạng `mail: username|pass` hoặc `mail: username` mà không có đuôi `@gmail.com`. Nếu chỉ dùng regex `\S+@gmail\.com` sẽ bị sót các tài khoản này (ví dụ `thanhdatbui1995uk`, `thanhdatbui1995ua`...). Cần parse prefix `mail:\s*([^\|\s]+)` và tự động thêm `@gmail.com` nếu chuỗi chưa có domain trước khi đưa vào checklive.
- **Web shop (`SHOPCLONE7` / doravo.net):**
  - Tồn tại script `cron/checklive/gmail.php` thiết kế để gửi danh sách email sang 3rd-party API qua `api_check_live_gmail` và `api_key_check_live_gmail` trong `settings`.
  - Hiện tại các trường API này đang để TRỐNG (chưa tích hợp dịch vụ web bên ngoài).
  - Trang admin `check-live-gmail.php` từng deploy ngày 2026-07-11 nhưng đã được rollback do chưa có endpoint check live web ổn định. Các SP Gmail (SP 48, 49, 50, 61) trên DB đều đang để `check_live = 'None'`.
- **Farm Android (`D:\Taadaa`):**
  - Không check qua web mà check trực tiếp trên máy thật qua `automation_core.google_health` (`run_google_live_check`).
  - Phân loại trực tiếp trên app Gmail / Settings Google: `LIVE`, `CAPTCHA / IDENTITY_BLOCKER` (die), `RELOGIN` (văng phiên), `PHONE_VERIFY` (manual).