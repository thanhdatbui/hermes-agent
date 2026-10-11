# Row Nurture Starvation & 4-Day Cycle Monitoring Invariants

## 1. Ngưỡng Cảnh Báo "Bỏ Đói" (Starvation Threshold) vs Độ Dài Chu Kỳ

### Sai lầm chết người (Pitfall):
- Đặt ngưỡng cảnh báo bỏ đói (Starvation threshold) thấp hơn độ dài của 1 chu kỳ xoay tua hoàn chỉnh (ví dụ: chu kỳ 4 ngày = 96 giờ, nhưng lại đặt ngưỡng 48 giờ).
- **Hậu quả:** Gây ra bão cảnh báo giả (false-alarm storm). Các Row đang nằm chờ lượt quay vòng tự nhiên (như Row 5, 6, 7, 8) sẽ liên tục bị gắn cờ đỏ `STARVED` dù script và hệ thống đang hoạt động hoàn toàn bình thường.

### Invariant bất biến:
- Trong mô hình xoay tua $N$-ngày (hiện tại Farm Taadaa là **chu kỳ 4 ngày**):
  $$\text{Starvation Threshold} \ge N \times 24\text{h} \quad (\text{chuẩn: } 96\text{h}, \text{ buffer an toàn: } 100\text{h})$$
- Mọi Row từ Row 1 đến Row 8 bắt buộc phải có ít nhất $\ge 1$ lần được nuôi thành công trong cửa sổ 96 giờ.
- CẤM TUYỆT ĐỐI đặt ngưỡng 48h trong chu kỳ 4 ngày.
- Chỉ khi một Row vượt quá 96 giờ mà không có bất kỳ phiên chạy thành công nào, hệ thống mới được phép kích hoạt `🚨 [STARVATION ALERT]`.

---

## 2. Kiến Trúc 3 Trụ Cột Giám Sát Sức Khỏe Farm (Three-Pillar Farm Health Monitoring)

Hệ thống giám sát vận hành Farm bắt buộc bao phủ đầy đủ 3 tầng độc lập:
1. **Trụ cột 1 - Sức Khỏe Cụm Máy (`🏥 Fleet Health`):**
   - Giám sát tầng phần cứng, kết nối USB/Hub, ADB liveness, IP/Proxy tunnel, phát hiện máy đơ/mất mạng.
2. **Trụ cột 2 - Sức Khỏe Follow (`🩺 Follow Health`):**
   - Giám sát tầng tài khoản TikTok: Nick Khỏe, Hồi phục Nấc 1/2, Án phạt Cooldown do bị TikTok nhả follow.
3. **Trụ cột 3 - Sức Khỏe Nuôi Acc 8 Row (`🌾 Row Nurture Health / Starvation Watchdog`):**
   - Giám sát tầng **Điều phối & Kịch bản theo Row**.
   - Phát hiện sớm các lỗi âm thầm: Lỗi logic script, hỏng mapping Excel theo Row, lỗi đường dẫn video cào, kẹt process launcher khiến một Row cụ thể bị bỏ quên nhiều ngày liên tiếp.

---

## 3. Quy Cách Báo Cáo & Phân Loại Trạng Thái Nuôi 8 Row

### Phân loại trạng thái trong cửa sổ 96h:
- 🟢 **Bình thường (Normal):** Thời gian từ ca chạy cuối $\le 72\text{h}$.
- 🟡 **Sắp đến lượt (Pending Rotation):** Thời gian từ ca chạy cuối từ $72\text{h} - 96\text{h}$ (đang chờ ca theo đúng lịch).
- 🔴 **BỊ BỎ ĐÓI (STARVED):** Thời gian từ ca chạy cuối $> 96\text{h}$ hoặc chưa từng chạy $\rightarrow$ **Cần can thiệp khẩn cấp**.

### Định dạng hiển thị trong Báo Cáo 6H Watchdog:
```text
🌾 【SỨC KHỎE NUÔI 8 ROW (96H)】
• Tiến độ: R1:🟢3h | R2:🟢27h | R3:🟢45h | R4:🟢21h | R5:🟢39h | R6:🟢15h | R7:🟢58h | R8:🟢34h
```
* Nếu có Row bị Starved:
  * Watchdog tự động thêm dòng: `• 🚨 CẢNH BÁO BỎ ĐÓI (>96h): Row [X]`
  * Header tin nhắn Telegram được nâng cấp thành:
    `🚨 [CẢNH BÁO BỎ ĐÓI] PHÁT HIỆN ROW [X] > 96H CHƯA NUÔI THÀNH CÔNG! - <Tên Ca> (Row <Current>)`

---

## 4. Kỷ Luật Lập Lịch Chu Kỳ 4 Ngày (4-Day Cycle Modulo 4 Invariants)

### Bảng phân bổ ca & phiên (3 ca/ngày):
- **Ngày 1 (Day 1 - Bảo vệ dải IP sau ngày nghỉ):**
  - Ca 1 (Sáng: 06:00, 08:00): Bốc Row 1 hoặc Row 2 (hai row khỏe nhất, cấm đưa Row 7/acc yếu vào ca sáng Ngày 1 để tránh nổ cầu dao IP).
  - Ca 2 (Trưa: 12:00, 14:00): Bốc Row 3 hoặc Row 4.
  - Ca 3 (Tối: 18:00, 20:00): Bốc Row 5 hoặc Row 6.
- **Ngày 2 (Day 2 - Bù trừ đối xứng):**
  - Ca 1 (Sáng): Bốc Row còn lại trong cặp (1, 2).
  - Ca 2 (Trưa): Bốc Row còn lại trong cặp (3, 4).
  - Ca 3 (Tối): Bốc Row còn lại trong cặp (5, 6).
- **Ngày 3 (Day 3 - Xử lý dải row phụ & dưỡng sinh sớm):**
  - Ca 1 (Sáng): Row 7.
  - Ca 2 (Trưa): Row 8.
  - Ca 3 (Tối): Ca dưỡng sinh luân phiên cho Row 3 / Row 4 (dàn acc ăn nhả/cooldown cần rửa trust). Cờ `is_rest_day = True`, `_follow_rate = 0`.
- **Ngày 4 (Day 4 - Dưỡng sinh xả tải toàn farm):**
  - Cả 3 ca đều chạy dưỡng sinh (`is_rest_day = True`, `_follow_rate = 0`):
    - Sáng: Row 3
    - Trưa: Row 4
    - Tối: Luân phiên Row 5 hoặc Row 6.

---

## 5. Tách Biệt Triệt Để Án Phạt Follow Cooldown vs Quyền Upload Video

### Quy tắc bất biến:
- **Án phạt Follow Cooldown chỉ cấm bấm nút follow:** Khi nick dính án nhả follow hoặc đang trong ca dưỡng sinh, bắt buộc `_follow_rate = 0` để chỉ lướt feed rửa trust.
- **TUYỆT ĐỐI KHÔNG CẤM UPLOAD VIDEO:**
  - Ca dưỡng sinh và nick dính Follow Cooldown **VẪN PHẢI UPLOAD ĐÚNG 1 VIDEO/NGÀY** để duy trì nhịp hoạt động tự nhiên của Creator.
  - Cờ `-AllowUploadHook` bắt buộc **LUÔN ĐƯỢC BẬT ở cả Phiên 1 (Feed) và Phiên 2 (Feed + Hook)** trong mọi ca chạy.
  - CẤM viết rào cản `if not is_rest_day` chặn upload hook.
  - Sổ cái giao dịch `shift_upload_history.json` là cơ chế chốt hạ duy nhất đảm bảo tính idempotency: Mỗi nick chỉ upload thành công đúng 1 video trong ngày, phiên sau tự động bỏ qua nếu phiên trước đã upload thành công.

