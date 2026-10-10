# Tier-Aware Circuit Breaker & Accelerated Probation Ladder

## 1. Bản Chất Kỹ Thuật: Cầu Dao IP Thông Minh Theo Cấp Độ (Tier-Aware Circuit Breaker)

### Sự Cố "Nick Non Bị Nhả Giam Oan Nick Khỏe 48H":
* Farm quy hoạch 80 máy / 40 proxy (1 IP : 2 Máy).
* Khi nick mầm non / tân binh (Row 3–8 hoặc mới reg bù) đi dò follow và bị nhả (`FOLLOW_FAILED`), cơ chế cũ giật cầu dao IP 48h (`trip_ip_breaker()`).
* Hậu quả: Dàn nick Cựu Binh Cấp Khỏe ở Row 1/2 vào ca 6h sáng hôm sau (hoặc máy partner cùng IP) bị ngắt oan 48h (`CIRCUIT_BREAKER_SKIPPED`), gây sụt giảm sản lượng follow nghiêm trọng.

### Dữ Liệu Thực Nghiệm Hiện Trường (257 phiên từ 02/10/2026):
* **Khi nick mầm non bấm xịt 1-2 cái bị nhả:** TikTok chỉ từ chối ở tầng tài khoản (Account-Level Restriction) do trust nick chưa đủ. Dải IP hoàn toàn không bị cắm cờ gateway. Thực tế các nick Khỏe chạy sau trên cùng IP vẫn follow thành công rực rỡ (tỷ lệ thành công cao).
* **Khi nick Cấp Khỏe (đã tốt nghiệp / cày nhiều follow) bị nhả:** TikTok mới thực sự cắm cờ IP / bão quét gateway. Lúc này các máy sau cùng IP đều bị nhả nốt (tỷ lệ lây nhiễm 100%).

### Quy Tắc Cầu Dao Chọn Lọc Theo Cấp Khỏe (User Invariant):
1. **CHỈ KÍCH HOẠT CẦU DAO IP 48H KHI NICK BỊ NHẢ LÀ NICK CẤP KHỎE (`was_graduated == True`):**
   - Chỉ khi nick cựu binh đã có bề dày follow an toàn bị nhả mới chứng minh IP có biến. Lúc này lập tức gọi `trip_ip_breaker(self.machine)` để bảo vệ máy partner.
2. **NICK CHƯA TỐT NGHIỆP (TÂN BINH / HỒI PHỤC 1 & 2) BỊ NHẢ: CẤM TUYỆT ĐỐI GIẬT CẦU DAO IP:**
   - Nick tự chịu án phạt cá nhân: tăng `fail_streak`, vào Cooldown (3 -> 7 -> 14 ngày dưỡng sinh lướt feed + up video, không follow), reset `probation_clean_days = 0`.
   - Cầu dao IP bỏ qua (`[IP_BREAKER_SKIPPED_TIER]`), giữ dải IP thông suốt cho Row 1/2 và máy partner.
   - **Chống Over-Engineering:** Không cần làm logic cộng dồn phức tạp; nick non tự vào tù độc lập.

---

## 2. Rút Ngắn Bậc Thang Hồi Phục: 2 Ngày Sạch / Nấc (Accelerated Probation)

### Vấn đề của cơ chế cũ (3 ngày sạch / nấc = 6 ngày mới tốt nghiệp):
* Do farm chạy theo lịch cách nhật (ngày chẵn / ngày lẻ), 6 ngày sạch thực tế ngoài đời kéo dài tới **14 – 15 ngày** (nửa tháng trời). Nick cựu binh lỡ sảy chân 1 lần phải bò lết quá lâu, làm mất sản lượng lớn.

### Quy Chuẩn 2 Ngày Sạch / Nấc (Tổng 4 Ngày Sạch Tốt Nghiệp):
* **HỒI PHỤC 1 (Probation Tier 1 - Tân binh đi dò & Mới ra tù, `clean_days < 2`):**
  - Quota: **1 – 2 lượt** / ca.
  - Tiến độ: Cần 2 ngày chạy sạch (~3 – 4 ngày ngoài đời thực).
* **HỒI PHỤC 2 (Probation Tier 2 - Tăng tải thử thách, `2 <= clean_days < 4`):**
  - Quota: **5 – 8 lượt** / ca.
  - Tiến độ: Cần thêm 2 ngày chạy sạch tiếp theo (~3 – 4 ngày ngoài đời thực).
* **TỐT NGHIỆP (Graduation - Lên Cấp Khỏe, `clean_days >= 4`):**
  - Đạt $\ge 4$ ngày sạch: Tự động tốt nghiệp (`graduated = True`, `fail_streak = 0`, xóa `probation_clean_days`), thăng hạng lên Nhóm Nick Khỏe (Full Quota 10 – 20 lượt).
  - Tổng thời gian hồi phục thực tế ngoài đời: **~8 – 9 ngày** (thay vì 15 ngày).

---

## 3. Quota Thử Lửa Đồng Nhất: 1 – 2 Lượt
* Gộp chung cả **Tân binh mới đủ tuổi đi dò (`age >= 21`, `video >= 6`)** và **Nick vừa mãn hạn tù quay lại**: đều bắt đầu ở Hồi phục 1 với quota **1 – 2 follow**.
* Đi dò 1–2 cái nếu thành công thì tích lũy ngày sạch; nếu bị nhả thì tự đi tù 3–14 ngày dưỡng sinh mà không làm cháy IP.

---

## 4. Vấn Đề Ngày Dưỡng Sinh Toàn Farm (Rest Day)
* Khi mỗi nick dính nhả đã tự động vào Cooldown dưỡng sinh cá nhân (3–14 ngày chỉ lướt feed + up video, không follow), bản thân nó **đã tự dưỡng sinh độc lập khi có biến**.
* Không cần ép toàn bộ farm nghỉ follow theo ngày cố định, tránh lãng phí tài nguyên của các nick và IP đang hoàn toàn khỏe mạnh.
