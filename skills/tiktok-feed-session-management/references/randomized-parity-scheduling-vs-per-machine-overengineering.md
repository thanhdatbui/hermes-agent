# Randomized Parity Scheduling vs Per-Machine Overengineering (Invariants)

## 1. Bối Cảnh & Bài Học Thực Tiễn (Anti-Overengineering Lesson)

### Cám dỗ thiết kế (The Overengineering Trap):
Khi muốn tăng tính ngẫu nhiên (Entropy/Anti-Pattern) để chống bị TikTok bắt bài, một ý tưởng thường nảy sinh là:
*"Trong cùng một ca (ví dụ Ca Sáng lúc 06:00), mỗi máy tự bốc ngẫu nhiên 1 Row khác nhau (Máy 1 chạy Row 1, Máy 2 chạy Row 2, Máy 3 chạy Row 7...)."*

### Hậu quả hệ thống khi áp dụng sai (Architectural Blast Radius):
1. **Phá vỡ PowerShell Batch Runner lõi:**
   Script canonical `run-feed-session.ps1` nhận tham số `-Row <int>` duy nhất cho toàn bộ 80 máy workers. Nếu mỗi máy chạy 1 row, phải đập đi viết lại cơ chế spawn, quản lý worker và truyền tham số, tăng độ phức tạp O(N).
2. **Làm tê liệt cấu trúc Artifact & Telemetry:**
   Cấu trúc thư mục chuẩn là `live/YYYY-MM-DD/row-<R>-<HHMMSS>/` (80 máy ghi nhận kết quả vào chung 1 phiên). Nếu máy chạy hỗn loạn nhiều row trong 1 ca, hệ thống sẽ phải sinh ra hàng chục thư mục rác hoặc làm hỏng logic quét cây thư mục.
3. **Phá hủy tính chính xác của Báo Cáo Watchdog Telegram:**
   Watchdog không thể báo cáo tiêu đề nhất quán như `Ca 1 hoàn tất (Row 1)` khi trong ca đó máy này chạy R1 máy kia chạy R2. Việc theo dõi sức khỏe và tỉ lệ lỗi từng Row bị phân mảnh hoàn toàn.

---

## 2. Giải Pháp Chuẩn Hóa: Randomized Parity 4-Day Cycle (Đảo Nhóm Chẵn / Lẻ Theo Chu Kỳ)

Thay vì xé lẻ từng máy chạy row riêng, hệ thống đạt được tính ngẫu nhiên tối đa mà **VẪN BẢO TOÀN 100% KIẾN TRÚC RUNNER & WATCHDOG HIỆN CÓ** bằng cách:

### Cơ chế Randomized Parity:
1. **Vẫn giữ nguyên 1 Ca = 1 Row trên toàn bộ Fleet:**
   - 80 máy Kibe và 80 máy Admin chạy chung 1 Row trong từng ca.
   - Giữ nguyên toàn bộ script `run-feed-session.ps1`, kho video theo niche và cấu trúc artifact.
2. **Đảo ngẫu nhiên nhóm Chẵn / Lẻ đầu chu kỳ 4 ngày:**
   - Mỗi chu kỳ 4 ngày mới (`cycle_idx`), hệ thống tự động băm hash để gieo xúc xắc ngẫu nhiên (Pseudo-random Hash Seed):
     * **Chu kỳ A (Odd-first):**
       - Ngày 1: Ca 1 (Sáng) = Row 1 | Ca 2 (Trưa) = Row 3 | Ca 3 (Tối) = Row 5.
       - Ngày 2: Ca 1 (Sáng) = Row 2 | Ca 2 (Trưa) = Row 4 | Ca 3 (Tối) = Row 6.
     * **Chu kỳ B (Even-first):**
       - Ngày 1: Ca 1 (Sáng) = Row 2 | Ca 2 (Trưa) = Row 4 | Ca 3 (Tối) = Row 6.
       - Ngày 2: Ca 1 (Sáng) = Row 1 | Ca 2 (Trưa) = Row 3 | Ca 3 (Tối) = Row 5.
3. **Ngày 3 & Ngày 4 vận hành phục hồi & xả tải:**
   - **Ngày 3:** Ca 1 = Row 7, Ca 2 = Row 8, Ca 3 = Dưỡng sinh acc yếu (ăn nhả + thiếu video).
   - **Ngày 4:** Cả 3 ca đều chạy dưỡng sinh toàn farm (Tắt 100% follow, lướt feed + up 1 video nếu chưa đăng).
4. **Bảo toàn Nhịp Sinh Học người dùng (User Persona):**
   - Khung Sáng (06h & 08h): Chỉ dành cho `{Row 1 hoặc Row 2}`.
   - Khung Trưa (12h & 14h): Chỉ dành cho `{Row 3 hoặc Row 4}`.
   - Khung Tối (18h & 20h): Chỉ dành cho `{Row 5 hoặc Row 6}`.
   - Từng tài khoản giữ vững thói quen online theo khung giờ cố định, thuật toán TikTok không thể bắt bài chu kỳ ngày cày.

---

## 3. Ranh Giới Phân Định Giám Sát: Telegram (Vĩ Mô) vs Dashboard Port 1905 (Vi Mô)

### Nguyên tắc bất biến chống Spam & Đảm bảo Tính Giám Sát:
1. **Telegram Watchdog = Giám Sát VĨ MÔ Cấp Fleet & Row:**
   - BẮT BUỘC phân tách báo cáo Sức khỏe 8 Row độc lập cho từng Farm (Kibe riêng, Admin riêng). CẤM gộp chung hoặc chỉ đọc `runtime/kibe/live` khiến Admin bị mù.
   - CẤM TUYỆT ĐỐI liệt kê chi tiết từng tài khoản lên Telegram (quy mô 1,280 accounts gây tràn giới hạn 4,096 ký tự và tạo bão tin rác).
   - Chỉ xuất cảnh báo tóm tắt số lượng nick bị bỏ đói (>96h) nếu có ngoại lệ.
2. **Web Dashboard (`http://127.0.0.1:1905`) = Giám Sát VI MÔ Cấp Account:**
   - Là Single Source of Truth để tra cứu chi tiết toàn bộ 1,280 accounts.
   - Bắt buộc có Tab `🌾 Sức Khỏe Nuôi Acc`:
     * Hỗ trợ **Sort 1-click "Đói nhất lên đầu"** (`hours_ago` giảm dần).
     * Bộ lọc nhanh: Theo Cụm (Kibe / Admin), theo Row (1-8), hoặc chỉ hiện nick bị bỏ đói (`🔴 > 96h`).
     * Hiển thị trạng thái phân tầng: 🟢 Bình thường (≤72h), 🟡 Sắp đến lượt (72h–96h), 🔴 Bị bỏ đói (>96h).
