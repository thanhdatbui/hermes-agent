# Probation Follow Dynamic Budgeting, Velocity Lockdown & Operational Invariants

## 1. Trần Follow Tối Đa Cựu Binh (Core Cap = 40)
- Mốc trần tuyệt đối của nhóm cựu binh (`veteran` - Following > 100, Video > 25, Tuổi > 180 ngày) đã được nâng từ **30 lên 40 follow/ngày** trong `_determine_budget_tier()`.
- Thuật toán Dò trần tăng động (`_roll_day()`): Mỗi chu kỳ chạy sạch không nhả và đạt mốc an toàn, trần kích hoạt được mở rộng $+2$:
  $$proven\_safe\_ceiling = \min(40, \max(curr\_proven, prev\_used))$$
  $$active\_ceiling = \min(40, \max(0, proven\_safe\_ceiling + 2))$$
- Cơ chế bảo hiểm gãy: Lùi 4 nấc nhưng khóa sàn không dưới 15:
  $$proven\_safe\_ceiling = \min(40, \max(0, \max(base\_max, curr\_proven - 4)))$$

## 2. Khóa Cứng 1 Phiên Cho Nick Hồi Phục (Probation Single-Session Lock)
- **Tử huyệt chia 2 phiên (P1 06:00 & P2 08:00):**
  - Quota của nick hồi phục (Tier 1: 3-5 follow, Tier 2: 5-6 follow) rất mỏng. Việc chia 5-6 follow thành 2 phiên cách nhau 2 tiếng tạo ra pattern bot lặp cữ (Pattern Spammer), kích hoạt Velocity Rate-Limit của TikTok ở Phiên 2.
  - Thực tế: M29, M38, M39 ở P1 chạy 6-7 follow sạch sẽ, sang P2 bấm thêm 1 follow vẫn nhận, nhưng do script cấp `budget = 2, 3` để vét trần ngày, nick bấm người thứ 2 thì bị chặn đứng (`FOLLOW_FAILED: TikTok không nhận follow`), xóa sạch `clean_days` và bị giam 3 ngày oan.
- **Quy tắc Single-Session Lock (`_probation_budget()`):**
  - Nếu nick đang trong diện probation (Tier 1 hoặc Tier 2) và `budget_used > 0` (đã chạy $\ge 1$ follow ở P1) ➔ P2 trả về `budget = 0`, ghi log `[PROBATION_SINGLE_SESSION_LOCK]` và bỏ qua (SKIP) hoàn toàn P2.
  - Dồn 100% ngân sách Tier 1 (3-4 follow) và Tier 2 (5-6 follow) chạy dứt điểm trong Phiên 1, sau đó cho nick nghỉ ngơi làm nguội. P2 chỉ đóng vai trò dự phòng khi P1 gặp sự cố mạng/offline (`budget_used == 0`).

## 3. Cơ Chế Tính Toán Động Cho Tier 1 & Tier 2 (Adaptive Probing)
Trong `_probation_budget()`:
1. **Phân hóa theo án tích (`fail_streak`):**
   - Nếu `fail_streak >= 3` (tái phạm nhiều lần, TikTok đang soi gắt): Tự động hạ trần thêm 1 follow (`cap = max(1, cap - 1)`) để nick chỉ chạy 1-2 lượt dò đường.
2. **Né mốc gãy lần trước (`last_failed_ceiling`):**
   - Luôn khóa trần chạy dưới mốc đã từng bị TikTok chặn:
     $$\text{cap} = \min(\text{cap}, \max(1, \text{last\_failed\_ceiling} - 1))$$
   - Khi dính fail ở bất kỳ nick nào, hàm `set_follow_failed()` lập tức ghi nhận `last_failed_ceiling = attempted if attempted is not None else (used + 1)`.
3. **Chống bẫy kẹt một chiều (Anti-Ratchet Trap):**
   - Mốc `last_failed_ceiling` chỉ là rào chắn tạm thời cho 1 cữ dò đường. Sau khi nick hoàn thành cữ chạy sạch và qua ngày `_roll_day()`, trường này được giải phóng để nick tự nhiên leo hạng lên Tier 2 và tốt nghiệp.

## 4. Kỷ Luật Cooldown Thực Tế & Nhận Định Tài Sản Farm
- **Bảng Cooldown theo Streak chuẩn:**
  * `Streak = 1`: Cooldown 3 ngày.
  * `Streak = 2`: Cooldown 5 ngày.
  * `Streak = 3`: Cooldown 7 ngày (1 tuần).
  * `Streak >= 4`: Cooldown 15 ngày (nửa tháng).
- **Thực tế lướt Feed trước Follow:**
  * 100% tài khoản trên farm trước khi chạy hook follow ĐỀU ĐÃ XEM FEED ĐẦY ĐỦ trong `multi_machine_feed_session.py` (xem video, dwell, like). Tuyệt đối không suy diễn ẩu là nick "chưa xem feed".
- **CẤM TUYỆT ĐỐI đề xuất đóng băng vĩnh viễn:**
  * Nick farm có tuổi, có video, vẫn LIVE là tài sản giá trị. Không bao giờ được phép đề xuất bỏ rơi hay "đóng băng vĩnh viễn" tài sản farm.
  * Với nick tái phạm nặng, giải pháp là ăn chắc mặc bền ở mức 1-2 follow dò đường, kiểm tra xem có bị nghẽn ở bước follow Anchor hay không, và bảo toàn chuỗi tương tác tự nhiên.
