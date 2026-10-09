# GPM Gmail Nurturing, YouTube Blank Feed Fix & Identity Warming Strategy

## 1. Bản Chất Rủi Ro Khi Nuôi Gmail Trên Trình Duyệt GPM (PC)
- **Tách biệt Consumer Activity vs Developer API Quota**:
  - *Consumer Activity (YouTube, Google News, Search, Gmail)*: Xây dựng Human Trust Score tầng người dùng cuối. Giúp tài khoản có "hơi thở sinh học", chống quét tài khoản rác/ngủ đông (Dormant Account).
  - *Developer API Quota (Google Cloud Code Assist / Antigravity OAuth)*: Thuộc diện giám sát lạm dụng hạ tầng (Google Cloud Abuse Detection).
  - **Quy tắc sống còn**: Tuyệt đối KHÔNG cấp quyền Developer Cloud API (Antigravity) ngay trong phiên đăng nhập đầu tiên trên profile GPM (dù đã ngâm 7 ngày trên S7). Hành vi vừa vào thiết bị mới đã lập tức đòi quyền Cloud API kích hoạt cờ *New Device Anomaly + Developer Privilege Escalation* (>90% checkpoint SMS/die).
  - **Chiến lược chuẩn**:
    + Phiên 1 (GPM): Đăng nhập Gmail $\rightarrow$ Lấy session ChatGPT-Web (bên thứ ba, lành tính) $\rightarrow$ Lướt YouTube / Google News $\rightarrow$ Đóng profile.
    + Ngâm profile GPM $\ge 7\text{ ngày}$ để thành *Trusted Device*.
    + Phiên 2 (sau 7 ngày): Mới cấp quyền OAuth Antigravity vào pool.

## 2. Bẫy Trang Chủ YouTube Bị Trống ("Thử tìm kiếm để bắt đầu")
- **Hiện tượng**: Trên các tài khoản mới hoặc chưa có lịch sử xem, trang chủ `https://www.youtube.com` bị trắng tinh, không có bất kỳ video nào mà chỉ hiện dòng: *"Thử tìm kiếm để bắt đầu - Hãy bắt đầu xem video để giúp chúng tôi tạo trang đề xuất..."*.
- **Bẫy F5/Reload**: Bấm F5 hoặc `page.reload()` hoàn toàn VÔ TÁC DỤNG vì YouTube không tự populate feed nếu thiếu session context.
- **Giải pháp kích hoạt feed 100% thành công**:
  1. Kiểm tra nếu feed trống (0 thẻ video hoặc có text *"Thử tìm kiếm để bắt đầu"* / *"Try searching to get started"*):
  2. Click vào tab **Shorts** (`a[title='Shorts']` hoặc điều hướng `youtube.com/shorts`), xem lướt 5 – 8 giây.
  3. Click quay lại **Trang chủ** (`a#logo` hoặc điều hướng `youtube.com`), chờ 3 – 4s. Feed lập tức bung ra ~30 video đề xuất tự nhiên!
  4. *Dự phòng (Fallback)*: Nếu vẫn chưa có video, focus thanh tìm kiếm YouTube gõ từ khóa ngẫu nhiên (ví dụ `'nhac tre'`, `'tin tuc 24h'`, `'review phim'`) và Enter.
- **Quy chuẩn xem video (Mốc vàng 1.5 – 2 phút / 90 - 120s)**:
  - Xem video thường (Regular video), hạn chế lướt Shorts cơ học.
  - Sau khi click video, chờ 5s cho player render, gửi phím `'k'` hoặc `Space` để đảm bảo playback đang chạy.
  - Chụp ảnh nghiệm thu TRONG LÚC VIDEO ĐANG PHÁT (thấy rõ player, thanh thời lượng, kênh).
  - **Cơ Chế Xử Lý Quảng Cáo YouTube Thông Minh (Smart Ad Skip & Watch Simulation)**:
    - Trong vòng 90 - 120s xem video (`/watch`), thiết lập vòng lặp polling (chu kỳ 2s) kiểm tra sự xuất hiện của nút Bỏ qua quảng cáo (Skip Ad).
    - Bộ selector nhận diện nút Skip Ad trên YouTube:
      `button.ytp-skip-ad-button, .ytp-ad-skip-button, button.ytp-ad-skip-button-modern, [class*='ytp-ad-skip-button']`
    - Tỷ lệ xác suất hành vi người thật:
      + **70% trường hợp**: Khi nút Skip Ad xuất hiện (thường sau 5s đếm ngược của YouTube):
        * Chờ thêm độ trễ ngẫu nhiên từ 2.0s đến 5.5s (tương đương giây thứ 7 - 10, mô phỏng phản xạ người dùng thật).
        * Hover chuột vào nút rồi bấm click (hoặc `click(force=True)`).
        * Log: `[email] Đã bấm Bỏ qua quảng cáo (sau delay ngẫu nhiên)`.
      + **30% trường hợp**: Giữ nguyên cho quảng cáo chạy tự nhiên đến hết (mô phỏng người dùng lười hoặc cắm máy nghe nhạc làm việc khác).
        * Dùng cờ `ad_ignored = True` để tránh log lặp lại cho cùng 1 quảng cáo trong khi nút skip vẫn còn hiển thị.
        * Reset `ad_ignored = False` khi nút skip biến mất.
        * Log: `[email] Giữ nguyên cho quảng cáo chạy tự nhiên`.

## 3. Kiến Trúc Khởi Động So Le (Staggered Dispatch) Trên Máy Trạm Dual Xeon
- **Cảnh báo Anti-Bot Clustering**: Khác cổng proxy 4G di động chỉ giải quyết tầng IP (Layer 3/4). Nếu mở đồng loạt 5 – 10 profile GPM cùng một giây trên cùng 1 máy PC vật lý, Google vẫn gom cụm qua vân tay phần cứng (WebGL, Canvas, AudioContext, JA3/JA4 TLS stack) và *Tính đồng pha hành vi (Phase Synchronization)*.
- **Giải pháp Staggered Launch**:
  - Không mở đồng loạt. Cấu hình độ trễ giãn cách so le giữa các profile: `delay = (idx - 1) * 45s + random(5, 15)s`.
  - Trên máy Xeon vẫn có thể có 3 – 5 profile cùng chạy đồng thời nhưng thời điểm khởi động và kết thúc hoàn toàn lệch pha.
  - Thêm Randomized Jitter: Profile A xem YouTube 80s + News 20s; Profile B xem News 25s + Search 15s + YouTube 65s.
  - Mỗi profile bind cố định 1 cổng proxy 4G riêng biệt.
