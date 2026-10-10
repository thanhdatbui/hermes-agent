# Burst Follow & Hibernation Cadence (GemPhoneFarm Benchmark vs Taadaa Runner)

## 1. Bối cảnh thực nghiệm (Tháng 10/2026)
- **Đối tượng thử nghiệm:** Cohort tài khoản TikTok Tik 5 (đã đăng > 10 video, độ tuổi > 30 ngày).
- **Thực tế:** Cùng dàn Tik 5 reg chung đợt, hệ thống Taadaa Runner trước đây bị drop/ngọng follow (kể cả Tik 3, Tik 4 đã có 10–12 video), trong khi workflow GemPhoneFarm thực tế đạt **tỷ lệ giữ follow > 50%**.
- **Đặc điểm mô hình của cả 2 bên:**
  * Cả 2 bên đều chạy **100% Follow Chéo Nội Bộ (Internal Cross-Follow)**: Mode 1 search UID nội bộ, Mode 2 follow anchor (mà anchor cũng được build từ Mode 1 nội bộ trước đó). Không bên nào có follow người ngoài xã hội.
  * Cả 2 bên đều có cơ chế **Kiểm tra nhả follow (Release Check)**: Hễ phát hiện bị nhả là phanh dừng ngay lập tức.

---

## 2. Các điểm cốt tử giải mã vì sao Tik 5 của ông anh chạy ngon (>50%) còn Tik 3, Tik 4 bên mình ngọng

### A. Cửa ngõ Anchor là Canary Gate Hợp Lệ (User Correction 2026-10-10)
- **Khẳng định nguyên lý:** Việc kiểm tra follow Anchor (`_ensure_anchor_followed`) trước khi mở danh sách con là **HOÀN TOÀN ĐÚNG ĐẮN VỀ MẶT THUẬT TOÁN**:
  * Nếu một tài khoản follow Anchor mà đã bị TikTok âm thầm rollback (nhả follow) thì tài khoản đó đang nằm trong diện **High Risk / Action Block ngầm**. Nếu cố mở list con ra bấm tiếp thì 100% các cú follow sau cũng sẽ bị nhả sạch.
  * Việc phanh dừng ngay tại cửa Anchor là chốt chặn **Fail-Closed chuẩn mực**, bảo vệ nick không bị nướng thêm hành động rác và tránh bị phạt nặng hơn.
- **Bản chất vì sao Anchor bị nhả:**
  * Không phải do cơ chế check Anchor bị sai hay lỗi code (đã đối soát DB xác nhận nhả thật 100%).
  * Nguyên nhân gốc rễ là **Tài khoản chưa kịp hồi phục (chưa tiêu hóa cờ phạt)** do mật độ chạy trên máy quá dày (chạy liên tục các slot/ngày, thiếu Rest Day xả bất thường phần cứng). Khi mật độ quá dày, thiết bị và nick bị gắn cờ từ trước, nên vừa chạm vào cú follow đầu tiên (ở Anchor) là bị server drop ngay lập tức.

### B. Quy tắc Bất di bất dịch khi bị nhả (User Invariant 2026-10-10)
- **ĐÃ BỊ NHẢ LÀ SẼ NHẢ HẾT CẢ PHIÊN:** Khi TikTok backend đã kích hoạt Action Block ngầm (silent drop) đối với một tài khoản, mọi cú tap follow tiếp theo trong cùng phiên sẽ bị drop 100%. **Càng cố follow tiếp càng chết nick và nát trust score**.
- Script của ông anh cũng có bước kiểm tra nhả và **hễ phát hiện nhả là dừng ngay lập tức**.
- CẤM TUYỆT ĐỐI tư tưởng "chấp nhận dung sai 40% để bấm tiếp trong cùng 1 phiên".

### C. Bản chất Cầu dao 40% (Fleet-Level 40% Circuit Breaker)
- Ngưỡng 40% trong ghi chú của ông anh: *"Nếu tỉ lệ nhả quá 40% thì dừng toàn bộ tik cho đi nuôi 1,2 ngày"*.
- Đây là **Cầu dao tổng theo Ca / Theo Đợt (Fleet/Batch Threshold)**:
  * Nếu trong một ca/ngày chạy mà có **> 40% số nick trên dàn máy bị dính cờ nhả follow** ➔ Tín hiệu TikTok đang siết chặt thuật toán hoặc dải IP/hạ tầng bị soi.
  * Xử lý: **Dừng toàn bộ các nick còn lại trên farm, hoãn follow và chuyển tất cả sang lướt nuôi 1–2 ngày**.

### D. Chu kỳ xoay tua 3 Tik/ngày + Rest Day toàn máy (Burst & Hibernate)
- Ghi chú thực chiến của ông anh: *"8 tick mỗi tick ngày đi 3 tick, đi hết 8 tick thì nghỉ 1 ngày. Ngày thứ 2 chạy cảm thấy follow ok thì làm tiếp còn k thì lướt nuôi"*.
- **Cách vận hành:**
  * Mỗi máy cài 8 nick. Mỗi ngày chỉ chạy **3 nick (3 row)**.
    * Ngày 1: Tik 1, 2, 3 (mỗi nick cày 20–30 follow).
    * Ngày 2: Tik 4, 5, 6.
    * Ngày 3: Tik 7, 8.
    * Ngày 4: **CẢ MÁY NGHỈ 1 NGÀY (Rest Day)**.
  * **Thời gian tiêu hóa gậy (Digestion Period):** Mỗi nick sau một cữ cày 20–30 follow sẽ được **ngủ đông từ 3 đến 4 ngày** mới đến lượt tiếp theo. Thời gian nghỉ dài giúp TikTok tự động gỡ cờ nghi vấn và giữ lại lượng follow thật (>50%).
  * Giảm tải điểm bất thường phần cứng (Hardware Anomaly Score) vì mỗi ngày máy chỉ mở 3 app thay vì đảo liên tục cả 8 nick.
- **Không huyễn hoặc "cơ chế nuôi chuyên biệt":** Ông anh không có script thần thánh nào để chữa cờ nhả. Khi bị nhả thì chỉ đơn giản là dừng follow, cho nick lướt feed thông thường 1–2 ngày để tự hồi phục.

---

## 3. Nhịp độ thực thi chi tiết trong GemPhone (Node Delays)
Trích xuất từ `TIKTOK-FLOW-TÌM-KIẾM-Thành-đạt_decrypted.json` (389 nodes):
1. **Search Anchor:** Search đúng 1 UID Anchor từ file `tik1va2.txt`, ngâm profile **5.8s – 12.5s** (Node `uo18cfi`).
2. **Mở danh sách:** Bấm tab `Đã follow` (Node `cicjh98` / `yuouuca`) mở danh sách Following của Anchor.
3. **Loop cào trong list:**
   - Trước khi tap: ngập ngừng `0.5s – 4.5s`.
   - Tap nút: `//node[@text="Follow" or @text="Follow lại"]`.
   - Vuốt cuộn danh sách: `swipe-scroll up` (750ms).
   - Nghỉ sâu giữa 2 lần follow: Node `7t6ltgz` (5.2s–18.5s), Node `vc1yhpb` (8.1s–14.4s), Node `7u8v7yd` (7.2s–15.4s).
   - 20–30 follow chạy rải rác kéo dài từ **7 đến 12 phút**.

---

## 4. Checklist Khắc Phục Cho Taadaa Runner

1. [x] **Giữ vững Canary Gate Anchor (`_ensure_anchor_followed`):** Chốt chặn Fail-Closed bảo vệ nick không bị nướng thêm lượt follow rác khi đang dính cờ nhả ngầm (đối soát DB xác nhận nhả thật).
2. [x] **Giữ nguyên nguyên tắc dừng ngay khi bị nhả (Fail-Closed Invariant):** Đã nhả 1 phát là dừng toàn bộ session của nick đó ngay lập tức (vì đã nhả là nhả sạch phía sau), cấm tư tưởng cố follow bù trong session.
3. [ ] **Triển khai thử nghiệm lịch xoay tua 3 slot/máy/ngày + Rest Day toàn máy:** Áp dụng chu kỳ 4 ngày (3 ngày chạy xoay tua 8 slot, ngày thứ 4 nghỉ cả máy để nick có 3–4 ngày tiêu hóa cờ).
4. [ ] **Kích hoạt Cầu dao 40% toàn ca:** Nếu trong 1 ca chạy có > 40% số máy bị nhả follow, tự động abort toàn bộ ca follow đó và chuyển farm sang lướt feed 24h–48h.
