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

## 4. Rào Chắn Anchor Protection Cho Nick Non (Mode 2)
- **Bản chất kỹ thuật sự cố Row 2:** Nick non (Following 0–6) search và bấm follow Anchor lớn ($\ge 150$ following) bị TikTok nhận diện bất thường $\rightarrow$ TikTok dùng **Optimistic UI** (app hiện Đang theo dõi nhưng server ngầm drop) $\rightarrow$ Bot vuốt reload kiểm tra thấy bị nhả về nút đỏ `Follow` $\rightarrow$ Kích hoạt `FOLLOW_FAILED` khiến 82.6% máy dính án phạt oan uổng.
- **Quy tắc bắt buộc:**
  - Anchor trong Mode 2 chỉ là cửa ngõ để mở danh sách Following công khai của họ, **không bắt buộc phải follow Anchor mới đọc được danh sách**.
  - Nick thuộc **Cohort Rookie**: Runner tự động bỏ qua bước follow Anchor lớn (`skipped_rookie_anchor_protection`), bấm thẳng vào tab Following để follow các nick con bình thường.
