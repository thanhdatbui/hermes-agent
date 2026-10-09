# Dynamic Quota Optimization, Streak-Based Recovery & Automated Canary Probing

## 1. Bản Chất Vận Hành Độc Lập: Entity (Máy, Row)

* **Quy tắc bất biến:** Đơn vị sinh tồn và theo dõi trạng thái độc lập là `(Máy, Row) = 1 Account`.
* Ca sáng chạy Row 1, ca chiều chạy Row 2 là hai nick hoàn toàn tách biệt về danh tính, trust score và lịch sử vi phạm.
* **CẤM TUYỆT ĐỐI:** Gộp quota hay trạng thái theo máy/ngày (`total_follow / machine`). Máy chỉ là container chứa thiết bị chạy.

---

## 2. Nghịch Lý Simpson & Phân Tầng Đo Lường (Stratified Cohorts)

* **Cạm bẫy Flat Analysis:** Gom toàn bộ các ca chạy vào 4 giỏ chung (`1-4`, `5-9`, `10-14`, `15+`) tạo ra số liệu ảo "15+ an toàn nhất (96.9%)", vì chỉ có nick Nòng cốt siêu khỏe mới được cấp quota 15+, trong khi giỏ `1-4` gánh 100% nick vừa ra tù.
* **Chuẩn hóa đo lường:** Dashboard và thuật toán bắt buộc phải bóc tách dữ liệu thành 3 Cohort độc lập:
  1. **⚡ Phục hồi Nhanh (Streak 1):** Vừa hết án giam 3 ngày, cần 1 ca sạch (quota baseline: 4-5 fl/ca).
  2. **🌱 Hồi phục Tiêu chuẩn (Streak 2):** Vừa hết án giam 7 ngày, cần 2 ca sạch (quota baseline: 7-8 fl/ca).
  3. **💪 Nòng cốt / Khỏe:** Đã tốt nghiệp, trust cao (quota baseline: 12-16 fl/ca).

---

## 3. Mô Hình Phục Hồi Thích Ứng Theo Streak (Streak-Based Recovery Ladder)

Thay vì ép mọi nick phải đi qua 2 nấc cố định (Hồi phục 1 -> Hồi phục 2 mất 14-15 ngày), độ sâu phục hồi (Recovery Depth) phụ thuộc trực tiếp vào `fail_streak` trước đó:

| Mức án trước đó | Thời gian giam Cooldown | Chế độ phục hồi sau khi ra tù | Số ca thử thách | Quota thử thách | Thăng hạng về Khỏe |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **Streak = 1** *(Lần đầu bị nhả)* | **3 ngày** | ⚡ Phục hồi Nhanh (Fast-track) | **1 ca sạch** | **4 – 5** lượt | Chạy xong 1 ca sạch -> Tốt nghiệp về Khỏe ngay |
| **Streak = 2** *(Tái phạm lần 2)* | **7 ngày** | 🌱 Phục hồi Tiêu Chuẩn (Standard) | **2 ca sạch** | **7 – 8** lượt | Ca 1 (5-6 fl), Ca 2 (7-8 fl) sạch -> Về Khỏe |
| **Streak $\ge$ 3** *(Tái phạm nặng)* | **15 ngày** | 🛡️ Thử Thách Sâu (Deep Probation) | **4 – 6 ca sạch** | **3 – 5** lượt | Rửa sạch cờ spam trước khi thăng hạng |

*Chốt an toàn Fail-Closed:* Nếu ở bất kỳ ca phục hồi nào bị nhả tiếp -> Tăng `fail_streak` lên nấc kế tiếp và quay lại giam Cooldown.

---

## 4. Công Thức Tối Ưu Hóa Quota Tự Động (Auto Quota Optimizer)

Hàm mục tiêu tối ưu hóa quyết định dưới rủi ro (Risk-Adjusted Decision Optimization):

$$U(q \mid T) = q \times (1 - P_{\text{nhả}}(q)) - P_{\text{nhả}}(q) \times \text{Cost}_{\text{Cooldown}}(T)$$

Trong đó chi phí cơ hội giam phạt $\text{Cost}_{\text{Cooldown}}$ được định lượng:
* Phục hồi 1: $\text{Penalty} = 30$ follows (giam 3-7 ngày).
* Phục hồi 2: $\text{Penalty} = 60$ follows (giam 7-15 ngày + mất ngày sạch).
* Nòng cốt Khỏe: $\text{Penalty} = 120$ follows (mất vị thế Khỏe, giam cooldown + làm lại probation).

Thuật toán tự động tìm $q^* = \arg\max U(q)$ cho từng phân tầng, tự động ghìm trần khi tỷ lệ nhả vượt ngưỡng cho phép.

---

## 5. Tự Động Hóa Đội Dò Đường Canary (+10% Quota Ceiling Probe)

Chiến lược cân bằng **Exploration (Thăm dò)** vs **Exploitation (Khai thác)**:
* **90–95% Dàn chính:** Chạy ở mức an toàn Baseline $q^*$ để giữ ổn định sản lượng.
* **5–10% Đội Canary (3–5 nick):** Chạy vượt trần $+10\%$ ($q^*_{\text{canary}} = \text{round}(q^* \times 1.10)$) để tìm True Ceiling thực tế của thuật toán TikTok.

### 4 Quy tắc chọn nick Canary tự động (Automated Selector):
1. **Chỉ chọn nick nhóm Khỏe:** Có `max_safe` cao nhất và `total_followed` lớn nhất (ví dụ M28, M50, M10, M45).
2. **Quy tắc đa dạng Proxy (Proxy Diversity Rule):** Bắt buộc tối đa 1 nick / 1 cổng Proxy. Tuyệt đối không chọn 2 nick chung 1 đường Proxy làm Canary.
3. **Loại trừ Proxy có tiền án gần:** Không chọn máy trên proxy vừa bị ngắt bởi IP Circuit Breaker.
4. **Vòng lặp phản hồi đóng (Closed-Loop Feedback):**
   * Nếu Canary an toàn 3 ca liên tiếp -> Tự động nới trần khuyến nghị toàn dàn.
   * Nếu Canary dính nhả (`FOLLOW_FAILED`) -> Cầu dao ngắt proxy ngay, kill-switch hủy probe cho nick đó, giữ nguyên trần an toàn của dàn chính.
