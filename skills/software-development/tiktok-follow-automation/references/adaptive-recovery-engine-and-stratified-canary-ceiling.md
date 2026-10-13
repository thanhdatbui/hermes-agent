# Adaptive Recovery Engine & Stratified Canary Ceiling Testing

Tài liệu chuẩn hóa kiến trúc điều phối Follow Quota, phân tầng theo dõi và cơ chế hồi phục thích ứng trên giàn TikTok Automation (Taadaa Farm).

---

## 1. Bản chất Nghịch lý Simpson (Simpson's Paradox) trên Dashboard
* **Hiện tượng cũ:** Khi gộp flat toàn bộ lịch sử chạy theo các giỏ cứng `1-4`, `5-9`, `10-14`, `15+`, dữ liệu sinh ra số ảo: giỏ `1-4` dính nhả 33.3%, còn giỏ `15+` an toàn 96.9%.
* **Bản chất kỹ thuật (Selection / Survivor Bias):**
  * Giỏ `1-4`: Toàn bộ là nick tân binh mới lên giàn hoặc nick yếu đang thụ án probation/cooldown. Chạy ít không phải là nguyên nhân nhả, mà do chỉ nick có nguy cơ nhả cao nhất mới bị gán chạy 1-4.
  * Giỏ `15+`: Chỉ những nick nòng cốt siêu khỏe (age >= 30-60d, >= 10-15 clip, trust cao, đã tốt nghiệp) mới được cấp chạy kịch trần.
* **Quy chuẩn phân tích:** Tuyệt đối cấm gộp flat. Bắt buộc phân tích độc lập theo từng Cohort: Tân binh, Hồi phục S1, Hồi phục S2, và Nòng cốt Khỏe.

---

## 2. Risk-Adjusted Quota Optimization (Hàm Tối Ưu Hóa Rủi Ro Ròng)
Thay vì hardcode cảm tính các dải quota [3-5], [7-9], [10-15], hệ thống tự động tính điểm hữu dụng kỳ vọng (Net Utility):

$$U(q) = q \times (1 - P_{\text{nhả}}(q)) - P_{\text{nhả}}(q) \times \text{Cost}_{\text{Cooldown}}$$

* **Chi phí cơ hội bị giam Cooldown ($\text{Cost}_{\text{Cooldown}}$):**
  * Phục hồi nhanh S1 (án 3 ngày): $\text{Cost} \approx 30$ fl
  * Phục hồi chuẩn S2 (án 7 ngày): $\text{Cost} \approx 60$ fl
  * Nòng cốt Khỏe (án 15 ngày + mất chuỗi sạch): $\text{Cost} \approx 120$ fl
* **Cơ chế:** Khi tỷ lệ nhả $P_{\text{nhả}}$ tăng dù chỉ vài %, hàm phạt sẽ ghìm ngay lập tức mức quota $q^*$ về vùng an toàn bền bỉ (Sweet Spot).

---

## 3. Chiến Lược Canary (+10% Quota): Phòng Lab vs. Bệnh Viện
* **Chỉ bốc nick từ nhóm Khỏe (Phòng Lab):**
  * Mục tiêu: Dò tìm biên chịu tải thực tế (Operating Envelope) của thuật toán TikTok.
  * Tỷ lệ bốc: 5–10% dàn khỏe (3–5 nick), tuân thủ **Diversity Rule** (mỗi máy 1 cổng proxy độc lập, không trùng IP).
  * Biên độ: Cấp Quota Canary = $\text{Baseline} \times 1.10$ (+10%, tương đương +1 đến +2 fl).
  * Vòng phản hồi (Closed-Loop): 3 ca liên tiếp sạch $\rightarrow$ mở rộng trần baseline toàn dàn. Dính 1 lần nhả $\rightarrow$ Kill-switch ngắt thử nghiệm ngay, bảo vệ 95% dàn chính.
* **Tuyệt đối CẤM Canary ở nhóm Hồi phục (Bệnh viện):**
  * Nick hồi phục vừa mãn hạn tù, ưu tiên số 1 là **sống sót và xuất viện càng nhanh càng tốt**.
  * Ép thêm 1 follow ở nhóm hồi phục nếu fail sẽ đẩy nick vào án phạt nặng hơn (S1 lên S2: giam 7 ngày; S2 lên S3: giam 15 ngày), tạo ra "nợ hồi phục" làm tê liệt công suất farm.

---

## 4. Adaptive Recovery Engine: Điểm Tín Nhiệm & Phân Luồng
Không áp dụng số ca cố định cào bằng. Khi nick mãn hạn Cooldown, hệ thống tự động chấm điểm tín nhiệm (Recovery Score 0 - 100):

$$\text{Recovery Score} = \max\Big(0,\; \text{Base Trust} - \text{Violation Penalty}\Big)$$

### A. Điểm Uy Tín Cơ Sở (Base Trust — tối đa 100đ):
* **Lịch sử cày Follow (`total_followed`):**
  * $\ge 100$ fl: **40đ** | $50 - 99$ fl: **30đ** | $20 - 49$ fl: **20đ** | $< 20$ fl: **10đ**
* **Kỷ lục chịu tải an toàn (`max_safe`):**
  * $\ge 30$ fl: **40đ** | $15 - 29$ fl: **30đ** | $5 - 14$ fl: **15đ** | $< 5$ fl: **5đ**
* **Số ca sạch tích lũy (`probation_clean_days`):**
  * Mỗi ca sạch: **+10đ** (tối đa 20đ).

### B. Điểm Trừ Vi Phạm (Violation Penalty — BẮT BUỘC TRỪ ĐIỂM):
* *Streak = 0:* Trừ **0đ**.
* *Streak = 1 (Vi phạm nhẹ lần đầu):* **Trừ 15đ**.
* *Streak = 2 (Tái phạm lần 2):* **Trừ 35đ**.
* *Streak $\ge$ 3 (Tái phạm nặng / Sổ đen):* **Trừ 60đ**.

### C. Phân luồng lộ trình:
* **🟢 Fast-track (Điểm $\ge 60$):** Cựu binh trust cao lỡ dính 1 lần nhả. **Đúng 1 ca sạch** (4–5 fl) là tự động thăng hạng về Khỏe ngay!
* **🟡 Thận trọng (Điểm $< 60$):** Nick mới/yếu. Cần **3 ca sạch**.
* **Cơ chế tự động nhảy nhóm:** Nick ở nhóm Thận trọng tự farm điểm qua Pipeline Upload Video (+20-30đ) hoặc tích lũy ca micro-follow sạch (+10đ/ca). Cán mốc $\ge 60$ điểm sẽ tự động mở khóa Fast-track.

---

## 5. Đổi từ Calendar Days sang Clean Sessions
* Do farm chạy đảo ca cách ngày (1/3), đo lường theo ngày lịch (`clean_days`) khiến 3 ngày bị kéo dài thành 7–9 ngày ngoài đời thực, giam cầm nick vô lý.
* Thuật toán TikTok chỉ soi lần gần nhất nick hoạt động có bất thường không. Đổi sang đếm **Số ca chạy sạch thực tế (Clean Sessions)**: 1 ca sạch cho Fast-track, 2 ca cho S2, 3 ca cho Cautious.
