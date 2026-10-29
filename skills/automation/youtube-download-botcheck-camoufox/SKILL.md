---

name: youtube-download-botcheck-camoufox

description: Fix yt-dlp bị YouTube bot-check ("Sign in to confirm you're not a bot" / HTTP 403 / NA) khi tải video — dùng Camoufox lấy cookies phiên thật. Áp dụng cho download_by_niche.py (Tiktok-video farm) và mọi tải YouTube.

---
# YouTube download qua bot-check (Camoufox cookies)


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

## Trigger

yt-dlp trả "Sign in to confirm you're not a bot", HTTP 403 rải rác, hoặc "NA" khi probe/tải YouTube.



## Root cause

YouTube chặn theo dấu hiệu **CLIENT** (thiếu browser fingerprint thật + không giải được JS challenge), không chỉ IP. Proxy di động đổi IP KHÔNG hết; chỉ cookies phiên / browser thật mới qua được.



## Fix: Camoufox cookies (đã kiểm chứng 17/08/2026)

1. Cài: `python -m pip install "camoufox[geoip]"` + `python -m camoufox fetch` (venv-core024 đã có sẵn)

2. Mở `https://www.youtube.com` headless bằng Camoufox (script mẫu: `D:\CodexRuntime\tiktok-video\test-camoufox-cookies-20260816.py`) → export cookies Netscape → `youtube-cookies-netscape.txt`

3. yt-dlp chạy với `--cookies-file <file>` → qua bot-check (test: video Numb OK, channel flat OK)

4. **Cookies hết hạn ~vài giờ** → refresh lại bằng Camoufox khi download bắt đầu "Sign in" trở lại

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
