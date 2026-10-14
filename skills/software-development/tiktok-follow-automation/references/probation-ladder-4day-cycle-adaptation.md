# Thích Ứng Bậc Thang Thử Thách (Graduated Probation) Với Chu Kỳ Xoay Tua 4 Ngày

## 1. Mâu thuẫn giữa Probation cũ (4 ca sạch) vs Chu kỳ 4 ngày (Burst & Hibernation)

### A. Độ trễ "ngâm chân" khi giữ nguyên 4 ca sạch
- Ở workflow cũ (chạy dồn dập hàng ngày hoặc cách nhật): 4 ca sạch mất khoảng 4–8 ngày ngoài đời thực để một nick hoàn thành Hồi phục 1 & 2 rồi tốt nghiệp lên Khỏe.
- Trong **Chu kỳ 4 ngày (Burst & Hibernation Cadence)**:
  - Mỗi tài khoản `(máy, row)` chỉ lên giàn follow **đúng 1 lần trong cả chu kỳ 4 ngày** (các ngày còn lại là ca của row khác, ngày dưỡng sinh hoặc ngày nghỉ toàn farm).
  - Nếu vẫn yêu cầu `clean_days >= 2` (Hồi phục 1) và `clean_days >= 4` (Hồi phục 2):
    * Chu kỳ 1 (Ngày 1): Hồi phục 1 (1–2 fl) -> clean=1.
    * Chu kỳ 2 (Ngày 5): Hồi phục 1 (1–2 fl) -> clean=2 (lên Hồi phục 2).
    * Chu kỳ 3 (Ngày 9): Hồi phục 2 (5–8 fl) -> clean=3.
    * Chu kỳ 4 (Ngày 13): Hồi phục 2 (5–8 fl) -> clean=4 (tốt nghiệp).
    * Chu kỳ 5 (Ngày 17): Mới chính thức chạy mức Khỏe (10–15 fl).
  - **Hậu quả:** Mất **17 ngày (gần 3 tuần)** chỉ để tốt nghiệp, trong cả 17 ngày gom vỏn vẹn ~15 follow (~1 follow/ngày), làm chậm nghiêm trọng tốc độ phát triển dàn nick.

### B. Rủi ro khi bỏ hẳn Hồi phục để nhảy thẳng Full Quota
- **Bẫy đột biến hành vi (Action Spike):** Nick vừa ra tù vẫn nằm trong danh sách giám sát ngầm của TikTok server. Nếu cấp ngay full quota (10–15 fl/phiên) sau khi mãn hạn, backend TikTok phát hiện đột biến sẽ kích hoạt án phạt tiếp theo với streak cao hơn (Streak 2: 5 ngày, Streak 3: 7 ngày, Streak 4+: 15 ngày).
- **Nguy cơ giật Cầu Dao IP MikroTik (Tier-Aware Breaker):** Trên farm Taadaa, chỉ khi nick Khỏe (`was_graduated == True`) bị nhả mới ngắt proxy MikroTik 48h. Nếu cho nick chưa qua thử thách lên Khỏe bừa bãi, tỷ lệ nhả sẽ làm giật cầu dao IP liên tục, kéo theo máy cùng dải IP bị tê liệt.

---

## 2. Quy Chuẩn Rút Gọn: 1 Phiên Sạch / 1 Nấc Thang (Fast-Track Adaptation)

Nhờ chu kỳ 4 ngày đã tạo ra **khoảng nghỉ đệm tự nhiên 72–96h** giữa 2 lần follow của cùng một nick (hành vi ngủ đông tự nhiên làm suy giảm cờ nghi vấn spam ở server TikTok), ta áp dụng quy tắc rút gọn:

| Nấc thang | Quota đề xuất | Thời gian thử thách | Điều kiện thăng hạng |
| :--- | :--- | :--- | :--- |
| **Hồi phục 1** *(Tân binh / Mới ra tù)* | **2 – 4 follows** / phiên | **Đúng 1 phiên duy nhất** (1 chu kỳ) | Chạy sạch, không bị rollback -> Thăng lên Hồi phục 2 ở chu kỳ kế tiếp. |
| **Hồi phục 2** *(Tăng tải an toàn)* | **6 – 8 follows** / phiên | **Đúng 1 phiên duy nhất** (1 chu kỳ) | Chạy sạch -> Tốt nghiệp lên **Khỏe** (Full Quota). |
| **Khỏe / Nòng cốt** | **10 – 15 follows** / phiên | Duy trì theo chu kỳ 4 ngày | Nếu bị nhả -> Phạt Cooldown theo streak và quay lại Hồi phục 1. |

- **Thời gian tốt nghiệp:** Rút ngắn từ **17 ngày xuống còn 8 ngày** (chỉ sau 2 chu kỳ chạy sạch).
- **Bảo toàn Canary Gate:** Phiên đầu (2–4 fl) đóng vai trò là probe dò đường an toàn: nếu nick chưa sạch án thì phanh ngay, chỉ phạt cá nhân account, không làm giật Cầu dao IP farm.
