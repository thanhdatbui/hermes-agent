# Tương Quan Chỉ Số Tài Khoản & Quy Chuẩn Dual Gate 60 Ngày / 15 Video

## 1. Kết Quả Định Lượng Thực Tế Toàn Farm (N = 415 tài khoản)

Đối soát chéo giữa `follow_state_*_row_*.json`, 102.873 lượt quét snapshot SQLite và `taikhoan_run_safe_combined.xlsx`:

### A. Ma trận Tương quan (Spearman Rank $\rho$ & Pearson $r$)
- **Lượt Thích (Heart / Like):**
  - Tương quan với Rủi ro bị nhả follow (`has_ever_failed`): $\rho = 0.0048$ (Gần bằng 0 tuyệt đối).
  - Tương quan tuyến tính với tổng follow: $r = 0.2373$ (Rất yếu).
  - Khi kiểm soát Ngày tuổi và Video: Tác động độc lập chuẩn hóa chỉ còn $\beta = 0.0572$ (<6%).
  - **Kết luận:** Lượt like/tim hoàn toàn KHÔNG CÓ TÁC DỤNG bảo vệ nick hay tăng sức chịu tải khi đi follow.
- **Người Theo Dõi (Follower):**
  - Tương quan với Ngày tuổi ($0.784$) và Video ($0.754$).
  - Tác động độc lập chuẩn hóa sau hồi quy đa biến: $\beta = 0.0791$ (<8%).
  - Follower tăng theo thời gian chủ yếu do follow chéo nội bộ và tích lũy tự nhiên; bản thân số follower cao không giúp nick thoát rate-limit khi bấm dồn dập.
- **Ngày Tuổi (Age Days) & Số Video (Video Count):**
  - Quyết định trên **85%** năng lực chịu tải: $\beta_{\text{age}} = 0.3904$, $\beta_{\text{video}} = 0.3654$.

---

## 2. Bản Chất Kiến Trúc TikTok: Inbound RecSys vs Outbound Risk Engine

1. **Phân tách 2 pipeline độc lập:**
   - **Inbound Content Engine (FYP):** Đánh giá View, Like, Retention để phân phối video cho người xem khác.
   - **Outbound Risk Control Engine (Anti-Spam):** Đánh giá Velocity (tốc độ bấm), Dwell Time, Session Cadence, Device-Account Affinity và Behavioral Aging để phát hiện bot/cào follow.
2. **Cơ chế chống Token Farming / Account Hijacking:**
   - TikTok cố tình không dùng View/Tim để cấp quota follow. Nếu nick triệu view được đi follow thả phanh, thị trường bot sẽ mua nick viral về biến thành máy spam.
   - Kể cả nick có 5.000 tim (như M56 `@tuantuannguyen56` 45 ngày 4.9k tim) hay nick 1.100 tim (`@huy010822` 51 ngày), nếu tuổi non và bấm follow dồn dập $\rightarrow$ Vẫn bị TikTok Silent Drop và tống Cooldown streak 4.

---

## 3. Chính Sách Dual Gate 60 Ngày / 15 Video (Quy Chuẩn Chốt Hạ)

### A. Tại sao loại bỏ phương án 45 ngày / 12 video?
- Thống kê nhóm 45–59 ngày ($N = 124$ nick): Tỷ lệ dính cấm Cooldown lên tới **91.9%**, sản lượng chỉ đạt $2.2$ follow/nick.
- Lứa 45 ngày vào cày follow sẽ dính lỗi "Velocity Spike trên tài khoản nguội", bấm phát thứ 2 là bị drop ngay.
- Farm hiện có sẵn **173 tài khoản $\ge 60$ ngày và $\ge 15$ video** (trong đó có 73 nick nòng cốt $\ge 180$ ngày), dư sức đáp ứng 150–200 follow sạch mỗi ngày mà không cần ép chín lứa 45 ngày.

### B. Quy tắc thực thi Dual Gate:
1. **Dưới 60 ngày HOẶC dưới 15 video:**
   - Khóa follow 100% (`budget = 0`, mode `blocked`).
   - Chạy chế độ **Dưỡng sinh thuần (Pure Feed)**: xem video, lướt FYP, thả tim, đăng video rải đều.
   - **CẤM bật follow tự nhiên trên Feed toàn farm:** Vì follow trên feed không có xác thực kép reload profile, dễ gây drop ngầm và tích lũy điểm phạt âm thầm.
2. **Từ 60 ngày VÀ từ 15 video trở lên:**
   - Mới chính thức mở quyền chạy follow runner.
   - Áp dụng bậc thang: Rookie/Probation (3–5 lượt) $\rightarrow$ Mid (6–8 lượt) $\rightarrow$ Veteran Sweet Spot (9–12 lượt/ngày).

---

## 4. Phân Định Cầu Dao IP (IP Circuit Breaker Tiering)

- **Nick Khỏe / Nòng Cốt (was_graduated is True) bị nhả:**
  - Nguyên nhân 99% do dải IP/Proxy bị TikTok quét diện rộng hoặc lỗi gateway.
  - **BẮT BUỘC ngắt Cầu Dao IP 48h** (`trip_ip_breaker`) để cứu toàn bộ các máy khác cùng proxy.
- **Nick Yếu / Đang thử thách (was_graduated is False) bị nhả:**
  - Nguyên nhân là **Account-Level Action Restriction** (khóa riêng ở cấp nick do tài khoản nguội), IP proxy hoàn toàn sạch.
  - **TUYỆT ĐỐI KHÔNG ngắt Cầu Dao IP**. Chỉ phạt Cooldown cục bộ nick đó, các nick khác cùng proxy vẫn chạy bình thường.
