# Dynamic Healing Row Selection & Anti-Consecutive Governance

## 1. Bối cảnh & Tử huyệt của Cơ chế Dưỡng Sinh Tĩnh (Static Heuristic Trap)
Trước đây, trong chu kỳ 4 ngày (96h), các ca Dưỡng sinh / Xả tải (Ca 3 Ngày 3 và cả 3 Ca Ngày 4) được gán cứng theo quy tắc if-else:
- Ca 3 Ngày 3: Luân phiên Row 3 và Row 4 (`healing_row = 3 if cycle_idx % 2 == 0 else 4`).
- Ngày 4 (Rest Day): Sáng Row 3, Trưa Row 4, Tối Row 5/6.

### 2 Lỗ hổng nghiêm trọng phát hiện thực tế:
1. **Hiện tượng Kẹp Ca (Back-to-back Run):**
   - Tối Ngày 3 (18h & 20h) chạy Row 3 dưỡng sinh.
   - Sáng Ngày 4 (06h & 08h) lại chạy tiếp Row 3! Khoảng cách giữa 2 ca chỉ 10 tiếng (từ 20h tối đến 6h sáng).
   - Đến trưa Ngày 5 (12h & 14h), Row 3 lại vào lịch cày chính. Một dàn nick bị lôi lên máy 3 lần trong vòng 48h, mất nhịp sinh học tự nhiên.
2. **Mù thông tin thực địa (Blind to Fleet Damage):**
   - Các Row 1, 2, 7, 8 bị LOẠI HOÀN TOÀN khỏi danh sách dưỡng sinh tĩnh.
   - Thực tế: Row 2 vừa cày hôm qua bị dính nhả follow tới **57.7%** (57/78 máy), Row 4 dính nhả **77.9%** (60/77 máy). Nhưng Row 2 không bao giờ được cấp slot đi dưỡng sinh để xả cờ phạt, mà phải ôm cờ chờ đến vòng cày tiếp theo. Ngược lại, Row 3 đang khỏe (chỉ 17.6% cooldown) lại bị đè ra chạy 2 ca liên tiếp.

---

## 2. Kiến Trúc Lựa Chọn Row Dưỡng Sinh Động (`healing_selector.py`)

Module điều phối: `D:/Taadaa/tools/healing_selector.py` được tích hợp vào `tiktok_runner.py` (`_determine_row()`).

### 2.1. Bốn Quy Tắc Điều Phối Bất Biến (Governance Invariants)
1. **Session Pairing Rule (Ghép cặp 2 Phiên cùng Ca):**
   - Phiên 2 (08h, 14h, 20h) **bắt buộc bốc đúng Row** của Phiên 1 (06h, 12h, 18h) trong cùng ca (đọc từ `runner_simple_state.json` với `expected_s1_window`).
   - Đảm bảo 1 dàn nick hoàn tất trọn vẹn 2 phiên (1 ca nuôi) trước khi chuyển ca.
2. **Anti-Consecutive Boundary Rule (Chống Kẹp Ca):**
   - Tại Phiên 1 của ca mới: **Bắt buộc loại trừ `last_row`** của ca liền kề trước đó.
   - Tuyệt đối không bao giờ cho 1 row chạy 2 ca liên tiếp qua ranh giới ca.
3. **Rest Day Multi-Ca Uniqueness (3 Ca Ngày Nghỉ 3 Row Khác Nhau):**
   - Vào Ngày 4 (Rest Day toàn farm gồm 3 ca): Mỗi ca dưỡng sinh loại trừ tất cả các row đã được chạy trước đó trong ngày (quét từ `runtime/kibe/live/YYYY-MM-DD/row-*`).
   - 3 ca trong ngày nghỉ sẽ giải cứu 3 Row bị tổn thương nặng nhất khác nhau.
4. **Data-Driven Scoring (Chấm Điểm Ưu Tiên Theo Tổn Thương Thực Tế):**
   - Điểm số cho từng candidate row $R \in \{1..8\} \setminus \{\text{excluded}\}$:
     $$\text{Score}(R) = 100 \times P_{\text{active\_cooldown}} + 20 \times P_{\text{young\_accounts}}$$
   - **$P_{\text{active\_cooldown}}$:** Tỷ lệ tài khoản trong Row đang có `cooldown_until_at > now`, hoặc `cooldown_until_date >= today`, hoặc `follow_failed = True` còn trong khung phạt `fail_streak` (3-7 ngày). Quét từ `D:/Taadaa/tiktok-follow/runs/state/follow_state_*_row_R.json`.
   - **$P_{\text{young\_accounts}}$:** Tỷ lệ tài khoản < 10 video từ SQLite `farm_account_info` + `snapshots`.

---

## 3. Hiệu Năng & Cache 60s Chống Nghẽn Đĩa
- Quét 413 file JSON state trong `runs/state` và SQLite mất ~1.5s - 2.0s nếu đọc chay.
- **Giải pháp:** Áp dụng bộ đệm in-memory 60s (`_CACHE_FAIL_RATES` và `_CACHE_YOUNG_RATES` với timestamp kiểm tra).
- **Kết quả:**
  - Lần gọi đầu tiên: ~1.7s nạp cache.
  - Các lần gọi tiếp theo trong vòng 60s: < 5ms ($O(1)$).
  - Vòng lặp kiểm thử 48 ngày (96 ca) chạy trong 2.45s thay vì timeout > 30s.
  - Vận hành production: Cron chạy 15 phút/lần nên mỗi tick luôn có fresh state.

---

## 4. Fallback An Toàn (Fail-Safe Priority Ladder)
Nếu xảy ra lỗi đọc file state hoặc SQLite bận/lock:
Hệ thống tự động bắt ngoại lệ và trả về fallback:
`fallbacks = [2, 4, 1, 3, 5, 6, 7, 8]` (ưu tiên theo mức độ nhạy cảm tổn thương thông thường, vẫn áp dụng luật loại trừ `candidates`). Không bao giờ làm crash cron.
