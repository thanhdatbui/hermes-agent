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

### C. Cầu dao IP MikroTik là Bản Nâng Cấp Cao Cấp của Luật Nhả 40% (User Invariant 2026-10-10)
- Nguyên lý của ông anh: *"Nếu tỉ lệ nhả quá 40% thì dừng toàn bộ tik cho đi nuôi 1,2 ngày"*. Đây là cơ chế bảo vệ dạng "búa tạ" thô sơ ở cấp toàn farm khi không kiểm soát được IP theo từng thiết bị.
- **Bản nâng cấp trên Farm Taadaa:** Hệ thống Cầu dao IP 48h theo cổng MikroTik PPPoE (1 IP : 2 máy) chính là bản nâng cấp granular vượt trội:
  * Khi Máy A bị TikTok nhả follow $\rightarrow$ Lập tức cúp cầu dao proxy cổng đó 48h để bảo vệ Máy B đi chung IP.
  * Các dải IP sạch khác của farm **vẫn tiếp tục vận hành bình thường**, không bị tê liệt hay chết chùm toàn farm một cách mù quáng.

### D. Chu kỳ xoay tua 3 Ca/ngày (Bỏ Hẳn Ca 0h Đêm) & Dưỡng Sinh Phục Hồi (Triển khai 2026-10-10)
- **Bỏ hoàn toàn ca 0h đêm (00:00 – 02:30):**
  * Loại bỏ hành vi bất thường cày đêm (Human Behavior Anomaly).
  * Cho phép thiết bị Android S7 và dải IP MikroTik nguội máy, giải phóng RAM và xả tải hoàn toàn từ 21:30 đến 05:59 sáng hôm sau.
- **Lịch xoay tua Chu kỳ 3 ngày (3 Ca / ngày: Sáng 06h/08h, Trưa 12h/14h, Tối 18h/20h):**
  * **Ngày 1:** Sáng Row 1 — Trưa Row 3 — Tối Row 5.
  * **Ngày 2:** Sáng Row 2 — Trưa Row 4 — Tối Row 6.
  * **Ngày 3:** Sáng Row 7 — Trưa Row 8 — **Ca tối chuyên dưỡng sinh luân phiên Row 3 / Row 4 pure feed (`rest_day=True`, 0 follow, 0 upload)**.
- **Hiệu quả:** Mỗi nick cày follow xong có từ **48h đến 72h nghỉ ngơi** tiêu hóa cờ trước cữ tiếp theo. Row 3 và Row 4 (hai row cần hồi trust nhất) được cấp slot lướt feed chuyên biệt để rửa sạch điểm rủi ro.

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
