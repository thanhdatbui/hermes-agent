# Case 175 & 176: Biometric Thumb Arc Swipe & Profile Zero-View Recovery Telemetry

## 1. Case 175: Humanized Thumb Arc Swipe Kinematics (Vuốt ngón tay sinh học)

### Vấn đề Anti-Fraud
- Trước đây, `DEFAULT_SWIPE_DURATION_MS = 650` (550ms – 750ms) tạo nên động tác kéo rê chậm lì, mang tính máy móc cao.
- Độ lệch ngón cái `drift` chỉ dao động quanh dải hẹp `-18..+12px`, kết hợp bẫy chặn thẳng đứng `if abs(raw_end_x - start_x) > 30: end[0] = start_x` khiến mọi thao tác quẹt bị nén thành đường thẳng cơ học.

### Giải pháp chuẩn hóa (Sol 5.6 Reviewed & Approved)
- **Tốc độ lướt sinh học (Bio-duration):**
  - `DEFAULT_SWIPE_DURATION_MIN_MS`: 240ms
  - `DEFAULT_SWIPE_DURATION_MAX_MS`: 400ms
  - `DEFAULT_SWIPE_DURATION_MS`: 330ms (tốc độ dứt khoát của người dùng lướt feed thật).
- **Mô phỏng góc nghiêng ngón cái (Thumb Arc Drift):**
  - Vùng đặt ngón cái `start_x`: `[470, 525]` (vùng đặt tay tự nhiên của người thuận tay phải).
  - Độ xoay ngón tay quanh cổ tay: `drift = random.randint(-35, 15)`.
  - Nới lỏng ngưỡng skew thẳng đứng: `|dx| > 45px` (thay vì 30px).
  - Hành lang an toàn `end_x`: clamped trong `[440, 540]` (cách mép trái >440px và cách cột tương tác bên phải >360px).
  - Tọa độ trục Y: `start_y: 1330–1410`, `end_y: 430–510` (quãng đường `822px – 980px` kích hoạt chuyển video trơn tru trên Galaxy S7).

---

## 2. Case 176: Telemetry Sức Khỏe Profile & Auto Deep Organic Rest (0-View Jail)

### Zero-Cost Observability (Bóc tách View từ Profile XML)
- Tận dụng XML sẵn có trong `_profile_identity_from_xml`:
  - Lọc bỏ nửa trên màn hình ($y < 850$) để không nhầm số Follower/Following/Likes ở Header.
  - Bỏ qua các ô nhãn: `"Đã ghim"` (Pinned), `"Nháp"` (Draft), `"Thích"` (Liked).
  - Trích xuất tối đa 6 view gần nhất: `latest_views: list[str]`.

### Thuật Toán Đánh Giá Sức Khỏe Chuẩn Thực Chiến (Chống Phạt Oan - Cách B)
- **Điều kiện tiên quyết:** Video mới nhất phải đã đăng `> 24h` (nếu `< 24h` thì bỏ qua, coi là đang trong độ trễ phân phối của TikTok).
- **Quy tắc kích hoạt Deep Organic Rest (3 ngày):**
  1. Kênh mới toanh (chỉ có đúng 1 video duy nhất): dính `0 view` sau 24h $\rightarrow$ Kích hoạt Deep Rest.
  2. Kênh có nhiều video: chỉ phạt khi **cả 2 video gần nhất liên tiếp đều dính `0 view`** (ví dụ `['0', '0', '340']`). Nếu chỉ 1 video mới nhất dính 0 view mà video liền kề có view (ví dụ `['0', '150', '420']`), hệ thống đánh giá là **HEALTHY** (flop nội dung đơn lẻ hoặc dính bản quyền âm thanh, không phạt oan).
- **Cơ chế Deep Organic Rest:**
  - Mở rộng `_is_account_organic_rest_day` hỗ trợ `force_rest_ledger`.
  - Khi dính cờ: Tự động ép nghỉ 3 ngày (100% lướt feed nuôi trust, 0 follow, 0 upload), tận dụng đúng khối Dưỡng sinh sẵn có trên Watchdog.

---

## 3. Kỷ Luật Coordinator vs Persistent Memory Leakage (RCA từ Claude Opus High)

### Root Cause
- Salience đè bẹp Lệnh cấm: Con số điểm audit `89/100` tạo perceived significance cao khiến model có xu hướng lưu lại thành tích (completion drive).
- Vi phạm quy chuẩn: Điểm số audit là **session outcome / transient fact**, tuyệt đối không được ghi vào persistent memory (vốn chỉ dành cho quy tắc bền vững và fact môi trường).

### Pre-Write Gate Checklist trước khi gọi tool `memory`
1. Fact này có thay đổi hoặc vô nghĩa ở phiên sau không? (Có $\rightarrow$ CẤM LƯU).
2. Dữ liệu này đã có trong Git commit / Case doc / PR chưa? (Có $\rightarrow$ CẤM LƯU).
3. Nội dung có chứa điểm số (`N/100`), Case ID (`Case N`), PR ID, hoặc động từ hoàn thành (`done/fixed/passed/audited`) không? (Có $\rightarrow$ CẤM LƯU TUYỆT ĐỐI).
