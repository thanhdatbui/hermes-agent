# Recon khommo247 Check TikTok (2026-08-20)

Mục tiêu: kiểm tra xem `https://khommo247.com/cong-cu/check-tiktok` có dùng làm nguồn check live TikTok tự động (cron) được không.

## Kết luận

**KHÔNG dùng được tự động nếu không có tài khoản khommo247.** 2 lớp chặn:
1. Cloudflare Managed Challenge — qua được với Camoufox headful (không cần tick).
2. Login wall backend — bấm Check vẫn đòi đăng nhập kể cả sau khi đóng modal "Để sau" → cần session đăng nhập thật.

## Thử nghiệm chi tiết

### Lớp 1 — Cloudflare
| Phương án | Kết quả |
|---|---|
| curl (local + VPS) | 403 / body rỗng hoặc chỉ challenge script |
| Browserbase browser_navigate | Kẹt "Thực hiện xác minh bảo mật", checkbox tick không qua (Ray ID đổi = CF chặn) |
| Playwright headless (Chrome channel) IP nhà | Kẹt "Just a moment..." |
| Playwright headful (cửa sổ thật) IP nhà | Vẫn kẹt "Just a moment..." (tự động hóa bị phát hiện qua CDP fingerprint) |
| **Camoufox headless** (`venv-core024`) | Kẹt "Just a moment..." |
| **Camoufox headful** (`venv-core024`) | ✅ **Qua CF sau ~8s, vào thẳng tool page** (title "Check TikTok Hàng Loạt - Kiểm Tra Tài Khoản Live/Die") |

Camoufox: `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe` (đã có `camoufox` cài sẵn; các venv khác trong tiktok-video: `venv`, `venv-live-0.2.25` KHÔNG có).
```python
from camoufox.sync_api import Camoufox
with Camoufox(headless=False) as browser:  # headless=True bị CF chặn!
    page = browser.new_page()
    page.goto("https://khommo247.com/cong-cu/check-tiktok", wait_until="domcontentloaded", timeout=60000)
    # chờ tới khi title rời khỏi "Just a moment"/"Chờ một chút"/"Loading"
```

### Cấu trúc trang (multi-tool)
- Một trang URL chứa NHIỀU tool (2FA/TOTP, Read Mail Hotmail, Check Gmail, Check X Profile, Check TikTok, Check Proxy, Xử lý văn bản...) — 37 textarea, 84 button trên 1 DOM; chỉ tool active visible.
- Tool Check TikTok:
  - textarea `#ttList` — placeholder mẫu `quyhng2407` (username; hỗ trợ `@user` và `https://tiktok.com/@user`, tối đa 1000+).
  - button `#ttBtnStart` — text "Check tất cả" (+ "Xuất TXT", "Xoá").
- ⚠️ textarea đầu tiên (`#telegramOtpProxy`) thuộc tool Telegram OTP, ẩn nhưng vẫn match `page.fill("textarea")` → luôn dùng `#ttList`.

### Lớp 2 — Login wall
- Bấm `#ttBtnStart` → modal `.tool-login-gate` xuất hiện: "Yêu cầu đăng nhập — Bạn cần đăng nhập để sử dụng công cụ này. Sau khi đăng nhập, hệ thống sẽ đưa bạn trở lại đúng trang công cụ." Modal chỉ có nút "Để sau".
- Click "Để sau": modal biến mất (selector `.tool-login-gate` = false), nhưng bấm `#ttBtnStart` lần nữa → KHÔNG có kết quả: `#ttList` giữ nguyên giá trị nhập, body chỉ reload, không có Live/Die. → xác nhận backend require session.

## Các nguồn check TikTok khác đã thử (đều fail/thấp, chỉ để tham khảo)
- TikTok oEmbed (`https://www.tiktok.com/oembed?url=...`): 200 + author_name cho acc công khai (LIVE), nhưng 400 "Something went wrong" cho CẢ acc die lẫn acc farm còn sống → không phân biệt được DIE. Rate-limit nhanh qua browser fetch.
- tikwm.com API: 403 Forbidden.
- `www.tiktok.com/api/user/detail/?uniqueId=...` (i18n): HTTP 200 body rỗng.
- `tiktok.com/@user` với header đầy đủ từ VPS = nguồn chính đang dùng (xem `tiktok-direct-vps-checklive-2026-08.md`).

## Việc cần làm nếu user muốn dùng khommo247

**CẬP NHẬT 2026-08-20 — đã giải quyết xong, KHÔNG cần bước DOM dưới đây:** Tool là UI bọc API HTTP đơn giản `POST /api/tiktok_check.php` body `{"username":...}` — chỉ cần 1 phiên Camoufox refresh cookies (`KHOMMO247SESSID_V2` + `cf_clearance`), rồi gọi API thẳng hàng loạt qua cùng proxy. Chi tiết + script mẫu + policy retry/quirk: `khommo247-tiktok-check-api-2026-08.md`.

(Kế hoạch DOM cũ, giữ tham khảo:)
1. User đăng ký tài khoản khommo247 (free, nút "Đăng ký" trên header) → cung cấp credentials (hoặc tự login 1 lần). ✓ Đã có: `thanhdatbui19951@gmail.com` đã đăng nhập trong profile persistent `%LOCALAPPDATA%\hermes\scripts\khommo_profile`.
2. Camoufox headful: login → đợi session cookie (cf_clearance + session) → fill `#ttList` → click `#ttBtnStart` → đọc kết quả từ DOM.
3. Cookie session khommo247 có thời hạn; cron daily cần refresh login định kỳ (bước này giờ chỉ để refresh cookies cho API call).