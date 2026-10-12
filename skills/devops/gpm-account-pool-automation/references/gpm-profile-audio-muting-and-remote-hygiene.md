# GPM Profile Audio Muting & Remote Desktop Hygiene

## 1. Problem
Khi chạy các kịch bản nuôi tài khoản tự động (Gmail nurture, YouTube, TikTok browsing...) trên GPMLogin qua máy trạm/server (như máy Kibe), việc remote vào máy (qua RDP, UltraViewer, AnyDesk, RustDesk) thường bị làm phiền bởi âm thanh video phát ồn ào và tốn tài nguyên giải mã audio vô ích.

## 2. Solutions

### A. Cờ Chromium `--mute-audio` qua GPMLogin API (Khuyên dùng trong automation)
GPMLogin v3 API hỗ trợ tham số `addition_args` khi khởi động profile:
- Endpoint: `GET /api/v3/profiles/start/{profile_id}?addition_args=--mute-audio`
- Hoặc kết hợp với các query param khác:
  `http://127.0.0.1:{port}/api/v3/profiles/start/{profile_id}?win_scale=0.8&addition_args=--mute-audio`
- Tác dụng: Toàn bộ các tab trong phiên trình duyệt Chromium đó đều bị câm âm thanh 100%, không phát ra tiếng và tiết kiệm CPU.

### B. Cấu hình trực tiếp trên GPMLogin GUI (Cho profile thủ công)
- Vào profile -> **Edit Profile** -> mục **Additional arguments** -> điền `--mute-audio`.
- Hoặc trong profile Chrome -> truy cập `chrome://settings/content/sound` -> chọn **Don't allow sites to play sound**.

### C. Cách ly âm thanh phía Remote (Triệt để cho người điều khiển)
- **Windows Remote Desktop (RDP / mstsc):**
  Options -> Local Resources -> Remote audio Settings -> Chọn **Do not play**.
- **UltraViewer / TeamViewer / AnyDesk / RustDesk:**
  Thanh điều khiển remote -> biểu tượng Loa / Sound -> Chọn **Mute audio transmission**.
- **Host Windows Master Volume:**
  Mute trực tiếp Master Volume của máy trạm farm/worker trên Taskbar Windows vì máy trạm chạy bot không cần xuất âm thanh ra loa.
