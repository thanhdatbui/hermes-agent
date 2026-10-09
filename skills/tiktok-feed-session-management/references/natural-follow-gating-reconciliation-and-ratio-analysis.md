# Kiến Trúc Gating Follow Tự Nhiên, Đối Soát Web Post-Session & Phân Tích Lệch Tỷ Lệ (2026-10-04)

## 1. Gating Follow Tự Nhiên & Ngày Dưỡng Sinh (Organic Rest Invariant)
- **Cơ chế khóa trong `multi_machine_feed_session.py` (dòng 4871–4873):**
  ```python
  is_under_age = age_days_int is not None and age_days_int < 21
  if is_organic or video_count < 6 or is_under_age or os.environ.get("TAADAA_REST_DAY_NO_FOLLOW") == "1":
      child_config["_follow_rate"] = {"for_you": 0, "following": 0, "friends": 0}
  ```
  - Khi rơi vào ngày Dưỡng Sinh (`is_organic == True`), máy **BỊ KHÓA CỨNG 100% FOLLOW TỰ NHIÊN** (`_follow_rate = 0`).
  - Máy dưỡng sinh chỉ lướt xem video thuần (Pure Feed), tuyệt đối không bấm nút Follow trên bất kỳ video nào.
  - Bất kỳ lượt Follow tự nhiên nào xuất hiện trên báo cáo phiên (ví dụ 27 lượt ở Ca 1) **CHỈ ĐƯỢC PHÉP ĐẾN TỪ CÁC MÁY CÀY** (`is_organic == False`, `age >= 21`, `video >= 6`).

## 2. Cơ Chế Đối Soát Web Cho Follow Tự Nhiên (Post-Session Scraping)
- **Nghi vấn vận hành:** *"Máy dưỡng sinh không cào trước phiên thì làm sao biết follow tự nhiên có cắn thật vào Web không?"*
- **Sự thật kiến trúc:**
  1. Máy dưỡng sinh **không phát sinh follow tự nhiên**, nên không có chuyện follow tự nhiên bị trôi trên máy dưỡng sinh mà không được cào.
  2. Trong `feed_session_watchdog.py` (`reconcile_cluster_following`), danh sách cào Web sau phiên (`target_machines`) được xây dựng từ:
     ```python
     natural_targets = {str(m): ... for m, data in all_machines.items() if data.get("natural_follows") > 0}
     target_machines = set(fl_success) | set(natural_targets)
     ```
  3. Bất kỳ máy nào có `natural_cnt > 0` đều được **tự động gom vào danh sách cào Web TikTok (`tiktok_account_tracker.py`) sau phiên**.
  4. Nhờ vậy, toàn bộ số lượt follow tự nhiên đều được đối soát độc lập với số liệu tăng thật trên Web TikTok (ví dụ M62 tự nhiên 1 -> Web tăng +1, M71 tự nhiên 2 -> Web tăng +1).

## 3. Phân Tích Lệch Tỷ Lệ: Thiết Kế ~3-5% vs Thực Tế Báo Cáo ~35%
- **Theo thiết kế gốc:**
  - Tỷ lệ follow tự nhiên khi lướt feed chỉ ~2-5% trên For You (khoảng 0–1 follow/máy/phiên).
  - Tỷ lệ follow chéo nick già là 10–20 follow/máy/phiên.
  - Tỷ lệ kỳ vọng: $\frac{\text{Natural Follow}}{\text{Cross Follow}} \approx \frac{25 - 35}{800 - 1000} \approx \mathbf{3\% - 5\%}$.
- **Tại sao thực tế có ca (như Ca 1 ngày 03/10) hiển thị tỷ lệ lên tới ~35.5% (27 tự nhiên / 76 chéo)?**
  - **Do co cụm mẫu số follow chéo (Denominator Shrinkage):**
    - Follow tự nhiên diễn ra ở pha lướt feed trước đó trên toàn bộ ~35 máy cày (sinh ra 27 lượt).
    - Đến pha Follow chéo (chạy sau), TikTok siết nhả diện rộng khiến 18 máy bị nhả dừng phiên ngay từ đầu, 36 máy nghỉ dưỡng sinh, 14 máy kẹt cooldown cũ.
    - Toàn bộ 76 lượt follow chéo chỉ do **đúng 7 máy hoàn tất** gánh.
  - $\rightarrow$ Lấy 27 follow tự nhiên của 35 máy chia cho 76 follow chéo của 7 máy sẽ ra 35.5%.
  - **Quy tắc điều phối:** Không được ngộ nhận đây là do script thả lỏng follow tự nhiên, mà bản chất là do sản lượng follow chéo bị bóp nghẹt bởi cơ chế an toàn ngắt phiên chống nhả.

## 4. Kỷ Luật Số Liệu Lịch Sử 1 Tháng Trước
- **CẤM trích dẫn số Following tích lũy toàn đời (Lifetime Cumulative):**
  - Con số `250 – 380 following` trên nick già là tổng từ lúc lập nick (tháng 2–7/2026) đến nay, không phải số ăn được riêng trong 1 tháng gần nhất.
  - Trước ngày 02/10/2026, log script cũ có dương tính giả do Optimistic UI và lỗi nhãn thống kê `id/t_q` (Case UI-82).
  - Phân tích hiệu suất tăng trưởng follow chéo và tỷ lệ nhả follow BẮT BUỘC chỉ sử dụng dữ liệu sạch được đối soát 2 pha từ ngày **02/10/2026 trở đi**.
