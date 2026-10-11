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

### Quy tắc Bắt Buộc: Phân Tách Báo Cáo Sức Khỏe Nuôi Theo Từng Cụm Farm (Dual-Farm Split Invariant)
- **Pitfall chết người:** Gộp chung tiến độ 8 Row của toàn bộ hệ thống hoặc chỉ trỏ `live_root` vào `runtime/kibe/live` khiến Farm Admin (Máy 201-280) bị tàng hình. Nếu Kibe chạy xong Row 3 nhưng Admin bị kẹt USB/rớt máy bỏ lỡ Row 3, hệ thống vẫn báo xanh 🟢 giả tạo vì chỉ nhìn Kibe.
- **Invariant bất biến:** Báo cáo sức khỏe nuôi 8 Row BẮT BUỘC phải phân tách độc lập theo từng cụm (Farm Kibe Máy 1-80 và Farm Admin Máy 201-280).
- Mỗi cụm đọc đúng thư mục `runtime/<cluster>/live` tương ứng, có chuỗi tiến độ R1..R8 riêng và cảnh báo Starvation riêng, đặt trực tiếp dưới khối báo cáo của cụm đó.

### Định dạng hiển thị trong Báo Cáo Watchdog:
```text
🏢 【FARM KIBE - MÁY 1-80】
... (Lướt feed, tim, follow) ...
🌾 Sức khỏe 8 Row: R1:🟢8h | R2:🟢32h | R3:🟢2h | R4:🟢26h | R5:🟢44h | R6:🟢20h | R7:🟢62h | R8:🟢38h

🏢 【FARM ADMIN - MÁY 201-280】
... (Lướt feed, tim, follow) ...
🌾 Sức khỏe 8 Row: R1:🟢8h | R2:🟢32h | R3:🟢2h | R4:🟢28h | R5:🟢46h | R6:🟢22h | R7:🟢64h | R8:🟢40h
```
* Nếu một Farm có Row bị Starved (> 96h):
  * Watchdog tự động thêm dòng cảnh báo ngay dưới Farm đó: `• 🚨 CẢNH BÁO BỎ ĐÓI (>96h): Row [X]`
  * Header tin nhắn Telegram được nâng cấp thành:
    `🚨 [CẢNH BÁO BỎ ĐÓI] PHÁT HIỆN ROW [X] CỤM [KIBE/ADMIN] > 96H CHƯA NUÔI THÀNH CÔNG!`

---

### Phân Định Ranh Giới Giám Sát: Telegram (Vĩ Mô) vs Web Dashboard Port 1905 (Vi Mô)
- **Quy tắc phân công kiến trúc:**
  1. **Telegram Watchdog = Giám sát VĨ MÔ cấp Fleet & Row:**
     * Chỉ báo cáo tiến độ 8 Row theo từng Farm và tỷ lệ tổng thể.
     * CẤM TUYỆT ĐỐI liệt kê chi tiết từng tài khoản lên Telegram (quy mô 1,280 accounts sẽ gây tràn ngưỡng 4,096 ký tự và tạo bão spam tin nhắn).
     * Chỉ đưa cảnh báo tóm tắt số lượng ngoại lệ nếu có nick bị starved cá biệt (>96h) kèm link trỏ về Dashboard.
  2. **Web Dashboard (`http://127.0.0.1:1905`) = Giám sát VI MÔ cấp từng Account:**
     * Là nơi duy nhất tra cứu chi tiết toàn bộ 1,280 accounts (Kibe + Admin).
     * Bắt buộc có Tab/Chế độ lọc `🌾 Sức Khỏe Nuôi Acc`:
       - Cho phép **Sort 1-click "Đói nhất lên đầu"** theo `last_nurtured` / `hours_since_last_nurture`.
       - Bộ lọc nhanh: Theo Cụm (Kibe / Admin), theo Row (1-8), hoặc chỉ hiện nick bị bỏ đói (`🔴 > 96h`).
       - Bóc tách nguyên nhân kẹt: App crash, mất ADB, lỗi proxy, hoặc trống slot.

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

