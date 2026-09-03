# Hermes Browser CDP Connect (dùng profile Chrome thật để qua CF)

Ghi nhận 2026-08-20: khi browser Hermes của session khác đang giữ `browser_profile` (Chrome với
`--remote-debugging-port=9222`), ta có thể **connect CDP vào mà không cần đợi session kia nhả profile** —
và profile thật (IP nhà + cf_clearance/cookies) qua Cloudflare NGAY, khác hẳn Browserbase (IP datacenter).

## Khi nào dùng

- User nói "dùng browser hermes tạo bên session khác (điều khiển qua plugin browser)" / "session kia chưa nhả à".
- Cần tận dụng cookies/cf_clearance/session login của profile Chrome Hermes mà không thể đọc Cookies DB
  (browser đang chạy → `Cookies` file bị khóa: `Device or resource busy` / PowerShell `IOException` — đừng cố copy).

## Cách tìm Chrome đang chạy

```bash
# Tìm process Chrome có --remote-debugging-port (git-bash đừng dùng $_ lồng trong PS string)
powershell -Command "Get-CimInstance Win32_Process -Filter \"Name like '%chrome%'\" | Where-Object { \$_.CommandLine -match 'remote-debugging' } | ForEach-Object { Write-Output \"PID: \$(\$_.ProcessId)\"; Write-Output \$_.CommandLine.Substring(0, 300) }"
```

Thấy `--user-data-dir="C:\Users\Kibe\AppData\Local\hermes\browser_profile" --remote-debugging-port=9222`
→ connect CDP vào 9222.

## Verify endpoint

```bash
curl -s http://127.0.0.1:9222/json/version      # trả Browser/Protocol-version/UA
curl -s http://127.0.0.1:9222/json/list          # list tab đang mở (có thể thấy session khác đang xem gì)
```

## Connect + mở tab mới (Playwright sync, dùng chung cookies/profile)

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    page = browser.new_page()          # tab MỚI, cùng profile/cookies
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    # chờ CF tự qua (title rời khỏi "Chờ một chút"/"Just a moment"/"Loading")
```

**Lưu ý khi connect CDP:** đây là browser của session khác — tạo tab mới + `page.close()` khi xong,
không đóng browser, không thay đổi state profile bất kỳ ngoài phạm vi.

## Kết quả thực tế khommo247 (2026-08-20)

- CDP profile thật: qua CF ngay (title = "Check TikTok Hàng Loạt"), `#ttList`/`#ttBtnStart` có.
- NHƯNG login gate `.tool-login-gate` VẪN bật mỗi lần bấm check — CF qua không giải quyết được
  login wall backend. Kết luận: khommo247 bắt buộc tài khoản đăng nhập thật.

## Pitfall

- Đừng cố copy `Cookies` DB khi browser đang chạy — bị khóa; nếu chỉ cần session thì CDP là đường đúng.
- `browser.contexts` khi connect CDP = 1 context (mặc định); `browser.new_page()` tạo tab trong context đó.
- Port có thể khác 9222 nếu session kia cấu hình khác — luôn grep commandline trước.