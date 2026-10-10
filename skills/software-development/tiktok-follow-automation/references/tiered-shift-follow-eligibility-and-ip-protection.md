# Phân Tầng Lịch Chạy Follow Theo Sức Khỏe Nick & Chống Giam Lây Cầu Dao IP 48H

## 1. Bản Chất Vấn Đề: Xung Đột Ca Chạy & Cầu Dao IP 48H (Cascading Lockout)

### Hiện trường thực tế:
* **Hạ tầng Farm:** 80 máy Samsung S7 chia sẻ 40 cổng proxy (1 IP : 2 Máy).
* **Lịch vận hành 4 ca / ngày:**
  * **00:00 & 01:30 (Ca 4 - Đêm):** Chạy Row 7 (lẻ) hoặc Row 8 (chẵn).
  * **06:00 & 08:00 (Ca 1 - Sáng):** Chạy Row 1 (lẻ) hoặc Row 2 (chẵn) — Dàn cựu binh trụ cột farm (20–108 follow, video nhiều).
  * **12:00 & 14:00 (Ca 2 - Trưa):** Chạy Row 3 (lẻ) hoặc Row 4 (chẵn).
  * **18:00 & 20:00 (Ca 3 - Tối):** Chạy Row 5 (lẻ) hoặc Row 6 (chẵn).
* **Nghịch lý "Nick Yếu Giam Lây Nick Khỏe":**
  * Nửa đêm (00:00), nếu nick Row 7/8 (nick mầm mới reg bù, trust yếu nhất) đi follow và bị TikTok nhả (`FOLLOW_FAILED`):
    * `trip_ip_breaker` kích hoạt giật cầu dao ngắt IP 48h rolling (`reset_at = now + 48h`).
    * Đến 06:00 sáng, Row 1/2 bước vào ca cày follow thì `check_ip_breaker` thấy proxy bị ngắt ➔ **Row 1/2 bị `CIRCUIT_BREAKER_SKIPPED`**, bị tước quyền cày follow trong 48 tiếng oan uổng!
  * Trưa (12:00), nếu nick non ở Row 3/4 vào cày follow dính nhả ➔ Lại giật cầu dao 48h ➔ Sáng hôm sau Row 1/2 tiếp tục bị giam!

---

## 2. Bẫy Cấm Mù Cả Row (User Correction & Field Data Insight)

* **Cạm bẫy Agent (Over-Simplification):** Vội vàng cấm cứng toàn bộ Row 3/4/5/6/7/8 không được đi follow.
* **Thực tế dữ liệu 160 nick Row 3 & Row 4 (10/10/2026):**
  * Có **24 nick** có lịch sử cày follow rất tốt:
    * `M21_r3` (`@cao.m.phng7`): 52 follow sạch, streak 0, following 68 profile.
    * `M16_r3` (`@lenhi09116`): 43 follow sạch, streak 0, following 119 profile.
    * `M9_r3` (`@dokieu203`): 35 follow, streak 0.
    * `M8_r3` (`@aliciwwt40z`): 36 follow.
  * Nếu cấm mù cả row sẽ **bỏ sót và triệt tiêu sản lượng của những nick khỏe thực sự**.
* **Phân tích bóc tách (FL > 0 vs FL == 0):**
  * **Tuổi nick (Age):** Nhóm follow được có tuổi trung bình **95.3 ngày** (tạo từ tháng 3 đến tháng 6, soaking sâu) vs nhóm bị nhả **67.8 ngày**.
  * **Following profile:** Nhóm follow được đã có lịch sử tương tác tự nhiên (`Following trung bình = 12.2`) vs nhóm bị nhả (`Following trung bình = 1.3`, đa số trinh nguyên 0 following).
  * **Kết luận:** Những nick follow được ở Row 3/4 là **nick cựu binh già dặn nằm ở slot Row 3/4**.

---

## 3. Quy Tắc Vận Hành Chuẩn: Tiered Follow Eligibility & Khóa Ca Đêm

### A. Khóa Tuyệt Đối Follow Ca Đêm (00:00 - 02:00) — Bảo Vệ Mở Bát 6H Sáng:
* **Toàn bộ Ca 4 (00:00 & 01:30):** BẮT BUỘC TẮT 100% Follow Hook (`skip_follow_night_shift_pure_feed`).
* Chỉ cho phép lướt feed + upload video, cấm tương tác follow.
* **Tác dụng:** Triệt tiêu hoàn toàn nguy cơ IP bị cúp lúc nửa đêm, bảo đảm 06:00 sáng IP luôn tinh khôi cho Row 1/2.

### B. Bộ Lọc Phân Tầng Cho Row 3..8 (Ca Ngày / Trưa / Tối):
Thay vì lọc theo row index, lọc theo **chỉ số sức khỏe & trust của từng tài khoản**:
1. **Được phép chạy Follow khi:**
   * Đã có lịch sử follow an toàn trước đó (`total_fl > 0` và `fail_streak == 0`), HOẶC:
   * Tuổi nick $\ge 60$ ngày VÀ số video $\ge 12$ video.
2. **Chưa đủ điều kiện (Nick mầm, 0 follow lịch sử, < 12 video, hoặc đang có streak nhả):**
   * Tự động Safe-Skip Follow Hook (`skip_follow_trust_building`), chuyển sang lướt feed dưỡng sinh + upload video.
   * CẤM cho nick non vào cày follow tự do để tránh làm cúp cầu dao IP 48h của dàn nick khỏe.
