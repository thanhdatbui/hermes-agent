# YouTube bot-check — Camoufox cookies recipe (16/08/2026, verified)

## Problem

`download_by_niche.py` (yt-dlp) tải YouTube gặp hàng loạt:

```
ERROR: [youtube] <id>: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies ...
```

Đây là bot-check theo **CLIENT** (yt-dlp thiếu browser fingerprint + không giải được JS challenge) — không phải theo IP. Bằng chứng: đổi proxy / retry không hết; IP máy Kibe bị blacklist sau nhiều request nhưng IP proxy di động sạch cũng dính trên video không phổ biến.

## Fix (duy nhất đã VERIFIED chạy thật)

**Camoufox** (Firefox patched chống bot-detect, fingerprint thật) mở YouTube → export cookies phiên → yt-dlp dùng `--cookies-file`.

### 1. Cài đặt (1 lần)

```bash
D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe -m pip install camoufox[geoip]
D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe -m camoufox fetch   # tải browser + UBO addon
```

Lưu ý: `python -m camoufox fetch` in rất nhiều dòng progress — chạy foreground với timeout 600, đừng hoảng.

### 2. Export cookies (mỗi vài giờ / khi download bắt đầu fail "Sign in" lại)

Script chuẩn (bản sync — KHÔNG bọc asyncio, Camoufox sync API fail trong asyncio loop với lỗi "Playwright Sync API inside the asyncio loop"):

```python
from pathlib import Path
from camoufox.sync_api import Camoufox

COOKIES = r"D:\CodexRuntime\tiktok-video\youtube-cookies-netscape.txt"

def netscape(cookies) -> str:
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        domain = c.get("domain", "")
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        lines.append("\t".join([domain, flag, c.get("path", "/"),
                                "TRUE" if c.get("secure") else "FALSE",
                                str(int(c.get("expires", 0) or 0)),
                                c.get("name", ""), c.get("value", "")]))
    return "\n".join(lines) + "\n"

def main() -> int:
    with Camoufox(headless=True) as browser:
        page = browser.new_page()
        page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)  # cho cookies + JS chạy
        print("title:", page.title(), flush=True)
        Path(COOKIES).write_text(netscape(page.context.cookies()), encoding="utf-8")
        print("wrote", COOKIES, flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

### 3. Dùng trong download

```bash
python scripts/download_by_niche.py ... --cookies-file D:/CodexRuntime/tiktok-video/youtube-cookies-netscape.txt
```

Flag `--cookies-file` thêm vào `download_by_niche.py` (commit `810cf96`): `yt_options()` → `options["cookies"] = str(args.cookies_file)`.

Verify 1 video đơn lẻ trước khi chạy batch:
```bash
python -m yt_dlp --cookies <file> --skip-download --print "ok %(title).40s" https://www.youtube.com/watch?v=<id>
```

## Kiểm chứng (16/08)

- Video Numb (trước đó "Sign in to confirm") → `ok Numb (Official Music Video)` với cookies Camoufox, IP máy Kibe, KHÔNG proxy.
- Channel flat-playlist (`@vuadaubepvietnam/videos`) → ra danh sách video id OK.
- Download batch thật: video 4.16MB + 746KB tải xong — chạy thật OK.
- Video Rick Astley (`dQw4w9WgXcQ`) vẫn "NA" — video cũ đặc biệt bị region/age-block, không phải bot-check (đừng dùng làm test).

## Cookies sống bao lâu

Vài giờ (session cookies YouTube). Download bắt đầu thấy "Sign in" trở lại → chạy lại bước 2, không cần đụng gì khác. Tự động hóa: wrapper loop gọi export cookies khi detect fail pattern.

## Dead-ends đã thử (đừng mất công lại)

| Cách | Kết quả |
|---|---|
| `pip install deno` + `--js-runtimes deno:<path>` + `--extractor-args youtube:jsc=deno` | "n challenge solving failed" — thiếu solver script đầy đủ (yt-dlp có `yt.solver.deno.lib.js` builtin nhưng không đủ) |
| `--cookies-from-browser chrome/edge` | "Could not copy Chrome cookie database" — Chromium App-Bound/DPAPI (yt-dlp issue #7271) |
| `--cookies-from-browser firefox` | Đọc được nhưng profile không có YouTube cookies (chưa đăng nhập) |
| Camoufox bắt googlevideo URL → tải qua requests/ffmpeg | `sabr.malformed_config` — URL là SABR segment cần Range headers đặc biệt; `scripts/browser_download.py` đã viết nhưng dead end, đường ăn chắc = cookies → yt-dlp |

## Proxy pool (nếu dùng kèm — user xác nhận dùng được cho download YouTube)

- File: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (76 proxy, cột 'proXy').
- **Format:** xlsx ghi `host:port:user:pass` (vd `test.taadaa.click:5101:mobi1:admin@1`) → URL yt-dlp phải là `http://user:pass@host:port` = `http://mobi1:admin@1@test.taadaa.click:5101`. Prefix `http://` thẳng vào raw → "Failed to resolve '1'". `next_proxy()` trong `download_by_niche.py` (flag `--proxy-pool`) xử lý format này — split(":") 4 phần rồi ghép lại.
- **Test proxy PHẢI đơn lẻ** — panel MobiProxy giới hạn kết nối đồng thời, test 8 worker song song trả 407 auth giả dù proxy sống (user chụp dashboard status xanh để chứng minh).
- **Test video phải là video/channel VN** — video nước ngoài phổ biến bị chặn với IP di động VN → "other"/NA sai lệch. Dùng `@vuadaubepvietnam` hoặc kênh VN tương tự.
