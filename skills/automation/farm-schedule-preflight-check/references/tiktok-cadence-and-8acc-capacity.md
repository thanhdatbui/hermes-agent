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

## 3. Giải Pháp Kiến Trúc Quy Hoạch 8 Acc/Máy (Row 1 - Row 8)

Để đạt mục tiêu tối đa hóa công suất 8 acc/máy (Ngày lẻ: Row 1, 3, 5, 7; Ngày chẵn: Row 2, 4, 6, 8) mà không phá nát máy và không xung đột job đêm:

### Giải pháp Khuyên dùng: Tối ưu Rút gọn Phiên (2 Phiên / Ca)
* Thay vì chạy 3 phiên/ca (105p feed), rút xuống **2 phiên / ca** (mỗi phiên 30 - 35p).
* Tổng thời gian 1 ca rút từ ~5 tiếng xuống còn **~2 tiếng - 2.5 tiếng** (bao gồm 1 pair gap 45p).
* **Lịch trình 4 ca trong ngày:**
  * **Ca 1 (Row 1/2):** `06:00` – `08:30`
  * **Ca 2 (Row 3/4):** `10:00` – `12:30`
  * **Ca 3 (Row 5/6):** `14:30` – `17:00`
  * **Ca 4 (Row 7/8):** `18:30` – `21:00`
* **Lợi ích toàn diện:**
  * Toàn bộ khung giờ đêm từ **21:30 đến 05:30 sáng hoàn toàn giải phóng**.
  * Chạy mượt mà: Up Avatar (22:00), Reg Chuỗi đêm (01:00), Clear Cache (04:00).
  * Thiết bị có 8 tiếng nghỉ ngơi, nguội máy, duy trì tuổi thọ pin và ổn định ADB.
