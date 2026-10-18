# Phân Định Yếu Tố Trust Tài Khoản & Cơ Chế Chuyển Tiếp Dưỡng Follow Tự Nhiên

## 1. Bản Chất Kỹ Thuật: Vanity Metrics (Like/Follower) vs Behavioral Trust (Age/Video)

### A. Ngộ nhận về Like và Follower
- **Giả thuyết sai lầm:** Cho rằng nick có video nhiều view, nhiều tim (1.000 – 5.000 tim) hoặc nhiều follower thì trust cao hơn và khi đi cày follow sẽ ít bị nhả / chịu tải được nhiều hơn.
- **Thực tế kiểm chứng từ 415 tài khoản farm Taadaa:**
  - Tương quan giữa Like (Heart) với việc nick có bị nhả follow hay không là **$\rho = 0.0048$ (gần như bằng 0 tuyệt đối)**.
  - Phân tích hồi quy chuẩn hóa ($\beta$ weights):
    $$\text{Sức chịu tải Follow} = \mathbf{0.3904} \times \text{Tuổi} + \mathbf{0.3654} \times \text{Video} + 0.0791 \times \text{Follower} + 0.0572 \times \text{Like}$$
  - Ngày tuổi và Số video chiếm **>85%** sức mạnh giải thích; Like và Follower đóng góp **<10%**.
  - Minh chứng thực tế: `@tuantuannguyen56` (4.931 tim, 45 ngày tuổi, 8 video) dính `fail_streak = 4` và bị khóa Cooldown; `@huy010822` (1.143 tim, 552 follower, 51 ngày tuổi) follow được 0 lượt và dính `fail_streak = 4`. Trong khi các nick $> 220$ ngày, $> 25$ video dù ít tim hơn vẫn cày $230 - 250$ follow an toàn.

### B. Nguyên nhân kiến trúc từ TikTok Backend
1. **Phân tách 2 pipeline độc lập:**
   - **Inbound Content Engine (FYP RecSys):** Đo view, completion rate, tim, share để quyết định phân phối video cho người khác xem.
   - **Outbound Risk Control Engine (Anti-Spam / Anti-Sybil):** Đo velocity (tốc độ bấm), dwell time, thói quen phiên, và lịch sử thiết bị (Device-Account Affinity / Behavioral Aging) để chống bot. Hai pipeline này hoàn toàn độc lập; Anti-Spam không đọc biến tim/view để nới lỏng rate-limit.
2. **Cơ chế chống Account Hijacking & Mua Nick:**
   - TikTok cố tình không ưu ái Outbound cho nick nhiều tim để chặn đứng thị trường mua nick viral / reup cắn đề xuất về làm bot spam follow. Kể cả nick triệu view nếu bấm follow dồn dập vẫn bị Silent Drop như thường.

---

## 2. Giai Đoạn Chuyển Tiếp 45 – 59 Ngày: Chống "Sốc Nhiệt" (Cold-to-Hot Spike)

### A. Tử huyệt của lứa 45 – 59 ngày khi đưa vào Runner
- Dữ liệu farm cho thấy lứa 45 – 59 ngày (TB 12.8 video) khi đưa vào `run_follow.py` có tỷ lệ **Cooldown lên tới 91.9%**, sản lượng chỉ đạt 2.2 follow/nick trước khi bị trảm.
- Nguyên nhân: Cấp hạn mức runner thông thường (4 – 6 lượt/ca) lên nick nguội sẽ kích hoạt bộ lọc **Velocity Spike**, dẫn đến Silent Drop và Account-Level Action Restriction.

### B. Nguy cơ của việc "Ép chờ đủ 60 ngày mới follow"
- Trên 124 nick lứa 45–59 ngày của farm, có tới **39.5% nick có Following = 0** (trung vị Following chỉ là 1 người).
- Nếu giữ trắng Following đến tận ngày thứ 60 rồi đùng một cái cho vào runner bấm liên tiếp 6–8 lượt, thuật toán Anti-Bot sẽ gắn cờ vì hành vi biến đổi đột ngột từ 0 lên đỉnh (Cold-to-Hot Spike).

### C. Quy tắc phân định rạch ròi: Cày Sản Lượng vs Dưỡng Trust
1. **Lứa 45 – 59 ngày ($\ge 10$ video): 👉 CẤM đưa vào Runner cày follow.**
   - Không chạy `run_follow.py`.
   - **Tích hợp vào Feed Session (`multi_machine_feed_session.py`):** Trong lúc lướt For You giải trí hàng ngày, kẹp xác suất tự nhiên: mỗi phiên lướt nếu gặp video phù hợp thì thả tim và **bấm follow đúng 1 creator đó trên Feed (tối đa 1 follow/ngày)**.
   - Mục đích: Không phải cày KPI sản lượng mà để **nuôi trust, hoàn thiện profile (Following > 0)** và tập dượt thói quen outbound tự nhiên.
2. **Lứa $\ge 60$ ngày ($\ge 15$ video): 👉 MỚI CHÍNH THỨC VÀO RUNNER CÀY FOLLOW.**
   - Đã có sẵn $10 - 15$ following tự nhiên và độ ấm tài khoản dày dặn.
   - Cấp quota theo bậc: **3 – 5 follow/ca** $\rightarrow$ Dò trần lên **6 – 8 follow/ca** $\rightarrow$ Veteran Core **Sweet Spot 9 – 12 follow/ngày**.

---

## 3. Phân Định Cầu Dao IP 48h: Nick Yếu vs Nick Khỏe

- **Khi Nick Yếu / Chưa Tốt Nghiệp (`was_graduated is False`) bị nhả:**
  - Bản chất là **Account-Level Action Restriction** (khóa riêng ở cấp nick do tài khoản nguội), dải proxy IP hoàn toàn không bị ảnh hưởng.
  - **KỶ LUẬT BẮT BUỘC:** CẤM TUYỆT ĐỐI ngắt Cầu Dao IP 48h. Chỉ phạt Cooldown cục bộ tài khoản đó, giữ nguyên IP để các nick khác cùng proxy và các ca chạy khác tiếp tục vận hành.
- **Khi Nick Khỏe / Nòng Cốt (`was_graduated is True`) bị nhả:**
  - Nick đã có lịch sử hàng trăm follow an toàn mà bị nhả ở lượt đầu tiên $\rightarrow$ 99% do **Dải Proxy IP bị TikTok quét diện rộng** hoặc lỗi gateway.
  - **KỶ LUẬT BẮT BUỘC:** Lập tức kích hoạt Cầu Dao IP 48h (`trip_ip_breaker`), khóa tạm thời quyền follow trên proxy đó để bảo vệ toàn bộ các nick/máy khác dùng chung dải mạng.
