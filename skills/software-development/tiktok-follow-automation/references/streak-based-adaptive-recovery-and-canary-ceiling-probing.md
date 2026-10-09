# Streak-Based Adaptive Recovery Depth & Automated Canary Quota Probing

## 1. Bản Chất Vận Hành Farm: Entity Lifecycle (Máy, Row)

### Đơn vị sinh tồn độc lập tuyệt đối: `(Machine, Row)`
- Một máy vật lý (ví dụ Samsung S7) chạy nhiều tài khoản khác nhau theo ca/slot (ca sáng Row 1, ca chiều Row 2, ca tối Row 3...).
- **CẤM TUYỆT ĐỐI gộp quota ngày theo máy:** Row 1 và Row 2 là 2 tài khoản TikTok hoàn toàn khác biệt về tuổi nick, số video, trust score và lịch sử vi phạm.
- Máy chỉ là container phần cứng. Toàn bộ theo dõi sức khỏe, nấc thang, và quota BẮT BUỘC gắn vào `(machine, row)`.

---

## 2. Nghịch Lý Simpson & Bẫy Thống Kê Flat Trên Dashboard

### Nguyên nhân con số ảo "15+ follow an toàn nhất (96.9%)":
- Dashboard gom toàn bộ các ca chạy vào 4 giỏ flat (`1-4`, `5-9`, `10-14`, `15+`).
- Mức `1 - 4 follow`: Nhận 100% ca chạy của nick yếu, nick vừa ra tù đang bị TikTok theo dõi gắt gao -> Tỷ lệ nhả dồn về đây (33.3%).
- Mức `15+ follow`: Chỉ duy nhất nick Nòng cốt siêu khỏe (>200 ngày, >20 clip, sống sót qua nhiều đợt quét) mới được cấp phép chạy -> Tỷ lệ an toàn cao (96.9%).
- **Hậu quả:** Gây ngộ nhận rằng chạy 15+ là an toàn cho mọi nick. Nếu đem nick mới/yếu chạy 15+ sẽ bị TikTok quét chết dàn ngay lập tức.
- **Giải pháp:** Xóa bỏ bảng gộp flat. BẮT BUỘC đo lường và đưa ra quota khuyến nghị riêng cho từng Cohort độc lập.

---

## 3. Cơ Chế Nấc Thang Thích Ứng Theo Streak (Streak-Based Adaptive Recovery)

Thay vì ép mọi nick đi qua 2 nấc cố định (Phục hồi 1 -> Phục hồi 2) mất 14 ngày làm lãng phí công suất của dàn nick khỏe, độ sâu phục hồi (`recovery depth`) được quyết định trực tiếp bởi `fail_streak` trước đó:

```text
               ┌── [Streak = 1] ──► PHỤC HỒI NHANH (Fast-track) ──► 1 ca sạch (5 - 7 fl) ──┐
               │                                                                            │
COOLDOWN MÃN HẠN ── [Streak = 2] ──► PHỤC HỒI TIÊU CHUẨN         ──► 2 ca sạch (5 - 8 fl) ──┼──► TRỞ LẠI
               │                                                                            │    NHÓM KHỎE
               └── [Streak >= 3] ─► THỬ THÁCH SÂU (Deep Probation) ──► 4-6 ca sạch (3 - 5 fl) ─┘
```

1. **Streak = 1 (Lần đầu bị nhả, Cooldown 3 ngày):**
   - **Phục hồi Nhanh (Fast-track):** Chỉ cần **1 ca chạy sạch** (quota 5 - 7 follow). Nếu ca này an toàn (0 drop) -> Tốt nghiệp quay lại nhóm Khỏe ngay lập tức.
2. **Streak = 2 (Tái phạm lần 2, Cooldown 7 ngày):**
   - **Phục hồi Tiêu Chuẩn (Standard):** Cần **2 ca sạch** liên tiếp (Ca 1: 5-6 fl, Ca 2: 7-8 fl) -> Mới được thăng hạng về Khỏe.
3. **Streak >= 3 (Tái phạm nặng, Cooldown 15 ngày):**
   - **Thử Thách Sâu (Deep Probation):** Bắt buộc chạy tải nhẹ (3 - 5 follow) qua 4 - 6 ca sạch để rửa sạch cờ spam trong sổ đen của TikTok.
4. **Chốt chặn Fail-Closed:**
   - Nếu ở bất kỳ ca phục hồi nào mà bị nhả tiếp -> Tăng `fail_streak` lên nấc tiếp theo và quay lại giam Cooldown dài hơn theo progressive backoff.

---

## 4. Công Thức Tối Ưu Hóa Quota Tự Động (Risk-Adjusted Decision Optimization)

Mục tiêu không phải tối đa hóa follow đơn thuần, mà là tối đa hóa giá trị ròng sau khi trừ chi phí thiệt hại do bị giam Cooldown:

$$U(q \mid T) = q \times (1 - P_{\text{nhả}}(q \mid T)) - P_{\text{nhả}}(q \mid T) \times \text{Cost}_{\text{Cooldown}}(T)$$

Trong đó chi phí giam Cooldown ($\text{Cost}_{\text{Cooldown}}$) tỷ lệ thuận với giá trị của nick:
- **Phục hồi 1 (Streak 1):** $\text{Cost} \approx 30$ follows (nguy cơ tăng lên Streak 2 giam 7 ngày).
- **Phục hồi 2 (Streak 2):** $\text{Cost} \approx 60$ follows (nguy cơ tăng lên Streak 3 giam 15 ngày).
- **Nòng Cốt / Khỏe:** $\text{Cost} \approx 120$ follows (mất vị thế Khỏe, giam 3 ngày + mất toàn bộ chuỗi ngày sạch).

---

## 5. Tự Động Hóa Dò Trần Bằng Đội Dò Đường Canary (+10% Quota)

Chiến lược kết hợp **Exploitation (90-95% Dàn chính)** và **Exploration (5-10% Canary)**:

### A. Tiêu chí chọn Nick Canary tự động (Automated Canary Selector):
- Chỉ bốc trong nhóm **Khỏe** có `Max Safe` cao nhất lịch sử và uptime ổn định.
- **Diversity Rule:** Tối đa 1 nick trên mỗi cổng Proxy, loại trừ các proxy vừa có máy dính `FOLLOW_FAILED`.
- **CẤM TUYỆT ĐỐI** bốc nick đang trong giai đoạn hồi phục làm Canary.

### B. Cấp Quota Canary tự động:
$$\text{Quota}_{\text{Canary}} = \text{Quota}_{\text{Baseline}} \times 1.10 \quad (+10\% \text{ Quota})$$
*(Ví dụ: Nhóm Khỏe chạy 12-14 thì Canary chạy 15-16 lượt/ca).*

### C. Vòng phản hồi tự động (Closed-Loop Feedback):
- **Canary thành công 3 ca liên tiếp:** Tự động mở rộng biên an toàn cho toàn dàn chính.
- **Canary bị nhả:** Kích hoạt Kill-switch ngay lập tức, khóa canary cho nick đó, giữ nguyên trần an toàn cho toàn dàn. Bán kính thiệt hại (Blast Radius) chỉ giới hạn trong 2-3 nick thử nghiệm.
