# Quản Lý Màn Hình & Nhiệt Độ Cho Phone Farm Dạng Box (Headless Mainboard)

## 1. Bản Chất Phần Cứng Box Farm
- Các máy trong farm là **bare mainboard (Samsung Galaxy S7 / Exynos 8890)** cắm trực tiếp vào chassis box, **không có tấm nền màn hình vật lý (AMOLED/LCD)**.
- Màn hình hiển thị mà người vận hành thấy trên PC là luồng mirror/stream giả lập qua phần mềm (như Scrcpy, Total Control, hoặc GemPhoneFarm PC view).
- Vì không có màn hình vật lý, thiết bị **không bị rủi ro cháy bóng (burn-in) hay hư hại đèn nền/tấm nền**.

## 2. Nguyên Tắc Tắt Màn Hình & Giảm Nhiệt Độ

### A. View Trên PC (Scrcpy / Tool View)
- **TẮT TOÀN BỘ KHI CHẠY TỰ ĐỘNG:**
  - Khi stream video lên PC, chip Exynos trên main phải liên tục chạy bộ giải mã phần cứng (Hardware Video Encoder) để nén khung hình H.264/H.265 rồi truyền qua USB bus.
  - Quá trình này làm tăng nhiệt độ SoC thêm **3°C – 7°C**. Với mật độ 20–40 main xếp sát nhau trong khay box, nhiệt độ cao liên tục sẽ dẫn đến:
    1. **Hở chân chip BGA** (rụng mối hàn giữa RAM, CPU và bo mạch).
    2. **Chai / hỏng IC nguồn (PMIC)** do dòng tải duy trì cao.
    3. **Suy hao tuổi thọ chip nhớ eMMC / UFS**.
  - Đồng thời gây nghẽn băng thông USB controller và ngốn tài nguyên CPU/GPU máy chủ PC.
  - **Quy tắc:** Chỉ mở view PC khi cần debug/can thiệp thủ công 1 máy cụ thể; khi chạy batch/cron tự động thì đóng toàn bộ cửa sổ stream.

### B. Trạng Thái Màn Hình Trên Thiết Bị (Android Display Power State)
- **Khi Máy Đang Chạy Bot (Reg, Feed, Upload, 2FA...):**
  - **BẮT BUỘC BẬT MÀN HÌNH (`screen_on=True`).**
  - Đa số ứng dụng Android (TikTok, Gmail, Settings) sẽ rơi vào trạng thái `onPause()` / `onStop()` hoặc ngủ ngầm nếu màn hình tắt.
  - Khi màn hình tắt, các lệnh ADB `uiautomator dump` (lấy UI XML) hoặc `screencap` sẽ bị lỗi trả về đen màn hình hoặc fail timeout, các lệnh click tọa độ `input tap` không tác dụng.
- **Khi Máy Nghỉ (Idle, Chờ Cron, Giữa Các Ca Chạy):**
  - **NÊN TẮT MÀN HÌNH (`input keyevent 26` / sleep):**
  - Khi tắt màn hình, GPU và SurfaceFlinger dừng vẽ khung hình 60 FPS, CPU tự hạ xung nhịp (downclocking/deep sleep), giúp mainboard hạ nhiệt nhanh chóng và bảo toàn linh kiện.

## 3. Bảo Đảm Tương Thích Với Toàn Bộ Kịch Bản Automation-Core

Toàn bộ 7 repository automation cốt lõi của Taadaa Farm:
1. `register gmail` (`gmail_reg_v10.py`)
2. `tiktok-follow` (`run_follow.py` / `adapter.py`)
3. `tiktok-luot nuoi acc` (`run_tiktok.py`)
4. `Tiktok-video` (`tiktok_workflow/state_machine.py`)
5. `Tiktok_Reg` (`tiktok_reg_live_email_v1.py` / `social_reg_v1.py`)
6. `tiktok-add-bao-mat-f2a` (`run_batch_live_2fa.py`)
7. `tiktok-log-in` (`live_adapter.py`)

Đều đã tích hợp `automation-core` ở bước Preflight (`prepare_android_for_automation` hoặc `prepare_device` với `wake=True, swipe_unlock=True`):
- **Tự động đánh thức:** Khi nhận job, script tự đọc `dumpsys power`, phát hiện màn hình đang tắt và gửi `input keyevent 224` (WAKEUP) + `input keyevent 82` (MENU) + vuốt mở khóa Keyguard.
- **Tự động kiểm tra mạng:** Gọi `require_android_vpn` xác thực kết nối proxy/WiFi trước khi thực thi.
- **Kết luận:** Việc cho máy tắt màn hình khi idle là **HOÀN TOÀN AN TOÀN**, không lo bot bị kẹt hay không tự mở được khi đến ca chạy tiếp theo.
