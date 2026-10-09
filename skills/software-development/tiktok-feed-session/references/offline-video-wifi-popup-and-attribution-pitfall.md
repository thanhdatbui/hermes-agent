# Anti-Pattern: Nhận Định Sai Nguồn Gốc Popup & Bài Học Xử Lý Popup Tải Video Ngoại Tuyến TikTok (06/09/2026)

## 1. Hiện Tượng Thực Tế & Lỗi Nhận Định (The Hallucination Pitfall)
Trong sự cố Farm Alert `[MÁY 78]` (`tiktok-luot nuoi acc`):
- Khi lướt feed, màn hình xuất hiện dialog thông báo:
  *"Tự động tải video về qua Wi-Fi để xem ngoại tuyến?"* cùng nút `"OK"`.
- **Lỗi nhận định sai lầm (Anti-Pattern):**
  - Worker/Coordinator vội vã suy đoán đây là tính năng Smart Downloads của app thứ ba (**YouTube**) chạy ngầm nhảy vào, hoặc nghi ngờ do **máy rớt Wi-Fi** kích hoạt offline mode.
  - User đã chấn chỉnh: *"Có phải do máy rớt wifi k"*, *"Nghe vô lí vc đang ở trong tiktok mắc gì youtube nhảy vào. Đọc log kĩ coi"*.
- **Bằng chứng thực tế khi đối soát O(1):**
  1. `wlan0`: state `UP`, IP `192.168.110.122`, ping `8.8.8.8` 0% packet loss, RTT ~54ms -> Mạng Internet hoàn toàn thông suốt, không hề rớt Wi-Fi.
  2. `dumpsys window`: `mCurrentFocus` là `com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity` -> 100% thuộc nội bộ package **TikTok**, không có app thứ ba nào đè lên.
  3. Bản chất: Đây là tính năng **"Video ngoại tuyến" (Offline Videos)** của chính TikTok (tự động cache video khi cắm sạc/có Wi-Fi).

## 2. Nguyên Nhân Kỹ Thuật (Allowlist & Detector Gap)
- Hàm `detect_offline_video_prompt` trong `python_runner/core/benign_popup.py` trước đây chỉ nhận diện hai cụm từ:
  `"video ngoại tuyến"` và `"tải video về để xem ngoại tuyến"`, chỉ tìm nút `("đóng", "close")`.
- Khi TikTok hiển thị biến thể dialog mới:
  `"Tự động tải video về qua Wi-Fi để xem ngoại tuyến?"` và nút hành động duy nhất là `"OK"`:
  - Detector trả về `None`.
  - Không có rule nào trong allowlist khớp, flow phân loại là `manual-needed:popup` (`popup is not in the shared TikTok allowlist; manual review required`).
  - Cơ chế swipe recovery thử lại 2 lần không qua và dừng phiên.
  - Đồng thời `detect_offline_video_prompt` chưa được đưa vào chuỗi `detect_allowed_generic_popup`.

## 3. Giải Pháp Chuẩn (Case 135)
1. **Mở rộng text markers:**
   Bổ sung các biến thể:
   - `"tự động tải video về qua wi-fi để xem ngoại tuyến"`
   - `"tự động tải video về"`
   - `"download videos automatically over wi-fi"`
2. **Mở rộng nút hành động:**
   Thêm nút `"ok"` vào danh sách tìm kiếm element: `("đóng", "close", "ok")`.
3. **Đăng ký vào generic allowlist:**
   Đưa `detect_offline_video_prompt(root)` vào hàm `detect_allowed_generic_popup(root)` trong `python_runner/core/benign_popup.py`.

## 4. Kỷ Luật Điều Phối Worker (Coordinator Patch Contract vs Open Goal)
- **Bài học cạn tool calls:** Khi Coordinator giao goal mở ("Điều tra và sửa popup...") cho subagent trong monorepo lớn, 3 worker liên tiếp cạn 35 tool calls (tổng cộng ~120 phút) chỉ để đọc đi đọc lại file.
- **Quy tắc Patch Contract:** Coordinator BẮT BUỘC định vị trước file (`benign_popup.py`), trích xuất `old_string` và soạn sẵn `new_string`, giới hạn worker ngân sách <= 5 tool calls. Worker `deleg_7aa50153` hoàn thành sửa và canary chỉ trong 5 phút khi có Patch Contract.
