# Kiến Trúc Nuôi Dưỡng Gmail Định Kỳ Trên GPM & Xử Lý Hiện Trường YouTube / Đóng Profile

Tài liệu đúc kết kinh nghiệm vận hành thực chiến từ buổi làm việc ngày 2026-09-20 với User Kibe trên trạm PC Dual Xeon và hệ thống GPMLogin Chromium (v3 port 19995).

---

## 1. Bản Chất Hiện Tượng "Trang Chủ YouTube Bị Trống" ("Thử tìm kiếm để bắt đầu")
- **Nguyên nhân gốc rễ**: Kể từ cuối năm 2023, Google áp dụng cơ chế mới: Đối với các tài khoản Google mới tạo hoặc tài khoản chưa bật / chưa có lịch sử xem (Watch History trống), khi mở `https://www.youtube.com`, trang chủ sẽ **hoàn toàn không hiển thị video đề xuất nào** (0 video) kèm thông báo *"Thử tìm kiếm để bắt đầu - Hãy bắt đầu xem video để giúp chúng tôi tạo trang đề xuất..."*.
- **Bẫy F5 / Reload vô tác dụng**: Bấm F5 hay reload lại trang 10 lần vẫn giữ nguyên màn hình trắng chữ vì tài khoản chưa hề phát sinh bất kỳ tương tác video nào trong phiên.
- **Giải Pháp "Shorts -> Home" Thần Thánh**:
  1. Click vào tab `Shorts` (hoặc điều hướng `https://www.youtube.com/shorts`) và cho xem lướt 5–8 giây.
  2. Sau đó click lại logo YouTube / `Trang chủ` (`a#logo` hoặc `https://www.youtube.com`).
  3. Feed Trang chủ YouTube sẽ lập tức được kích hoạt và bung ra đầy đủ ~30 video đề xuất tự nhiên!
  4. Fallback: Nếu vẫn chưa bung, dùng thanh search YouTube gõ từ khóa ngẫu nhiên (`nhac tre`, `tin tuc hom nay`, `review phim`) để ra kết quả video thật.

---

## 2. Kỷ Luật Lọc Bỏ Quảng Cáo & Vào Trang `/watch` Video Thật
- **Bẫy Click Trúng Card Quảng Cáo ("Được tài trợ • TikTok")**:
  - Trên feed YouTube, thẻ video đầu tiên thường là thẻ quảng cáo in-feed (`Được tài trợ` / `Sponsored`).
  - Nếu locator click trúng thẻ này, click dễ bị fail (`Element is not visible`) hoặc đưa profile vào landing page quảng cáo ngoài luồng.
  - **Quy tắc lọc**: Quét các link `a#video-title-link[href*='/watch']`, kiểm tra thẻ cha (`ancestor::ytd-rich-item-renderer | ancestor::ytd-video-renderer`), nếu chứa text `["Được tài trợ", "Sponsored", "Ad", "advertisement"]` thì **BẮT BUỘC BỎ QUA NGAY**.
  - Lấy đúng `href` của video nội dung thật, click hoặc điều hướng trực tiếp tới `https://www.youtube.com{href}` và chờ `wait_for_url("**/watch*", timeout=15000)`.
- **Cơ Chế Bỏ Qua Quảng Cáo Đầu Video Thông Minh (Smart Ad Skip 70/30)**:
  - Khi xem video trên YouTube thường có quảng cáo in-stream đầu video:
    + **70% trường hợp**: Đợi 5 giây đếm ngược, chèn thêm độ trễ ngẫu nhiên 2.0s – 5.5s (tương đương giây thứ 7–10, phản xạ người thật), sau đó hover chuột và click nút `Bỏ qua quảng cáo` (`.ytp-skip-ad-button, .ytp-ad-skip-button-modern`).
    + **30% trường hợp**: Kệ cho quảng cáo tự chạy hết (mô phỏng người dùng lười hoặc treo máy làm việc khác).
  - Sau đó tiếp tục xem video chính trong **90 – 120 giây** (chuẩn 2 phút tạo heartbeat và nạp cookie AdSense).

---

## 3. Quản Lý Tab Tuần Tự & Phân Bổ Tỷ Lệ Xác Suất
- **Kỷ Luật Duy Nhất 1 Tab (Sequential Tab Lifecycle)**:
  - Tuyệt đối KHÔNG mở đồng loạt 3 tab (YouTube, News, Search) cùng lúc trong 1 profile.
  - Chỉ duy trì **DUY NHẤT 1 TAB** (`context.pages[0]`). Làm xong việc này thì đóng tab hoặc điều hướng sang trang kế tiếp.
  - Dùng helper `cleanup_extra_tabs(context, keep_page)` dọn sạch popups, tab rác phát sinh.
- **Phân Bổ Tỷ Lệ Hành Vi (Dynamic Task Distribution)**:
  - Người thật không ai lần nào mở máy cũng làm cả 3 việc. Cần phân bổ xác suất:
    + **50% lượt nuôi**: CHỈ xem YouTube 90–120s rồi tắt.
    + **30% lượt nuôi**: Đọc Google News 45–60s (cuộn trang mượt mà qua `human_scroll`) + Search Google 1 câu đời sống rồi tắt. (Tuyệt đối không mở YouTube).
    + **20% lượt nuôi**: Hỗn hợp (xem YouTube + đọc báo/search tuần tự từng việc).

---

## 4. Kiểm Soát Session Google & Đóng Dứt Điểm Profile GPM
- **Preflight Cookie Guard (Kiến trúc 2 tầng Gate 0 + Gate 1)**:
  - **Gate 0 (Disk Preflight - BẮT BUỘC TRƯỚC KHI GỌI START GPM)**:
    + Xem chi tiết tại `references/gpm-nurture-disk-cookie-preflight-gate.md`.
    + Đọc trực tiếp file SQLite `Default/Network/Cookies` (hoặc `Default/Cookies`) trên ổ cứng. Kiểm tra `COUNT(*) WHERE host_key LIKE '%google.com' AND name IN ('SID', 'SSID', 'HSID', 'SAPISID')`.
    + Nếu $< 2$ token: BỎ QUA NGAY LẬP TỨC tại tầng lọc ứng viên (`skipped_no_cookie`), gắn cờ `NEEDS_LOGIN` vào state file. **Tuyệt đối CẤM gọi API start GPM hoặc mở Chromium khi chưa có cookie trên đĩa** vì sẽ gây nghẽn batch, lag PC và tốn proxy 4G vô ích.
  - **Gate 1 (In-Browser Verification - Phòng thủ thứ cấp)**:
    + Sau khi Playwright kết nối CDP, kiểm tra lại `context.cookies()`. Nếu phát hiện bất thường, dừng kịch bản và đóng profile ngay lập tức.
- **Hard Process Cleanup (Tránh Đọng Taskbar)**:
  - Khi đóng profile, gọi `browser.close()` -> `context.close()`.
  - Gọi endpoint đóng chuẩn: **`GET http://127.0.0.1:19995/api/v3/profiles/close/{id}`** (kèm fallback `/profiles/stop/{id}`).
  - Kiểm tra nếu tiến trình còn sót lại thì gọi force terminate, đảm bảo cửa sổ profile biến mất 100% khỏi thanh Taskbar của Windows.
