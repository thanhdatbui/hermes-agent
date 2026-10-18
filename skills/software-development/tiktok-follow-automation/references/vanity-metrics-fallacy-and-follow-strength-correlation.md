# Vanity Metrics Fallacy & Phân Tích Tương Quan Độ Mạnh Follow Thực Tế (Empirical Study N=415)

## 1. Bối Cảnh & Câu Hỏi Vận Hành
- **Giả thuyết đặt ra:** Liệu tài khoản có nhiều Lượt Thích (Like / Heart) và Người Theo Dõi (Follower) thì khi đi follow có "khỏe" hơn không? Có ít bị TikTok nhả follow (Action Restriction) hay chịu tải được quota cao hơn không?
- **Đối tượng nghiên cứu:** $N = 415$ tài khoản TikTok thực tế đang chạy follow trên toàn bộ cụm farm Taadaa (đối soát chéo giữa `follow_state_*_row_*.json`, $102.873$ snapshot profile trong SQLite `snapshots`, và workbook an toàn `taikhoan_run_safe_combined.xlsx`).

---

## 2. Kết Quả Định Lượng Thực Nghiệm

### A. Ma trận Hệ số Tương quan
| Biến Đầu Vào | Tuyến Tính Pearson ($r$) với Tổng Follow | Thứ Hạng Spearman ($\rho$) với Tổng Follow | Tương Quan Rủi Ro Nhả (`has_ever_failed`) | Mức Phạt Lũy Tiến (`fail_streak`) |
| :--- | :---: | :---: | :---: | :---: |
| **Ngày Tuổi (Age Days)** | **0.7267** | **0.6750** | 0.0134 | 0.2195 |
| **Số Video (Video Count)** | **0.7252** | **0.6235** | 0.0847 | 0.3183 |
| **Follower** | 0.5199 | 0.6569 | 0.0662 | 0.2874 |
| **Lượt Thích (Heart/Like)** | **0.2373** | **0.3330** | **0.0048** *(Bằng 0)* | 0.1907 |

### B. Trọng số Hồi quy Chuẩn hóa (Standardized Beta Coefficients)
Mô hình hồi quy đa biến dự đoán sản lượng follow an toàn tích lũy:
$$\text{Follow Capacity} = \mathbf{0.3904} \times \text{Age} + \mathbf{0.3654} \times \text{Video} + 0.0791 \times \text{Follower} + 0.0572 \times \text{Like}$$

- **Ngày tuổi ($\beta = 0.3904$)** và **Số video ($\beta = 0.3654$)** chiếm tới **>85%** sức mạnh giải thích.
- **Follower ($\beta = 0.0791$)** và **Like ($\beta = 0.0572$)** chỉ đóng góp dưới **10%** giá trị độc lập.

---

## 3. Bản Chất Kỹ Thuật & Cạm Bẫy Ngộ Nhận (Vanity Fallacy)

### 1. Ảo tưởng về Lượt Like (Heart Fallacy):
- Hệ số tương quan giữa Like và nguy cơ bị nhả follow là $\rho = 0.0048$ (gần như bằng 0).
- Nick có hàng trăm Like nhưng non ngày tuổi (< 60 ngày) khi đi follow vẫn có tỷ lệ bị Cooldown/nhả follow lên tới **72.6%** (ngang ngửa hoặc cao hơn cả nick ít like).
- **Lý do:** Lượt thích là chỉ số Inbound Content Engagement (người khác thích video của nick), TikTok hoàn toàn **không** dùng chỉ số này để cấp quota Outbound Graph Action (tần suất đi kết nối / follow tài khoản khác).

### 2. Tương quan giả & Nhân quả đảo chiều của Follower (Follower Confounding):
- Follower tương quan rất chặt với Ngày tuổi ($0.784$) và Số video ($0.754$). Nick già đăng nhiều video tự khắc tích lũy follower tự nhiên.
- **Nhân quả đảo chiều (Reverse Causality):** Khi nick già được cấp trần cao ($15 - 30$ lượt/ngày) và tích lũy $100 - 200$ lượt follow thành công, một tỷ lệ tự nhiên sẽ follow lại (Reciprocal Follow-back). Tức là **"Cày được nhiều follow $\rightarrow$ sinh ra Follower"**, chứ không phải *"Có sẵn Follower $\rightarrow$ giúp nick cày follow khỏe hơn"*.

---

## 4. Quy Tắc Vận Hành Chuẩn Hóa
1. **Tuyệt đối KHÔNG đưa Like / Follower vào bộ lọc điều phối:**
   - CẤM tốn chi phí buff like, mua tim hoặc cày follower chéo trước khi đưa nick vào follow pool.
   - Không sửa đổi hàm `determine_cohort` để dựa vào Like hay Follower.
2. **Kiên định với Dual Gate & Stratified Cohorts hiện tại:**
   - Hệ thống tiếp tục giữ vững 2 chốt chặn sinh tử đã được thực nghiệm chứng minh:
     * **Điều kiện tối thiểu (Dual Gate):** $\text{Age} \ge 30\text{d} \;\mathbf{AND}\; \text{Video} \ge 10$.
     * **Phân tầng Cohort:**
       - Rookie: $\text{Age} < 60\text{d} \;\mathbf{OR}\; \text{Video} < 15 \;\mathbf{OR}\; \text{Following} < 30 \rightarrow$ Khóa cứng trần 16.
       - Veteran: $\text{Age} > 180\text{d} \;\mathbf{AND}\; \text{Video} > 25 \;\mathbf{AND}\; \text{Following} > 100 \rightarrow$ Dò trần 30.
