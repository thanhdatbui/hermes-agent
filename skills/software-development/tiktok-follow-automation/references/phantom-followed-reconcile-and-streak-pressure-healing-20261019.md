# Phantom Followed Reconcile, Streak Pressure & Dynamic Healing Scheduling (2026-10-19)

## 1. Bản Chất Lỗi "Dữ Liệu Following Ảo" (Pre-Oct 1 Phantom Followed)
- **Hiện tượng**: Tài khoản có `len(state.followed)` cao bất thường so với số `Following` thực tế đọc từ Web snapshot TikTok (ví dụ M27 state ghi 115, nhưng Web chỉ có 43 follow).
- **Nguyên nhân cốt lõi**:
  * Trước ngày 01/10/2026, runner chưa có cơ chế verify hậu kiểm Path B (pull-to-refresh). Khi runner tap nút Follow trên UI, dù server TikTok âm thầm từ chối (Action Block / silent drop), script vẫn gọi `state.mark(uid, 'followed')`.
  * Hàng trăm UID bị ghi nhận oan là "đã follow" với timestamp `< 2026-10-01`.
- **Hậu quả**:
  1. *Cháy tệp Target*: Tệp nick nội bộ farm (~120-150 nick) bị script đánh dấu là đã follow gần hết. Khi vào ca chạy, script không tìm thấy target hợp lệ hoặc bị ép follow anchor lạ, dẫn tới fail phiên.
  2. *Sai lệch phân loại Cohort*: Hệ thống thấy `len(followed) > 100` nhầm tưởng là cựu binh `veteran`, cấp trần cao khiến nick non chết oan.
- **Quy trình Reconcile chuẩn (`tools/reconcile_phantom_followed.py`)**:
  * Quét đối soát `len(state.followed)` vs `snapshots.following` mới nhất từ Web.
  * Nếu `state_count > real_web` và tồn tại entries trước 2026-10-01: tính `diff = state_count - real_web`.
  * Lọc các entries có timestamp `< '2026-10-01'`, sắp xếp theo thời gian tăng dần và loại bỏ tối đa `diff` entries ảo.
  * Tự động sao lưu file state gốc sang `.bak_reconcile_<date>` trước khi ghi đè.
  * Kết quả thực tế 19/10/2026: Thanh lọc thành công **303 follow ảo** trên **19 tài khoản** (M27 từ 115 về 43, M23 từ 143 về 115, M32 từ 20 về 0...), trả lại tệp target sạch.

---

## 2. Áp Lực Án Tích Toàn Farm & Tử Huyệt Của Bộ Chọn Dưỡng Sinh Cũ (`healing_selector.py`)
- **Phân bổ thực tế của 211 nick dính `fail_streak >= 2` toàn farm**:
  * **Row 2**: 58 nick (`sum_streak = 205`) — Nặng nhất farm.
  * **Row 1**: 50 nick (`sum_streak = 151`) — Nặng thứ 2 farm.
  * **Row 4**: 46 nick (`sum_streak = 111`).
  * **Row 3**: 31 nick (`sum_streak = 77`).
  * *Row 5, 6, 7, 8*: chỉ có từ 0 đến 12 nick dính streak (Row 8 = 0).
- **Lỗ hổng của `healing_selector.py` cũ**:
  * Chỉ tính tỷ lệ fail phẳng `fail_rate` (đếm nick, coi streak 1 ngang với streak 6) và cộng điểm `young_rate` (tỷ lệ nick < 10 video).
  * Do Row 7, Row 8 có nhiều nick non (`young_rate` cao 80-90%), Row 7 và Row 8 luôn thắng điểm và chiếm trọn các ca dưỡng sinh.
  * Trong khi đó, **Row 1 và Row 2 (nơi tập trung 90% nick dính án phạt tù đọng)** lại bị coi là "hàng khỏe" và bị bỏ đói nhịp dưỡng sinh suốt nhiều tuần.
- **Công thức chấm điểm cứu hộ mới theo Áp Lực Án Tích (`streak_pressure`)**:
  $$\text{Score} = 100 \times \text{fail\_rate} + \mathbf{60 \times avg\_streak} + 20 \times \text{young\_rate}$$
  * Trong đó: $\text{avg\_streak} = \frac{\sum \text{fail\_streak}}{\text{total\_accounts}}$.
  * Điểm thực tế sau cải tiến: **Row 2 (254.6 điểm)** và **Row 1 (213.7 điểm)** vượt trội hoàn toàn so với Row 5–8 (75–95 điểm).
  * Trong 4 ca dưỡng sinh (Tối N3 và 3 ca N4), hệ thống tự động bốc tuần tự **Row 2 ➔ Row 1 ➔ Row 4 ➔ Row 3** để xả tải, lướt feed ngâm tài khoản và đăng video, chấm dứt tình trạng bỏ rơi nick bị thương.

---

## 3. Hoàn Thiện Cơ Chế Động Cho Probation Tier 1 & 2
- **Khóa 1 Phiên Duy Nhất (Single-Session Lock)**:
  * Nick probation (Tier 1 trần 3-4, Tier 2 trần 5-6) dồn 100% ngân sách chạy ở Phiên 1 (06:00).
  * Nếu `budget_used > 0`, Phiên 2 (08:00) tự động trả về `budget = 0` (SKIP), triệt tiêu rủi ro bị TikTok rate-limit do khoảng cách 2h quá ngắn.
- **Né Mốc Gãy Lần Trước (`last_failed_ceiling`)**:
  * Ghi nhận `last_failed_ceiling` trên 100% tài khoản khi gặp lỗi (kể cả probation).
  * Khi tính ngân sách: `if last_failed_ceiling >= 2: cap = min(cap, max(1, last_failed_ceiling - 1))`. Luôn chạy dưới mốc đã từng bị TikTok chặn.
- **Bóp Trần Khi Án Tích Nặng (`fail_streak >= 3`)**:
  * Nick tái phạm nhiều lần: `if fail_streak >= 3: cap = max(1, cap - 1)`. Chỉ cấp 1-2 follow dò đường an toàn.
