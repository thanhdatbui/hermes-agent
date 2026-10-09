# Quy Chuẩn Cấu Hình Tắt Màn Hình & Chống Nung Mainbox Farm S7

## 1. Bản Chất Kỹ Thuật (Box Farm Main Samsung S7)
- Các thiết bị trong farm là dạng **mainboard cắm trong box chuyên dụng**, không có màn hình vật lý (AMOLED/LCD) thật.
- Khung hình view trên PC (Xiaowei, Scrcpy...) được chip Exynos/GPU mã hóa SurfaceFlinger và đẩy qua USB.
- **Rủi ro khi treo màn hình luôn sáng (`stay_on_while_plugged_in = 7`):**
  - GPU và SoC liên tục render, nhiệt độ tăng 3°C - 7°C.
  - Trong box mật độ cao (20-40 main/box), nhiệt độ cao kéo dài gây hở chân chip BGA (CPU/RAM), chai IC nguồn PMIC và hỏng chip nhớ flash.

## 2. Các Cạm Bẫy Khi Điều Khiển Tắt Màn Qua ADB

### Cạm bẫy 1: Dùng `keyevent 26` (Nút Nguồn - Toggle)
- `keyevent 26` là lệnh **đảo trạng thái (toggle)**. Nếu máy đang chập chờn giữa thức và ngủ hoặc một service vừa đánh thức máy, gửi lệnh 26 sẽ **bật màn hình trở lại**.
- **Giải pháp:** BẮT BUỘC dùng **`input keyevent 223` (`KEYCODE_SLEEP`)** — đây là lệnh ép ngủ bắt buộc một chiều.

### Cạm bẫy 2: Cờ Developer Options `stay_on_while_plugged_in = 7`
- Khi cờ này mang giá trị 7, Android hiểu rằng khi cắm nguồn USB/AC thì không bao giờ tắt màn hình.
- Dù có gán `screen_off_timeout = 600000` (10 phút) hay `15000` (15 giây), bộ đếm thời gian của `PowerManagerService` cũng **bị đóng băng không chịu đếm ngược**.
- **Giải pháp:** Phải gán `settings put global stay_on_while_plugged_in 0` và `svc power stayon false`.

### Cạm bẫy 3: Samsung Always On Display (AOD)
- Khi tắt màn hình, S7 thường chuyển sang chế độ Dozing để chạy `com.samsung.android.app.aodservice` hiển thị đồng hồ ngầm, khiến tool view PC vẫn nhận khung hình.
- **Giải pháp:** Gán `settings put system aod_mode 0`.

### Cạm bẫy 4: Thả nổi timeout quá ngắn (< 60 giây)
- Nếu để timeout quá ngắn (ví dụ 15s), khi bot đang chạy mà gặp hiện tượng lag app, quay vòng, nghẽn mạng proxy hay ADB dump chậm, màn hình sẽ tự tắt phụt giữa chừng.
- Khi màn hình tắt, Android chuyển Activity sang `onStop()`, lệnh ADB click/tap bấm vào màn hình đen dẫn đến click trượt và gãy quy trình bot.
- **Giải pháp:** Đặt timeout fail-safe chuẩn **10 phút (`600000` ms)**. Trong 10 phút, bot thoải mái thao tác; khi bot xong hoặc lỗi dừng lại thì máy tự ngủ.

## 3. Chuỗi Lệnh Chuẩn Hóa Nguyên Tử Cho Thiết Bị
BẮT BUỘC dùng chuỗi lệnh nối bằng `&&` (không dùng `;` để tránh gãy lệnh giữa chừng):
```bash
adb -s <SERIAL> shell "settings put global stay_on_while_plugged_in 0 && svc power stayon false && settings put system aod_mode 0 && settings put system screen_off_timeout 600000 && input keyevent 223"
```

## 4. Nguyên Tắc Vận Hành Với `automation-core`
- **Khi bắt đầu task:** `automation-core` (`prepare_android_for_automation` / `prepare_device`) tự động gửi `input keyevent 224` (`KEYCODE_WAKEUP`) và giải phóng keyguard để bật màn hình dậy chạy bot.
- **Hiện trường lỗi:** Màn hình tắt sau 10 phút chỉ là tắt hiển thị (Display OFF), app lỗi và RAM vẫn giữ nguyên. Khi AI / Canary chạy vào reproduce, core sẽ tự bật màn hình lên lại và hiện trường lỗi vẫn còn nguyên 100%.
- **Quy tắc tuyệt đối:** CẤM các script preflight hoặc runner tự ý bật lại `stay_on_while_plugged_in = 7`.
