# Daily Follow Matrix & Trust Ceiling Analytics (Sweet Spot Quota)

## 1. Bối Cảnh & Vấn Đề Vận Hành

### Hiện tượng nhả follow đột ngột trên nick nòng cốt
- Các nick nòng cốt (tuổi đời > 200 ngày, > 20 video) sau khi tốt nghiệp lộ trình 3 nấc (`Graduated Probation Ladder`) thường được cấp Full Quota (10 – 20 follow/phiên, tức 20 – 30+ follow/ngày).
- Khi chạy quota cao, nick dễ bị TikTok server kích hoạt bộ đệm chống spam (Trust Ceiling) và nhả follow hàng loạt (Silent Drop).
- Ví dụ thực tế ngày 09/10/2026:
  - M39 (`@thanh.huyn4934`): Phiên 1 chạy 14 follow mượt, Phiên 2 chạy thêm 1 follow (tổng 15 follow/ngày) $\rightarrow$ lượt 16 bị TikTok ngắt và nhả follow.
  - M2 (`@thanh.h.dng00`): Cày 240 follow lịch sử, nhưng khi chạy ca sáng ăn 1 follow, sang lượt 2 bị nhả.
  - M1, M9, M14: Bị nhả ngay tại lượt đầu tiên do TikTok siết thuật toán trong ca.

### Tại sao cần Daily Follow Matrix theo từng nick?
- Thống kê tổng của toàn farm (Total Follows/day) chỉ phản ánh sản lượng chung, KHÔNG cho thấy trần chịu tải của từng nick.
- Bảng ma trận theo ngày (Daily Follow Matrix) và phân tích vùng an toàn (Trust Threshold Analytics) cho phép:
  1. Nhìn rõ lịch sử từng nick: trước khi bị nhả, nick đã chạy bao nhiêu follow/ngày?
  2. Xác định con số quota tối ưu ("Sweet Spot" - con số vàng) để tối đa hóa số follow giữ được mà không chạm trần rủi ro.

---

## 2. Kiến Trúc Dữ Liệu & Tối Ưu Hóa Truy Vấn O(1)

### Nguồn dữ liệu
1. **SQLite Database (`D:/Taadaa/data/tiktok_tracker.db`):**
   - Bảng `daily_account_actions` lưu `(target_date, may, username, internal_follows, updated_at)`.
   - Bảng `session_account_actions` lưu chi tiết theo từng ca chạy.
2. **State Files (`D:/Taadaa/tiktok-follow/runs/state/follow_state_{m}_row_{r}.json`):**
   - Lưu dict `followed: {username: iso_timestamp}` chi tiết đến từng giây.
   - Lưu `last_failed_date`, `fail_streak`, `last_budget_decision`.

### Kỷ luật chống lag Dashboard (:1905)
- **CẤM TUYỆT ĐỐI:** Quét động 411 state files JSON mỗi khi người dùng truy cập hoặc F5 Dashboard.
- **Giải pháp O(1):**
  - Truy vấn trực tiếp từ bảng `daily_account_actions` với window 14 ngày:
    ```sql
    SELECT target_date, may, username, SUM(internal_follows) as follows
    FROM daily_account_actions
    WHERE target_date >= date('now', '-14 days')
    GROUP BY target_date, may, username;
    ```
  - Pre-aggregate dữ liệu trạng thái nhả follow từ các file state theo chu kỳ hoặc lưu snapshot cache (`follow_metrics_cache`), bảo đảm thời gian phản hồi API `/api/follow-health` luôn `< 50ms`.

---

## 3. Thiết Kế Giao Diện Dashboard (Port 1905)

### A. Bảng Ma Trận Lịch Sử Ngày Chạy (Daily Matrix Heatmap)
- **Quy tắc hiển thị cốt lõi (User Correction Invariant):** Cột ngày BẮT BUỘC tính theo **các ngày/ca nick thực tế có chạy** có giãn cách (ví dụ: `09-27`, `09-29`, `09-30`, `10-01`, `10-02`, `10-03`, `10-04`, `10-05`, `10-06`, `10-07`, `10-08`, `10-09`), TUYỆT ĐỐI KHÔNG dùng ngày lịch cố định liên tục vô nghĩa vì mỗi nick chạy có chu kỳ nghỉ dưỡng và giãn cách ngày (rest 1/3, cooldown 3 ngày).
- **Bộ lọc mặc định (Default Filter Invariant):** Mặc định bảng ma trận BẮT BUỘC hiển thị **`Tất Cả` (Toàn bộ 410 nick)** thay vì chỉ hiển thị nhóm `Khỏe` (11 nick). Tuyệt đối không để mặc định nhóm `Khỏe` vì sẽ ẩn toàn bộ máy đang dính Cooldown, gây hiểu nhầm là ma trận chỉ có máy chưa bị nhả. Bổ sung cụm nút lọc nhanh: `Tất Cả (410)` | `Khỏe (11)` | `Cooldown (344)`.
- **Thứ tự sắp xếp mặc định theo độ khỏe (Health-Descending Sort Invariant):** Danh sách máy BẮT BUỘC sắp xếp mặc định theo **độ khỏe giảm dần (`health_score` descending)** thay vì theo số thứ tự máy tăng dần (`M1, M2...`):
  1. **Nhóm Khỏe / Nòng Cốt đứng đầu:** Sắp xếp theo `Tổng đã follow (total_followed)` hoặc `Max Safe` giảm dần (ví dụ `M28 R1` 214 fl, `M50 R1` 213 fl lên trên cùng; nick ít follow xuống dưới).
  2. **Tiếp theo là Nhóm Hồi Phục:** Sắp xếp theo số ngày sạch (`clean_days`) và follow tích lũy.
  3. **Cuối cùng là Nhóm Cooldown:** Sắp xếp từ án phạt nhẹ (`fail_streak = 1`) đến nặng (`streak 4+`), ưu tiên nick cày nhiều follow lên trước.
  4. **Tương tác sắp xếp trên đầu cột (Interactive Column Sort):** Cho phép bấm vào các tiêu đề cột (`Máy ↕`, `Nhóm ↕`, `Tổng ↕`, `TB/Ca ↕`, `Max Safe ↕`) để đảo chiều tăng/giảm mượt mà ngay trên điện thoại hoặc desktop.
- **Tối ưu hiển thị Mobile (Mobile Responsive Invariant):**
  - Cột `MÁY` cố định bên trái khi cuộn ngang: `position: sticky; left: 0; background: #0f172a; z-index: 1; border-right: 1px solid #334155;`.
  - Thanh cuộn cảm ứng mượt mà: `-webkit-overflow-scrolling: touch;`.
  - Giảm cỡ chữ (11px), cố định dòng (`white-space: nowrap`), tô nền đỏ nhạt (`rgba(239,68,68,0.04)`) cho các nick Cooldown để phân biệt ngay trên màn hình nhỏ.
- **Dòng:** Danh sách từng tài khoản (`M1 @username`, `M2 @username`...).
- **Quy chuẩn màu sắc trực quan:**
  - 🟢 **Xanh lá (Stable):** Ca follow an toàn không bị nhả (hiển thị số lượt, ví dụ `+5`, `+9`, `+14`, nền xanh trong suốt viền xanh).
  - 🔴 **Đỏ (Drop Spike):** Ca bị TikTok nhả follow (hiển thị `🛑 N`, nền đỏ viền đỏ cảnh báo).
  - ⚪ **Dấu gạch ngang `-` (Rest / Cooldown):** Ca nghỉ giãn cách hoặc đang thụ án Cooldown.
- **Các cột tổng hợp:** `Tổng` (tổng đã follow), `TB/Ca` (trung bình follow mỗi ca có chạy), `Max Safe` (lượt follow cao nhất trong 1 ca mà vẫn an toàn không bị nhả).

### B. Biểu đồ Vùng An Toàn (Trust Threshold Analytics)
Phân nhóm các ca chạy vào 4 giỏ hạn mức dựa trên đo lường lịch sử toàn farm:
- **1 – 4 follow/ngày:** Nhóm ca chạy thăm dò / sau nhả (~232 ca chạy, an toàn ~97.8%).
- **5 – 9 follow/ngày:** Nhóm cân bằng tối ưu (162 ca chạy lịch sử, **100.0%** an toàn tuyệt đối, 0 ca nhả).
- **10 – 14 follow/ngày:** Nhóm tiệm cận trần an toàn (126 ca chạy lịch sử, **100.0%** an toàn trước khi dính đợt quét).
- **15+ follow/ngày:** Vùng chạm trần rủi ro cao (chạm ngưỡng rate-limit/spike của TikTok; ví dụ M39 an toàn ở 14, lên 15 bị nhả ngay; M2 đẩy 28-30, M9 đẩy 32 bị TikTok siết cờ phạt ngầm).

---

## 4. Thuật Toán Tìm Con Số Vàng (Sweet Spot Quota Engine)

### Cơ sở định lượng từ dữ liệu lịch sử thực tế (Empirical Backing)
- Con số **9 – 12 follow/ca** cho nhóm Nòng Cốt không phải con số cảm tính hay lý thuyết suông, mà là **điểm rơi tối ưu (Sweet Spot)** từ thực nghiệm lịch sử:
  - Dưới 10 lượt: 100% an toàn nhưng sản lượng tăng chậm.
  - Từ 15 lượt trở lên: Rủi ro kích hoạt thuật toán rate-limit của TikTok tăng vọt.
  - Khoảng 9 – 12 lượt: Tối đa hóa sản lượng follow mà vẫn nằm trọn dưới ngưỡng trần rủi ro (an toàn > 98.4%).

### Công thức tính điểm tối ưu (`quota_score`)
Cho mỗi mức quota $Q \in [1, 20]$:
$$\text{Score}(Q) = (\text{Follows Giữ Được} \times 0.7) - (\text{Tỷ lệ Nhả} \times 100 \times 0.3)$$

### Quy tắc điều phối theo vòng đời tài khoản:
1. **Tân binh (Mới đủ Dual Gate age >= 30d, vid >= 10):**
   - Khởi động cố định: **3 – 5 follow/ngày** (Hồi phục 1).
2. **Nick sau mãn hạn Cooldown (Ra tù):**
   - Bắt buộc đi qua lộ trình 3 nấc: **3 – 5** (3 ngày sạch) $\rightarrow$ **7 – 9** (3 ngày sạch tiếp theo) $\rightarrow$ Tốt nghiệp.
3. **Nick Khỏe / Nòng cốt (Đã tốt nghiệp):**
   - Không thả nổi quota lên mức cực đại (20-30 lượt).
   - Khống chế trần an toàn ở mức Sweet Spot: **9 – 12 follow/ngày** để duy trì follow bền bỉ qua các đợt quét của TikTok server.

---

## 5. Van Kiểm Soát Đồng Thời (Follow Concurrency Gate)

### Kỷ luật `DEFAULT_FOLLOW_MAX_CONCURRENCY = 15 - 20`
- Khi 40–80 máy lướt feed xong cùng lúc, **CẤM TUYỆT ĐỐI** để toàn bộ máy ùa vào chạy follow đồng thời.
- Quá tải ADB server (`5037`) và bus USB 2.0 (EHCI) gây timeout `1200s` và giật lag, khiến TikTok server nhận diện bot và nhả follow hàng loạt.
- Hệ thống duy trì 15–20 slot file lock (`slot-0.lock` .. `slot-19.lock`) dưới `~/.taadaa/tiktok-follow-concurrency-v1` (hoặc `~/.codex/follow-concurrency-locks`). Máy chạy xong nhả lease cho máy tiếp theo, bảo đảm luồng follow luôn mượt mà và tự nhiên.
