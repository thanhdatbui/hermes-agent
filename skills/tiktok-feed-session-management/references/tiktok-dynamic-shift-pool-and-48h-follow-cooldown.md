# Cơ Chế Nuôi TikTok Dynamic Theo Ca, Phễu Sức Khỏe & Follow Cooldown 48h

## 1. Bối Cảnh & Mục Tiêu Nghiệp Vụ
- **Bài toán:** Thay thế chu kỳ 4 ngày lịch cứng nhắc (D0-D3 ép toàn farm chạy cùng row, nghỉ dưỡng sinh đồng loạt lãng phí tài nguyên) bằng **Cơ chế Nuôi Dynamic theo Ca kết hợp Quản Trị Tầng Account**.
- **Mục tiêu:**
  1. Mỗi máy tự động luân chuyển tuần tự qua đủ 8 nick của nó, không bao giờ để đói nick.
  2. Nick đề xuất và nick khỏe luôn được ưu tiên bốc chạy trước.
  3. Tách bạch hoàn toàn giữa **Quyền Nuôi (Feed + Upload video)** và **Quyền Follow (Follow Hook)**.

## 2. Ranh Giới Khung Ca & Pool Cố Định
- 🌅 **Ca 1 (Sáng: 06:00 & 08:00):** Từng máy CHỈ ĐƯỢC CHỌN trong Pool `{Row 1, Row 2, Row 7}`.
- ☀️ **Ca 2 (Trưa: 12:00 & 14:00):** Từng máy CHỈ ĐƯỢC CHỌN trong Pool `{Row 3, Row 4, Row 8}`.
- 🌙 **Ca 3 (Tối: 18:00 & 20:00):** 
  - Ngày 1 & 2: Chạy trong Pool `{Row 5, Row 6}`.
  - Ngày 3: Bốc **Row Động** (chuyên nuôi dưỡng sinh / xả phạt).
- 🔒 **Luật S2 bám S1 (Tuyệt Đối 100%):** Trong cùng 1 ca, Phiên 2 bám chặt 100% nick mà Phiên 1 của máy đó đã chọn (Snapshot Freeze, không tính toán lại phễu ở Phiên 2).

## 3. Thứ Bậc Phễu Bốc Nick (Health Selection Funnel)
- **Các Ca Thường (Ca 1, Ca 2, Ca 3 Ngày 1-2):**
  Bốc tuần tự theo chu kỳ độ khỏe:
  $$\text{Nick Khỏe} \longrightarrow \text{Đề xuất} \longrightarrow \text{Hồi phục 2} \longrightarrow \text{Hồi phục 1} \longrightarrow \text{Nick Nhả} \longrightarrow \text{Nick Yếu}$$
  - Đảm bảo chạy đủ các nick trong Pool của ca đó rồi mới quay vòng lặp lại từ đầu.
- **Riêng Ca 3 Ngày 3 (Ca chuyên nuôi & xả phạt):**
  Bốc tự do theo phễu dưỡng sinh:
  $$\text{Đề xuất (giữ đà)} \longrightarrow \text{Nick Nhả (lướt feed xả phạt)} \longrightarrow \text{Nick Yếu (bổ sung clip)}$$

## 4. Van Khóa Follow Tự Động (Follow Cooldown 48h)
- **Tách biệt 2 quyền:** Mọi nick bốc vào ca đều được lướt feed và đăng video bình thường.
- **Quy tắc Cooldown 48h:**
  - Bình thường một nick cách gần 72h mới quay lại lượt chạy, nên Cooldown 48h là khoảng đệm an toàn tuyệt đối.
  - Chỉ tính khi nick **đã từng đi follow** (kể cả thành công hay thất bại/bị phạt).
  - Nếu lần follow gần nhất `< 48h`: Kích hoạt `rest_day_no_follow: true` (CHỈ lướt feed + up video, TẮT HOÀN TOÀN FOLLOW).
  - Nếu lần follow gần nhất $\ge 48h$: Cấp phép follow bình thường (vẫn phải qua các gate an toàn: video $\ge 6$, tuổi $\ge 21$ ngày, feed ấm $\ge 3$ swipes).
- **Fail-Closed & Telemetry:** Nếu state file bị rỗng hoặc lỗi parse $\to$ Mặc định TẮT FOLLOW để bảo vệ nick, và BẮT BUỘC ghi log/bắn telemetry lỗi lên Watchdog Report để phân biệt lỗi script với nghỉ tự nhiên.

## 5. Cơ Chế Báo Cáo Two-Phase Commit Của Watchdog (Chống Mất Report)
- Khi Watchdog xuất report Telegram:
  1. **Phase 1 (Pending Claim):** Lưu `session_key` và `message` vào `pending_delivery` trong state file; TUYỆT ĐỐI KHÔNG commit vào `reported_sessions`.
  2. **Phase 2 (Confirmation):** Ở lượt quét kế tiếp, kiểm tra `last_delivery_error` trong `jobs.json` của Hermes:
     - Nếu có lỗi mạng socket/proxy timeout: Giữ pending, in lại message để scheduler retry.
     - Nếu không có lỗi (đã giao tin an toàn): Mới chính thức chuyển `session_key` vào `reported_sessions` và xóa pending.
