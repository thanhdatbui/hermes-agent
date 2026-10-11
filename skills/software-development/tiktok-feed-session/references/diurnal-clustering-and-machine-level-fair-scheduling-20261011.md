# Diurnal Clustering & Machine-Level Weighted Fair Scheduling (2026-10-11)

## 1. Bản Chất Kỹ Thuật (Architecture Invariant)
Trong điều phối nuôi tài khoản TikTok trên farm đa máy (80-160 điện thoại, mỗi máy 8 accounts):
- **CẤM Global Synchronous Single-Row Burst:** Việc cả 80 máy cùng mở app, cùng truy cập 1 Slot (ví dụ ca sáng cả farm cùng chạy Row 1) tạo ra:
  * Đỉnh tải hạ tầng (burst lưu lượng 4G/proxy, spike độ trễ).
  * Chữ ký hành vi tương quan cao (High Correlation Footprint) dễ bị giám sát nhận diện tự động hóa theo lô.
  * Blast radius rộng (lỗi trên Row 1 làm hỏng toàn bộ ca chạy của cả farm).
- **Phân Cụm Khung Giờ (Diurnal Habit Clustering):**
  * Hành vi người dùng thật có nhịp sinh học tự nhiên tương đối ổn định (70–85% phiên nằm trong khung giờ ưu tiên).
  * Gom cụm theo ca trong ngày:
    * **Cụm Sáng (06h - 09h):** `{Row 1, Row 2, Row 7}`
    * **Cụm Trưa (12h - 15h):** `{Row 3, Row 4, Row 8}`
    * **Cụm Tối (18h - 21h):** `{Row 5, Row 6}`
  * Không ép cố định 100% một giờ, cho phép biến thiên tự nhiên.

---

## 2. Machine-Level Slot Selection vs Pure Random
- **Tại sao CẤM Random Thuần Túy:**
  * Bốc ngẫu nhiên đều (33.3% mỗi slot trong cụm) dẫn đến hiện tượng **BỎ ĐÓI (Starvation)**: Theo xác suất, sẽ có tài khoản nhiều ngày liền không được bốc, trong khi tài khoản khác bị bốc liên tục.
- **Giải Pháp: Weighted Fair Scheduler (Deficit + Starvation Guard):**
  * Mỗi máy tự bốc slot trong cụm của nó dựa trên điểm ưu tiên:
    $$\text{Priority} = \text{Quota Deficit} + \text{Vulnerability Bonus} - \text{Recent Penalty}$$
  1. **Quota Deficit:** Row nào trong tuần chạy ít hơn so với mục tiêu sẽ được ưu tiên cao hơn.
  2. **Vulnerability Bonus (Từ tracker.db):**
     * Nick thiếu video (`video_count < 10`): Ưu tiên chạy để đăng video.
     * Nick bị nhả follow (`follow_cooldown`): Bốc vào ca dưỡng sinh để lướt feed xả tải (0 follow).
     * Nick đứng hình (0 delta view/heart 7 ngày): Ưu tiên lướt feed kích hoạt tương tác.
  3. **Recent Penalty:** Trừ điểm row vừa chạy hôm qua để nhường lượt cho các row còn lại trong cụm.
  4. **Random Tie-Breaker:** Chỉ dùng ngẫu nhiên để phá thế hòa khi các row ngang điểm.

---

## 3. Cơ Chế Chăm Sóc Theo Nhóm Trạng Thái (Targeted Action Routing)
- **Score Cao do Cooldown:** Hành động bắt buộc là **HOLD / PURE FEED ONLY**, CẤM BẤM FOLLOW (`_follow_rate = 0`). Tuyệt đối không dùng tự động hóa ép tăng tương tác để bù chỉ số.
- **Score Cao do Thiếu Video:** Ưu tiên lướt feed + Upload video ngay (1 video/ngày).
- **Score Khỏe Mạnh:** Giữ nguyên lịch cày thông thường, không lôi vào ca dưỡng sinh làm lãng phí tài nguyên.
