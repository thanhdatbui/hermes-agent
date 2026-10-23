# TikTok Cadence & Quy Hoạch Công Suất 8 Acc/Máy (Row 1 - Row 8)

Tài liệu tham chiếu chuẩn hóa kiến trúc điều phối nuôi acc, giới hạn thuật toán Follow TikTok và giải pháp quy hoạch khung giờ farm khi vận hành tối đa 8 tài khoản/máy trên hạ tầng Samsung S7.

---

## 1. Bản Chất Giới Hạn Follow của Thuật Toán TikTok

### 1.1. Cơ chế Rolling Quota (Không cộng dồn)
* TikTok tính quota hành vi (follow, like, share) theo **cửa sổ trượt (Rolling 24h) và theo phiên (session)**.
* **Không có cơ chế tích lũy:** Nếu 1 tài khoản nghỉ 2 ngày không chạy, ngày thứ 3 tài khoản đó **vẫn chỉ có hạn mức an toàn của 1 ngày**, hoàn toàn không thể "xả bù" gấp đôi.
* Việc dồn 35 follow vào 1 ngày sau 2 ngày nghỉ sẽ kích hoạt bộ lọc bất thường (Spam Velocity Filter), dẫn đến:
  1. **Shadow-follow (Ghost follow):** Nút Follow đổi trạng thái sang "Đang follow" trên UI máy thật, nhưng server TikTok âm thầm drop request (không tăng follower ở nick đích, reload hoặc check nick khác không thấy).
  2. **Trust score bị hạ:** Tài khoản bị gắn cờ bot/automation, giảm phân phối video khi đăng ở các phiên sau.

### 1.2. So sánh hiệu quả Follow Cadence
* **35 follow / 2 ngày một lần:** Dễ chạm trần rủi ro, tỷ lệ rụng (drop/unfollow) cao, tiến độ 1k follow thực tế bị chậm do follow ảo.
* **20 - 25 follow / mỗi ngày:** Tự nhiên, tỷ lệ giữ follow >90%, trust tài khoản tăng trưởng bền vững.
* **25 - 28 follow / cách ngày (chia 3 phiên: 8-10 follow/phiên):** Ngưỡng an toàn tối ưu nếu bắt buộc chạy cách ngày để chia tải thiết bị farm.

---

## 2. Phân Tích Điểm Nghẽn Thời Gian Khi Nuôi 4 Ca / Ngày (8 Acc/Máy)

### 2.1. Thời lượng thực tế của cấu trúc 1 Ca (3 Phiên)
Theo thiết kế runner `hermes_cron` (`python_runner/hermes_cron/blocks.py`):
* Mỗi ca gồm 3 Session (Phiên 1, Phiên 2, Phiên 3):
  * Session duration: ~35 - 40 phút feed/tương tác.
  * Pair gap giữa các session: `35 - 60 phút` (bắt buộc để giãn cách hành vi tự nhiên).
* **Tổng thời gian chiếm dụng của 1 Ca = ~4.5 đến 5.5 tiếng!**

Timeline 3 ca hiện tại (6 acc/máy: Chẵn 2,4,6; Lẻ 1,3,5):
* Ca 1 (Sáng): `06:00` $\rightarrow$ `~11:30`
* Ca 2 (Chiều): `12:30` $\rightarrow$ `~18:00`
* Ca 3 (Tối): `19:00` $\rightarrow$ `~23:30 / 00:00`
$\rightarrow$ Thiết bị đã hoạt động **13 - 14 tiếng/ngày**.

### 2.2. Ba rủi ro chết người nếu nhét Ca 4 vào khung đêm (00:00 - 05:30)
1. **Xung đột trực tiếp với chuỗi Cronjob đêm:**
   * `22:00 – 01:00`: `avatar-post-feed-watchdog` (up avatar cho row cuối ngày).
   * `01:00`: `night-chain-reg-pipeline` (Reg Gmail $\rightarrow$ Reg TikTok). Nếu Ca 4 đang lướt TikTok, device lock bị chiếm $\rightarrow$ batch Reg bị kẹt hoặc conflict app.
   * `04:00`: `end-of-day-clear-tiktok-cache` (dọn dẹp cache TikTok 80 máy).
2. **Độ bền phần cứng (Samsung Galaxy S7):**
   * Chạy 4 ca với cấu trúc 3 phiên = **18 - 19 tiếng/ngày màn hình sáng**.
   * Nhiệt độ máy tăng cao liên tục $\rightarrow$ phồng pin, đơ máy, uiautomator crash (`EXIT=137`, `uiautomator_null_root_node`), ADB transport lost hàng loạt.
3. **Dấu hiệu hành vi ban đêm:**
   * Acc hoạt động liên tục lúc 2h - 4h sáng hàng tuần rất dễ bị hệ thống chống gian lận của TikTok phân loại là thiết bị cày farm.

---

## 3. Quy Hoạch Chuẩn Hóa Chu Kỳ 4 Ngày (96h Parity, Bỏ Ca 0h Đêm)

Hệ thống đã chuẩn hóa sang **Chu kỳ cố định 4 ngày x 3 Ca x 2 Phiên / ngày** (áp dụng từ 11/10/2026, loại bỏ hoàn toàn ca đêm 00:00/01:30):

### 3.1. Cấu trúc 3 Ca x 2 Phiên / ngày:
* **Ca 1 (Sáng):** Phiên 1 lúc `06:00` (Feed only), Phiên 2 lúc `08:00` (Feed + Upload/Follow).
* **Ca 2 (Trưa):** Phiên 1 lúc `12:00` (Feed only), Phiên 2 lúc `14:00` (Feed + Upload/Follow).
* **Ca 3 (Tối):**  Phiên 1 lúc `18:00` (Feed only), Phiên 2 lúc `20:00` (Feed + Upload/Follow).
* **Dead Zone (21:30 - 05:59):** Đêm nghỉ hoàn toàn, bỏ ca 0h đêm. Dàn S7 làm mát và chạy `end-of-day-clear-tiktok-cache` (03:00 - 04:30).

### 3.2. Phân bổ Chu kỳ 4 ngày (Base date 11/10/2026, Parity 96h):
* **Day 0 (Ngày 1):** Ca 1 (Row 1) - Ca 2 (Row 3) - Ca 3 (Row 5).
* **Day 1 (Ngày 2):** Ca 1 (Row 2) - Ca 2 (Row 4) - Ca 3 (Row 6).
* **Day 2 (Ngày 3):** Ca 1 (Row 7) - Ca 2 (Row 8) - Ca 3 (Dưỡng sinh Row 3/4 pure feed).
* **Day 3 (Ngày 4):** Dưỡng sinh xả tải toàn farm (pure feed).

* **Lợi ích toàn diện:**
  * Mỗi Row quay lại đúng sau 96h (4 ngày x 24h, cùng slot giờ), triệt tiêu hoàn toàn hiện tượng lệch starve 120h.
  * Toàn bộ đêm từ **21:30 đến 05:59 sáng hoàn toàn giải phóng** cho thiết bị làm mát, bảo vệ pin và duy trì kết nối USB/ADB ổn định.
