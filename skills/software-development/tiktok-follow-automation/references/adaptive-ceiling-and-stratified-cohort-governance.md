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
  - **Pre-flight Trust Gate:** Nick có Following < 10 và đang dưỡng tuyệt đối không ép chạy cày mỏ follow chéo ngay.
  - **Dưỡng sinh làm ấm (Feed Nurture):** Bắt buộc chạy Feed Session thuần (lướt For You, xem video đủ dwell time, thả tim tự nhiên) để làm ấm Inbound Trust trước.
  - **Mồi tự nhiên trước khi cày mỏ:** Nếu muốn kiểm tra tính năng follow, mồi follow tự nhiên 1 tài khoản trên Feed For You; khi TikTok thực sự ghi nhận trên server thì mới đưa nick vào kịch bản follow hàng loạt.
