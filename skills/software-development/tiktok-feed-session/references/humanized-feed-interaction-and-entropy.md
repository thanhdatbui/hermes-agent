# Chuẩn Tương Tác Tự Nhiên & Nâng Cao Entropy Hành Vi (Humanized Behavioral Simulation)

## 1. Bối Cảnh & Cơ Chế Phát Hiện Của ByteDance Security SDK
ByteDance Security SDK (thường gồm `libmetasec_ml.so`, module BDTuring, anti-abuse ML engine) không phát hiện tự động hóa bằng một lệnh đơn lẻ, mà dựa trên **Risk Scoring & Anomaly Detection** qua hai kênh chính:
1. **MotionEvent Physics & Metadata:** Lệnh `adb shell input tap/swipe` từ PC tạo ra các sự kiện cảm ứng có chữ ký cơ học:
   - Áp lực nhấn (`Pressure`): luôn cố định 1.000 (phương sai bằng 0).
   - Kích thước tiếp xúc (`Touch Major/Minor/Size`): bằng 0.
   - Quỹ đạo vuốt: thẳng đứng tuyệt đối $dx = 0$ từ đầu đến cuối với vận tốc đều (không có gia tốc sinh học bắt đầu chậm -> tăng tốc -> giảm tốc).
2. **Behavioral Entropy (Độ Hỗn Loạn Hành Vi):** Các bot thông thường có chuỗi hành động đoán trước được (lặp tuần tự A -> B -> C: mở app -> xem video -> thả tim -> vuốt -> lặp lại).

---

## 2. Các Chuẩn Tương Tác Đã Tích Hợp Vào `feed_swipe_smoke.py`

### 2.1 Cử Chỉ Vuốt Nghiêng Ngón Tay Tự Nhiên (Natural Thumb Drift)
- **Mục tiêu:** Triệt tiêu hoàn toàn chữ ký bot $dx = 0$ khi vuốt lướt feed.
- **Tham số tọa độ:**
  - `start_x`: ngẫu nhiên trong vùng `[465, 525]` px (ở 1/3 giữa màn hình 1080p).
  - Độ lệch ngón tay (`drift`): ngẫu nhiên `[-18, +12]` px mô phỏng góc vung ngón cái tự nhiên của bàn tay phải/trái.
  - `end_x`: `max(450, min(540, start_x + drift))` — **100% nằm trọn trong hành lang an toàn [450, 540] px**.
- **Khoảng cách an toàn biên:** Cách mép trái (0..150 px - vùng kích hoạt Camera Story) và mép phải (930..1080 px - vùng lật Profile) ít nhất 350 px.
- **Skew Fallback (Phòng thủ tham số ngoài):** Trong `_perform_feed_swipe`, nếu nhận tham số có $|\Delta X| > 30\text{ px}$, hệ thống tự động ép thẳng đứng an toàn $start\_x = end\_x$.

### 2.2 Hành Vi Bấm "Lưu" (Bookmark / Favorite) Sau Khi Thả Tim
- **Mục tiêu:** Bổ sung tín hiệu gắn kết sâu (High Engagement Signal) có trọng số uy tín cao gấp 3-5 lần lượt like thông thường.
- **Logic:** Chỉ khi video đã được thả tim thành công, mới có xác suất bấm Lưu.
- **Tham số:**
  - Xác suất: ngẫu nhiên **15% – 30%** sau mỗi lần like video thành công.
  - Vị trí nút Lưu: quét element có `text="Lưu"` hoặc `content-desc` chứa "lưu", "yêu thích", "favorite", "bookmark" nằm ở thanh công cụ bên phải ($X \ge 750\text{ px}$).
  - Độ trễ tự nhiên: nghỉ **0.8s – 1.8s** sau khi thả tim rồi mới tap nút Lưu; sau khi tap Lưu nghỉ tiếp **0.4s – 0.8s**.

### 2.3 Xem Lướt Bình Luận (Comment Peek)
- **Mục tiêu:** Phá vỡ tính chu kỳ tuần tự, tăng độ hỗn loạn hành vi (Entropy) cho phiên nuôi nick.
- **Điều kiện kích hoạt (Authoritative Gate):**
  - Chỉ áp dụng độc quyền trên các video **Deep Inspect** (`is_deep_inspect_video = not is_fast_swipe_candidate` và có `raw_xml` mới).
  - Xác suất: ngẫu nhiên **12%** (trung bình 1–2 lần trong phiên 20 video).
- **Chuỗi thao tác:**
  1. Quét tìm nút Bình luận trên thanh công cụ ($X \ge 750\text{ px}$, `content-desc` hoặc `text` chứa "bình luận", "comment").
  2. Bấm mở sheet bình luận: `input tap cx cy`.
  3. Ngâm đọc lướt từ **2.0s – 4.0s**.
  4. Có **50% xác suất** cuộn nhẹ 1 nhịp ngắn (300ms: Y từ 1400 lên 1100).
  5. Đóng sheet bình luận bằng phím Back: `input keyevent 4`, nghỉ **0.6s – 1.2s** để giao diện phục hồi.
- **Cơ chế Fail-Closed:** Kiểm tra `get_focused_activity(ctx)`. Nếu package sau khi đóng sheet không còn thuộc TikTok (`trill`, `musically`, `aweme`) hoặc gặp ngoại lệ, BẮT BUỘC log `result="failed_dismissal"` và trả về `False` để ngăn luồng chạy sai trạng thái.

### 2.4 Giới Hạn Hook Upload Video (Chỉ Chạy Phiên 2)
- Trong `scripts/run-feed-session.ps1`:
  - Điều kiện cũ: `if ($AllowUploadHook -or $SessionIndex -in 1, 2)` -> làm cả 2 phiên đều kích hoạt upload, hao cạn kho video nhanh.
  - Điều kiện chuẩn mới: `if ($AllowUploadHook -or $SessionIndex -eq 2)` -> **chỉ phiên cuối ca (phiên 2)** mới được phép chạy hook upload.
  - Nếu phiên 2 gặp lỗi không đăng được, tài khoản sẽ đợi đến chu kỳ ca kế tiếp (4 ngày sau) mới đăng tiếp, mô phỏng đúng nhịp sinh hoạt tự nhiên của người thật.
