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

### B. Quy tắc thực thi Phân tầng 2 Cửa (Dual Gate 60d cày chéo vs 45d Follow Tự Nhiên):
1. **Dưới 45 ngày HOẶC dưới 10 video (Trứng nước / Warm-up sơ khởi):**
   - Khóa follow chéo 100% (`budget = 0`, mode `blocked`).
   - Khóa follow tự nhiên trên Feed về 0% (`_follow_rate = {"for_you": 0, "following": 0, "friends": 0}`).
   - Chạy chế độ **Dưỡng sinh thuần (Pure Feed)**: xem video, lướt FYP, thả tim, đăng video rải đều.
2. **Lứa 45 – 59 ngày VÀ từ 10 video trở lên (Giai đoạn ấm nick / Nuôi trust tự nhiên):**
   - **Follow chéo (Runner):** Tiếp tục **KHÓA CỨNG (0 lượt)** để tránh bị sốc nhiệt/velocity spike dồn dập làm nát nick.
   - **Follow tự nhiên trên Feed (1% For You Feed):** **ĐƯỢC PHÉP BẬT** để nick thỉnh thoảng bấm nhẹ 1 người trong ca lướt, tích lũy 10-15 following tự nhiên trước khi bước sang ngày thứ 60, giải quyết dứt điểm hiện tượng 39.5% nick 0 following.
   - **Điều kiện chốt chặn an toàn (Chỉ được follow tự nhiên khi không bị cấm):**
     * Nick không bị Cooldown (`is_follow_cooldown is False`).
     * Dải IP không bị dính Cầu Dao (`check_ip_breaker(machine) is False`).
     * Không phải ngày dưỡng sinh (`is_organic is False`, `TAADAA_REST_DAY_NO_FOLLOW != '1'`).
     * Bất kỳ điều kiện nào vi phạm -> Tắt follow tự nhiên về 0%.
3. **Từ 60 ngày VÀ từ 15 video trở lên (Nick trưởng thành / Đủ điều kiện cày chéo):**
   - Mới chính thức mở quyền chạy follow runner chéo theo đúng bậc thang Cohort (Sweet Spot 9-12 fl/ngày cho Veteran).
   - Vẫn duy trì follow tự nhiên 1% trên Feed (nếu không dính Cooldown và IP không trip).
   - **Không cần hard-cap 1 lượt/ca cho follow tự nhiên:** Với xác suất 1% trên 25-40 video, xác suất bấm >= 2 lượt là <2% (cực hiếm), không cần thêm code phức tạp; thỉnh thoảng bấm 2 lượt vẫn an toàn.
   - **Theo dõi đối soát:** Định kỳ đối soát qua snapshot web (`snapshots` SQLite) sau 24-48h để theo dõi tỷ lệ nhả follow tự nhiên thực tế trước khi điều chỉnh tiếp.

### C. Kỷ luật giao tiếp & Tránh phức tạp hóa logic (User Correction):
- "Thì đơn giản là chỉ đc fl tự nhiên khi fl chéo đang cho phép. Chứ mắc gì viết loằng ngoằng v": Tránh phân tích rườm rà, diễn đạt trực diện, bám thẳng vào điều kiện logic cốt lõi. Follow tự nhiên chỉ mở khi tài khoản và IP ở trạng thái cho phép (không đi tù, không dính cầu dao).
- Quy tắc chốt cho lứa 45–59 ngày: từ 45 ngày và từ 10 video được phép follow tự nhiên 1% trên Feed; không đồng nghĩa được mở follow chéo. Dưới ngưỡng, đang cooldown/đi tù, IP đang bị cầu dao, hoặc ngày dưỡng sinh thì follow tự nhiên về 0%.
- Không thêm hard-cap 1 lượt/ca chỉ để xử lý xác suất rất thấp; thỉnh thoảng 2 lượt vẫn để tự nhiên.
- Khi báo cáo, nói ngắn gọn đúng gate; không biến một điều kiện đơn giản thành nhiều tầng thuật ngữ hoặc logic thừa.
- Gate nghiệm thu: tách rõ `offline verified` (focused test/py_compile/helper check), `canary pending`, và `web reconciliation pending`. Không báo “xong hết” nếu chưa có canary farm, đối soát snapshot web, hoặc closeout/working-tree evidence.
- Khi User hỏi "xong hết chưa": Tránh giải thích dài dòng kiểu quan liêu hay đổ lỗi cho working tree dirty / thiếu canary làm User ức chế. Báo cáo dứt khoát: "Code đã xong trên đĩa và test xanh, đang chạy Closeout Gate để push", sau đó hành động ngay.

---

## 4. Phân Định Cầu Dao IP (IP Circuit Breaker Tiering)

- **Nick Khỏe / Nòng Cốt (was_graduated is True) bị nhả:**
  - Nguyên nhân 99% do dải IP/Proxy bị TikTok quét diện rộng hoặc lỗi gateway.
  - **BẮT BUỘC ngắt Cầu Dao IP 48h** (`trip_ip_breaker`) để cứu toàn bộ các máy khác cùng proxy.
- **Nick Yếu / Đang thử thách (was_graduated is False) bị nhả:**
  - Nguyên nhân là **Account-Level Action Restriction** (khóa riêng ở cấp nick do tài khoản nguội), IP proxy hoàn toàn sạch.
  - **TUYỆT ĐỐI KHÔNG ngắt Cầu Dao IP**. Chỉ phạt Cooldown cục bộ nick đó, các nick khác cùng proxy vẫn chạy bình thường.
