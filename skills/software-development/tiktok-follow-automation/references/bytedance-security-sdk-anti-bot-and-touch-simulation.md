# Kỹ Thuật Chống Phát Hiện Bot ByteDance (TikTok Security SDK Reverse Engineering & Human Simulation)

Tài liệu này ghi lại phát hiện thực nghiệm và phân tích chuyên sâu từ Reverse Engineering về ByteDance Security SDK (`libmetasec_ml.so`, BDTuring, DroidGuard) và cách hệ thống tự động hóa điện thoại thật (Phone Farm) vượt qua các thuật toán phát hiện bot / silent rollback follow.

---

## 1. 3 Tử Huyệt Khi Điều Khiển Farm Qua ADB

ByteDance Security SDK không cần tìm chuỗi "adb" trong tiến trình, nó thu thập các chỉ số vật lý trực tiếp từ Linux Input Subsystem và Android WindowManager:

### 1.1 Touch Injection & MotionEvent Signatures
- **Lực nhấn (`Pressure`):**
  - Người thật: Biến thiên liên tục từ nhẹ đến mạnh (`0.12 -> 0.45 -> 0.8 -> 0.2`, `variance > 0.1`).
  - Lệnh `adb shell input tap/swipe`: Luôn trả về `Pressure = 1.000` cố định 100% (`variance = 0`).
- **Diện tích tiếp xúc ngón tay (`Touch Major / Minor / Size`):**
  - Ngón tay thật: Bầu ngón tay có diện tích tiếp xúc (`major = 7.4px, minor = 5.2px`).
  - Lệnh ADB: `size = 0, major = 0, minor = 0`.
- **Cử chỉ vuốt thẳng đứng tuyệt đối ($dx = 0$):**
  - Bot cơ học: Quẹt từ `start_x` lên `end_x` với $dx = 0$ cố định hàng trăm video liên tiếp.
  - Người thật: Ngón tay cái xoay theo khớp xương cổ tay, luôn có độ cong tự nhiên $\Delta X = \pm 15 \sim 25\text{ px}$.

### 1.2 Device Clustering Correlation (Giao Thoa Cụm Thiết Bị)
- Hệ thống Anti-Fraud nhóm các máy có cùng đặc điểm bất thường:
  - Cùng phần cứng: CPU Exynos, GPU Mali, cùng danh sách cảm biến (`SensorList`), cùng DPI/độ phân giải.
  - Cùng dải IP/Subnet 4G hoặc gateway MobiProxy.
  - Cùng uptime tương đương (khởi động cùng lúc sau khi cúp điện/bật hub).
  - **Mật độ tài khoản:** 8 nick/máy luân phiên đổi qua TikTok Switcher theo chu kỳ cố định là dấu hiệu rõ ràng của farm.

### 1.3 Chuỗi Hành Vi Có Độ Hỗn Loạn Thấp (Low Sequence Entropy)
- Kịch bản lặp tuần tự (A -> B -> C): Mở app -> xem 2-4s -> lướt -> xem 10s -> thả tim -> lướt -> follow.
- Thuật toán Machine Learning nhận diện được đồ thị hữu hạn các hành động lặp đi lặp lại.

---

## 2. Các Giải Pháp Đã Triển Khai Vào Codebase

### 2.1 Cử Chỉ Vuốt Nghiêng Tự Nhiên (`Natural Thumb Drift`)
- **Vị trí áp dụng:** `feed_swipe_smoke.py` (`tiktok-luot nuoi acc`) và `adapter.py` (`Tiktok-video`).
- **Thông số kỹ thuật:**
  - `start_x` ngẫu nhiên trong khoảng `[465, 525]` px.
  - `end_x = start_x + random.randint(-18, 12)` px, kẹp chặt trong hành lang an toàn `[450, 540]` px ngay tâm màn hình 1080p.
  - Khoảng cách tới mép trái (Camera/Story $X \le 150$) và mép phải (Profile $X \ge 930$) luôn $> 300\text{ px}$, triệt tiêu 100% nguy cơ văng màn hình.
  - Duration biến thiên ngẫu nhiên `[350, 480]` ms thay vì cố định.
  - **Skew Fallback:** Nếu tham số truyền vào bị lệch nguy hiểm ($|\Delta X| > 30\text{ px}$), tự động ép thẳng đứng $start\_x = end\_x$.

### 2.2 Hành Vi Xem Lướt Bình Luận (`Comment Peek`)
- **Vị trí áp dụng:** `feed_swipe_smoke.py` (`_maybe_peek_comments`).
- **Cơ chế:**
  - Gated độc quyền trên các video **Deep Inspect** (video có dump XML) với xác suất **12%** (khoảng 1–2 lần mỗi ca).
  - Tap nút Bình luận trên thanh công cụ bên phải (`X >= 750 px`).
  - Ngâm đọc sheet bình luận **2.0s – 4.0s**.
  - Có **50% xác suất** cuộn nhẹ 1 nhịp ngắn (300ms) đọc tiếp.
  - Đóng bằng phím Back (`KEYCODE_BACK`), chờ 0.6s – 1.2s ổn định.
  - **Fail-Closed Gate:** Kiểm tra gói ứng dụng active sau khi Back. Nếu văng khỏi TikTok hoặc kiểm tra lỗi, ghi log `result="failed_dismissal"` và dừng an toàn.

### 2.3 Thả Tim Đi Kèm Lưu Yêu Thích (Bookmark/Favorite)
- **Vị trí áp dụng:** `feed_swipe_smoke.py` (`_maybe_like_video`).
- **Cơ chế:**
  - Khi một video được chọn Thả tim thành công, có tỷ lệ **15% – 30%** tiếp tục bấm nút **"Lưu"** (`content-desc` hoặc `text` là "Lưu" / "Mục yêu thích").
  - Delay ngâm **0.8s – 1.8s** sau khi tim rồi mới bấm Lưu.
  - Tín hiệu Bookmark có trọng số tin cậy (Trust Weight) cao gấp 3-5 lần Like thông thường.

### 2.4 Dwell Time Ngâm Trước Thao Tác Trọng Yếu
- **Vị trí áp dụng:** `mode1_search_follow.py`, `mode2_follow_followers.py` (`tiktok-follow`) và `state_machine.py` (`Tiktok-video`).
- **Pacing chuẩn nhịp GemPhone:**
  - Ngâm Profile trước khi bấm Follow: **6.0s – 12.0s**.
  - Chờ server phản hồi sau khi bấm Follow: **2.5s – 5.0s**.
  - Nghỉ giữa 2 lượt follow: **8.0s – 25.0s**.
  - Ngâm trước khi bấm nút "Đăng" video (Post): **1.8s – 3.5s** sau khi caption hoàn tất.
