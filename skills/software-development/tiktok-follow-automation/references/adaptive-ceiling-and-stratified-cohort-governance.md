# Quy Chuẩn Dò Trần Tăng Tiến & Phân Tầng Cohort Theo Dữ Liệu Nick (Consensus Spec V2)

## 1. Vấn Đề Cốt Lõi: Động Hóa Quota & Chống Thiên Kiến Lệch Mẫu (Selection Bias)
- **Hạn chế của trần tĩnh:** Cố định 16 follow/ca cho nick khỏe làm nghẽn sản lượng của các dàn nick già có thể đạt 25–30 lượt/ca (như farm ngoài). Nhưng nếu cấp bừa 25–30 cho nick non thì 82.6% dính nhả và vào tù hàng loạt (như sự cố Row 2 ngày 16/10).
- **Thiên kiến chọn lọc (Selection / Survivorship Bias):** Nick già (Following >100, Video >25, Tuổi >180d) vượt qua được mức 5–9 follow ở Hồi phục và 25–30 ở nick khỏe là do Inbound Trust của nick dày, KHÔNG PHẢI vì mức đó an toàn cho toàn bộ farm. Cấm dùng Mean toàn farm để áp trần.

---

## 2. Phân Tầng Tài Khoản Trước Ca Chạy (Stratified Cohorts)
Phân loại bắt buộc trước khi tính budget (`determine_cohort` trong `follow_state.py`):

| Cohort | Điều kiện Profile Metadata | Hồi phục 1 (T1) | Hồi phục 2 (T2) | Trần Khỏe (Core Cap) |
| :--- | :--- | :---: | :---: | :---: |
| **Rookie (Nick mỏng / non)** | Following < 30 HOẶC Video < 15 HOẶC Tuổi < 60d | Cap 4 (Range 2–4) | Cap 6 (Range 6) | **Khóa cứng 16** (không cho rướn) |
| **Mid-tier (Nick vừa)** | Following 30–100, Video 15–25, Tuổi 60–180d | Cap 4 (Range 2–4) | Cap 8 (Range 6–8) | **Dò trần tới 22** |
| **Veteran (Nick già / dày)** | Following > 100 VÀ Video > 25 VÀ Tuổi > 180d | Cap 5 (Range 3–5) | Cap 9 (Range 6–8) | **Dò trần tới 30 (Kịch kim)** |

---

## 3. Cơ Chế Dò Trần Tăng Tiến Có Bộ Nhớ (Adaptive Progressive Ceiling)
- **Quy tắc leo trần (+2):** Sau mỗi ca chạy sạch không nhả, nick Veteran/Mid nâng trần dò:
  $$\text{active\_ceiling} = \min(\text{core\_cap}, \;\text{proven\_safe\_ceiling} + 2)$$
  Trần phân bổ đều qua 2 phiên P1 và P2 (mỗi phiên tối đa 15 lượt) để không kích hoạt Rate Limit giờ của TikTok.
- **Khóa trần theo ca P1 & P2 (Shift Cap Deduction — Fix lỗi P2 bấm nick thứ 2 bị nhả):**
  - **Bản chất lỗi cũ:** Runner cấp mới budget ở Phiên 2 mà không trừ budget đã dùng ở Phiên 1 trong cùng một ca. TikTok áp dụng thuật toán Leaky Bucket / Sliding Window; nick Hồi phục T1 vừa ăn 4 follow ở P1, sang P2 lại bị cấp tiếp 4 follow -> nick rướn bấm đến cái thứ 2 là bị TikTok silent-drop ngay lập tức!
  - **Quy tắc khấu trừ bắt buộc:**
    $$\text{remaining} = \max(0, \;\text{cap} - \text{budget\_used})$$
    Nếu $\text{remaining} \le 0 \rightarrow$ Phiên 2 tự động **Safe-Skip (`budget = 0`)**, chỉ lướt feed dưỡng sinh, tuyệt đối không bấm follow để bảo toàn ngày sạch (`probation_clean_days`).
    - *Tier 1 (Cap 4 lượt/ca):* P1 ăn 4 lượt -> P2 safe-skip 0 lượt. P1 ăn 2 lượt -> P2 cấp tiếp $4 - 2 = 2$ lượt.
    - *Tier 2 (Cap 8 lượt/ca):* P1 ăn 4 lượt -> P2 ăn tiếp tối đa 4 lượt (tổng ca không quá 8).
- **Kỷ luật khi ăn nhả (FOLLOW_FAILED):**
  - Chấp hành Cooldown (đi tù 3–5 ngày theo `fail_streak`), thu hồi cờ tốt nghiệp, đi lại Hồi phục 1 $\rightarrow$ Hồi phục 2.
  - **Bộ nhớ bảo toàn:** Ghi nhận `last_failed_ceiling`. Hạ trần tham chiếu:
    $$\text{proven\_safe\_ceiling} = \max(\text{base\_max}, \;\text{proven\_safe\_ceiling} - 4)$$
  - **Khôi phục thông minh khi tốt nghiệp lại:** Tốt nghiệp Hồi phục 2 xong, nick nhận lại ngay trần tham chiếu an toàn (ví dụ từng gãy ở 25 $\rightarrow$ cấp lại 20 lượt), không bắt nick khỏe phải bò lại từ đáy 10–15.
- **Phanh an toàn lần 2:** Nếu ở trần lùi (20 lượt) mà tiếp tục bị nhả lần 2 $\rightarrow$ Lùi tiếp về sàn cơ sở 15–16 lượt và khóa cứng, chấp nhận nick đã bị TikTok hạ trust dài hạn, không cho rướn nữa.

---

## 4. Cơ Chế Nhả Follow & Rào Chắn Cho Nick Non (Anti-Action Restriction)
- **Bản chất kỹ thuật của "Nhả Follow":** Là **Account-Level Action Restriction (Khóa tính năng Follow ở cấp tài khoản)** do TikTok Backend âm thầm từ chối (Silent Drop / Optimistic UI rollback).
- **CẢNH BÁO / PITFALL CHÍ MẠNG (Bài học Row 2):**
  - **Sai lầm ngộ nhận:** Tưởng rằng "chỉ có follow Anchor lớn mới bị nhả, né Anchor vào bấm nick con trong Following list sẽ ăn".
  - **Thực tế chứng minh từ log M27 & M42:** M27 và M42 đã follow Anchor từ trước, bỏ qua Anchor đi thẳng vào bấm nick con đầu tiên $\rightarrow$ **Vẫn bị TikTok nhả 100% ngay tại nick con!**
  - **Nguyên nhân gốc rễ:** Nick non (Following 0–6) là "tài khoản nguội" (Cold Account). Khi đùng một cái vào tìm kiếm và bấm follow liên tiếp $\rightarrow$ AI TikTok kích hoạt bộ lọc **Velocity Spike trên nick nguội**, khóa cứng toàn bộ quyền follow của nick trong phiên đó. Anchor chẳng qua chỉ là nơi đầu tiên bot chạm vào nút follow!
- **Quy tắc vận hành chuẩn hóa cho Nick Non (Rookie):**
  - **Chưa đủ khỏe = Tuyệt đối CẤM FOLLOW:** Khi nick chưa đủ khỏe / chưa đủ trust (Following < 10, video < 10, đang trong thời gian dưỡng), TikTok kích hoạt Account-level Action Restriction. Lúc này **bấm ai cũng nhả**, kể cả follow tự nhiên trên Feed. CẤM tuyệt đối mọi hình thức follow (chéo mỏ hay tự nhiên) khi nick chưa đủ điều kiện.
  - **Dưỡng sinh thuần (Pure Feed Session):** Nick chưa đủ điều kiện bắt buộc chỉ chạy Feed thuần (lướt For You, xem video đủ dwell time, thả tim tự nhiên, 0 follow) để nuôi trust cho tới khi tài khoản đủ điều kiện.
  - **Không chế luật né Anchor:** Khi nick đã đủ điều kiện vào ca follow thì chạy đúng luồng chuẩn tự nhiên (xem video, like, follow Anchor rồi mở Following). CẤM các chiêu trò lách né như "bỏ qua Anchor lớn để bấm nick con" vì khi đã bị nhả là do nick bị khóa tính năng, không phải do Anchor.

---

## 5. Kiến Trúc Báo Cáo & Giám Sát (Observability Architecture: Telegram vs DB/Dashboard)
- **Quy tắc phân định cốt lõi:** Tuyệt đối không biến Telegram thành database để xả rác chat. Hệ thống phân chia rạch ròi 2 tầng:
  - **Telegram Alert = Control Tower (Tháp điều khiển):** Chỉ báo cáo KPI cấp cao và ngoại lệ (Exceptions/Anomalies) trong 1 tin nhắn súc tích để Operator liếc mắt trong 3 giây là nắm tình hình.
    - Bình thường (Khớp 100%): Chỉ in 1 dòng tóm tắt `+ Đối soát TikTok Web (+X Following thật - Khớp 100% so với script báo)`.
    - Bất thường (Lệch số / Lỗi): Chỉ in đúng các máy bị lệch hoặc lỗi kèm lý do, không in danh sách các máy chạy bình thường.
  - **SQLite DB & Dashboard 1905 = Telemetry & Forensics (Hồ sơ bệnh án):** Mọi dữ liệu chi tiết sâu (danh sách từng UID con, thời gian dwell time, lịch sử tăng tiến ceiling, trạng thái fail streak, trace log) được lưu trữ đầy đủ trong SQLite (`tiktok_tracker.db`) và hiển thị trên Dashboard cổng 1905 (`http://192.168.110.123:1905`).
  - **Cạm bẫy Fallback Mặc Định Trần Modal (Dashboard / Helper Trap):**
    * Khi nick chưa tốt nghiệp (`graduated is False` hoặc `total_followed < 15`), file state chưa có `proven_safe_ceiling`.
    * Helper/Dashboard CẤM fallback `proven_safe_ceiling = 15` và `active_ceiling = 17` cho nick chưa tốt nghiệp/rỗng lịch sử.
    * Với Tân Binh / Hồi phục, `proven_safe_ceiling` phải là `Chưa có` / `0 lượt`, và `active_ceiling` phải phản ánh đúng quota trần của stage hiện tại theo Cohort (T1: 4 lượt, T2: 6 lượt), tránh làm người dùng ngộ nhận nick chưa từng chạy đã chứng minh được trần 15.
- **Khả năng mở rộng (Scalability):** Thiết kế này đảm bảo khi farm mở rộng từ 160 lên 500+ máy, chat Telegram vẫn giữ nguyên độ gọn gàng, không bị nghẽn hay trôi tin nhắn cảnh báo quan trọng.

