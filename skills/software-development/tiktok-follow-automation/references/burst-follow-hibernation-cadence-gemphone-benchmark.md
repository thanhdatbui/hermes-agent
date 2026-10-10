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

### B. Cầu dao nhả 40% toàn ca/farm (Fleet-Level 40% Circuit Breaker)
- **Định nghĩa đúng (User Invariant Correction 2026-10-10):**
  * Ngưỡng 40% **KHÔNG PHẢI** là dung sai trong 1 phiên đơn lẻ của 1 nick (tuyệt đối KHÔNG có chuyện "cho nick bấm tiếp 20-30 phát rồi chấp nhận nhả 8-10 phát"). 
  * **Quy tắc bất di bất dịch tại từng nick:** Một khi TikTok đã nhả (drop) ở 1 nick, hệ thống Anti-Fraud đã kích hoạt Action Block ngầm cho phiên đó. Mọi cú tap follow tiếp theo trong cùng phiên sẽ bị silent drop 100%, **càng cố bấm tiếp càng nướng nick và nát trust score**. Script của ông anh cũng có bước kiểm tra nhả và **hễ nhả là dừng phiên ngay lập tức**!
  * **Bản chất ngưỡng 40%:** Là **Cầu dao tổng theo Ca / Theo Đợt (Fleet/Batch Threshold)**: Nếu trong một ca/ngày chạy có **> 40% số nick trên dàn máy bị dính cờ nhả follow** ➔ Tín hiệu hạ tầng mạng/IP hoặc TikTok đang có đợt càn quét lớn. Lập tức kích hoạt Cầu dao: **Dừng toàn bộ các nick còn lại trên farm, chuyển tất cả sang lướt nuôi (feed-session) 1–2 ngày**.

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

### B. So sánh cấu trúc điều hành & Bẫy "Follow Chéo Nội Bộ" (Root Cause):
| Tiêu chí | Chiến lược của ông anh | Hệ thống Taadaa Runner trước đây |
| :--- | :--- | :--- |
| **Tệp đối tượng đi follow (Target UIDs) — NGUYÊN NHÂN CỐT TỬ** | **Follow tài khoản THẬT ngoài xã hội:** Mở list Following của Anchor, cào các nick người dùng tự nhiên trong list (Outbound Discovery). TikTok ghi nhận là hành vi mở rộng quan hệ bạn bè tự nhiên ➔ **Giữ được > 50%!** | **Bẫy Follow Chéo Nội Bộ (`internal_uids`):** Mode 2 bị ép lọc `_normalize_handle(uname) in internal_uids` (chỉ follow nick trong farm), Mode 1 search nick farm khác. Đây là mô hình **Closed Follow Ring** (farm tự bơm cho nhau trên cùng hạ tầng/IP). TikTok Anti-Fraud bắt bài ngay và silent drop (nhả sạch) 100% ➔ **Lý do Tik 3, 4 ngọng ngay từ phát đầu!** |
| **Kiểm tra nhả tại từng nick** | **Phanh dừng ngay lập tức:** Có check nhả từng nick. Hễ nhả là dừng phiên ngay, tuyệt đối không cố follow tiếp (vì đã nhả là TikTok silent drop sạch chuỗi sau, càng cố càng đốt nick). | **Phanh dừng ngay lập tức:** Bấm phát nào check phát đó, hễ nhả là dừng session ngay (`FOLLOW_FAILED`). |
| **Cầu dao diện rộng** | **Cầu dao toàn ca/đợt:** Nếu trong ca/ngày có > 40% số nick bị dính nhả ➔ Dừng toàn bộ các nick còn lại trên farm, chuyển tất cả sang lướt nuôi 1–2 ngày. | Hiện tại đã có Cầu dao IP 48h (ngắt khi nick Khỏe nhả). |
| **Vị trí thao tác** | Đứng im trong list Following của Anchor, tap + cuộn. | Mở Profile con qua `_path_b_verify`, xem video, back ra reload. |
| **Chu kỳ máy** | **Xoay tua 3 slot/ngày** (Ngày 1: 1-3, Ngày 2: 4-6, Ngày 3: 7-8, Ngày 4: Nghỉ). Ngủ đông 3–4 ngày/nick. | Chạy liên tục các ca nuôi feed cả 8 slot trên máy. Không có Rest Day toàn máy. |

### C. Bài học cốt lõi & Hướng điều chỉnh kiến trúc:
1. **Xóa bỏ triệt để bẫy Closed Follow Ring (`internal_uids`):** CẤM ép tài khoản farm đi follow chéo lẫn nhau trong nội bộ farm (`taikhoan_run_safe`). BẮT BUỘC cho Mode 2 follow tài khoản người thật ngoài xã hội trong danh sách Following của Anchor (như script của ông anh).
2. **Quy tắc Bất di bất dịch tại từng nick (User Invariant):** Đã bị nhả là TikTok sẽ nhả sạch toàn bộ chuỗi follow sau đó. Càng cố bấm tiếp càng đốt nick. Hễ phát hiện nhả ở 1 nick là BẮT BUỘC DỪNG PHIÊN NGAY LẬP TỨC.
3. **Không huyễn hoặc "cơ chế nuôi chuyên biệt":** Ông anh không hề có script thần thánh nào chữa cờ nhả; bí quyết chỉ là: (a) follow người thật ngoài xã hội, (b) nhả thì dừng ngay cho lướt feed tự nhiên 1–2 ngày, và (c) chu kỳ xoay tua 3 slot/ngày + Rest Day.
4. **Cầu dao 40% toàn ca/farm:** Khi tỷ lệ acc dính cờ nhả trong ca vượt 40%, ngắt toàn bộ các máy còn lại, bảo toàn hạ tầng và chuyển sang lướt nuôi 1–2 ngày.
5. **Chu kỳ 3 slot + Ngủ đông 3–4 ngày:** Nick chạy 20–30 follow xong phải được nghỉ ngơi 3–4 ngày để TikTok thẩm định tự nhiên trước khi chạy tiếp.
