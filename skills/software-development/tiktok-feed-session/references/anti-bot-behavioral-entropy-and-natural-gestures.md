# TikTok Feed Anti-Bot Behavioral Entropy & Natural Gesture Standards

Tài liệu chuẩn hóa các cơ chế hành vi người thật và cử chỉ tự nhiên trên TikTok Android (triển khai ngày 14/09/2026 sau phản biện từ chuyên gia Mobile Anti-Fraud GPT-5.6 Sol).

## 1. Tầng Cảm Ứng & Cử Chỉ (Touch & Gesture Layer)
- **Tử huyệt của ADB `input swipe`:** Lệnh `adb shell input swipe` truyền thống luôn có `dx = 0` (đường thẳng tắp), `pressure = 1.000` cố định, `size = 0`, và vận tốc tuyến tính không có gia tốc ngón tay (`acceleration = 0, jerk = 0`). Đây là chữ ký bot (synthetic signature) rất dễ bị ByteDance Security SDK (`libmetasec_ml.so`) nhận diện.
- **Chuẩn Natural Thumb Drift (Độ nghiêng ngón tay cái tự nhiên):**
  - Điểm bắt đầu `start_x`: ngẫu nhiên trong vùng tâm an toàn `[465, 525]` px.
  - Điểm kết thúc `end_x`: lệch nhẹ tự nhiên $\Delta X = -18\text{px} \sim +12\text{px}$ theo góc vung ngón cái, nằm trọn trong hành lang an toàn `[450, 540]` px giữa màn hình 1080p.
  - Khoảng cách an toàn: cách mép Camera bên trái (`0..150px`) và Profile bên phải (`930..1080px`) ít nhất 300px.
  - **Skew Fallback Guard:** Nếu tham số truyền vào bị lệch quá mức nguy hiểm ($|\Delta X| > 30\text{px}$), hệ thống tự động ép thẳng đứng an toàn ($end\_x = start\_x$) để triệt tiêu 100% nguy cơ văng màn hình.

## 2. Tầng Tương Tác Hành Vi & Độ Hỗn Loạn (Behavioral Entropy Layer)
- **Random Like Rates per Session:**
  - Tab Đang Follow (`following`): Biến thiên ngẫu nhiên **30% – 60%** mỗi phiên.
  - Tab Bạn bè (`friends`): Biến thiên ngẫu nhiên **50% – 80%** mỗi phiên.
  - Tab Đề xuất (`for_you`): Giữ nguyên dải an toàn **8%**.
- **Tương tác Lưu Bookmark / Yêu thích (Bookmark/Favorite):**
  - *Sau khi Thả tim thành công:* Xác suất 15% – 30% tìm nút "Lưu" trên thanh công cụ bên phải (`X >= 750`), nghỉ 0.8s – 1.8s rồi mới tap Lưu.
  - *Independent Bookmark (Lưu độc lập không cần Like):* Xác suất 3% – 5% trên các video không được Like hoặc nút Like bị ẩn/lỗi, vẫn tìm nút Lưu và tap độc lập. Phá tan chữ ký tương quan cứng Like $\rightarrow$ Save. Bắt buộc kiểm tra `res.ok is True` tránh false-success.
- **Tương tác Đọc Lướt Bình Luận (Comment Peek):**
  - Kích hoạt độc quyền trên các video Deep Inspect với xác suất ngẫu nhiên **12%**.
  - Tap nút bình luận bên phải (`X >= 750`), ngâm đọc **2.0s – 4.0s** (có 50% xác suất cuộn nhẹ 1 nhịp đọc tiếp).
  - Đóng sheet bằng phím Back (`KEYCODE_BACK`), nghỉ 0.6s – 1.2s.
  - **Fail-closed Verification:** Kiểm tra package sau khi đóng sheet, nếu mất focus TikTok phải ghi log `result="failed_dismissal"` và trả về `False`.
- **Nhịp Vuốt Ngược Xem Lại Video (Rewind Swipe - Session Narrative):**
  - Trong feed session (từ video thứ 3 trở đi, trừ video cuối ca), có xác suất ngẫu nhiên **5% – 8%** vuốt ngược từ trên xuống dưới (`[sx, 480]` $\rightarrow$ `[ex, 1380]`) với cờ `allow_downward=True`.
  - Dừng ngâm xem lại video **2.0s – 4.0s** rồi tiếp tục, mô phỏng hoàn hảo sự xao nhãng của người thật.

## 3. Tầng Nhịp Độ & Pacing (Follow & Upload)
- **Follow Pacing (`tiktok-follow`):**
  - Dwell time ngâm Profile mục tiêu: **6.0s – 12.0s** trước khi bấm Follow (học theo node delay `5812, 12549 ms` của GemPhone ông Khoa).
  - Post-tap delay: Chờ server đồng bộ **2.5s – 5.0s** ngẫu nhiên (thay vì 1.5s).
  - Inter-follow delay: Giãn cách **8.0s – 25.0s** giữa 2 lần follow.
- **Upload Pacing (`Tiktok-video`):**
  - Dwell delay trước khi bấm Đăng: Sau khi điền caption/hashtag, ngâm dừng **1.8s – 3.5s** trước khi tap nút "Đăng" (chống cờ Automated Instant Posting).
  - Profile Grid & Restore Swipe: Lệch tự nhiên $\Delta X = -15\text{px} \sim +12\text{px}$, thời lượng ngẫu nhiên **420ms – 490ms**.
  - Giới hạn Hook Upload: Chỉ phiên 2 (phiên cuối ca) mới được kích hoạt upload video, bảo toàn kho video trong thời gian ngâm án phạt.
