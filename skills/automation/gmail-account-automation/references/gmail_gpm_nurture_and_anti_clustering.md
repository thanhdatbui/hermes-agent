# Gmail Nurturing & Identity Warming Architecture (GPM Chromium PC)

## 1. Bản Chất Rủi Ro Khi Nuôi Tài Khoản Google (Google Risk Engine)
- **2FA TOTP $\neq$ Trust Score cao:** 2FA chỉ giảm nguy cơ bị đánh cắp mật khẩu (Account Takeover), nhưng KHÔNG chứng minh tài khoản là con người thật. Tuy nhiên, 2FA TOTP là **LÁ CHẮN THOÁT HIỂM (Verification Fallback)** bắt buộc: khi đổi thiết bị/IP từ S7 sang GPM PC, có TOTP sẽ giúp vượt qua bước xác minh mà không bị ép vào màn hình SMS số điện thoại (`challenge/iap`).
- **Phân định rạch ròi 2 phân khúc hệ thống của Google:**
  1. **Consumer Ecosystem (YouTube, Search, News, Gmail):** Hệ thống chấm điểm hành vi người dùng cuối (End-User). Điểm trust ở đây giúp tài khoản bền bỉ, chống bị quét DIE theo cụm định kỳ.
  2. **Developer API (Google Cloud / Code Assist / Antigravity):** Hệ thống giám sát lạm dụng hạ tầng (Cloud Abuse Detection).
     - **CẤM TUYỆT ĐỐI** dùng script gọi API Gemini/Antigravity để "nuôi tài khoản" vì hành vi này sẽ kích hoạt cờ quét lạm dụng API tự động (API Quota Abuse).
     - **CẤM TUYỆT ĐỐI** cấp quyền OAuth Antigravity (Google Cloud API) ngay trong phiên đầu tiên vừa đăng nhập GPM. Phải ngâm profile GPM $\ge 7\text{ ngày}$ có sinh hoạt tự nhiên rồi mới cấp quyền Antigravity.

---

## 2. Các Trụ Cột Nuôi Dưỡng Chuẩn (Consumer Footprint)
1. **YouTube Thường (1.5 – 2 phút):**
   - **Mốc vàng 60–120s:** Tạo gói tin heartbeat `/api/stats/watchtime`, nạp cookie Google AdSense/AdMob, lưu lịch sử xem `Watch History` trên `MyActivity`.
   - **Hạn chế Shorts:** Lướt Shorts cơ học liên tục với tỷ lệ hoàn thành 100% video ngắn là chữ ký điển hình của bot cày view.
2. **Google News (`news.google.com`):**
   - Lướt điểm tin 15–20s và click đọc 1 bài báo (đọc 30–45s).
   - Tích hợp sâu cookie `GAPS` và `NID`, định danh người dùng đọc tin tức thời sự gắn liền vị trí địa lý Việt Nam.
3. **Google Search (`google.com/search`):**
   - Tìm kiếm ngẫu nhiên từ khóa đời sống (thời tiết, công nghệ, bóng đá, ẩm thực) và dừng lại xem kết quả 10–15s.

---

## 3. Kiến Trúc Nuôi Cho Trạm Dual Xeon (Chống Gom Cụm Farm)
- **Khác Proxy 4G VẪN BỊ GOM CỤM:** Nếu mở đồng loạt 5–10 profile tại cùng một thời điểm, Google sẽ gom cụm dựa trên tính đồng pha thời gian (Phase Synchronization), phần cứng GPU renderer, và chữ ký TLS JA3/JA4.
- **Giải pháp: Khởi động so le (Staggered Dispatch) + Lệch nhịp (Jitter):**
  - Giãn cách khởi động giữa các profile từ **45 đến 90 giây** ngẫu nhiên (`--stagger 45`).
  - Mỗi profile bắt buộc chiếm 1 cổng proxy di động 4G độc quyền, không chạy trùng IP cùng thời điểm.
  - Trình tự thao tác ngẫu nhiên giữa các profile (Profile A xem YouTube trước, Profile B đọc News trước...).
- **Kịch bản vận hành:**
  - Script độc lập: `D:\Taadaa\GPM auto\scripts\cron_gpm_gmail_nurture.py` (sao lưu tại `C:\Users\Kibe\AppData\Local\hermes\scripts\cron_gpm_gmail_nurture.py`).
  - Trạng thái lưu tại: `D:\Taadaa\runtime\kibe\cron-state\gpm_gmail_nurture_state.json`.
  - Chu kỳ: Mỗi profile được đi dạo chơi 1 lần sau mỗi 4–5 ngày.

---

## 4. Kiểm Soát Session Đăng Nhập & Kỷ Luật Nghiệm Thu (2026-09-20 Update)
- **Kiểm tra Session 2 lớp (Preflight SQLite Offline + Live CDP):**
  - **Lớp 1 (Offline DB Preflight):** Quét file SQLite Cookies (`Default/Network/Cookies` hoặc `Default/Cookies`) trong `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile`. Chỉ lọc profile có $\ge 2$ cookie session (`SID`, `SSID`, `HSID`, `SAPISID` với `host_key LIKE '%google.com'`). Quét 405 profile chỉ mất ~0.12s.
  - **Lớp 2 (Live CDP Cookie Check):** Sau khi Playwright CDP kết nối, kiểm tra `context.cookies(["https://accounts.google.com", "https://www.youtube.com", "https://google.com"])`. Nếu thiếu session cookie, ngắt sớm (fail-fast), đánh dấu state `NEEDS_LOGIN`, tắt profile và không chạy tác vụ nuôi.
- **Kỷ Luật Anti-Spam Telegram:** Tuyệt đối không xuất `MEDIA:<path>` ra stdout từ cron nuôi định kỳ để tránh spam hình ảnh hàng ngày. Ảnh debug/nghiệm thu chỉ lưu local tại `SCREENSHOT_DIR` (`D:\Taadaa\GPM auto\debug_screenshots`).
- **Thời Điểm Chụp Ảnh Debug YouTube:** Tuyệt đối không chụp ở giây thứ 2 ngay lúc URL `/watch` vừa mở (tránh chụp dính preroll ad / loading spinner). Phải chụp sau khi đã qua bước xử lý quảng cáo (sau khi click Bỏ qua quảng cáo) hoặc ở giây thứ 25+ khi video chính đang phát thực sự.

