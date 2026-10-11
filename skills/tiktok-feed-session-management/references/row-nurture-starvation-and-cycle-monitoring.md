# Row Nurture Starvation & 4-Day Cycle Monitoring Invariants

## 1. Ngưỡng Cảnh Báo "Bỏ Đói" (Starvation Threshold) vs Độ Dài Chu Kỳ

### Sai lầm chết người (Pitfall):
- Đặt ngưỡng cảnh báo bỏ đói (Starvation threshold) thấp hơn độ dài của 1 chu kỳ xoay tua hoàn chỉnh (ví dụ: chu kỳ 4 ngày = 96 giờ, nhưng lại đặt ngưỡng 48 giờ).
- **Hậu quả:** Gây ra bão cảnh báo giả (false-alarm storm). Các Row đang nằm chờ lượt quay vòng tự nhiên (như Row 5, 6, 7, 8) sẽ liên tục bị gắn cờ đỏ `STARVED` dù script và hệ thống đang hoạt động hoàn toàn bình thường.

### Invariant bất biến:
- Trong mô hình xoay tua $N$-ngày (hiện tại Farm Taadaa là **chu kỳ 4 ngày = 96 giờ**):
  $$\text{Chu Kỳ Nuôi} = 96.0\text{h}, \quad \text{Dung Sai Trễ/Retry} = 12.0\text{h}, \quad \text{Ngưỡng Bỏ Đói (Starvation Threshold)} = 108.0\text{h}$$
- CẤM TUYỆT ĐỐI đặt ngưỡng 48h trong chu kỳ 4 ngày.
- Mọi Row từ Row 1 đến Row 8 được thiết kế để quay vòng lặp lại **chính xác 96 giờ** (4 ngày $\times$ 24 giờ).
- Dung sai 12 giờ cho phép các ca bị trễ do nghẽn ADB, retry runner hoặc lệch lịch ca không kích hoạt báo động giả.
- Chỉ khi một Row vượt quá **108 giờ** mà không có bất kỳ phiên chạy thành công nào, hệ thống mới kích hoạt `🚨 [STARVATION ALERT]`.

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
     * Bắt buộc có Tab/Chế độ lọc `🌾 Sức Khỏe Nuôi Acc` (Endpoint: `/api/nurture-health`):
       - Cho phép **Sort 1-click "Đói nhất lên đầu"** theo `last_nurtured` / `hours_since_last_nurture`.
       - Bộ lọc nhanh: Theo Cụm (Kibe / Admin), theo Row (1-8), hoặc chỉ hiện nick bị bỏ đói (`🔴 > 96h`).
       - Bóc tách nguyên nhân kẹt: App crash, mất ADB, lỗi proxy, hoặc trống slot.
     * **Quy tắc Mapping Row (Slot `tik` Invariant):**
       - **Pitfall:** Suy diễn Row từ số máy `may` bằng công thức phân bổ `((may - 1) // 8) + 1`.
       - **Thực tế Taadaa Farm:** Mỗi điện thoại chứa 8 accounts ứng với 8 slot Row 1 đến Row 8. Trường `tik` trong bảng SQLite `farm_account_info` CHÍNH LÀ Row slot của nick trên thiết bị (`tik = 1..8`).
       - **Bắt buộc:** Map `row_num = int(tik)` (fallback 1 nếu null/lỗi). CẤM TUYỆT ĐỐI dùng số máy `may` để suy diễn Row.
     * **Kỹ thuật Quét Live Artifact O(1) (CẤM `rglob("*")`):**
       - **Pitfall:** Dùng `Path(live_root).rglob("*")` để tìm folder `row-*`. Trong farm 80 máy chạy 60 ngày, `rglob("*")` duyệt đệ quy qua >200,000 files/dirs, gây nghẽn đĩa và timeout tiến trình >600s.
       - **Bắt buộc:** Chỉ quét 2 cấp phẳng:
         1. Cấp 1: `root_path.glob("????-??-??")`, chỉ lấy tối đa 7 ngày mới nhất.
         2. Cấp 2: Trong mỗi ngày, chỉ duyệt `d_dir.glob("row-*")` để bóc tách timestamp từ tên folder `row-<R>-<HHMMSS>`. Thời gian quét hoàn tất <0.05 giây.

---

## 4. Kỷ Luật Lập Lịch Chu Kỳ 4 Ngày: Randomized Parity & Anti-Overengineering

### Chống bẫy Over-Engineering (Pitfall: "Permutation per-machine trong cùng 1 ca"):
- **Sai lầm:** Cố gắng cho mỗi máy chạy một Row khác nhau trong cùng một ca (ví dụ Máy 1 chạy Row 1, Máy 2 chạy Row 2 lúc 06:00).
- **Hậu quả:** 
  1. Phá vỡ cấu trúc batch runner PowerShell lõi (`run-feed-session.ps1` nhận 1 tham số `-Row` cho cả 80 workers).
  2. Phá vỡ cấu trúc thư mục artifact `live/YYYY-MM-DD/row-X-HHMMSS/` và làm tê liệt toàn bộ parser của Watchdog.
  3. Khiến tiêu đề và đối soát của Watchdog Telegram bị sai lệch (không thể báo cáo "Ca 1 hoàn tất (Row 1)" khi máy này chạy R1 máy kia chạy R2).

### Cơ chế Chuẩn Hóa: Randomized Parity 4-Day Cycle (Chu kỳ 4 ngày đảo nhóm chẵn/lẻ ngẫu nhiên):
Vẫn giữ nguyên **1 Ca = 1 Row trên toàn bộ fleet** để đảm bảo tính đồng bộ, ổn định và báo cáo chính xác, nhưng triệt tiêu hoàn toàn khả năng TikTok "bắt bài" chu kỳ bằng cách **đảo ngẫu nhiên thứ tự nhóm Chẵn/Lẻ theo từng chu kỳ 4 ngày**:
- Mỗi chu kỳ 4 ngày (`cycle_idx = (ordinal - BASE_ORDINAL) // 4`), hệ thống tự động gieo xúc xắc ngẫu nhiên (Pseudo-random Hash Seed):
  * **Nếu chu kỳ bắt đầu bằng Nhóm Lẻ (Odd-first):**
    - **Ngày 1 (Day 1):** Ca 1 (Sáng) = Row 1 | Ca 2 (Trưa) = Row 3 | Ca 3 (Tối) = Row 5.
    - **Ngày 2 (Day 2):** Ca 1 (Sáng) = Row 2 | Ca 2 (Trưa) = Row 4 | Ca 3 (Tối) = Row 6.
  * **Nếu chu kỳ bắt đầu bằng Nhóm Chẵn (Even-first):**
    - **Ngày 1 (Day 1):** Ca 1 (Sáng) = Row 2 | Ca 2 (Trưa) = Row 4 | Ca 3 (Tối) = Row 6.
    - **Ngày 2 (Day 2):** Ca 1 (Sáng) = Row 1 | Ca 2 (Trưa) = Row 3 | Ca 3 (Tối) = Row 5.
- **Ngày 3 (Day 3 - Về đích & Xả tối):**
  * Ca 1 (Sáng: 06h & 08h): **Row 7** (Cày thực tế).
  * Ca 2 (Trưa: 12h & 14h): **Row 8** (Cày thực tế).
  * Ca 3 (Tối: 18h & 20h): **Dưỡng sinh nick yếu** (Tắt follow, lướt feed + up 1 video).
- **Ngày 4 (Day 4 - Nghỉ xả tải toàn Farm):**
  * Cả 3 Ca (Sáng, Trưa, Tối): **Dưỡng sinh nick yếu** (bao gồm cả nick ăn nhả follow lẫn nick non chưa đủ 10 video).
  * **Tắt 100% follow** (`_follow_rate = 0`), thuần túy lướt feed rửa trust + đăng 1 video/ngày nếu nick chưa đăng.
- **Bảo toàn nhịp sinh học (User Persona):**
  * Cặp `{Row 1, Row 2}` luôn luôn lướt Sáng (06h & 08h).
  * Cặp `{Row 3, Row 4}` luôn luôn lướt Trưa (12h & 14h).
  * Cặp `{Row 5, Row 6}` luôn luôn lướt Tối (18h & 20h).
  * Thói quen giờ giấc của từng tài khoản được giữ vững, không bao giờ bị xáo trộn giờ lướt.

---

## 5. Tách Biệt Triệt Để Án Phạt Follow Cooldown vs Quyền Upload Video

### Quy tắc bất biến:
- **Án phạt Follow Cooldown chỉ cấm bấm nút follow:** Khi nick dính án nhả follow hoặc đang trong ca dưỡng sinh, bắt buộc `_follow_rate = 0` để chỉ lướt feed rửa trust.
- **TUYỆT ĐỐI KHÔNG CẤM UPLOAD VIDEO:**
  - Ca dưỡng sinh và nick dính Follow Cooldown **VẪN PHẢI UPLOAD ĐÚNG 1 VIDEO/NGÀY** để duy trì nhịp hoạt động tự nhiên của Creator.
  - Cờ `-AllowUploadHook` bắt buộc **LUÔN ĐƯỢC BẬT ở cả Phiên 1 (Feed) và Phiên 2 (Feed + Hook)** trong mọi ca chạy.
  - CẤM viết rào cản `if not is_rest_day` chặn upload hook.
  - Sổ cái giao dịch `shift_upload_history.json` là cơ chế chốt hạ duy nhất đảm bảo tính idempotency: Mỗi nick chỉ upload thành công đúng 1 video trong ngày, phiên sau tự động bỏ qua nếu phiên trước đã upload thành công.

