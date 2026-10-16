# GPM Gmail Inventory Observability, Session Dropout Detection & Nurture Verification

## 1. Vấn Đề Thường Gặp & Điểm Mù Vận Hành

### 1.1 Tâm lý vận hành: "Ngày nào cũng báo thành công nhưng không rõ tổng số"
- **Hiện tượng:** Các watchdog ca chạy (Sáng, Chiều, Tối) như `gpm-gmail-login-shifts-watchdog` chỉ báo cáo số lượng biến động theo từng ca (ví dụ: `✓ 34 | ✗ 7 | 22 acc nhường máy`).
- **Hậu quả:** Người vận hành không nắm được:
  1. Tổng số profile GPM hiện có là bao nhiêu?
  2. Bao nhiêu profile đã có tài khoản Gmail thực tế và bao nhiêu profile đã có session Google hợp lệ (`GroupId = 10` - Google Live Ready)?
  3. Tỷ lệ hoàn thành so với tổng kho Gmail farm (`gmail_clean_v2.xlsx`).
- **Nguyên tắc báo cáo chuẩn:** Báo cáo tổng kết ca ngoài các con số delta (kết quả ca) **bắt buộc** phải kèm snapshot hiện trạng tổng thể (Cumulative Totals: Tổng profile GPM, Tổng Gmail LIVE, Số profile sẵn sàng OAuth/Nurture).

---

## 2. Bản Đồ Trạng Thái Kho Profile Gmail GPM

### 2.1 Cấu trúc lưu trữ Source of Truth
1. **SQLite Database GPM:** `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`
   - Bảng `Profiles`:
     - `Name`: Định dạng chuẩn `{Số_máy} - {Email} - {Cổng_proxy}`.
     - `GroupId`: Phân nhóm vòng đời profile (ví dụ: Group `Google Live Ready` / `ChatGPT Ready`).
     - `ProfilePath`: Đường dẫn thư mục profile Chrome cục bộ.
2. **Kích thước Session Cookie trên đĩa:**
   - `<ProfilePath>/Default/Network/Cookies`:
     - File cookie > 50KB: Session sống, đã lưu trữ đầy đủ authentication cookies của Google/YouTube.
     - File cookie < 10KB hoặc không tồn tại: Profile mới tạo hoặc session đã bị xóa/chưa login.
3. **Bảng đối soát kho Gmail Farm:**
   - `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`: Tổng kho Gmail sạch của farm đã phân bổ theo từng máy S7.

---

## 3. Cơ Chế Kiểm Tra Gmail Bị "Văng" Session (Session Dropout & Liveness Detection)

### 3.1 Các tầng kiểm tra văng session trong hệ thống
1. **Tầng 1: Passive Check trong Cron Nuôi (`cron_gpm_gmail_nurture.py`)**
   - Khi cron nuôi mở profile GPM qua CDP để lướt YouTube/Google News:
   - Script điều hướng đến `https://myaccount.google.com/` hoặc kiểm tra avatar/header trên `youtube.com`.
   - Nếu xuất hiện nút "Sign in" / "Đăng nhập" hoặc redirect về `accounts.google.com/signin`:
     $\rightarrow$ Phát hiện **VĂNG SESSION (COOKIE EXPIRED / CHECKPOINT)**.
     $\rightarrow$ Đánh dấu trạng thái profile cần tái đăng nhập (Re-login queue) và hạ nhóm `GroupId`.
2. **Tầng 2: Active Lifecycle Sync (`sync_gpm_lifecycle.py`)**
   - Chạy định kỳ đầu ca sáng (07:00-08:45):
   - Đối soát danh sách profile GPM với trạng thái thực tế của tài khoản.
   - Phát hiện các profile có Gmail bị DIE, khóa vĩnh viễn hoặc checkpoint không thể tự gỡ $\rightarrow$ cô lập profile, không để chiếm dụng proxy và RAM.
3. **Tầng 3: LLM Pool Health Check (`cron_chatgpt_web_pool_watchdog.py`)**
   - Đối với các tài khoản phục vụ ChatGPT Web / Codex:
   - Watchdog mỗi 6h gửi test request xác thực phiên. Nếu 401 Unauthorized $\rightarrow$ tự động kích hoạt healer mở lại profile qua CDP để làm mới session token.

---

## 4. Tình Trạng & Quy Chuẩn Giám Sát Cron Nuôi Profile (`gpm-gmail-nurture-watchdog`)

### 4.1 Cơ chế hoạt động của Cron Nuôi (`cron_gpm_gmail_nurture.py`)
- **Tần suất:** Chạy mỗi giờ (`0 * * * *`), xoay tua các profile đã có session (`GroupId = 10`).
- **Hành vi mô phỏng người dùng thật (Organic Behavior):**
  1. *Lướt YouTube:* Tìm kiếm từ khóa ngẫu nhiên, xem video từ 45–120 giây, like ngẫu nhiên.
  2. *Google Search & News:* Tìm kiếm tin tức xu hướng, cuộn trang đọc bài báo 30–60 giây.
  3. *Tương tác nhẹ:* Giữ ấm cookie, tạo browsing history và cookie tracking tự nhiên cho Google.
- **Giới hạn an toàn:**
  - Tối đa 2–3 profiles chạy đồng thời (tránh nghẽn RAM và tràn CPU máy host).
  - Sử dụng đúng cổng proxy 1:1 đã gán cho profile trong `PROXYgandienthoai.xlsx`.

### 4.2 Tiêu chí xác nhận Cron Nuôi "Vẫn chạy ổn"
1. **Heartbeat & Telemetry:** File log hoặc output định kỳ xác nhận số lượng profile đã nuôi thành công trong lượt.
2. **Không có zombie process:** Các tiến trình Chrome do CDP mở bắt buộc phải được dọn dẹp sạch sẽ sau khi hoàn tất phiên nuôi (gọi `_kill_gpm_chrome`).
3. **Tỷ lệ giữ cookie:** Tỷ lệ tài khoản duy trì cookie sống sau 7 ngày nuôi đạt $\ge 90\%$.
