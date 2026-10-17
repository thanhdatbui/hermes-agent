# Execution Engine vs Supervisor Watchdog & WinRT OCR Modular Architecture (17/10/2026)

## 1. Bản chất Monolith & Tại sao phải bóc tách trong môi trường AI Pair-Programming

### Định nghĩa
* **Monolith (Nguyên khối):** File script gom toàn bộ database query, thuật toán xử lý dữ liệu, kiểm tra Excel, điều khiển ADB và cả ngàn dòng giao diện HTML/CSS/JS vào chung một file (> 2.000 – 5.000 dòng).
* **Tác hại đối với Agent AI:**
  1. **Đốt Quota & Nghẽn Context:** AI phải nạp 20.000 – 30.000 tokens mỗi lượt chỉ để đọc file, nhanh chóng chạm trần 5h / Weekly quota.
  2. **Ảo giác & Sửa sai dây chuyền:** Sửa một hàm ở dòng 200 dễ vô tình làm vỡ logic ở dòng 2.500 do code bị kết dính chặt chẽ (tight coupling).
  3. **Bất khả thi khi viết Test:** Không thể viết unit test cô lập, khiến test suite chạy chậm và che giấu regression bugs.

### 3 Cơ chế Gác cổng Bắt buộc Khi Viết Script Mới (Anti-Monolith CI Gates)
1. **Phanh cơ học Closeout Gate (`MAX_DIFF_BYTES_GATE = 30_000` bytes):**
   - Chốt chặn vật lý tự động tại `closeout_gate.py`.
   - Nếu commit tạo diff > 30 KB (~600 dòng), gate FAIL-FAST lập tức với lỗi `DIFF_TOO_LARGE`, từ chối chấm điểm và cấm push.
   - Ép buộc tác giả (người hoặc AI) phải phân rã tính năng mới thành các module nhỏ (100 – 300 dòng).
2. **Bộ Test Gác Cổng Kiến trúc (`test_*architecture_gate.py`):**
   - Khóa trần cứng số dòng file: ví dụ `assertLess(len(lines), 3000)` đối với monolith đang rút gọn, hoặc `< 300` dòng cho file thin-entrypoint.
   - Cấm tái định nghĩa domain logic inline (`test_no_inline_domain_redefinitions`).
3. **Phân tầng Trách nhiệm Duy nhất (Single-Responsibility Pattern):**
   - `core/`: Data models & logic tính toán độc lập.
   - `flows/` hoặc `services/`: Nghiệp vụ vận hành và điều phối.
   - `tests/`: Bộ test tương ứng cho từng module.

---

## 2. Phân định Kiến trúc: Execution Engine vs Supervisor Watchdog

Khi thiết kế hệ thống vận hành tự động nhiều máy (Farm Multi-Device Automation), tuyệt đối không gộp chung luồng thực thi tác vụ với luồng giám sát:

| Tiêu chí | Execution Engine (`multi_machine_feed_session.py`) | Supervisor Watchdog (`feed_session_watchdog.py`) |
| :--- | :--- | :--- |
| **Bản chất** | **Thợ làm (Execution Worker)** | **Giám sát viên (Watchdog Daemon)** |
| **Nhiệm vụ** | Trực tiếp can thiệp app/thiết bị: mở TikTok, cuộn lướt video For You / Following / Friends, thả tim, follow, chuyển tài khoản, ghi nhận tương tác. | Canh gác bên ngoài vòng lặp: phát hiện phiên nuôi bị treo/kẹt quá ngưỡng thời gian, quét dọn tiến trình mồ côi (parasite), giải phóng thiết bị kẹt khóa (`device_lock`), khôi phục phiên. |
| **Vòng đời** | Chạy theo **Ca nuôi** (mỗi ca kéo dài 1 – 2 giờ theo lịch phân ca). | Chạy **định kỳ liên tục** (15 phút/lần qua cronjob) độc lập với ca nuôi. |
| **Cron Mapping** | Được gọi bởi cron **`phase9-runner-tiktok-feed`** (thông qua `tiktok_runner.py` -> `run-feed-session.ps1` -> `run_tiktok.py`). | Được gọi bởi cron **`tiktok-feed-session-watchdog`** để giám sát sinh tồn. |

**Kỷ luật Bóc tách:** Không được nhồi logic dọn dẹp hệ thống hay cứu hộ thiết bị vào sâu bên trong Execution Engine; mọi cơ chế phục hồi bất thường phải nằm ở tầng Supervisor Watchdog để đảm bảo engine chính luôn mỏng và tập trung vào nghiệp vụ cốt lõi.

---

## 3. Chuyển dịch Kiến trúc: UI Automator Dump XML sang Windows Native WinRT OCR

### Lý do Thực tiễn trên Farm Thiết bị Yếu (Samsung S7 / Android 7)
1. **Lỗi Tràn RAM & Treo Tiến trình:**
   - Lệnh `adb shell uiautomator dump` thường xuyên bị Android kernel `kill -9` (`EXIT=137`) do thiết bị cũ cạn bộ nhớ RAM.
   - Dump XML mất từ **1.5s đến 3.5s** cho mỗi lần đọc màn hình, kéo tụt hiệu năng farm.
   - File XML trên thiết bị thường bị đọc nhầm dữ liệu cũ (*stale file caching*).
2. **Giao diện Hiện đại Không Có Node XML:**
   - Ứng dụng TikTok dùng nhiều Flutter, WebKit WebView hoặc Custom Canvas, khiến dump XML trả về `null root node` hoặc cây rỗng không có ID/Text.

### Lợi thế của WinRT OCR (`automation_core.ocr`)
* **Tốc độ:** Chụp screencap đẩy thẳng về Windows và giải mã WinRT OCR mất **0.2s – 0.4s** (nhanh gấp 5–8 lần dump XML).
* **Zero-Token Offline:** Chạy 100% offline trên CPU Windows qua `Windows.Media.Ocr`, **tốn đúng 0 token LLM, 0 đồng tiền API**.
* **Kháng Mã hóa Giao diện:** Nhận diện ký tự trực tiếp trên bitmap hình ảnh, không phụ thuộc vào `resource-id` hay thuộc tính accessibility của Android.

### 4 Quy tắc Vàng Khi Sử Dụng OCR Thay XML
1. **Không Nuốt Ngoại Lệ (No Silent Exception Swallowing):**
   - Tuyệt đối cấm `except Exception: pass` hoặc trả về rỗng mà không log telemetry.
   - Bắt buộc ghi nhận: `elapsed_ms`, `serial`, và mã lỗi (`invalid_screencap`, `ocr_error`, `temp_cleanup_failed`).
2. **Quy tắc Follow Dominance (Chống Bẫy Nút Quan Hệ):**
   - Loại trừ vùng thanh tab điều hướng đỉnh màn hình: Đặt ngưỡng quét `y_min = 200` để tránh nhận nhầm chữ "Bạn bè" trên thanh tab thành trạng thái đã follow profile.
   - Giới hạn độ dài từ của nút bấm: `len(n_txt.split()) <= 3` để tránh match nhầm phần mô tả Bio dài.
   - Loại trừ các nhãn đếm số thống kê: Regex lọc sạch các từ khóa `followers`, `dang follow`, `da follow`.
3. **Rào Cản Màn Hình Nhạy Cảm (Sensitive Screen Guard):**
   - Khi quét dập popup bằng từ khóa ("Để sau", "Hủy", "Đóng"): Quét toàn màn hình trước xem có từ khóa nhạy cảm (`mật khẩu`, `captcha`, `otp`, `đăng nhập`, `thanh toán`).
   - Nếu phát hiện từ khóa nhạy cảm: FAIL-CLOSED ngay lập tức, cấm tự ý bấm đóng làm hỏng luồng xác thực danh tính.
4. **Mô hình Hybrid Đa Tầng:**
   - **Tầng 1 (Primary for Speed):** Dùng WinRT OCR xử lý nhanh các popup thông thường, verify avatar, và đọc trạng thái profile.
   - **Tầng 2 (Deep Action):** Dùng `atx-agent` (HTTP port 7912) khi cần tương tác sâu theo thuộc tính accessibility trên các trường form phức tạp.
