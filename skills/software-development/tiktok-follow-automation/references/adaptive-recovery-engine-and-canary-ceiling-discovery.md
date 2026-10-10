# Adaptive Recovery Engine & Canary Ceiling Discovery

## 1. Bản Chất Entity Lifecycle: (Máy, Row) Là Đơn Vị Độc Lập

* **Quy tắc cốt lõi (User Invariant):**
  - Đơn vị sinh tồn và vận hành trên farm là `(Máy, Row) = 1 Account riêng biệt`.
  - Ca sáng chạy Row 1, ca chiều chạy Row 2 là 2 nick hoàn toàn khác nhau về danh tính, lịch sử lẫn trust score.
  - **CẤM TUYỆT ĐỐI:** Gộp quota ngày theo máy hoặc đánh giá sức khỏe theo số thứ tự máy. Máy chỉ là container chứa thiết bị, Account trên từng Row mới là thực thể có vòng đời.

---

## 2. Nghịch Lý Simpson & Bẫy Thống Kê Flat (Pooled Analysis)

### Hiện tượng số ảo: "15+ follow an toàn nhất (96.9%)"
* **Bản chất thống kê:** Bảng phân tích flat cũ gom chung toàn bộ các ca chạy của mọi nick vào 4 giỏ:
  - Giỏ `1 - 4 fl/ca`: Chứa gần như 100% ca chạy của nick Phục hồi (vừa ra tù, trust đang yếu, bị TikTok soi) $\rightarrow$ Tỷ lệ nhả bị dồn cục về đây (nhả 33.3%).
  - Giỏ `15+ fl/ca`: Chỉ duy nhất nick Khỏe lâu năm mới được cấp phép chạy mức này $\rightarrow$ Tỷ lệ giữ 96.9%.
* **Kết luận:** Đây là **Thiên kiến kẻ sống sót (Survivorship Bias)**. Mức 15+ an toàn không phải vì chạy 15+ làm tăng an toàn, mà vì chỉ nick siêu khỏe mới được phép chạy 15+. Đem nick yếu ra chạy 15+ sẽ bị quét sạch 100%.
* **Giải pháp bắt buộc:** Xóa bỏ bảng gộp chung flat. Bắt buộc hiển thị theo **Phân Tầng Độc Lập (Stratified Cohorts)**:
  - Khuyến nghị riêng cho Phục Hồi Nhanh (S1).
  - Khuyến nghị riêng cho Phục Hồi Chuẩn (S2).
  - Khuyến nghị riêng cho Nòng Cốt / Khỏe.

---

## 3. Adaptive Recovery Engine: Thích Ứng Theo Streak & Số Ca Sạch

### Điểm nghẽn cũ: "Clean Days $\neq$ Clean Sessions"
* Trước đây áp dụng rule cứng: `clean_days >= 3` ở Nấc 1 và `clean_days >= 6` ở Nấc 2.
* Do lịch chạy đảo ca cách ngày (1/3), 1 nick trung bình 2.5–3 ngày mới chạy 1 ca:
  - 3 clean days $\rightarrow$ Mất **7 – 9 ngày ngoài đời thực**.
  - 6 clean days $\rightarrow$ Mất **14 – 18 ngày ngoài đời thực**.
  $\rightarrow$ Tạo ra nút thắt cổ chai vô lý, làm ứ đọng hơn 200 nick ở nhóm phục hồi dù nick chỉ lỡ dính 1 lần nhả nhẹ.

### Cơ chế chấm điểm tín nhiệm (Recovery Trust Score 0 - 100):
$$\text{Score} = \text{Lịch sử Follow (25đ)} + \text{Chịu tải Max Safe (25đ)} + \text{Ngày sạch (20đ)} + \text{Mức độ vi phạm (30đ)}$$

1. **Tổng follow an toàn (`total_followed`):** $\ge 100$ fl (+25đ), $\ge 50$ fl (+18đ), $\ge 20$ fl (+10đ).
2. **Kỷ lục ca an toàn lớn nhất (`max_safe`):** $\ge 30$ fl (+25đ), $\ge 15$ fl (+18đ), $\ge 5$ fl (+10đ).
3. **Tiến độ sạch (`probation_clean_days`):** Mỗi ca sạch +10đ (tối đa 20đ).
4. **Mức độ vi phạm (`fail_streak`):** Streak 1 (+30đ), Streak 2 (+15đ), Streak $\ge 3$ (0đ).

### Phân luồng lộ trình tự động:
* **🟢 Fast-track (Score $\ge 70$ — Nick nòng cốt lỡ dính án nhẹ):**
  - Chỉ cần **ĐÚNG 1 CA SẠCH** (4–5 follow) ở ca đầu tiên ra tù.
  - Chạy xong 0 drop $\rightarrow$ Tự động thăng hạng về nhóm Khỏe ngay lập tức!
* **🟡 Cautious Baseline (Score $< 70$ — Nick tân binh / tiền án nặng):**
  - Bắt buộc hoàn thành **3 ca sạch**.
* **Cơ chế farm điểm cho nhóm Cautious leo lên Fast-track:**
  - **Upload Pipeline (Giá trị cao nhất):** Đăng video đều đặn giúp TikTok định danh nick là Creator thật $\rightarrow$ Tấm khiên chống rate-limit mạnh nhất (+20–30đ).
  - **Micro-Follow sạch:** Chạy nhỏ giọt 3–4 follow/ca tích lũy ca sạch (+10đ/ca).
  - **Feed Sessions:** Lướt feed tạo Interest Graph tự nhiên để duy trì trust.

---

## 4. Chiến Lược Canary Dò Trần (+10% Quota)

### Nguyên lý Exploration vs Exploitation:
* **90–95% Dàn Chính (Exploitation):** Chạy theo Baseline Quota an toàn để tạo sản lượng ổn định.
* **5–10% Canary Fleet (Exploration):** Chạy vượt trần **+10%** (ví dụ Baseline 16 $\rightarrow$ Canary 18) để liên tục thăm dò phản ứng của server TikTok.

### INVARIANT CỐT LÕI: CANARY CHỈ ĐẶT Ở NHÓM KHỎE
* **Khỏe = Phòng Thí Nghiệm (Lab):** Nick trâu, chịu đòn tốt, fail chỉ dính Streak 1 nghỉ 3 ngày $\rightarrow$ Rủi ro cực nhỏ, giá trị học hỏi lớn.
* **Hồi phục (S1/S2) = Bệnh Nhân:** Mục tiêu duy nhất là **sống sót và xuất viện về Khỏe**.
  - **CẤM TUYỆT ĐỐI:** Bốc nick đang hồi phục làm Canary ép tải.
  - Ép tải nick hồi phục nếu fail sẽ bị tăng lên Streak 2 (giam 7d) hoặc Streak 3 (giam 15d), xóa sạch chu kỳ phục hồi $\rightarrow$ Tổn thất cực nặng nề!

### Diversity Rule khi bốc Canary Fleet:
* Tự động chọn 4–5 nick có `max_safe` và `total_followed` cao nhất từ nhóm Khỏe.
* **Bắt buộc:** Mỗi nick 1 cổng Proxy riêng biệt, loại trừ các proxy vừa dính ngắt cầu dao IP Circuit Breaker để bảo đảm tính khách quan và độc lập.
