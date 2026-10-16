# Gmail GPM Re-login Proxy Cooldown Exemption & Rolling Nurture Protocol

## 1. Quy tắc Phân Định Cooldown Proxy 24h: Acc Mới vs Acc Bị Văng (Re-login)

> 📌 **Chỉ thị vận hành bất biến từ User:**  
> *"Log in acc bị văng thì k tính cooldown 24h. Chỉ acc mới log lên ms bị tính."*

### 1.1. Acc mới tạo / Login lần đầu lên GPM
- **Định nghĩa:** Tài khoản chưa từng đăng nhập trên GPM, hoặc profile mới tạo chưa từng lưu Google session thành công.
- **Ràng buộc:** BẮT BUỘC áp trần nghiêm ngặt **tối đa 2 tài khoản / port proxy / ngày** (cooldown 24h giữa các mẻ mới trên cùng một cổng proxy).
- **Mục đích:** Bảo vệ dải IP 4G của farm khỏi danh sách đen (Blacklist / Sentinel) của Google khi phát hiện nhiều danh tính đăng nhập mới từ cùng một endpoint.

### 1.2. Acc cũ bị văng session (Re-login / Refresh Cookie)
- **Định nghĩa:** Tài khoản đã có sẵn profile GPM, đã gán cổng proxy cố định 1:1, nhưng bị hết hạn cookie hoặc bị Google bắt đăng nhập lại (`status: NEEDS_LOGIN`).
- **Quy tắc:** **MIỄN TRỪ HOÀN TOÀN COOLDOWN 24H**.
- **Thực thi:** Cho phép đăng nhập lại ngay lập tức mà không phải chờ 24h, nhằm khôi phục cookie sống cho Group 10 (`Google_Live_Ready`) và cung cấp session cho các downstream pool (ChatGPT-Web, Codex, OAuth).

---

## 2. Kiến Trúc Nuôi Cuốn Chiếu (Rolling Concurrency = 5)

### 2.1. Hạn chế của mô hình nuôi theo mẻ ngắt quãng (Periodic Batch)
- Mô hình cũ chạy `--concurrency 2 --limit 6` mỗi giờ 1 lần (`0 * * * *`) khiến 77+ tài khoản mất nhiều ngày mới quay vòng xong một lượt, đồng thời tài nguyên RAM/CPU bị bỏ phí giữa các khung giờ rảnh.

### 2.2. Chuẩn hóa Worker Pool 5 Profiles Cuốn Chiếu
- **Độ rộng song song:** Duy trì đồng thời tối đa **5 profile GPM** (`concurrency = 5`).
- **Khởi động so le (Staggered Launch):** Giãn cách 30s giữa các lượt mở profile để tránh nghẽn cổng CDP 19995 và sốc CPU.
- **Cơ chế cuốn chiếu (Rolling Queue):**
  1. Profile A hoàn thành kịch bản nuôi (xem YouTube 90-120s hoặc Google News/Search 45-60s).
  2. Đóng trình duyệt (`Context.close()`, `Browser.close()`, GPM stop API).
  3. Kiểm tra dọn dẹp triệt để tiến trình Chrome zombie qua `psutil`.
  4. Ngay lập tức bốc Profile B trong danh sách Group 10 vào thế chỗ.
- **Độ phủ & Nhịp độ chuẩn hóa (User Approved):**
  * **Chu kỳ giãn cách profile (NURTURE_INTERVAL_SECONDS):** **2 ngày (48 giờ)** thay vì 5 ngày (120h là quá lâu khiến session nguội và Google tự thu hồi cookie; 1 ngày là quá dày gây pattern máy móc và hao data 4G).
  * **Trần an toàn nuôi hàng ngày (MAX_DAILY_NURTURE):** Giới hạn tối đa **25 – 30 profile / ngày** để bảo vệ băng thông data proxy 4G (tránh nghẽn làm drop điện thoại S7 đang chạy TikTok/Upload) và giải phóng RAM/CPU máy chủ.
  * Với kho ~77 profile Group 10, nhịp độ 30 acc/ngày sẽ xoay vòng trọn vẹn 100% kho sau đúng 2.5 – 3 ngày.

---

## 3. Kỷ Luật Báo Cáo: Silent Hàng Giờ vs Tổng Kết Mỗi 6H

### 3.1. Silent Watchdog hàng giờ (Chống Spam Telegram)
- Cron nuôi chạy hàng giờ hoặc liên tục **CẤM in stdout** khi vận hành bình thường.
- Tuyệt đối không gửi tin nhắn báo *"Hoàn tất nuôi X/Y profiles"* mỗi giờ lên kênh Telegram của User (tránh bão 24 tin/ngày làm loãng thông điệp).
- Mọi chỉ số được ghi âm thầm vào `LOG_FILE` và telemetry JSON trên đĩa.

### 3.2. Báo cáo gộp định kỳ mỗi 6h (`00:00, 06:00, 12:00, 18:00`)
- Tích hợp số liệu nuôi vào bản tin báo cáo định kỳ 6h (`cron_gmail_gpm_2fa_6h_report`):
  - Tổng số lượt tương tác thành công / thất bại trong 6h qua.
  - Tỷ lệ phân bổ hành vi: YouTube vs Google News/Search.
  - Danh sách tài khoản phát hiện văng session (`NEEDS_LOGIN`) để bàn giao cho ca login xử lý.
- **Alert khẩn cấp:** CHỈ bắn tin cảnh báo ngay lập tức khi phát hiện proxy toàn farm sập hoặc tiến trình Chromium bị treo hàng loạt.
