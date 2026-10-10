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

## 4. Điểm khác biệt mấu chốt so với Taadaa Runner hiện tại

| Tiêu chí | GemPhoneFarm Workflow | Taadaa Runner (Hiện tại) |
| :--- | :--- | :--- |
| **Vị trí thao tác** | Đứng im trong list Following của Anchor, tap + cuộn. | Mở Profile con qua `_path_b_verify`, xem video, back ra reload. |
| **Áp lực Activity UI** | Cực thấp (1 Activity duy nhất). | Cực cao (liên tục switch Activity Profile ↔ List). |
| **Đối soát nhả follow** | **Không verify reload.** Chấp nhận nhả một phần, giữ lại phần còn lại. | Verify 100% từng nick. Nhả hoặc sync chậm là gắn `FOLLOW_FAILED`. |
| **Hậu quả khi bị nhả** | Không tự giam nick. Chu kỳ sau chạy tiếp. | Tự giam nick vào Cooldown 48h ➔ 4 ngày ➔ 7 ngày (tự khóa chân). |

### Bài học cốt lõi:
- Việc verify quá sớm và quá chặt chẽ (`_path_b_verify` 100% + Pull-to-refresh) vô tình biến các lỗi sync delay hoặc cờ nhẹ thành án phạt nặng, khiến dàn nick tự rơi vào trạng thái đóng băng ("ngọng").
- Để scale sản lượng follow an toàn cho dàn nick đã có video (> 10 video): Áp dụng nhịp nghỉ sâu giữa các lần tap (8–18s) trong cùng 1 list Anchor + chu kỳ Burst 20–30 follow kèm ngủ đông 3–4 ngày.
