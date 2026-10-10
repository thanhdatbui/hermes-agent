# Shared IP Proxy Collision & Canary Ceiling Testing

## 1. Sự Cố Trùng Lặp IP Proxy (1 IP : 2 Máy) & Lây Nhiễm Cờ Phạt (Cross-Machine Taint)

### Hiện trường thực tế (09/10/2026):
* Quy hoạch Farm Kibe: 80 máy Samsung S7 chia sẻ 39–40 đường proxy (tỷ lệ 1 Proxy : 2 Máy, ví dụ Cổng 5101 gán M1 & M39, Cổng 5116 gán M14 & M52).
* Trong 6 nick nòng cốt bị TikTok nhả follow sáng 09/10/2026, có 4 nick nằm trong 2 cặp chung chính xác 1 IP:
  * **Cặp Cổng 5116:** Lúc 06:21, M52 (`@vy.nguyen8730`) vào ca follow, ăn 1 follow rồi bị TikTok ngắt (`FOLLOW_FAILED`). Đúng 18 phút sau (06:39), M14 (`@hong.bo.anh83`) nhảy vào app cày follow trên chính IP 5116 đó -> TikTok đã gắn cờ nghi vấn IP từ 18 phút trước, M14 vừa bấm follow lượt đầu tiên là bị nhả ngay lập tức (0 lượt) và dính án phạt Cooldown 3 ngày.
* Đối soát lịch sử: Từng có 79 ca chạy trong đó 2 máy chung 1 IP cùng cày follow trong ngày, với hơn 7.200 lượt follow cách nhau dưới 10 phút (thậm chí 5–38 giây).
* **BẪY DỮ LIỆU LỖI TRƯỚC 02/10/2026 (User Correction):**
  - Dữ liệu trước ngày 02/10/2026 (bao gồm các ngày 31/08, 01/09 và cả ngày 01/10) bị sai lệch do **HÀM VERIFY CŨ BỊ LỖI FALSE-POSITIVE** (nhận diện nhầm stat labels và chưa xử lý nút `id/fo4`). Lỗi này chỉ được vá dứt điểm vào rạng sáng 02/10/2026 (commit `c12242d`).
  - Mọi phân tích, đo lường tỷ lệ nhả và follow an toàn **BẮT BUỘC chỉ trích xuất từ 02/10/2026 trở đi** để đảm bảo độ chuẩn xác 100%. Khi đo chuẩn từ 02/10:
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

### Khảo Sát Thực Nghiệm Lây Nhiễm Xuyên Ca (Cross-Shift Multi-Row: Sáng vs Chiều/Tối):
Khảo sát từ 10.677 lượt follow và 389 hồ sơ lỗi state trên hệ thống farm:
1. **Trường hợp IP Sạch (Sáng follow bình thường -> Chiều/Tối chạy row khác):**
   - Ghi nhận 19 ca tiêu biểu (ví dụ 01/10 Port 5113 M49_r1 sáng -> M11_r3/r5 chiều; 01/10 Port 5114 M50_r1 sáng -> M12_r3/r5 chiều; 03/10 & 07/10 Port 5118 M16_r1 sáng -> M16_r3 chiều...).
   - **Kết luận:** Giãn cách ca sáng và chiều/tối (>= 4-6 tiếng) khi IP có Trust Score sạch cho phép các row khác trên máy hoặc máy partner cùng IP chạy follow bình thường an toàn.
2. **Trường hợp IP Bẩn (Sáng dính nhả -> Chiều/Tối chạy row khác cùng IP):**
   - Khảo sát 45 ca sáng dính `FOLLOW_FAILED` mà chiều/tối có row khác cùng IP vào follow:
     - **44 / 45 ca (97.8%) CŨNG BỊ NHẢ NỐT** (ăn cờ phạt lây nhiễm chéo, ví dụ 03/10 M11_r1 sáng -> M11_r3 & M49_r3 chiều dính nhả; 06/10 M15_r2 sáng -> M53_r6 tối; 07/10 M16_r1 sáng -> M54_r3 chiều...).
     - Chỉ duy nhất 1 ca (2.2%) ngoại lệ follow được.
   - **Bằng chứng thực nghiệm khẳng định:** Cửa sổ phạt (Taint Window) của TikTok trên IP nhạy cảm kéo dài trọn chu kỳ ngày. Cơ chế **IP Circuit Breaker ngắt đến hết ngày (`23:59:59`)** là tối quan trọng, cấm tuyệt đối mở cho ca sau chạy cố.

### Giải Pháp Chuẩn: IP Circuit Breaker (Cầu Dao Tự Ngắt Theo IP 48H Rolling)
* **Bẫy Cấm Cứng / Session Mutex (User Correction):** Nếu cấm cứng 1 IP / 1 máy hoặc khóa mutex theo phiên trong ca chạy batch thì sẽ làm mất 50% công suất của dàn máy trong phiên đó.
* **Cơ chế Soft Guard tối ưu (Đã nâng cấp 48h rolling):**
  1. **Tự động ngắt khi có sự cố:** Khi Máy A dính `FOLLOW_FAILED` (`set_follow_failed` trong `follow_state.py`), hàm `trip_ip_breaker(machine)` tự động kích hoạt giật cầu dao, ghi nhận proxy bị `TRIPPED` vào bảng `ip_circuit_breaker` trong SQLite `tiktok_tracker.db` với `reset_at = now + 48 hours`.
  2. **Safe-skip máy anh em và row sau:** Khi Máy B hoặc row sau chuẩn bị chạy (`run_follow.py`), preflight gọi `check_ip_breaker(machine)`. Hàm kiểm tra `status == 'TRIPPED'` và `reset_at > now`. Nếu IP đang trong thời gian cách ly 48h, tự động skip follow với trạng thái `CIRCUIT_BREAKER_SKIPPED` (`failed=False`, `follow_failed=False`), không phạt nick, đồng thời ghi nhận `saved_machines` vào DB.
  3. **Chỉ cấm Follow — Nuôi/Feed vẫn chạy bình thường:** Trong 48h ngắt cầu dao, các nick trên IP đó CHỈ BỊ CHẶN BẤM FOLLOW. Toàn bộ tiến trình nuôi/lướt feed dưỡng sinh vẫn chạy bình thường để "rửa IP" bằng lưu lượng xem video tự nhiên.
  3. **Giám sát trực quan trên Dashboard (:1905):** Hiển thị widget `⚡ Cầu Dao Tự Ngắt IP` và gắn nhãn Proxy Port + Partner Machine (`M28 :5134 (🔗M66)`) trên ma trận.
  4. **Báo cáo trong Report Ca Follow Telegram (feed_session_watchdog.py — User Invariant):**
     * Trong mục Follow chéo, BẮT BUỘC gom nhóm cực ngắn (1 dòng) số lượng proxy bị ngắt và nick anh em được bảo vệ (tránh in danh sách cổng dài dòng làm loãng report):
       - Có máy partner được cứu: `⚡ Cầu dao tự ngắt IP (X proxy đã khóa): Khóa cứu Y máy (M<A>, M<B>)`
       - Không có máy partner cần cứu: `⚡ Cầu dao tự ngắt IP (X proxy đã khóa)`
     * Đối với máy nhả follow sau khi cày được một số lượt (`Nhả ở Hồi phục 1/2` hoặc `Nhả ở Cấp Khỏe`), BẮT BUỘC ghi kèm số lượt thực tế cạnh tên máy: `(M1: 2 lượt)`, `(M18: 12 lượt)`. Cấm in trơ trọi `(M1)` làm user hiểu lầm là nhả trắng 0 lượt như `Nhả liền`.
     * Trong mục `Bỏ qua`, bóc tách riêng: `Khóa IP do máy cùng IP nhả (X: M...)` thay vì gộp mù vào lỗi script hay dưỡng sinh thông thường. Không báo lỗi ảo khi nick được an toàn skip bởi Circuit Breaker.
     * **BẪY TRÀN TẢI TELEGRAM 4096 KÝ TỰ (HTTP 400 MESSAGE_TOO_LONG):**
       - Khi ca chạy có nhiều máy dính nhả và nhiều proxy bị ngắt cầu dao (ví dụ 22 proxy ngắt, 25 máy nhả), tổng độ dài tin nhắn báo cáo gộp dễ dàng vượt quá giới hạn 4.096 ký tự của Telegram API (thường đạt 4.500 - 5.500 ký tự).
       - Telegram API sẽ từ chối gửi tin nhắn với mã lỗi HTTP 400: `Bad Request: message is too long`. Nếu chỉ bọc `try...except logger.warning`, tin nhắn báo cáo Follow sẽ bị nuốt im lặng mà không hề gửi tới nhóm `-5127276494` (`Tiktok Follow`).
       - **Giải pháp bắt buộc (Auto-Chunking & Cluster Scoping):**
         1. **Line-Aware Auto-Chunking:** Trong `dispatch_split_reports()`, kiểm tra độ dài `full_msg`. Nếu `> 4000` ký tự, tự động ngắt theo dòng giữ nguyên `keepends=True` thành các chunks `<= 3900` ký tự và gửi lần lượt qua Telegram.
         2. **Cluster Scoping cho Circuit Breaker:** Bảng danh sách Cầu dao IP chỉ xuất hiện 1 lần trong khối cụm liên quan (`cluster.get("name") == "kibe"`), tuyệt đối không lặp lại trong khối cụm Admin khiến độ dài tin nhắn tăng gấp đôi.
  5. **Kỷ luật cô lập kiểm thử & Chống xóa nhầm DB Production (Pytest Isolation Guard):**
     * Trong `follow_state.py` và `run_follow.py`, bắt buộc bọc guard `if not os.environ.get("PYTEST_CURRENT_TEST"):` trước khi gọi `trip_ip_breaker()` hoặc `check_ip_breaker()`.
     * *Bài học xương máu:* Nếu không có guard này, các unit test thử nghiệm nhánh `FOLLOW_FAILED` sẽ tự động ghi cờ `TRIPPED` vào DB live `D:/Taadaa/data/tiktok_tracker.db`, dẫn đến các test case tiếp theo chạy trên Machine 1 bị Circuit Breaker ngắt hàng loạt (`CIRCUIT_BREAKER_SKIPPED`) và làm vỡ test suite `test_cli.py`.
     * **CẤM TUYỆT ĐỐI DELETE TRÊN DB PRODUCTION ĐỂ ÉP TEST PASS:** Khi test bị vướng state, CẤM TUYỆT ĐỐI chạy script `DELETE FROM ip_circuit_breaker` trên database live (`D:/Taadaa/data/tiktok_tracker.db`). Hành vi này sẽ xóa sạch danh sách proxy đang ngắt thực tế của ca chạy, làm mất lá chắn an toàn khiến các máy anh em (M8, M75, M78...) mất bảo vệ và lao vào IP dính cờ phạt. Phải sửa bằng cách bọc guard `PYTEST_CURRENT_TEST` hoặc monkeypatch test fixture.
     * **Quy trình khôi phục bảng Cầu Dao khi bị xóa nhầm (Zero-Loss Incident Recovery):** Nếu bảng bị xóa nhầm trong ca chạy, KHÔNG quét đĩa diện rộng (`os.walk`). Vào thẳng thư mục artifact live của ca chạy hiện tại (`D:/Taadaa/runtime/kibe/live/<DATE>/<BATCH>/machines/machine_<N>/<RUN_ID>/follow_result.json`), lọc các máy có `status == 'FOLLOW_FAILED'` hoặc `follow_failed == True`, map với file gán proxy (`D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx`) để lấy lại danh sách `proxy_key` và nạp phục hồi nguyên trạng vào SQLite.
     * **Chuẩn hóa tích hợp & Telemetry (Code Quality & Closeout Gate Standards):**
       - **CẤM hard-code tuyệt đối `D:/Taadaa/tools` trong code repo:** Dùng đường dẫn tương đối động qua `Path(__file__).resolve().parents[N] / "tools"` để giữ tính portable cho test/staging/production.
       - **Structured Telemetry khi trip/check:** Cấm nuốt lỗi im lặng hoặc chỉ log warning sơ sài; bắt buộc dùng `logger.exception("[IP_BREAKER] trip failed machine=%s error_type=%s error=%s", ...)` kèm structured payload (`extra={"circuit_breaker": ...}`) để phục vụ truy vết.
       - **Mock Test Pattern cho Circuit Breaker:** Khi viết unit test (`test_cli.py`, `test_follow_state.py`), tạo mock module `types.ModuleType("ip_circuit_breaker")` và `monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)` để kiểm thử cả 2 nhánh: (1) skip an toàn khi IP bị ngắt (`CIRCUIT_BREAKER_SKIPPED`, exit code 1) và (2) khả năng tự hồi phục khi module breaker ném exception (`fail-open`).
       - **Canary Hook Test Stub:** Trong các test kiểm thử `--canary-hook`, bắt buộc dùng stub class `FakeState` có `budget_remaining() -> int`, không dùng `pytest.fail("state")` vì canary entrypoint hiện đã tích hợp khởi tạo state để ghi nhận budget telemetry.

### 2. Decision Matrix: Khi Cổng Bị Ngắt, Có Nên Đổi Proxy (Change Proxy) Cho Máy Sau Chạy Cố?

* **User Query / Decision Point:** Nếu proxy 1 acc bị lỗi (`FOLLOW_FAILED` / ngắt cầu dao), có nên đổi proxy khác để acc sau vẫn được chạy không?
* **Quy tắc Vận Hành Chuẩn:** **CẤM TUYỆT ĐỐI đổi proxy để máy sau chạy cố khi nguyên nhân là `FOLLOW_FAILED` (TikTok nhả/chặn).**
  - **Lý do 1: Phá vỡ Aging Trust Score:** Nick farm được nuôi theo cơ chế IP Tĩnh Dài Hạn (Home Wi-Fi Baseline) gắn chặt `[Hardware ID + Subnet/ASN + Geolocation]`. Đổi proxy đột ngột gây lỗi *Impossible Travel* / Flapping, kích hoạt cờ đỏ Anti-Fraud (bắt giải Captcha, checkpoint SMS hoặc shadowban).
  - **Lý do 2: Tránh Cháy Lan Trong Bão Thuật Toán:** Khi nhiều proxy bị ngắt liên tiếp trong thời gian ngắn, đây là "bão quét tương tác" từ thuật toán TikTok. Nếu đổi proxy mới cho máy sau lao vào chạy tiếp -> Máy sau tiếp tục bị trảm trên proxy mới -> Vừa chết thêm nick, vừa mất thêm proxy dự phòng.
  - **Lý do 3: Tỷ lệ Đánh Đổi Lỗ Nặng (Risk vs Reward):** Cố chạy chỉ thu thêm 9–12 follow/ca, nhưng rủi ro dính Cooldown 3–15 ngày hoặc hỏng vĩnh viễn nick nuôi nhiều tháng.
  - **Lý do 4: Bẫy Account Switcher Làm Cháy Lan IP Mới (User Insight):**
    - Trên mỗi điện thoại Samsung S7, các nick vận hành qua tính năng Account Switcher của app TikTok.
    - Khi mở app TikTok để chuyển sang nick mới (Row sau), app luôn **render phiên làm việc của nick cũ trước** (chính là nick ca trước vừa dính vết nhả follow).
    - Nick cũ lập tức gửi request ping vi phạm lên TikTok trên dải IP mới toanh trước khi kịp bấm chuyển tài khoản.
    - **Hậu quả:** Tự tay liên kết IP mới với tài khoản vi phạm, làm bẩn IP mới ngay từ giây đầu tiên và lây cờ đỏ sang nick mới ở ca sau.
* **Hiện trường thực nghiệm: Cầu dao 24h là KHÔNG ĐỦ (User Query & Field Proof):**
  - Khảo sát 236 lượt theo dõi IP từ 02/10 đến 10/10/2026 sau ngày dính nhả: Nếu ngày hôm sau (qua 00:00) cho chạy tiếp trên cùng IP đó thì **161 / 169 ca (95.2%) VẪN TIẾP TỤC BỊ DÍNH NHẢ NỐT!** Chỉ 4.8% thành công.
  - Cửa sổ phạt (Taint Window) của TikTok trên IP nhạy cảm kéo dài tối thiểu **48h đến 72h** (đồng bộ với thời gian cooldown của nick). Cầu dao ngắt chỉ trong ngày (23:59:59) là chưa đủ an toàn nếu qua hôm sau cho cày dồn dập.
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

---

## 5. Điều Phối Nick Chung IP Khác Ca (Cross-Shift / Sáng-Chiều) & Switcher Đa Nick

### A. Tình huống nghiệp vụ & Bản Chất Lệch Độ Trưởng Thành Các Row (User Correction & Insight):
- Khi khảo sát hiện tượng "Sáng follow bình thường nhưng Chiều/Tối cùng máy lại bị nhả" (15 ca ghi nhận từ 02/10 đến 07/10/2026), **nguyên nhân cốt lõi không phải do phần cứng hay Account Switcher làm bẩn nick sau**, mà do **ĐỘ LỆCH SỨC KHỎE (ROOKIE vs VETERAN) GIỮA CÁC ROW**:
  - **Row 1 & 2:** Dàn cựu binh nuôi lâu, >= 90% nick có >= 10-25 video, trung bình tích lũy 20–108 follow sạch.
  - **Row 3 đến 8:** Dàn nick gối đầu/mới reg bù, **76% - 90% nick CHƯA TỪNG follow được lần nào (0 follow)**, video ít.
  - Khi đưa nick non nớt (Rookie) vào cày follow thì dù chạy ở ca nào nó cũng sẽ bị thuật toán TikTok vặn cổ (`FOLLOW_FAILED`).
  - **Bằng chứng thực nghiệm bóc tách 44 ca chiều/tối bị nhả:** 88% (44/50) là nick mầm 0 follow lịch sử, 6% là nick yếu (<5 follow), chỉ 4% (2 ca) là acc cựu binh. Khẳng định: hiện tượng chiều/tối dính nhả chủ yếu do **nội tại nick quá yếu** chứ không phải do lây nhiễm máy/IP từ ca sáng.
  - **Bằng chứng phản biện:** Khi cho nick Row 3 nhưng là **Nick Khỏe có Trust** chạy buổi trưa/chiều (M16_r3 `@lenhi09116` cày 10 follow ngày 03/10 và 15 follow ngày 07/10; M21_r3 `@hongloan992` cày 5 follow ngày 03/10 và 17 follow ngày 07/10), máy và IP hoàn toàn gánh được cả 2 ca mượt mà!

### B. Mô Hình Khóa Kép (Dual-Layer Anti-Spam: Account vs IP Gateway) & Tử Huyệt Quota Hồi Phục:
1. **TikTok phạt theo 2 tầng hoàn toàn độc lập:**
   - **Tầng 1 - Khóa theo Account (Account Penalty State):** Cắm cờ trực tiếp vào profile TikTok. Nick bị cờ thì đổi sang IP sạch hay máy khác vẫn bị tuột follow trong suốt thời gian Cooldown (3–15 ngày).
   - **Tầng 2 - Khóa theo IP/Subnet (Gateway Anomaly Flag):** Thuật toán cắm cờ IP khi phát hiện volume tương tác bất thường. Khi IP bị cắm cờ (48h–72h), **BẤT KỲ ACC NÀO (KỂ CẢ CỰU BINH SIÊU KHỎE)** bấm follow qua IP đó đều bị từ chối/nhả tại gateway (minh chứng: 50 ca acc khỏe cựu binh M14, M52, M1, M39 bị nhả rạng sáng 09/10).
2. **Tử huyệt của Quota Hồi Phục khi chạy trên IP dính cờ:**
   - Quy chế cấp quota hồi phục nhỏ (3–5 follow) cho nick mãn hạn Cooldown là **BẮT BUỘC ĐÚNG để re-test trust**.
   - **NHƯNG NẾU CHO NICK HỒI PHỤC CHẠY TRÊN IP CHƯA HẠ NHIỆT (IP dính cờ 48h):** Nick sẽ bị nhả ngay lập tức do cơ chế Gateway Flag của IP ➔ Operator/Agent lầm tưởng nick chưa hồi phục và tăng án phạt streak, trong khi thủ phạm thực sự là dải IP đang bị cắm cờ.
   - **Quy tắc bất di bất dịch:** Nick đang trong diện Probation / Hồi phục **CHỈ ĐƯỢC PHÉP CHẠY TRÊN IP HOÀN TOÀN SẠCH** (IP không có bất kỳ máy/row nào dính lỗi trong 48h qua).

### B. Quy tắc vận hành chuẩn: HOÃN FOLLOW TOÀN BỘ ĐẾN HẾT NGÀY (23:59:59) KHI DÍNH NHẢ
1. **Phạm vi khóa của Circuit Breaker:** Bảng `ip_circuit_breaker` khóa theo `proxy_key` với `target_date = today` và `reset_at = 23:59:59`. Mọi ca chạy sau trong cùng ngày (bất kể khác máy hay cùng máy khác row) khi gọi `check_ip_breaker()` đều nhận cờ `TRIPPED` và tự động safe-skip.
2. **Cơ sở kỹ thuật (Taint Window 24h):**
   - TikTok cắm cờ nghi vấn theo bộ ba `[Hardware ID + IP/Subnet + Pattern]`. Cửa sổ phạt không hết sau vài tiếng.
   - **Kịch bản khác máy chung IP (Cặp proxy song sinh, ví dụ M14 & M52):** Tỷ lệ nhả khi chạy đôi cùng IP trong ngày là 70.6%. Ca sáng đã gãy thì ca chiều lao vào follow sẽ tiếp tục ăn nhả ngay lượt đầu (0 follow) và dính án phạt Cooldown 3–15 ngày.
   - **Kịch bản cùng máy Switcher (8 nick/máy, sáng Nick A, chiều Nick B):** Mức độ rủi ro tối đa vì trùng cả IP lẫn Hardware ID. TikTok sẽ dễ dàng liên kết và quét trảm chùm nick clone trên thiết bị.
3. **Cơ chế bảo vệ nick ca sau:**
   - **Trạng thái ghi nhận:** `CIRCUIT_BREAKER_SKIPPED` (`failed=False`, `follow_failed=False`). Nick không bị tính lỗi, không tăng `fail_streak`, không bị gán cooldown.
   - **Chuyển đổi công năng sang Dưỡng Sinh (Feed / Read-only):** Cấm đi follow (hành vi write nhạy cảm), nhưng ĐƯỢC PHÉP chạy phiên lướt nuôi dưỡng sinh (xem video, tương tác nhẹ). Hành vi này vừa an toàn vừa giúp "rửa IP" bằng lưu lượng người dùng tự nhiên.
   - **Báo cáo Telegram (User Invariant):** Liệt kê rõ trong shift report: `⚡ Cầu dao tự ngắt IP: Đã khóa cứu nick M<B> (do M<A> cùng IP dính nhả từ ca sáng)`.

### C. Tử Huyệt Điều Phối Ca 0h & Nghịch Lý Nick Yếu Giật Cầu Dao Giam Oan Nick Khỏe (User Invariant 10/10/2026):
- **Cạm bẫy lịch đồng hồ 0h00:**
  - Khi lịch farm chạy theo ngày dương lịch bắt đầu từ 00:00 (Ca 4 - Đêm) với **Row 7/8** (dàn nick mầm non nớt nhất, mới reg bù, ít video, chưa có trust follow).
  - Nếu để Row 7/8 được phép chạy follow hook lúc 0h: do nội tại nick yếu, TikTok phát hiện bất thường và nhả follow ngay (`FOLLOW_FAILED`) ➔ `trip_ip_breaker` kích hoạt khóa proxy đó trong **48 giờ rolling** (`now + 48h`).
  - Đến **06:00 sáng** (Ca 1 - Sáng), **Row 1/2** (Dàn cựu binh trụ cột, 20–108 follow sạch, tài sản lớn nhất của farm) bước vào ca cày follow ➔ `check_ip_breaker` thấy proxy bị khóa từ lúc 00:30 do Row 7/8 làm cúp ➔ **Row 1/2 bị `CIRCUIT_BREAKER_SKIPPED` giam oan 48 tiếng!**
  - Tương tự với **Row 3/4** ở Ca 2 (12:00 trưa): nếu Row 3/4 còn yếu chạy follow dính nhả ➔ Lại giật cầu dao 48h ➔ Sáng hôm sau (và hôm sau nữa) Row 1/2 tiếp tục bị giam!
- **Kỷ Luật Bảo Vệ IP Sạch Cho Dàn Cựu Binh (Core Fleet IP Priority):**
  1. **Ưu tiên tuyệt đối Ca 1 (06:00 & 08:00 sáng) cho Row 1/2:** Row 1 (ngày lẻ) và Row 2 (ngày chẵn) là dàn tài sản trụ cột, bắt buộc phải là đối tượng đầu tiên được sử dụng dải IP sạch nhất trong chu kỳ để cày follow.
  2. **Cấm tuyệt đối Follow Hook ở Ca 4 (00:00 & 01:30 đêm):** Ban đêm thuật toán quét gắt gao và nick chạy ca đêm là Row 7/8 (nick mầm). 100% ca đêm chỉ chạy **Dưỡng Sinh Thuần Túy (Pure Feed + Upload)**, cấm mọi hành vi follow.
  3. **Cầu Dao Thông Minh Theo Cấp Độ Động (Tier-Aware Circuit Breaker - User Correction):**
     * **Sai lầm nếu cấm cứng theo Row:** Cấm mù toàn bộ Row 3 đến 8 sẽ làm tê liệt các tài nguyên nick khỏe thực thụ (ví dụ M21_r3 cày 52 fl, M16_r3 cày 43 fl vẫn đang nằm ở Row 3).
     * **Cơ chế kích hoạt Cầu dao theo tầng:**
       - **Tân binh / Đi dò (Cấp 1 - quota 1 lượt):** Cho phép dò để sớm phát hiện nick khỏe; nếu bị nhả CHỈ PHẠT NICK (cooldown 3-14 ngày dưỡng sinh), **CẤM TUYỆT ĐỐI GIẬT CẦU DAO IP** để không làm giam oan Row 1/2 hay máy partner.
       - **Cấp 2 (5-9 lượt) & Cấp Khỏe (10+ lượt):** Khi bị nhả, BẮT BUỘC giật cầu dao 48h rolling (`trip_ip_breaker()`) vì 100% gateway IP đã bị TikTok cắm cờ.
     * Chi tiết kiến trúc xem tại `references/tier-aware-circuit-breaker-and-dynamic-probing.md`.
