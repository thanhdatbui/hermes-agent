# Burst Follow & Hibernation Cadence (GemPhoneFarm Benchmark vs Taadaa Runner)

## 1. Bối cảnh thực nghiệm (Tháng 10/2026)
- **Đối tượng thử nghiệm:** Cohort tài khoản TikTok Tik 5 (đã đăng > 10 video, độ tuổi > 30 ngày).
- **Thực tế:** Cùng dàn Tik 5 reg chung đợt, hệ thống Taadaa Runner trước đây bị drop/ngọng follow, trong khi workflow GemPhoneFarm thực tế đạt **tỷ lệ giữ follow > 50%**.
- **Source đối soát:** Giải mã trực tiếp từ workflow gốc `TIKTOK-FLOW-TÌM-KIẾM-Thành-đạt_Protected.gemphonefarm` (389 nodes).

---

## 2. Chiến lược "Burst & Hibernate" (Đánh dồn dập & Ngủ đông sâu)

### A. Chu kỳ xoay tua slot (Slot Rotation & Rest Day)
- Mỗi thiết bị cài 8 slot TikTok (Tik 1 đến Tik 8).
- Không chạy đồng loạt 8 slot trong ngày:
  * **Ngày 1:** Chạy Slot 1, 2, 3 (mỗi slot cày 20–30 follow).
  * **Ngày 2:** Chạy Slot 4, 5, 6.
  * **Ngày 3:** Chạy Slot 7, 8.
  * **Ngày 4:** **Nghỉ toàn bộ cả máy (Rest Day)**.
- **Thời gian tiêu hóa gậy (Digestion Period):**
  * Mỗi tài khoản sau một phiên cày 20–30 follow sẽ được **ngủ đông từ 3 đến 4 ngày** trước khi đến lượt chạy tiếp theo.
  * Khi cày 20–30 follow/ngày, thuật toán Anti-Abuse gắn cờ nghi vấn tạm thời (Soft Probation). Thời gian nghỉ 3–4 ngày đủ để hệ thống đánh giá lại, nhận thấy không có hành vi spam liên tục nên tự động gỡ cờ và giữ lại > 50% lượt follow thật.
  * Giảm tải điểm bất thường phần cứng (Hardware Anomaly Score) vì mỗi ngày máy chỉ mở 3 app/profile thay vì đảo liên tục cả 8 nick.

### B. Cầu dao nhả 40% (40% Drop Circuit Breaker)
- Nếu trong một đợt chạy phát hiện tỷ lệ nhả follow > 40%:
  * Ngay lập tức dừng toàn bộ các slot còn lại trên máy.
  * Chuyển toàn bộ tài khoản sang chế độ **lướt nuôi (feed-session)** trong 1–2 ngày để tái tạo trust score trước khi mở lại follow.

---

## 3. Kiến trúc luồng & Nhịp độ thực thi trong GemPhone (Node Delays)

Khác với việc search liên tục gây áp lực bàn phím, script GemPhone tối ưu theo mô hình:
1. **Search đúng 1 Anchor:**
   - Đọc 1 UID Anchor từ file `tik1va2.txt`.
   - Vào Profile Anchor, ngâm từ **5.8s – 12.5s** (Node `uo18cfi`).
2. **Mở danh sách Following của Anchor:**
   - Tap tab `Đã follow` (Node `cicjh98` / `yuouuca`) để mở danh sách người mà Anchor đang theo dõi.
3. **Loop cào hàng loạt trong list (Repeat Tasks 6, 8, 10, 7):**
   - **Trước khi tap:** Chờ ngẫu nhiên `0.5s – 4.5s`.
   - **Tap nút Follow:** `//node[@text="Follow" or @text="Follow lại"]`.
   - **Vuốt cuộn danh sách:** `swipe-scroll up` (duration 750ms).
   - **Khoảng nghỉ giữa 2 lần follow (Inter-follow Delays):**
     * Node `7t6ltgz`: **5.2s – 18.5s**
     * Node `vc1yhpb`: **8.1s – 14.4s**
     * Node `7u8v7yd`: **7.2s – 15.4s**
   - **Tổng thời gian phiên:** 20–30 follow mất **7 đến 12 phút**. Nhịp đi rải rác mô phỏng hoàn toàn người dùng đang lướt tìm bạn bè.

---

## 4. Điểm khác biệt mấu chốt & Nghịch lý "Tự trói chân" (Root Cause Analysis)

### A. Thực trạng Farm đối soát (Tháng 10/2026):
- Khi quét 410 file trạng thái `runs/state/follow_state_*_row_*.json`:
  * **Row 1:** 65/80 nick bị khóa (`follow_failed: True`), 74 nick dính án phạt `fail_streak`.
  * **Row 2:** 71/78 nick bị khóa.
  * **Row 3 & 4:** 64–70 nick bị khóa (streak 1–3), tê liệt gần như toàn bộ.
  * **Tik 5:** Ông anh đã chạy follow ổn (>50% retention), trong khi bên ta Tik 3 & 4 vẫn còn "ngọng" nặng.

### B. So sánh cấu trúc điều hành:
| Tiêu chí | Chiến lược của ông anh | Hệ thống Taadaa Runner hiện tại |
| :--- | :--- | :--- |
| **Dung sai nhả (Tolerance)** | **Chấp nhận dung sai 40%:** Bấm 20–30 phát, nhả 8–10 phát (giữ 12–15 phát) ➔ **Thành công**, tích lũy follow đều. | **Zero-tolerance (0% dung sai):** Chỉ cần 1 phát bị nhả hoặc lag sync ➔ Dập tắt session ngay lập tức với 0 follow. |
| **Hậu quả khi bị nhả** | Nhả > 40% ➔ Dừng cho đi lướt nuôi 1–2 ngày (không tăng streak, không phạt giam cầm). | Tự giam nick vào Cooldown 3d ➔ 5d ➔ 7d ➔ 15d. Vừa mãn hạn lại bị ép nấc probation 1–2 fl/ngày ➔ Nick tê liệt vĩnh viễn. |
| **Vị trí thao tác** | Đứng im trong list Following của Anchor, tap + cuộn. | Mở Profile con qua `_path_b_verify`, xem video, back ra reload. |
| **Chu kỳ máy** | **Xoay tua 3 slot/ngày** (Ngày 1: 1-3, Ngày 2: 4-6, Ngày 3: 7-8, Ngày 4: Nghỉ). Ngủ đông 3–4 ngày/nick. | Chạy liên tục các ca nuôi feed cả 8 slot trên máy. Không có Rest Day toàn máy. |

### C. Bài học cốt lõi & Hướng điều chỉnh kiến trúc:
1. **Ân xá Farm:** Cần cơ chế dọn sạch cờ `follow_failed` và `fail_streak` ảo do hệ thống tự dập tắt để cứu dàn Row 3, 4, 5.
2. **Cầu dao theo Tỷ lệ phiên (Session-level Drop Rate):** Thay vì dừng ở nick đầu tiên, cho phép chạy đủ quota với delay sâu 8–18s. Nếu cuối phiên đối soát tỷ lệ nhả > 40% mới ngắt và chuyển sang lướt feed nuôi 1–2 ngày.
3. **Chu kỳ 3 slot + Ngủ đông 3–4 ngày:** Nick chạy 20–30 follow xong phải được nghỉ ngơi để TikTok thẩm định tự nhiên trước khi chạy tiếp.
