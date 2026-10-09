# Case 172: Chuyển Dịch Sang Phân Phối Mềm Liên Tục (Continuous Behavioral Rates) Cho Tương Tác Like & Comment Peek

## 1. Bối cảnh & Phản biện Kiến trúc từ GPT-5.6 Sol (Tier-1 Anti-Fraud)
- **Điểm mù cũ (Population Homogeneity):**
  - Mặc dù mỗi video có xúc xắc ngẫu nhiên, nhưng toàn bộ 160 máy trên farm đều nhận chung 1 mức like cố định cho tab For You (8% cứng) và Comment Peek (12% cứng).
  - Thuật toán học máy phân cụm (Clustering / Isolation Forest / Anomaly Detection) của ByteDance không cần bắt từng nick là bot, mà nó soi dấu hiệu "quần thể có entropy thấp": hàng trăm tài khoản có cùng vector hành vi với độ lệch chuẩn xấp xỉ 0.
  - Phản biện của Sol: Việc chia các nhóm archetype cứng (30% nhóm A, 50% nhóm B, 20% nhóm C) vẫn tạo ra 3 cụm robot mới được sinh ra từ cùng 1 luật toán học. Con người thật phân bố liên tục (continuous) và có nhiễu ngẫu nhiên mềm.

## 2. Giải pháp chuẩn (Case 172): Phân phối Động theo Cấp Phiên (Session-Level Continuous Rates)

### A. Like tab For You phân phối liên tục (5% - 12%):
- Trong `python_runner/flows/feed_swipe_smoke.py` (`_feed_like_rates()`):
  ```python
  if raw is None:
      # Phân phối mềm động (Dynamic Continuous Rates): For You (5-12%), Following (30-60%), Friends (50-80%)
      return {
          FEED_TYPE_FOR_YOU: random.randint(5, 12),
          FEED_TYPE_FOLLOWING: random.randint(30, 60),
          FEED_TYPE_FRIENDS: random.randint(50, 80),
      }
  ```
- Được tính toán 1 lần duy nhất lúc khởi tạo session (`like_rates = _feed_like_rates(ctx)`) và tái sử dụng nhất quán trong toàn bộ phiên.

### B. Comment Peek phân phối liên tục (8% - 16%):
- Khởi tạo giá trị `session_comment_peek_rate` 1 lần trước vòng lặp lướt feed:
  ```python
  # Session-level continuous comment peek rate (8% - 16%) per session
  session_comment_peek_rate = random.randint(8, 16) if is_feed_session else 12
  ```
- Truyền tham số `peek_rate_percent=session_comment_peek_rate` vào hàm `_maybe_peek_comments` tại mỗi nhịp Deep Inspect, đảm bảo tính nhất quán tâm lý người dùng trong phiên lướt.

### C. Giữ nguyên dải an toàn phần cứng (16 - 22 video):
- Không tăng số video lên 26 để tránh làm quá tải pin và nhiệt độ CPU Exynos 8890 trên dàn máy Galaxy S7 cũ, bảo toàn lịch trình chuyển ca của farm.

## 3. Thẩm định độc lập & Kiểm thử
- **GPT-5.6 Sol High Reasoning:** `VERDICT: APPROVED`.
- **Pytest:** `test_feed_swipe_smoke.py` (7/7 passed), `test_camera_dismissal_and_profile_nav.py` (15/15 passed).
- **Commit:** `13458ea` trên repo `tiktok-luot nuoi acc`.
