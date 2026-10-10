# Shared IP Proxy Collision & Canary Ceiling Testing

## 1. Sự Cố Trùng Lặp IP Proxy (1 IP : 2 Máy) & Lây Nhiễm Cờ Phạt (Cross-Machine Taint)

### Hiện trường thực tế (09/10/2026):
* Quy hoạch Farm Kibe: 80 máy Samsung S7 chia sẻ 39–40 đường proxy (tỷ lệ 1 Proxy : 2 Máy, ví dụ Cổng 5101 gán M1 & M39, Cổng 5116 gán M14 & M52).
* Trong 6 nick nòng cốt bị TikTok nhả follow sáng 09/10/2026, có 4 nick nằm trong 2 cặp chung chính xác 1 IP:
  * **Cặp Cổng 5116:** Lúc 06:21, M52 (`@vy.nguyen8730`) vào ca follow, ăn 1 follow rồi bị TikTok ngắt (`FOLLOW_FAILED`). Đúng 18 phút sau (06:39), M14 (`@hong.bo.anh83`) nhảy vào app cày follow trên chính IP 5116 đó -> TikTok đã gắn cờ nghi vấn IP từ 18 phút trước, M14 vừa bấm follow lượt đầu tiên là bị nhả ngay lập tức (0 lượt) và dính án phạt Cooldown 3 ngày.
* Đối soát lịch sử: Từng có 79 ca chạy trong đó 2 máy chung 1 IP cùng cày follow trong ngày, với hơn 7.200 lượt follow cách nhau dưới 10 phút (thậm chí 5–38 giây).
* **BẪY DỮ LIỆU LỖI 31/08 & 01/09 (User Correction):** Dữ liệu ngày 31/08 và 01/09 đo được tỷ lệ nhả 0% thực chất là do HÀM VERIFY CŨ BỊ LỖI (nhận diện sai trạng thái follow), sau đó mới được vá lại. Khi lọc riêng dữ liệu chuẩn xác của tháng 10/2026:
  - Co-run (2 máy/IP cùng chạy trong ngày): 24 / 34 ca bị nhả (**70.6%**) 🔴
  - Solo (1 máy/IP chạy lẻ): 39 / 107 ca bị nhả (**36.4%**)
  -> Rủi ro dính nhả khi chạy đôi cùng IP cao gần gấp đôi so với chạy đơn!

### Hiện tượng "Ăn nhả dắt dây" (Cascading Domino Failure):
Truy vết chi tiết timestamp 8 ca chết đôi trên cùng IP tháng 10/2026 chứng minh: Khi Máy A dính `FOLLOW_FAILED`, TikTok cắm cờ IP nghi vấn. Máy B vào sau trong vòng 2 – 25 phút bị dính nhả ngay từ lượt đầu (0 lượt):
- 09/10 (Port 5102): M2 fail 06:22 -> M40 vào 06:24 dính nhả ngay (cách 1.9 phút).
- 09/10 (Port 5116): M52 fail 06:21 -> M14 vào 06:39 dính nhả ngay (cách 18.2 phút).
- 09/10 (Port 5122): M56 fail 06:22 -> M18 vào 06:38 dính nhả ngay (cách 16.3 phút).
- 07/10 (Port 5104): M4 fail 06:31 -> M42 vào 06:39 dính nhả ngay (cách 8.7 phút).
- 07/10 (Port 5132): M64 fail 06:25 -> M26 vào 06:43 dính nhả ngay (cách 18.3 phút).
- 07/10 (Port 5137): M69 fail 06:43 -> M31 vào 06:50 dính nhả ngay (cách 7.4 phút).
- 07/10 (Port 10001): M72 fail 06:29 -> M33 vào 06:47 dính nhả ngay (cách 17.9 phút).
- 03/10 (Port 5131): M25 fail 06:24 -> M63 vào 06:46 dính nhả ngay (cách 22.8 phút).

### Giải Pháp Chuẩn: IP Circuit Breaker (Cầu Dao Tự Ngắt Theo IP)
* **Bẫy Cấm Cứng / Session Mutex (User Correction):** Nếu cấm cứng 1 IP / 1 máy hoặc khóa mutex theo phiên trong ca chạy batch thì sẽ làm mất 50% công suất của dàn máy trong phiên đó.
* **Cơ chế Soft Guard tối ưu (Đã triển khai):**
  1. **Tự động ngắt khi có sự cố:** Khi Máy A dính `FOLLOW_FAILED` (`set_follow_failed` trong `follow_state.py`), hàm `trip_ip_breaker(machine)` tự động kích hoạt giật cầu dao, ghi nhận proxy bị `TRIPPED` vào bảng `ip_circuit_breaker` trong SQLite `tiktok_tracker.db` đến hết ngày (`23:59:59`).
  2. **Safe-skip máy anh em:** Khi Máy B chuẩn bị chạy (`run_follow.py`), preflight gọi `check_ip_breaker(machine)`. Nếu IP đang bị ngắt, Máy B tự động skip ca với trạng thái `CIRCUIT_BREAKER_SKIPPED` (`failed=False`, `follow_failed=False`), không phạt nick, đồng thời ghi nhận `saved_machines` vào DB.
  3. **Giám sát trực quan trên Dashboard (:1905):** Hiển thị widget `⚡ Cầu Dao Tự Ngắt IP` và gắn nhãn Proxy Port + Partner Machine (`M28 :5134 (🔗M66)`) trên ma trận.
  4. **Báo cáo trong Report Ca Follow Telegram (feed_session_watchdog.py — User Invariant):**
     * Trong mục Follow chéo, BẮT BUỘC liệt kê rõ ràng các IP bị ngắt và nick anh em được bảo vệ:
       `⚡ Cầu dao tự ngắt IP (X proxy đã khóa do dính nhả):`
       `- Cổng <PORT>: M<A> dính nhả lúc <HH:MM:SS> -> Đã ngắt IP không follow | Đã khóa cứu nick: M<B>`
     * Trong mục `Bỏ qua`, bóc tách riêng: `Khóa IP do máy cùng IP nhả (X: M...)` thay vì gộp mù vào lỗi script hay dưỡng sinh thông thường. Không báo lỗi ảo khi nick được an toàn skip bởi Circuit Breaker.
  5. **Kỷ luật cô lập kiểm thử & Chống xóa nhầm DB Production (Pytest Isolation Guard):**
     * Trong `follow_state.py` và `run_follow.py`, bắt buộc bọc guard `if not os.environ.get("PYTEST_CURRENT_TEST"):` trước khi gọi `trip_ip_breaker()` hoặc `check_ip_breaker()`.
     * *Bài học xương máu:* Nếu không có guard này, các unit test thử nghiệm nhánh `FOLLOW_FAILED` sẽ tự động ghi cờ `TRIPPED` vào DB live `D:/Taadaa/data/tiktok_tracker.db`, dẫn đến các test case tiếp theo chạy trên Machine 1 bị Circuit Breaker ngắt hàng loạt (`CIRCUIT_BREAKER_SKIPPED`) và làm vỡ test suite `test_cli.py`.
     * **CẤM TUYỆT ĐỐI DELETE TRÊN DB PRODUCTION ĐỂ ÉP TEST PASS:** Khi test bị vướng state, CẤM TUYỆT ĐỐI chạy script `DELETE FROM ip_circuit_breaker` trên database live (`D:/Taadaa/data/tiktok_tracker.db`). Hành vi này sẽ xóa sạch danh sách proxy đang ngắt thực tế của ca chạy, làm mất lá chắn an toàn khiến các máy anh em (M8, M75, M78...) mất bảo vệ và lao vào IP dính cờ phạt. Phải sửa bằng cách bọc guard `PYTEST_CURRENT_TEST` hoặc monkeypatch test fixture.
     * **Quy trình khôi phục bảng Cầu Dao khi bị xóa nhầm (Zero-Loss Incident Recovery):** Nếu bảng bị xóa nhầm trong ca chạy, KHÔNG quét đĩa diện rộng (`os.walk`). Vào thẳng thư mục artifact live của ca chạy hiện tại (`D:/Taadaa/runtime/kibe/live/<DATE>/<BATCH>/machines/machine_<N>/<RUN_ID>/follow_result.json`), lọc các máy có `status == 'FOLLOW_FAILED'` hoặc `follow_failed == True`, map với file gán proxy (`D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx`) để lấy lại danh sách `proxy_key` và nạp phục hồi nguyên trạng vào SQLite.

### 2. Decision Matrix: Khi Cổng Bị Ngắt, Có Nên Đổi Proxy (Change Proxy) Cho Máy Sau Chạy Cố?

* **User Query / Decision Point:** Nếu proxy 1 acc bị lỗi (`FOLLOW_FAILED` / ngắt cầu dao), có nên đổi proxy khác để acc sau vẫn được chạy không?
* **Quy tắc Vận Hành Chuẩn:** **CẤM TUYỆT ĐỐI đổi proxy để máy sau chạy cố khi nguyên nhân là `FOLLOW_FAILED` (TikTok nhả/chặn).**
  - **Lý do 1: Phá vỡ Aging Trust Score:** Nick farm được nuôi theo cơ chế IP Tĩnh Dài Hạn (Home Wi-Fi Baseline) gắn chặt `[Hardware ID + Subnet/ASN + Geolocation]`. Đổi proxy đột ngột gây lỗi *Impossible Travel* / Flapping, kích hoạt cờ đỏ Anti-Fraud (bắt giải Captcha, checkpoint SMS hoặc shadowban).
  - **Lý do 2: Tránh Cháy Lan Trong Bão Thuật Toán:** Khi nhiều proxy bị ngắt liên tiếp trong thời gian ngắn, đây là "bão quét tương tác" từ thuật toán TikTok. Nếu đổi proxy mới cho máy sau lao vào chạy tiếp -> Máy sau tiếp tục bị trảm trên proxy mới -> Vừa chết thêm nick, vừa mất thêm proxy dự phòng.
  - **Lý do 3: Tỷ lệ Đánh Đổi Lỗ Nặng (Risk vs Reward):** Cố chạy chỉ thu thêm 9–12 follow/ca, nhưng rủi ro dính Cooldown 3–15 ngày hoặc hỏng vĩnh viễn nick nuôi nhiều tháng.
* **Ma Trận Phân Biệt Xử Lý Proxy:**

| Bản chất sự cố | Triệu chứng kỹ thuật | Xử lý điều phối |
| :--- | :--- | :--- |
| **TikTok cắm cờ (`FOLLOW_FAILED` / Nhả follow)** | Mạng vẫn thông, vào được TikTok nhưng bấm follow bị nhả hoặc app báo lỗi tương tác. | **CẤM ĐỔI PROXY ĐỂ CHẠY TIẾP.** Kích hoạt Circuit Breaker, máy anh em Safe-Skip (`CIRCUIT_BREAKER_SKIPPED`). Nghỉ ngơi dưỡng sinh, mai chạy tiếp. |
| **Hạ tầng Mạng chết (`Dead Proxy / Timeout`)** | Proxy chết hẳn, rớt kết nối (`curl` timeout, mất IP, không ra được internet). | **ĐƯỢC PHÉP ĐỔI.** Thay bằng proxy mới nhưng bắt buộc phải là **proxy tĩnh cùng nhà mạng/cùng dải**, và phải kiểm tra curl thông mạng trước khi nạp vào máy. |

---

## 2. Chiến Lược Dò Trần Bằng Đội Dò Đường (Canary Cohort Testing)

### Cạm bẫy "Lấy mẫu số nhỏ áp đặt trần cả dàn":
* Không dùng toàn bộ dàn máy để vừa cày sản lượng vừa dò trần. Khi trần sập, cả dàn sẽ dính cờ đỏ hàng loạt (Blast Radius quá lớn).
* Không vội vàng kết luận trần cứng cho cả dàn chỉ dựa trên vài ca bị nhả lẻ tẻ.

### Phân tầng kiểm thử trần (Canary Architecture):
1. **90–95% Dàn chính (Core Fleet):** Giữ ở cận dưới an toàn tuyệt đối (ví dụ 8–10 follow/ca). Nhóm này chịu trách nhiệm tạo sản lượng đều đặn, không mạo hiểm.
2. **5–10% Đội dò đường (Canary Cohort):** Chọn ra 3–5 nick trâu nhất (những nick có `Max Safe` lịch sử từng đạt 40–50 như M28, M50). Chỉ nhóm nhỏ này mới được tăng dần tải (+2 follow mỗi chu kỳ) để thăm dò phản ứng của thuật toán TikTok.
3. **Quy tắc nghiệm thu trần:**
   - Nếu Canary vượt qua 3 chu kỳ sạch liên tiếp ở mức cao hơn -> Mới cân nhắc nâng nhẹ cận trên của dàn chính.
   - Nếu Canary dính nhả -> Bán kính thiệt hại chỉ gói gọn trong 2-3 nick thử nghiệm, 95% dàn chính hoàn toàn an toàn.

---

## 3. Chống Over-Engineering Trong Điều Phối Lịch Chạy

* **User Invariant:** Khi hệ thống đã có sẵn nhịp cơ sở tự nhiên (chu kỳ cách 2 ngày mới chạy 1 ca + dưỡng sinh random), CẤM tự ý đẻ thêm các luật phân bổ gượng ép như "chia chẵn/lẻ" hay "cụm ngày 1/ngày 2".
* Càng can thiệp nhiều rule cứng gượng ép, profile hành vi của farm càng mất tính ngẫu nhiên và dễ bị AI Anti-Fraud của TikTok phát hiện mẫu lặp.

---

## 4. Kiến Trúc Wave Scheduler (Turn 1 / Turn 2) & Bản Chất "IP Càng Ổn Định Nick Càng Khỏe"

### A. Tại sao "IP càng ổn định nick càng khỏe" (Nhận định từ thực tế vận hành)?
* **Bản chất người dùng thật (Home Wi-Fi Baseline):** Người thật dùng mạng Wi-Fi gia đình (Viettel/FPT) có IP ổn định nhiều tuần hoặc nhiều tháng.
* **Liên kết Fingerprint 3 yếu tố:** TikTok gắn chặt `[Hardware ID + Dải Subnet/ASN + Geolocation]`. Khi nick xuất hiện liên tục trên cùng 1 dải IP quen thuộc trong 30–60 ngày, điểm tín nhiệm (**Aging Trust Score**) sẽ tăng lũy tiến.
* **Tử huyệt của Rotating IP (Proxy xoay liên tục):** Đổi IP sau mỗi 5–15 phút gây lỗi **"Impossible Travel"** (vừa ở Hà Nội 10 phút sau nhảy sang TP.HCM) -> Thuật toán kích hoạt cờ đỏ, shadowban hoặc bắt giải checkpoint SMS/Captcha.
* **Mâu thuẫn kỹ thuật:** IP ổn định là RẤT TỐT, nhưng nó kỵ **Concurrency Spikes (Spam đồng thời)**: Hai máy cùng 1 IP cùng bắn request follow lên server TikTok trong cùng 1 phút -> TikTok phát hiện mẫu bot Sybil Attack ngay lập tức.

### B. Giải pháp: Wave Scheduler (Canary Partitioning & Temporal Anti-Collision)
Toàn bộ 80 máy Kibe dùng 40 proxy (mỗi proxy 2 máy: `[M1, M39]`, `[M2, M40]`...):
1. **Wave 1 (Turn 1 — Tối đa 40 máy):**
   * Từ mỗi cặp proxy, hệ thống bốc đúng **1 máy duy nhất** (ví dụ bốc M1, M2, M3... M38).
   * Shuffle ngẫu nhiên thứ tự chạy.
   * **Bảo đảm:** 100% các máy chạy ở Wave 1 có IP **hoàn toàn độc lập** với nhau. Tần suất gửi request qua từng IP tại thời điểm $T_0$ chính xác bằng 1.
2. **Chốt chặn Cầu Dao (Canary Circuit Breaker):**
   * Nếu máy ở Wave 1 dính nhả (`FOLLOW_FAILED`) -> Cầu dao lập tức ngắt cổng proxy đó cho đến hết ngày.
3. **Wave 2 (Turn 2 — 40 máy còn lại):**
   * Chỉ những cổng proxy hoàn toàn sạch ở Wave 1 mới được cấp phép cho máy thứ hai (M39, M40, M41...) chạy tiếp.
   * Máy có anh em dính lỗi ở Wave 1 tự động bị khóa skip an toàn (`CIRCUIT_BREAKER_SKIPPED`), **cứu sống 100% nick còn lại**, không bị trảm dắt dây!

### C. Khung Tham Chiếu Ngưỡng An Toàn Cho 1 Residential IP (24 Giờ):
* **Mật độ thiết bị:** Cố định **1 – 2 thiết bị / 1 Residential IP** (Chuẩn farm Kibe hiện tại: 2 máy/IP là tối ưu nhất).
* **Số nick active/ngày:** Tối đa **2 – 4 nick / IP**.
* **Khoảng cách thời gian (Time Gap):** Tối thiểu **30 – 45 phút** giữa các máy chạy trên cùng IP.
* **Trần tổng Follow / IP / 24h:** **Không quá 40 – 50 lượt** cho cả 2 máy cộng lại. Vượt quá ngưỡng này, tỷ lệ dính shadow-follow (F5 mất số) lên tới hơn 80%.
