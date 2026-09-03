# YouTube bot-check + Camoufox cookies (2026-08-16)

Khi `download_by_niche.py` / `yt-dlp` trả "Sign in to confirm you're not a bot"
hoặc HTTP 403 rải rác khi tải video YouTube về `D:\video goc`.

## Chuỗi triệu chứng (đã gặp 1 session)

1. Lần đầu tải OK (folder 298: 65 video) → tải tiếp ~30 folder thì YouTube bắt đầu
   `ERROR: [youtube] <id>: Sign in to confirm you're not a bot`.
   → **IP máy Kibe bị YouTube đánh dấu** sau nhiều request yt-dlp liên tục.
   - Thậm chí video phổ biến (Rick Astley `dQw4w9WgXcQ`, Numb `kXYiU_JCYtU`) cũng bị chặn.
   - Test tay 1 video lẻ qua yt-dlp THƯỜNG vẫn OK (cookies tươi + 1 request) — đừng kết luận
     "hết lỗi" từ 1 test lẻ; chạy 1 folder nhỏ mới là phép thử thật.
2. Bật JS runtime: cài `deno` (pip) → yt-dlp `--js-runtimes deno:... --extractor-args
   "youtube:jsc=deno"` → vẫn `n challenge solving failed`. KHÔNG đủ — challenge solver
   builtin của yt-dlp không giải được nếu YouTube cần nhiều hơn.
3. `--cookies-from-browser chrome/edge` → `Could not copy Chrome cookie database`
   (Chromium App-Bound/DPAPI — yt-dlp issue #7271). Firefox đọc được nhưng profile kibe
   chưa từng login YouTube → không có cookie hữu ích.
4. Proxy di động (`PROXYgandienthoai.xlsx`) → giảm 403 nhưng KHÔNG hết ("other"/NA
   nhiều) vì YouTube chặn theo client-fingerprint (ugextractor đầu ra không chuẩn),
   không chỉ theo IP.

## Giải pháp ĐÃ CHẠY ĐƯỢC: Camoufox → export cookies → yt-dlp --cookies-file

Camoufox = Firefox patched chống bot-detect (fingerprint thật + uBlock Origin chống
định vị). YouTube tin tưởng nó như trình duyệt thật → trả cookies "sạch" mà yt-dlp
dùng được.

```bash
PY="D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe"
$PY -m pip install camoufox[geoip]      # ~vài chục MB
$PY -m camoufox fetch                   # tải browser binary + UBO addon (lần đầu)
```

Script export cookies (bản sync — KHÔNG bọc asyncio, playwright sync + asyncio lỗi
nhau: "Playwright Sync API inside the asyncio loop"):

```python
# D:\CodexRuntime\tiktok-video\test-camoufox-cookies-20260816.py
from pathlib import Path
from camoufox.sync_api import Camoufox

def netscape(cookies) -> str:
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        domain = c.get("domain", "")
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure") else "FALSE"
        expires = str(int(c.get("expires", 0) or 0))
        lines.append("\t".join([domain, flag, path, secure, expires, c.get("name",""), c.get("value","")]))
    return "\n".join(lines) + "\n"

with Camoufox(headless=True) as browser:
    page = browser.new_page()
    page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)   # chờ JS + cookies
    Path(r"D:\CodexRuntime\tiktok-video\youtube-cookies-netscape.txt").write_text(
        netscape(page.context.cookies()), encoding="utf-8")
```

Chạy download với cookies:
```bash
download_by_niche.py ... --continue-on-insufficient \
  --cookies-file "D:/CodexRuntime/tiktok-video/youtube-cookies-netscape.txt"
```
Kết quả thật 16/08: 4-33 MB video tải OK qua cookies, folder 301 (27 video), 305 (14).

**Cookies hết hạn nhanh (vài giờ).** Khi download quay lại "Sign in" → chạy LẠI script
export (refresh) rồi relaunch. Đừng chạy loop 24/7 với 1 cookies file.

## Proxy pool — format & pitfalls

File `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`, sheet `Proxy`, cột `proXy`
định dạng `host:port:user:pass` (vd `test.taadaa.click:5101:mobi1:admin@1`):

- URL yt-dlp phải là `http://user:pass@host:port` — **ĐẢO THỨ TỰ**. Sửa sai kiểu
  `http://host:port:user:pass` → `NameResolutionError host='1'` (yt-dlp parse user = `1`).
  `next_proxy()` trong download_by_niche.py đã xử lý: `parts = raw.split(":"); host,port,
  user = parts[0], parts[1], ":".join(parts[2:])` → `http://{user}@{host}:{port}`.
- Pass có chứa `@` — phần `user:pass` trong URL chính là `mobi1:admin@1@host` —
  split theo `:` (không phải `@`) mới đúng.
- KHÔNG phải proxy nào cũng active: 407 Proxy Authentication Required / connect timeout
  (mirotik1.taadaa.click:10001-10004 chết). Lọc trước khi xoay.
- **Test proxy bằng video local, không bằng video nước ngoài hot**: Rick Astley bị chặn
  trên proxy di động VN → "other"/NA sai lệch. Dùng `@vuadaubepvietnam/videos` (kênh VN)
  thì proxy OK.
- **407 khi chạy 8 worker song song** — proxy panel giới hạn kết nối đồng thời. Download
  `--parallel 1` (đã là chuẩn) → không dính.
- **CHỐT CUỐI 16/08 đêm: tăng worker ĐƯỢC nếu kèm `--proxy-pool`** — user: "tăng thêm
  worker dùng proxy khác trong pool proxy đc k" → chạy `--parallel 4 --proxy-pool <xlsx>
  --cookies-file`. `next_proxy()` xoay TOÀN CỤC (module-level counter) → mỗi thread dùng
  proxy khác IP → không spam cùng IP. KHÔNG tăng worker khi không có proxy xoay.

## Camoufox bắt media URL (browser_download.py) — đã thử, có pitfall SABR

`scripts/browser_download.py` (commit `810cf96`): mở video page bằng Camoufox, bắt
`response` chứa `googlevideo.com/videoplayback`, chọn URL `itag` không-audio, tải qua
`page.context.request.get(url)` (giữ cookies browser).

- Kết quả: URL bắt được là **SABR segment** → tải về 31 bytes
  `sabr.malformed_config` — không tải trực tiếp được (cần Range/segment protocol).
  → yt-dlp + cookies tươi vẫn là con đường đáng tin hơn; browser_download là fallback.
- `Browser` object KHÔNG có `.request` — dùng `page.context.request`.

## Lệnh test nhanh sau này

```bash
PY="D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe"
# 1. Test cookies có tươi/đủ không
$PY -m yt_dlp --cookies youtube-cookies-netscape.txt --skip-download \
  --print "ok %(title).40s" "https://www.youtube.com/watch?v=kXYiU_JCYtU"
#   "ok" → cookies OK; "Sign in..." → refresh cookies; "NA" → video chặn region (thử kênh VN)
# 2. Test proxy riêng lẻ (đừng 8 worker cùng lúc)
$PY -m yt_dlp --proxy "http://mobi5:admin@1@test.taadaa.click:5105" --skip-download \
  --print "ok" "https://www.youtube.com/@vuadaubepvietnam/videos"
```