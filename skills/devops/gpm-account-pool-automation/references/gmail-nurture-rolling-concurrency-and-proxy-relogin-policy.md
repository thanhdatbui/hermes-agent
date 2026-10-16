# Chính Sách Nuôi Profile GPM Gmail Cuốn Chiếu & Tách Biệt Cooldown Proxy Re-login

## 1. Tách Biệt Cooldown Proxy: Re-login vs Acc Mới Log Lần Đầu

### Triệu chứng & Bẫy Kẹt Vận Hành
- Trước đây hệ thống áp dụng trần cứng `MAX_LOGINS_PER_PROXY = 2` (2 acc / port proxy / ngày) cào bằng cho tất cả các tài khoản.
- Hậu quả: Khi các tài khoản cũ bị văng cookie Google session (`NEEDS_LOGIN`), watchdog login phát hiện nhưng lại bị chặn do port proxy đó đã chạm trần 2 acc/ngày trong các ca trước $\rightarrow$ Tài khoản bị treo, không được cứu session kịp thời.

### Quy Tắc Chuẩn Hóa Bất Biến (User Correction)
1. **Acc mới log lần đầu (Chưa có profile / chưa từng login):**
   - BẮT BUỘC áp trần tối đa **2 acc / port proxy / ngày** để chống bot-check Google và bảo vệ dải IP 4G.
2. **Acc cũ bị văng session (Đã có profile GPM gán port cố định):**
   - **MIỄN TRỪ HOÀN TOÀN cooldown 24h và trần 2 acc/ngày.**
   - Thao tác re-login chỉ là refresh session trên đúng thiết bị và proxy đã định danh từ trước, không gây sốc IP như nạp acc mới.
   - Code watchdog lọc proxy BẮT BUỘC nhận diện cờ `is_relogin` (từ `nurture_reported_needs_login` hoặc `is_lost_session`), cho phép bypass qua bộ lọc proxy count và KHÔNG cộng dồn vào biến đếm số lượt login mới của ngày.

---

## 2. Kỷ Luật Nuôi Profile GPM Gmail (Group 10 - Google_Live_Ready)

### A. Chu Kỳ & Giãn Cách Nuôi (Nurture Interval)
- **Cấm nuôi mỗi ngày (24h):** Ngày nào cũng mở trình duyệt lướt YouTube/News với cùng pattern ngắn 1–2 phút sẽ tạo robotic footprint, dễ kích hoạt Google reCAPTCHA.
- **Cấm giãn cách quá dài (5 ngày / 120h):** Google tự thu hồi cookie sau thời gian dài không hoạt động (session expiration), khiến tài khoản bị "nguội" và văng session âm thầm.
- **Chu kỳ chuẩn:** **2 – 3 ngày / lần (48h – 72h)**. Giữ cookie luôn "ấm" (warm) với hành vi duyệt web tự nhiên.

### B. Giới Hạn Trần Nuôi Theo Ngày (Daily Safety Cap)
- **Bắt buộc giới hạn:** Đối với kho 70–80 acc, đặt trần **25 – 30 profile / ngày**.
- **Lý do bảo vệ hạ tầng Farm:**
  1. *Bảo toàn Data 4G:* Profile GPM dùng chung dải proxy Mobi 4G với điện thoại farm S7. Kịch bản nuôi có xem YouTube (50–70%), nếu thả nổi liên tục sẽ đốt cạn data gói cước, gây nghẽn mạng farm.
  2. *Bảo vệ RAM/CPU Host:* Tránh mở Chromium liên tục làm nóng máy và nghẽn cổng CDP của GPMLogin.

### C. Cơ Chế 5 Workers Cuốn Chiếu (Rolling Concurrency)
- Chạy song song **5 workers** với khởi động so le 30s (Staggered Launch).
- Cơ chế Worker Pool: Acc nào hoàn thành kịch bản (2–3 phút) thì đóng dứt điểm profile, kiểm tra `psutil` diệt sạch tiến trình zombie và bốc ngay profile tiếp theo vào nuôi.

---

## 3. Kỷ Luật Báo Cáo: Silent Watchdog Hàng Giờ + Digest 6H

1. **Khung chạy hàng giờ (0 * * * *):**
   - Áp dụng triệt để nguyên tắc **Silent Watchdog**: Im lặng tuyệt đối (stdout rỗng) khi 100% profile nuôi thành công. CẤM gửi tin nhắn Telegram hàng giờ gây spam (24 tin/ngày).
   - Chỉ in alert tức thì khi phát hiện acc bị `NEEDS_LOGIN` (văng cookie) hoặc lỗi treo Chrome zombie để hệ thống xử lý khẩn cấp.
2. **Báo cáo gộp định kỳ 6h (00:00, 06:00, 12:00, 18:00):**
   - Tổng hợp 1 tin duy nhất vào kênh GPM:
     - Tổng số lượt nuôi trong 6h qua.
     - Số acc thành công vs lỗi.
     - Danh sách acc bị văng session (`NEEDS_LOGIN`) bàn giao cho ca login kế tiếp.
