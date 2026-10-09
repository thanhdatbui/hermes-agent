# Case UI-100: Khảo Sát Tỉ Lệ Tái Phát Nhả Follow Sau Ra Tù & Cơ Chế Follow Trust (07/10/2026)

## 1. Dữ Liệu Thực Nghiệm (411 State Files / 80 Máy)
Khảo sát toàn diện 411 state file (`runs/state/follow_state_*.json`) tại `D:/Taadaa/tiktok-follow`:
- **Tổng số tài khoản theo dõi:** 411 nick.
- **Nick chưa từng dính phạt (Streak = 0):** 22 nick (5.4%).
- **Nick mới dính phạt lần đầu (Streak = 1 - đang/vừa xong cữ 3 ngày):** 174 nick (42.3%).
- **Nick đã từng mãn hạn ra tù (Streak >= 2):** 215 nick (52.3%).

### Tỉ lệ hành vi thực tế sau khi ra tù (trên 215 nick):
1. **Cứ ra tù là dính nhả liền lập tức (0 follow được / fail ngay lượt đầu):**
   - **184 - 200 nick (~85.6% - 93.0%)**.
   - Streak bị đẩy lũy tiến: Streak 2 (phạt 5 ngày: 152 nick), Streak 3 (phạt 7 ngày: 42 nick), Streak >= 4 (phạt 15 ngày: 21 nick, cao nhất Streak 6).
2. **Ra tù follow được vài cái (1 - 5 cái) rồi dính lại ngay:**
   - **15 - 29 nick (~7.0% - 13.5%)**.
   - Thường chỉ ăn được vài lượt ở cữ warm-up phiên đầu (3-5 lượt), đến phiên sau hoặc ngay trong cữ đó thì TikTok server silent-drop.
3. **Ra tù phục hồi hoàn toàn (về Streak 0 và follow bình thường ổn định):**
   - **Đúng 2 nick trên 411 nick (~0.9%)**: Máy 1 Row 1 và Máy 52 Row 1. Cả 2 đều có >22 video và tuổi đời > 4 tháng.

---

## 2. Phân Tích Tương Quan: Row & Lượng Video

### Theo Row (Slot máy 1 - 8):
- **Row 1:** Trung bình 23.8 video/nick. Tỉ lệ chưa dính fail cao nhất (12/80 nick ~ 15%). Nhưng khi đã vào tù thì ra tù vẫn bị dính nhả liền tới **93.3%**.
- **Row 2:** Tỉ lệ nhích được vài cái sau ra tù cao nhất (16/54 nick ~ 29.6%) do lượng video vừa đủ (~12.5 video) để ăn nhẹ cữ warm-up trước khi bị nhả lại.
- **Row 5, 6, 7:** Dàn nick mới (~6.1 - 6.9 video). Một khi dính vào tù thì **100% ra tù là bị dính nhả liền ngay lượt đầu**.

### Theo Số Lượng Video:
- **Dưới 10 video (Chưa đạt Dual Gate):** 94.7% ra tù dính nhả liền lập tức; chỉ 5.3% theo dõi được vài cái.
- **10 - 19 video (Đạt chuẩn tối thiểu):** 82.5% ra tù dính nhả liền; 17.5% theo dõi được vài cái rồi dính lại.
- **>= 20 video (Dày video):** 91.3% ra tù dính nhả liền; 8.7% theo dõi được vài cái.

---

## 3. Bản Chất Kỹ Thuật & Bài Học Vận Hành

1. **Follow Trust != Feed Trust (Hai cờ hoàn toàn độc lập):**
   - TikTok lưu cờ spam follow ở cấp độ UID trên server (Account-level Action Block / Path B: app hiện "Đang theo dõi" nhưng server drop request, reload profile sẽ bật ngược lại "Follow").
   - Việc chỉ cho nick nghỉ (cooldown 3-15 ngày) và chỉ lướt feed **HOÀN TOÀN KHÔNG TỰ HỒI TRUST FOLLOW**. Vừa bấm follow lại là server quét dính ngay.

2. **Cạm Bẫy Follow Chéo Khép Kín (Closed-loop Cluster Hazard):**
   - Khi các nick trong cùng farm follow qua lại lẫn nhau hoặc bám vào cùng một cụm Anchor/Row nội bộ, mật độ edge quá dày đặc. Khi một số nick bị cắm cờ, toàn bộ cluster bị đưa vào diện giám sát. Nick ra tù follow tiếp nick trong cluster sẽ kích hoạt filter ngay lập tức.

3. **Nguyên Tắc Dưỡng Nick Ra Tù:**
   - Nick sau khi mãn hạn cooldown bắt buộc phải giữ giới hạn nghiêm ngặt (3-5 lượt/ngày).
   - Tuyệt đối không reset streak ngay trong ngày (chờ qua ngày hôm sau).
   - Với các nick có streak >= 4 (bị phạt 15 ngày), cần ưu tiên tăng cường Inbound Trust (đăng thêm video chất lượng, giãn cách tương tác) thay vì ép chạy follow tiếp tục.
