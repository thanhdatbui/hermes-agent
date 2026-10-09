# Fleet-Wide Post-Cooldown Relapse & Video-Row Correlation Audit (07/10/2026)

## 1. Bối cảnh & Quy mô Khảo sát
- **Dữ liệu đối soát:** 411 state files (`runs/state/follow_state_*.json`) trên 80 máy phone farm.
- **Mục tiêu:** Đánh giá hành vi thực tế của các tài khoản sau khi mãn hạn cooldown (ra tù): tỷ lệ dính nhả liền liên tục vs tỷ lệ follow được vài cái vs tỷ lệ phục hồi hoàn toàn.

---

## 2. Số liệu Tổng quan Fleet (411 accounts)
- **Chưa từng dính phạt (Streak = 0):** 22 nick (5.4%)
- **Mới dính phạt lần đầu (Streak = 1 - đang/vừa xong cữ 3 ngày):** 174 nick (42.3%)
- **Đã từng mãn hạn ra tù (hoặc tái phạm >= 2 lần):** 215 nick (52.3%)

### Hành vi sau khi ra tù (trên 215 nick đã qua cooldown):
1. **Cứ ra tù là dính nhả liền liên tục (Fail ngay lượt đầu / 0 follow được):** 184 - 200 nick (~85.6% - 93.0%).
2. **Ra tù follow được vài cái (1 - 5 cái) rồi dính lại:** 15 - 29 nick (~7.0% - 13.5%).
3. **Phục hồi hoàn toàn (Streak về 0, follow ổn định > 50-100 lượt):** Đúng 2 nick (0.5% toàn farm).

---

## 3. Tương quan theo Số lượng Video & Inbound Trust
- **< 10 video (Chưa đạt chuẩn Dual Gate):** 179 nick.
  - Tỷ lệ ra tù nhả liền: **94.7%** (71/75 nick ra tù).
  - Tỷ lệ follow được vài cái: **5.3%** (4/75 nick).
- **10 - 19 video (Đạt chuẩn tối thiểu):** 159 nick.
  - Tỷ lệ ra tù nhả liền: **82.5%** (94/114 nick ra tù).
  - Tỷ lệ follow được vài cái: **17.5%** (20/114 nick) — cao gấp 3 lần nhóm < 10 video.
- **>= 20 video (Dày dặn video):** 62 nick.
  - Tỷ lệ ra tù nhả liền: **91.3%** (21/23 nick ra tù).
  - Tỷ lệ chưa từng bị phạt cao nhất farm: 10 nick (~16.1%).
  - Cả 2 nick duy nhất phục hồi hoàn toàn của farm đều thuộc nhóm này (> 22 video, tuổi acc > 4 tháng).

---

## 4. Tương quan theo Row (Vị trí Slot trên Máy)
- **Row 1:** 80 nick, Avg 23.8 video. Chưa từng dính fail: 12 nick (cao nhất). Nhưng khi đã dính jail thì ra tù nhả liền 93.3%.
- **Row 2:** 78 nick, Avg 12.5 video. Tỷ lệ "nhích" được vài cái sau ra tù cao nhất (29.6% - 16 nick) nhờ ăn được cữ warm-up 3-5 cái.
- **Row 3 & Row 4:** Avg 8.9 - 10.6 video. Tỷ lệ nhả liền sau ra tù đều trên 91%.
- **Row 5, 6, 7:** Dàn acc mới add sau, Avg 6.1 - 6.9 video. 100% tài khoản khi ra tù bị nhả lại ngay lập tức.

---

## 5. Kết luận Vận hành & Khuyến nghị
1. **Nghỉ follow đơn thuần KHÔNG tự hồi phục Trust:** Một khi đã bị TikTok gắn cờ spam follow, việc chờ hết hạn cooldown rồi bấm tiếp gần như chắc chắn kích hoạt silent-drop lại (> 85%).
2. **Video tạo đệm bảo vệ nhưng không xóa vết:** Có >= 10 video giúp nick chịu được 1 vài lượt follow mồi (warm-up) thay vì đứt ngay lập tức, nhưng muốn phục hồi hoàn toàn bắt buộc cần tài khoản tuổi cao (> 100 ngày) và tương tác tự nhiên organic sâu.
