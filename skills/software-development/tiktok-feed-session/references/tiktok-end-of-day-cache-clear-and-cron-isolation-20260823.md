# TikTok End-of-Day Cache Clear & Cron Schedule Isolation (2026-08-23)

## 1. Bối cảnh & Hiện tượng
- Thiết bị Samsung Galaxy S7 sau nhiều ca lướt TikTok bị phình dung lượng cache (từ vài trăm MB lên hàng GB), gây tràn RAM và kích hoạt Android OOM killer đẩy app về Home Launcher dẫn đến alert `TikTok focus lost`.
- **Câu hỏi vận hành:** Có nên dọn cache trước mỗi phiên lướt hay không?

## 2. Quy tắc Vận hành Cache & Chống Xung đột Lịch trình
1. **Tuyệt đối CẤM `pm clear`:** Lệnh `pm clear` cấp OS sẽ xóa sạch session token, cookies và account data $\rightarrow$ làm mất nick / văng login.
2. **Không dọn cache trước mỗi phiên (Anti-pattern):**
   - Dọn cache liên tục gây tình trạng Cold Start: app phải tải lại toàn bộ tài nguyên (font, UI, video buffer, thumbnail) qua mạng/proxy $\rightarrow$ tăng độ trễ và dễ gây nghẽn/timeout ở các video đầu phiên.
3. **Lịch dọn cache chuẩn = Cuối ngày (04:00 AM):**
   - Thực hiện 1 lần duy nhất trong ngày sau khi kết thúc toàn bộ ca lướt và chuỗi tác vụ đêm.
   - **Phân luồng tránh đụng độ (Cron Collision Isolation):**
     - `00:00 - 03:00`: Chuỗi ban đêm (`night-chain-reg-gmail-tiktok`).
     - `04:00`: Dọn cache toàn farm (`end-of-day-clear-tiktok-cache` / `cron_clear_tiktok_cache.py`).
     - `06:00`: Bắt đầu chu kỳ nuôi acc sáng (`tiktok_picker` / `tiktok_runner`).

## 3. Cơ chế mở màn hình "Giải phóng dung lượng"
- **Primary (Deep Link Intent):**
  ```bash
  am start -a android.intent.action.VIEW -d "snssdk1180://clean_cache" com.ss.android.ugc.trill
  ```
  *(Hoạt động 100% không cần kéo widget ra màn hình Home, không lo lệch tọa độ UI).*
- **Fallback 1:** `snssdk1233://clean_cache` (bản musically/quốc tế).
- **Fallback 2:** Tap widget Home tại `(810, 260)` (offsets $\pm 120$px).

## 4. Bất biến Đa luồng & Khóa Xoay / Về Home Bắt buộc
- **Chạy đa luồng (ThreadPoolExecutor `max_workers=10`):** Xử lý 80 máy song song trong 2-3 phút, tránh lỗi `provider timeout` (vượt ngưỡng timeout 3600s của cron khi chạy tuần tự).
- **Khối `finally` bảo đảm an toàn trên từng máy:**
  Sau khi dọn cache (dù thành công, fail hay timeout), script BẮT BUỘC thực hiện:
  1. `am force-stop com.ss.android.ugc.trill` (đóng hoàn toàn app).
  2. `input keyevent KEYCODE_HOME` (đưa máy về Launcher màn hình chính).
  3. `settings put system accelerometer_rotation 0` & `user_rotation 0` (khóa cứng hướng màn hình dọc portrait, chống lỗi app làm xoay ngang màn hình).

## 5. Hiện tượng Task Stack & False-positive "unexpected popup" sau khi mở dọn cache
- **Hiện tượng:** Khi cron dọn cache mở Deep Link `snssdk1180://clean_cache` (TikTokHostActivity), dù sau đó có lệnh force-stop / close recents, trong một số trường hợp TikTok khi khởi chạy lại qua launcher intent / monkey vẫn resume thẳng vào màn hình Cài đặt "Giải phóng dung lượng" thay vì Trang chủ/Feed.
- **Phân loại lỗi:** Classifier nhận diện màn hình Cài đặt (không có các tab Feed mà có nút Xóa bộ nhớ) là `manual-needed:popup` ("unexpected popup/dialog marker detected").
- **Xử lý nhanh tại hiện trường:** Gửi lệnh `KEYCODE_BACK` (hoặc tap nút mũi tên `←` trên góc trái) để thoát sub-activity Cài đặt và quay lại Feed chính.

