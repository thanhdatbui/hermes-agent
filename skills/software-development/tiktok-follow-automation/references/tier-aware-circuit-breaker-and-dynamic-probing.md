# Dynamic Tier-Aware Circuit Breaker & Safe Account Probing

## 1. Tử Huyệt Của Cầu Dao Giật Mù (Blind Breaker Trip Trap)

### A. Hiện tượng "Em làm sai, anh đi tù 48h":
- Quy hoạch Farm: 80 máy Kibe dùng 40 proxy (tỷ lệ 1 Proxy : 2 Máy) và 8 Row tài khoản (Row 1/2 cựu binh, Row 3..8 gối đầu/mới reg).
- Khi hệ thống chạy kiểm tra `trip_ip_breaker()` vô điều kiện cho mọi ca `FOLLOW_FAILED`:
  - Lúc 00:00 - 02:00 (Ca 4) hoặc 12:00 (Ca 2), một nick non ở Row 7/8 hoặc Row 3/4 vào ca, bấm 1 lượt follow rồi bị TikTok nhả do nội tại nick chưa đủ trust.
  - Cầu dao IP lập tức kích hoạt ngắt 48h (`reset_at = now + 48h`).
  - Sáng hôm sau lúc 06:00, Row 1/2 (dàn cựu binh khỏe nhất farm, 20–108 follow sạch) thức dậy vào ca follow thì bị dính `CIRCUIT_BREAKER_SKIPPED`, bị giam 48h oan uổng!

### B. Bóc tách nguyên nhân kỹ thuật: Lỗi Account vs Lỗi Gateway IP:
1. **Lỗi ở Tầng Account (Tân binh / Nick thử thách non nớt):**
   - Nick mới hoặc nick đang hồi phục chưa có điểm trust trên thiết bị (Device Soaking).
   - Khi bấm follow, TikTok từ chối ở tầng tài khoản cá nhân. **Dải IP hoàn toàn sạch và vô tội**.
   - Việc giật cầu dao ngắt IP 48h trong trường hợp này là **phản ứng thái quá (false alarm)**, làm tê liệt công suất của cả dàn máy.
2. **Lỗi ở Tầng Gateway IP (Nick Cấp Khỏe / Nick Cấp 2 có tải bị nhả):**
   - Khảo sát thực tế: Khi một nick Cấp 2 (5–9 follow) hoặc Cấp Khỏe (10+ follow) bị nhả, **100% các máy anh em chạy sau cùng IP trong ngày đều bị dính nhả nốt** (M34/M73, M78/M71, M72/M33, M77/M37).
   - Đây là bằng chứng xác thực rằng TikTok đã gắn cờ nghi vấn lên Gateway IP hoặc đang có bão quét tương tác trên dải proxy đó.

---

## 2. Quy Chuẩn Cầu Dao Thông Minh Theo Cấp Độ Động (Tier-Aware Circuit Breaker)

Cấp độ của nick được tính điểm và thăng hạng liên tục theo ngày sạch (`probation_clean_days`):

| Cấp độ Nick | Điều kiện kỹ thuật | Hành vi khi dính `FOLLOW_FAILED` | Xử lý Cầu Dao IP |
| :--- | :--- | :--- | :--- |
| **🌱 Cấp 1: Tân Binh / Đi Dò / Mới Ra Tù** | `clean_days < 3`, `graduated == False`, quota 1–4 lượt. | Nick tự tăng `fail_streak`, nhận cooldown 3–14 ngày dưỡng sinh, reset `clean_days = 0`. | **CẤM GIẬT CẦU DAO IP (NO TRIP).** Giữ nguyên dải IP cho các nick khác hoạt động. |
| **🌿 Cấp 2: Hồi Phục 2 (Tăng tải an toàn)** | `3 <= clean_days < 6`, quota 5–9 lượt. | Tước nấc, tăng streak, chuyển về cooldown. | **BẮT BUỘC GIẬT CẦU DAO 48H ROLLING.** Bảo vệ máy anh em ngay lập tức. |
| **💪 Cấp 3: Khỏe (Đã Tốt Nghiệp / Veteran)** | `clean_days >= 6` HOẶC `graduated == True`, quota 10–20 lượt. | Tước cờ `graduated`, chuyển về cooldown. | **BẮT BUỘC GIẬT CẦU DAO 48H ROLLING.** Cảnh báo bão thuật toán trên IP. |

---

## 3. Triết Lý Dò Nick An Toàn (Safe Dynamic Probing - User Invariant)

### A. Chống cấm cứng theo Row:
- **USER INVARIANT:** Tuyệt đối KHÔNG cấm vĩnh viễn Row 3 đến 8 hay đặt quy định cứng nhắc theo hàng ngang.
- Thực tế farm có 24 nick ở Row 3 & 4 là nick cựu binh khỏe (như `@cao.m.phng7` cày 52 fl, `@lenhi09116` cày 43 fl). Cấm cứng theo Row sẽ bỏ sót và làm tê liệt các tài nguyên khỏe này.

### B. Dò 1 Lượt (Probe = 1) Không Gây Hại Nick:
- Bấm 1 lượt follow rồi bị nhả **không làm chết acc hay hỏng nick**, miễn là có cơ chế Progressive Backoff (Streak 1: nghỉ 3 ngày $\rightarrow$ Streak 2: nghỉ 7 ngày $\rightarrow$ Streak 3: nghỉ 14 ngày).
- Trong những ngày nghỉ cooldown, nick vẫn lướt feed và upload video bình thường để nuôi dưỡng trust tự nhiên.
- Vài ngày sau khi hết hạn cooldown, nick lại được bấm thử 1 lượt. Nếu thành công thì thăng hạng, nếu bị nhả thì tiếp tục nghỉ ngơi.
- **Lợi ích:** Phát hiện sớm các nick có tiềm năng follow mà hoàn toàn không gây nguy hại cho dải IP chung của farm.
