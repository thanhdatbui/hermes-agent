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

### D. Chu kỳ Xoay tua 4 Ngày Hoàn Chỉnh + Xúc Xắc Ngày 5 (Chốt hạ 2026-10-10)
- **Bỏ hoàn toàn ca 0h đêm (00:00 – 02:30):**
  * Loại bỏ hành vi bất thường cày đêm (Human Behavior Anomaly).
  * Cho phép thiết bị Android S7 và dải IP MikroTik nguội máy, giải phóng RAM và xả tải hoàn toàn từ 21:30 đến 05:59 sáng hôm sau.
- **Chu kỳ 4 ngày xoay tua (3 Ca / ngày: Sáng 06h/08h, Trưa 12h/14h, Tối 18h/20h):**
  * **Ngày 1:** 3 ca, bốc thăm ngẫu nhiên (50/50) giữa nhóm `[1, 3, 5]` hoặc `[2, 4, 6]`.
  * **Ngày 2:** 3 ca, chạy nhóm còn lại (`[2, 4, 6]` hoặc `[1, 3, 5]`).
  * **Ngày 3:** Ca 1 (Row 7) — Ca 2 (Row 8) — Ca 3 (Lướt feed acc yếu).
  * **Ngày 4 (Tái cân bằng hành vi / Recovery Day):** Nghỉ follow hoàn toàn. Chạy 3 ca lướt feed chuyên cho các nick đang bị nhả follow (nếu không có nick bị nhả thì chọn các nick yếu chạy 3 ca).
  * **Ngày 5:** Bắt đầu chu kỳ mới, lúc này mới xúc xắc lại giữa `(1,3,5)` vs `(2,4,6)` để phá vỡ chu kỳ tuần hoàn cơ học (Temporal Correlation Pattern).
- **Quy tắc Đăng Video Ngày Dưỡng Sinh / Lướt Feed (Advisor Sol & User Invariant 2026-10-10):**
  * **NGÀY LƯỚT FEED VẪN ĐĂNG VIDEO BÌNH THƯỜNG!**
  * Hai hệ thống của TikTok độc lập: Hệ thống Hành vi (Anti-Fraud) phạt spam follow, còn Hệ thống Đề xuất (Recommendation) chấm điểm chất lượng kênh. Người thật / Creator thật vào ngày nghỉ vẫn đăng video và lướt feed bình thường. Đăng video chứng minh tài khoản là Creator thật, không phải bot spam.
  * **Ngày nghỉ follow: VẪN ĐĂNG VIDEO + LƯỚT FEED BÌNH THƯỜNG, CHỈ TẮT DUY NHẤT HÀNH ĐỘNG FOLLOW!**
  * **Cơ chế Đăng Video Idempotent (Phiên 1 hoặc Phiên 2 — Cấm Single Point of Failure):**
    - Thay vì chỉ đóng đinh ở Phiên 2 (dễ mất trắng lượt đăng cả ngày nếu Phiên 2 lỗi app/mạng), cho phép chạy kiểm tra đăng ở cả **Phiên 1 (Primary)** và **Phiên 2 (Fallback)**.
    - **Nguyên tắc Idempotent 1 video/ngày:** Phiên nào đăng thành công trước thì chốt state `posted = true` cho ngày đó; phiên còn lại tự động bỏ qua (Skip).
    - **Cấm Double-post:** Bắt buộc kiểm tra state cấp ngày trước khi upload; đã đăng trong ngày thì tuyệt đối không đăng thêm video thứ 2.
    - **Giãn cách tự nhiên:** Phiên 1 lỗi thì tắt ca chờ đến khung giờ Phiên 2 mới thử lại, cấm retry dồn dập tức thì làm TikTok nghi ngờ bot spam.
- **CẤM TỰ Ý XÓA ÁN COOLDOWN / FAIL_STREAK (User Correction 2026-10-10):**
  * Án Cooldown và `fail_streak` sinh ra do TikTok nhả follow thực tế phải được giữ nguyên.
  * Coordinator CẤM TUYỆT ĐỐI tự ý quét và xóa sạch án phạt Cooldown/fail_streak khi chưa có sự cho phép rõ ràng từ Operator.

---

## 3. Nhịp độ thực thi chi tiết trong GemPhone (Node Delays & So sánh Khoảng nghỉ)
Trích xuất từ `TIKTOK-FLOW-TÌM-KIẾM-Thành-đạt_decrypted.json` (389 nodes) và đối chiếu với Taadaa Runner:
1. **Search Anchor:** Search đúng 1 UID Anchor từ file `tik1va2.txt`, ngâm profile **5.8s – 12.5s** (Node `uo18cfi`).
2. **Mở danh sách:** Bấm tab `Đã follow` (Node `cicjh98` / `yuouuca`) mở danh sách Following của Anchor.
3. **Loop cào trong list & các khoảng nghỉ sâu:**
   - Trước khi tap: ngập ngừng `0.5s – 4.5s`.
   - Tap nút: `//node[@text="Follow" or @text="Follow lại"]`.
   - Vuốt cuộn danh sách: `swipe-scroll up` (750ms).
   - **Khoảng nghỉ thường giữa 2 lần follow:**
     * Node `7t6ltgz`: nghỉ **5.2s – 18.5s**
     * Node `vc1yhpb`: nghỉ **8.1s – 14.4s**
     * Node `7u8v7yd`: nghỉ **7.2s – 15.4s**
   - **Các nhịp nghỉ đệm sâu bất thường (Deep Jitter / Pacing Nodes):**
     * Node `muwrdaa`: nghỉ **16.5s – 27.0s**
     * Node `bfeodrk`: nghỉ **15.9s – 43.5s**
   - **Tổng thời gian phiên:** 20–30 follow chạy rải rác kéo dài từ **7 đến 12 phút**.
4. **Bản chất khác biệt & So sánh thời gian chạy thực tế (Taadaa Runner vs GemPhone):**
   - **Cơ chế Path B Verify (Không vuốt reload profile con):**
     * Trong `_path_b_verify`, khi tap mở Profile của nick con từ follower list lên, **TUYỆT ĐỐI KHÔNG vuốt pull-to-refresh**: TikTok client khi mở profile mới đã tự động kéo fresh state từ server. Nếu follow bị nhả, nút lập tức render lại `Follow` / `Follow lại` ngay trên Profile.
     * Vuốt pull-to-refresh reload trang **CHỈ DÙNG ở 2 vị trí**: (1) Anchor (`_ensure_anchor_followed` sau khi tap trên video player rồi back ra profile), và (2) Module 1 (`mode1_search_follow.py` khi đứng nguyên tại profile search).
   - **So sánh tổng thời gian thực thi (Cả 2 bên đều ~8–12 phút / phiên 20 nick):**
     * **Taadaa Runner:** Tap follow + chờ 2.5–5s + Path B mở profile đọc nút (2.5s, không vuốt) + (30% xem video 12–20s) + back về list + delay giữa các nick (8–25s) ➔ ~25–35s / nick ➔ 20 nick tốn ~8–11 phút. Ưu điểm: Bắt nhả chắc chắn 100% tại chỗ mà không tạo vòng lặp reload thừa.
     * **GemPhone:** Đứng im trong list, tap follow + delay 5.2–18.5s + các nhịp nghỉ đệm sâu 16–43s (Node `muwrdaa`, `bfeodrk`) + vuốt cuộn ➔ ~18–25s / nick ➔ 20–30 nick tốn ~7–12 phút.
   - **Tiến độ triển khai Chu kỳ 4 ngày (3 Ca / ngày: 8 tick trong 3 ngày + 1 ngày Rest Day):**
     * Triển khai qua `tiktok_runner.py` trên 2 cụm Kibe & Admin. Trạng thái live đã xác minh đang chạy ổn định đúng lịch trình (Ngày 1: rows lẻ 1, 3, 5; Ngày 2: rows chẵn 2, 4, 6; Ngày 3: row 7, 8, dưỡng; Ngày 4: nghỉ toàn máy).
5. **Kỷ luật điều phối phiên thảo luận (Coordinator Discipline):**
   - Khi phiên thảo luận kỹ thuật kéo dài với nhiều tranh luận về luồng/thuật toán, Coordinator BẮT BUỘC phải chốt và tổng kết rõ ràng mọi thắc mắc ban đầu của User (đặc biệt là các so sánh thông số định lượng như khoảng nghỉ/delay) trước khi kết thúc phiên; tuyệt đối không để trôi việc rồi báo xong phiên.

---

## 4. Checklist Khắc Phục Cho Taadaa Runner

1. [x] **Giữ vững Canary Gate Anchor (`_ensure_anchor_followed`):** Chốt chặn Fail-Closed bảo vệ nick không bị nướng thêm lượt follow rác khi đang dính cờ nhả ngầm (đối soát DB xác nhận nhả thật).
2. [x] **Giữ nguyên nguyên tắc dừng ngay khi bị nhả (Fail-Closed Invariant):** Đã nhả 1 phát là dừng toàn bộ session của nick đó ngay lập tức (vì đã nhả là nhả sạch phía sau), cấm tư tưởng cố follow bù trong session.
3. [x] **Chu kỳ 4 ngày xoay tua + Xúc xắc Ngày 5:** Ngày 1-2 chạy xen kẽ, Ngày 3 (7,8,yếu), Ngày 4 (dưỡng sinh nick nhả, 0 follow), Ngày 5 xúc xắc lại.
4. [x] **Bảo toàn quyền Đăng Video ngày nghỉ:** Ngày lướt feed vẫn đăng video bình thường, chỉ ngưng follow.
5. [x] **Kỷ luật Cooldown State:** Giữ nguyên án phạt Cooldown, cấm Coordinator tự ý xóa án khi chưa có lệnh.
