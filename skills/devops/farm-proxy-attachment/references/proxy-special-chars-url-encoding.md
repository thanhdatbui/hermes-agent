# Proxy Special Characters & URL Encoding Standard for Downloader / CLI Tools

## Vấn đề
- Proxy pool di động định dạng `host:port:user:password` (ví dụ từ file `PROXYgandienthoai.xlsx`).
- Mật khẩu proxy thường chứa các ký tự đặc biệt như `#`, `@`, `!`, `:`, `%`.
- Khi ghép chuỗi thô thành `http://user:password@host:port`:
  - Ký tự `#` bị các thư viện HTTP / `yt-dlp` / `urllib` hiểu là **URL Fragment** cắt cụt mật khẩu $\rightarrow$ dính lỗi `407 Proxy Authentication Required` hoặc `Failed to parse proxy URL`.
  - Ký tự `@` gây tách sai thông tin userinfo / host.

## Giải pháp chuẩn hóa (Idempotent URL Encoding)
Trong các script Python xử lý proxy (như `download_by_niche.py`), bắt buộc chuẩn hóa qua hàm parse chuẩn:

```python
import urllib.parse

def format_proxy(raw: str) -> str:
    """Format xlsx host:port:user:pass or existing proxy URL into safe encoded http proxy URL."""
    raw = str(raw).strip()
    if not raw:
        return ""
    
    # Nếu đã là URL có scheme chuẩn
    if raw.startswith(("http://", "https://", "socks5://", "socks5h://")):
        parsed = urllib.parse.urlsplit(raw)
        if parsed.username or parsed.password:
            user = urllib.parse.quote(urllib.parse.unquote(parsed.username or ""), safe="")
            pwd = urllib.parse.quote(urllib.parse.unquote(parsed.password or ""), safe="")
            netloc = f"{user}:{pwd}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
        return raw

    # Format 4 phần từ Excel: host:port:user:pass
    parts = raw.split(":")
    if len(parts) >= 4:
        host, port = parts[0], parts[1]
        user = urllib.parse.quote(urllib.parse.unquote(parts[2]), safe="")
        pwd = urllib.parse.quote(urllib.parse.unquote(":".join(parts[3:])), safe="")
        return f"http://{user}:{pwd}@{host}:{port}"
    return f"http://{raw}"
```

## Lưu ý Reviewer & Bảo mật
- **Không hardcode credential thật vào docstring hoặc test case** để tránh vi phạm Security Gate khi commit/review.
- Dùng `unquote` trước khi `quote` để đảm bảo tính **Idempotent** (tránh bị double-encoding `%23` $\rightarrow$ `%2523`).
