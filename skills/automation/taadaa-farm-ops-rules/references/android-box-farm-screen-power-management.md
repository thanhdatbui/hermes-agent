# Quy Tắc Quản Lý Màn Hình Farm Box Android (Samsung S7 / Mainboard Box)

## 1. Bản Chất Phần Cứng Farm Box
- Thiết bị chạy trong box chỉ có **mainboard gắn vào box**, không có màn hình vật lý (không sợ burn-in AMOLED).
- Màn hình hiển thị trên PC (Xiaowei, Scrcpy) là luồng stream video lấy từ SurfaceFlinger / VPU nén H.264 qua USB.
- **Rủi ro chí mạng:** Để màn hình sáng liên tục hoặc mở view PC nhiều máy sẽ làm SoC Exynos quá nhiệt (+3°C đến 7°C) dẫn đến hở chân chip BGA (rụng RAM/CPU), chai chip nguồn PMIC, nghẽn bus USB.
- **Mục tiêu:** Màn hình phải tự tắt khi máy nghỉ (idle) để bảo vệ phần cứng.

---

## 2. Các Cạm Bẫy Khi Điều Khiển Màn Hình Qua ADB

### Cạm bẫy 1: Cài đặt Developer Options `stay_on_while_plugged_in = 7`
- Khi cắm sạc/USB từ box, Android kích hoạt cờ sạc không tắt màn hình nếu `stay_on_while_plugged_in != 0`.
- **Hậu quả:** Dù đã đặt `screen_off_timeout 600000` (10 phút) hay gọi `svc power stayon false`, bộ đếm thời gian của Android PowerManager **bị đóng băng hoàn toàn**, màn hình không bao giờ tự tắt.
- **Khắc phục:** BẮT BUỘC gán `settings put global stay_on_while_plugged_in 0`.

### Cạm bẫy 2: Lệnh `input keyevent 26` (Nút Nguồn) là Toggle
- `keyevent 26` bật nếu đang tắt, tắt nếu đang bật. Khi máy đang trong trạng thái chuyển tiếp (transition/dozing), gửi 26 có thể vô tình đánh thức màn hình sáng trở lại.
- **Khắc phục:** Dùng lệnh ép ngủ 1 chiều `input keyevent 223` (`KEYCODE_SLEEP`).

### Cạm bẫy 3: Always On Display (AOD) của Samsung
- Trên Samsung S7, tắt màn hình thường chuyển sang chế độ Dozing để hiển thị đồng hồ AOD (`com.samsung.android.app.aodservice`). Màn hình vẫn gửi frame về tool view PC.
- **Khắc phục:** Gán `settings put system aod_mode 0`.

### Cạm bẫy 4: Chuỗi lệnh shell Android bị đứt đoạn
- Tránh dùng dấu `;` ghép lệnh shell ADB vì lỗi một lệnh có thể khiến các lệnh quan trọng phía sau bị bỏ qua.
- Sử dụng `&&` để đảm bảo chuỗi lệnh nguyên tử.

---

## 3. Lệnh Chuẩn Atom Để Tắt Màn Hình & Thiết Lập Timeout 10 Phút

Khi cần đưa toàn bộ hoặc một máy về chế độ tự tắt sau 10 phút:

```bash
adb -s <SERIAL> shell "settings put global stay_on_while_plugged_in 0 && \
svc power stayon false && \
settings put system aod_mode 0 && \
settings put system screen_off_timeout 600000 && \
input keyevent 223"
```

Giải thích các thông số:
1. `stay_on_while_plugged_in 0`: Cho phép tắt màn khi cắm sạc USB.
2. `svc power stayon false`: Ngắt cờ giữ sáng của PowerManager.
3. `aod_mode 0`: Tắt triệt để Always On Display.
4. `screen_off_timeout 600000`: Hẹn giờ đúng 10 phút không tương tác là tự động tắt màn hình (đủ dài để bot/app hoàn tất task mà không lo bị tắt giữa chừng khi lag UI/ADB).
5. `input keyevent 223`: Ép màn hình tắt đen ngay lập tức (`Display Power: state=OFF`).

---

## 4. Tương Thích Với Automation Core & Canary Reproduce
- **Không lo mất hiện trường lỗi:** Khi app crash hoặc dính popup giữ hiện trạng, sau 10 phút màn hình tắt nhưng tiến trình app và trạng thái UI trong RAM **vẫn được bảo lưu 100%**, Android không hề kill app.
- **Tự động thức dậy khi chạy bot / Canary:** Khi script mới chạy hoặc AI chạy canary reproduce, `automation-core` luôn gọi hàm khởi động (`prepare_android_for_automation` / `prepare_device`), trong đó tự động gửi `input keyevent 224` (bật màn) và `wm dismiss-keyguard` (mở khóa) để tiếp tục thao tác bình thường.
