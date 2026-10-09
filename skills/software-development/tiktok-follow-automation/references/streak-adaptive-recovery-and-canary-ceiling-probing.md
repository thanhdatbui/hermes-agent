# Streak-Adaptive Recovery, Cohort Sweet Spot & Canary Ceiling Probing

## 1. Nguyên Lý Vận Hành Cốt Lõi: Đơn Vị Account `(Máy, Row)` Độc Lập
- **Máy chỉ là container phần cứng, Account mới là thực thể sinh tồn:**
  - Ca sáng chạy Row 1, ca chiều chạy Row 2 là 2 nick hoàn toàn khác nhau về danh tính, trust score và lịch sử.
  - **CẤM TUYỆT ĐỐI:** Gộp quota ngày hay gộp trạng thái theo số máy. Mọi metric follow, drop, cooldown và recovery bắt buộc gắn chặt vào tuple `(machine, row, account_id)`.

---

## 2. Cơ Chế Hồi Phục Thích Ứng Theo Streak (Streak-Adaptive Recovery Ladder)
Thay vì ép mọi nick đi qua 2 nấc cứng (Phục hồi 1 -> 2 mất 14-15 ngày), chiều sâu thử thách được quyết định trực tiếp bởi `fail_streak` trước đó:

| Mức án Cooldown | Thời gian giam | Chế độ phục hồi sau khi ra tù | Số ca thử thách | Quota thử thách | Điều kiện thăng hạng về Khỏe |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **Streak = 1** *(Lần đầu bị nhả)* | **3 ngày** | ⚡ **Phục hồi Nhanh (Fast-track)** | **Đúng 1 ca** | **5 – 7** lượt | 1 ca sạch (0 drop) -> Tốt nghiệp về Khỏe ngay! |
| **Streak = 2** *(Tái phạm lần 2)* | **7 ngày** | 🔄 **Phục hồi Tiêu Chuẩn (Standard)** | **2 ca sạch** | **5 – 8** lượt | Ca 1 (5-6 fl), Ca 2 (7-8 fl) sạch -> Về Khỏe. |
| **Streak >= 3** *(Tái phạm nặng/sổ đen)* | **15 ngày** | 🛡️ **Thử Thách Sâu (Deep Probation)** | **4 – 6 ca sạch** | **3 – 5** lượt | Chạy tải nhẹ qua nhiều ca để rửa sạch cờ spam. |

*Chốt an toàn Fail-closed:* Nếu bị nhả ở bất kỳ ca phục hồi nào -> Lập tức tăng `fail_streak += 1` và giam lại vào Cooldown dài hơn theo progressive backoff.

---

## 3. Auto Quota Engine & Toán Học Sweet Spot Theo Từng Cohort
- **Triệt tiêu Nghịch lý Simpson (Simpson's Paradox):**
  - CẤM TUYỆT ĐỐI gom chung toàn farm vào 4 giỏ flat (`1-4`, `5-9`, `10-14`, `15+`).
  - Phân tích bắt buộc chia thành các Cohort độc lập: Tân binh, Phục hồi nhanh (S1), Phục hồi tiêu chuẩn (S2+), Nòng cốt (Khỏe).
- **Hàm mục tiêu Tối ưu hóa Rủi ro (Risk-Adjusted Decision Optimization):**
  $$U(q \mid T) = \Big[ q \times (1 - P_{\text{nhả}}(q \mid T)) \Big] - \Big[ P_{\text{nhả}}(q \mid T) \times \text{Cost}_{\text{Cooldown}}(T) \Big]$$
  Trong đó chi phí cơ hội giam Cooldown:
  - $\text{Cost}_{\text{Cooldown}}(\text{S1}) \approx 30\text{ follows}$ (mất cữ giam 7d).
  - $\text{Cost}_{\text{Cooldown}}(\text{S2}) \approx 60\text{ follows}$ (mất cữ giam 15d + mất ca sạch).
  - $\text{Cost}_{\text{Cooldown}}(\text{Khỏe}) \approx 120\text{ follows}$ (mất trạng thái Khỏe, giam 3d + làm lại từ đầu).
- **Điểm ngọt tối ưu ($q^*_T$):** Mức quota có điểm $U(q)$ cao nhất trong Cohort $T$ thỏa mãn ngưỡng rủi ro $P_{\text{nhả}} \le \text{Threshold}(T)$.

---

## 4. Chiến Lược Canary Vượt Trần 10% Dò Ngưỡng (Canary Ceiling Probing)
- **Cân bằng Exploration vs Exploitation:**
  - **90 – 95% Dàn chính (Khai thác):** Chạy baseline an toàn $q^*$ để tối đa hóa sản lượng ổn định.
  - **5 – 10% Đội Canary (Thăm dò biên):** Chạy vượt trần **+10%** ($q_{\text{canary}} = \text{round}(q^* \times 1.1)$) để kiểm tra xem TikTok đã nâng hay hạ trần tải.
- **4 Điều kiện an toàn bắt buộc cho Canary:**
  1. Chỉ chọn nick trâu nhất nhóm Khỏe (`Max Safe` cao, tuổi đời > 100 ngày, video >= 15). CẤM bốc nick đang hồi phục.
  2. Tăng đúng +10% (tương đương +1 đến +2 follow), không nhảy vọt.
  3. Cơ chế Rollback tức thì: Nếu 1 nick Canary bị nhả -> Ngắt ngay nhánh thử nghiệm, giữ nguyên baseline dàn chính.
  4. Cách ly IP: Chạy trên proxy sạch, không chạy chung ca với nick đang hồi phục.

---

## 5. Cạm Bẫy Bug Thống Kê Cần Tránh
- **Kiểm tra trạng thái Cooldown:** BẮT BUỘC dựa vào mốc thời gian hết hạn (`cooldown_until_at > now` hoặc `cooldown_until_date >= today`).
- **CẤM** chỉ dựa vào cờ `follow_failed == True` để kết luận đang Cooldown, vì cờ này chỉ được reset khi nick thực sự vào ca chạy mới; nick đã mãn hạn 5-7 ngày vẫn bị đè là Cooldown nếu dùng logic cũ.
