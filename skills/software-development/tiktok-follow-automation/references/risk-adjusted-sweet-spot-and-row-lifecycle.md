# Risk-Adjusted Sweet Spot Optimization & Row-Level Account Lifecycle

## 1. Nguyên Tắc Cốt Lõi: Đơn Vị Độc Lập Là (Máy, Row)

### A. Thực trạng vận hành thực tế
- Mỗi điện thoại trong farm chạy nhiều tài khoản theo cơ chế phân bổ ca:
  - **Ca sáng:** Chạy `Row 1` (Account A).
  - **Ca chiều:** Chạy `Row 2` (Account B).
- **CẤM TUYỆT ĐỐI gộp quota ngày theo máy:** Account A và Account B là 2 thực thể vòng đời hoàn toàn độc lập về tuổi tài khoản (`age`), số lượng video (`video_count`), trust score, lịch sử vi phạm (`fail_streak`) và ngày mãn hạn cooldown (`cooldown_until_date`).
- Mọi quyết định quota, phân tầng sức khỏe và ghi nhận trạng thái vi phạm BẮT BUỘC gắn vào cặp khóa `(machine, account_row_index)`.

---

## 2. Finite State Machine Chuẩn Của Từng Account

```text
                     [fail / nhả follow]
 🟢 KHỎE (Healthy) ────────────────────────┐
 (10 - 15 follow/ca)                       │
    ▲                                      ▼
    │ [clean_days >= 6]               🔴 COOLDOWN THEO STREAK
    │                                 (Giam 3d / 7d / 15d)
 🌱 PHỤC HỒI 2 (7 - 9 fl/ca)               │
    ▲                                      ▼ [mãn hạn cooldown]
    │ [clean_days >= 3]               🌱 PHỤC HỒI 1 (3 - 5 fl/ca)
    └──────────────────────────────── (fail tiếp -> streak += 1 -> quay lại Cooldown)
```

### Quy tắc nấc thang và lũy tiến phạt:
1. **🟢 KHỎE (Normal/Healthy):** Quota 10 – 15 follow/ca. Khi bị nhả $\rightarrow$ `set_follow_failed()`, tăng `fail_streak = 1`, đưa vào `COOLDOWN` (giam 3 ngày). Quota trong cooldown = **0 follow**.
2. **🌱 PHỤC HỒI 1:** Sau khi hết hạn cooldown, nick quay lại thử thách:
   - Quota thăm dò: **3 – 5 follow/ca**.
   - **Thành công (chạy sạch):** Tích lũy `probation_clean_days`. Đủ 3 ngày sạch $\rightarrow$ Thăng hạng lên **Phục hồi 2**.
   - **Thất bại (nhả tiếp):** Reset `probation_clean_days = 0`, tăng `fail_streak` (Streak 1 $\rightarrow$ 2 hoặc 2 $\rightarrow$ 3) $\rightarrow$ Quay lại `COOLDOWN` với thời gian giam dài hơn (7 ngày hoặc 15 ngày).
3. **🌱 PHỤC HỒI 2:** Quota tăng lên **7 – 9 follow/ca**:
   - **Thành công (chạy sạch):** Đạt đủ tổng cộng 6 ngày sạch $\rightarrow$ Tốt nghiệp (`graduated = True`), xóa streak, quay về nhóm **Khỏe**.
   - **Thất bại (nhả tiếp):** Reset ngày sạch, tăng `fail_streak` $\rightarrow$ Giam lại vào `COOLDOWN`.

---

## 3. Bản Chất Nghịch Lý Simpson & Số Ảo "15+ An Toàn Nhất"

### Nguyên nhân kỹ thuật dẫn đến số liệu ảo:
1. **Thiên kiến kẻ sống sót (Survivorship Bias):** Mức 15+ follow/ca chỉ được cấp cho những nick nòng cốt siêu khỏe, sống sót qua hàng chục đợt quét. Nhóm này tỷ lệ giữ follow dĩ nhiên cao (96.9%).
2. **Ca bị nhả bị cụt số follow (Truncated Failures):** Khi TikTok phát hiện bot và nhả follow, session follow thường bị ngắt hoặc chặn ngay tại lượt 1 hoặc 2. Do đó, các ca thất bại bị ghi nhận là ca chạy với count = 1–2 $\rightarrow$ Bị dồn cục vào giỏ `1 - 4 follow/ca`, làm giỏ này mang tiếng "nhả 33.3%".
3. **Gộp chung dữ liệu (Pooled Flat Analysis):** Gom tất cả các tầng sức khỏe vào 1 bảng phân tích duy nhất đã bóp méo bức tranh thực tế.

---

## 4. Công Thức Toán Học: Risk-Adjusted Decision Optimization

Không dùng heuristic cảm tính [3-5], [7-9], [10-15]. Con số Sweet Spot cho từng phân tầng $T$ được tính toán tự động từ log lịch sử:

### A. Hàm mục tiêu (Objective Function):
$$U(q \mid T) = Y(q \mid T) - \lambda \cdot R(q \mid T)$$

Trong đó:
* $q$: Mức quota thử nghiệm ($q \in [1, 20]$).
* $Y(q \mid T)$: **Sản lượng follow kỳ vọng giữ được** = $q \times (1 - P_{\text{nhả}}(q \mid T))$.
* $R(q \mid T)$: **Kỳ vọng thiệt hại do Cooldown** = $P_{\text{nhả}}(q \mid T) \times \text{Cost}_{\text{Cooldown}}(T)$.
* $\lambda$: Hệ số ưu tiên an toàn ($\lambda \ge 1.0$).

### B. Bảng Chi Phí Cooldown ($\text{Cost}_{\text{Cooldown}}$) theo tầng:
* **Phục hồi 1:** Nhả tiếp $\rightarrow$ Streak 2 (giam 7 ngày) hoặc Streak 3 (giam 15 ngày) $\rightarrow$ Mất cơ hội chạy follow trong 7–15 ngày:
  $$\text{Cost}_{\text{Cooldown}}(\text{PH1}) \approx 30\text{ follows}$$
* **Phục hồi 2:** Nhả tiếp $\rightarrow$ Vứt bỏ 3 ngày sạch đã tích lũy + giam 7–15 ngày:
  $$\text{Cost}_{\text{Cooldown}}(\text{PH2}) \approx 60\text{ follows}$$
* **Khỏe:** Đang ở đỉnh cao bị nhả $\rightarrow$ Mất cờ tốt nghiệp, giam 3 ngày + phải cày lại 6 ngày sạch ở PH1 và PH2:
  $$\text{Cost}_{\text{Cooldown}}(\text{Khỏe}) \approx 120\text{ follows}$$

### C. Con Số Khuyến Nghị Tối Ưu (Sweet Spot $q^*$):
$$q^*_T = \arg\max_{q} \Big[ q \times (1 - P_{\text{nhả}}(q)) - P_{\text{nhả}}(q) \times \text{Cost}_{\text{Cooldown}}(T) \Big]$$
*kèm điều kiện khống chế tỷ lệ nhả tối đa:*
* Phục hồi 1: $P_{\text{nhả}} \le 5\%$ (ưu tiên số 1 là bảo vệ nick không tăng streak).
* Phục hồi 2: $P_{\text{nhả}} \le 4\%$.
* Khỏe: $P_{\text{nhả}} \le 2\%$.
