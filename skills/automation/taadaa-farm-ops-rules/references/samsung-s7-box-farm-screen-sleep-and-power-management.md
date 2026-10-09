# Samsung S7 Box Farm Screen Sleep & Power Management Reference

## Bối cảnh phần cứng
- Máy box farm Samsung Galaxy S7 (Exynos 8890) không gắn màn hình thật, chỉ có mainboard cắm trong box.
- View màn hình trên PC qua USB thông qua các tool mirror (như Xiaowei, Scrcpy, Anlink).
- Khi chạy tự động, việc mở stream màn hình trên PC bắt chip SoC/GPU trên mainboard S7 phải nén H.264/H.265 liên tục, làm tăng nhiệt độ thêm 3°C - 7°C, gây nguy cơ rụng chân chip BGA, hỏng IC nguồn (PMIC) và suy hao chip nhớ eMMC/UFS.
- Khi máy rảnh (idle), cần tắt màn hình và đưa về trạng thái ngủ (`Asleep`, `Display Power: state=OFF`) để SoC/GPU hạ xung, nghỉ hoàn toàn.

## Cạm bẫy khi tắt màn hình Samsung S7 qua ADB

### 1. `input keyevent 26` (KEYCODE_POWER) là lệnh TOGGLE
- Nếu máy đang ở trạng thái ngủ lơ lửng, Dozing, hoặc màn hình vừa bị đánh thức bởi background service/network event, việc gọi `keyevent 26` sẽ **bật màn hình trở lại** thay vì tắt.
- **Giải pháp chuẩn xác:** Dùng `input keyevent 223` (`KEYCODE_SLEEP`). Đây là lệnh cưỡng bức ngủ 1 chiều của Android: nếu đang bật thì tắt ngay, nếu đang ngủ thì giữ nguyên.

### 2. Dịch vụ Always On Display (AOD) của Samsung
- Trên Samsung S7, khi màn hình tắt, hệ thống mặc định kích hoạt dịch vụ `com.samsung.android.app.aodservice` (DozeService) hiển thị đồng hồ AOD.
- Dù màn hình vật lý không có, tool PC view (như Xiaowei) vẫn bắt khung hình AOD làm người vận hành thấy màn hình không tắt, và GPU vẫn phải vẽ khung hình Dozing.
- **Giải pháp:** Phải tắt AOD bằng `settings put system aod_mode 0`.

### 3. Cấu hình Stay-On cắm sạc
- `automation-core` khi chuẩn bị máy chạy task thường thiết lập `svc power stayon true`, `stay_on_while_plugged_in 7` và `screen_off_timeout 1800000` (30 phút).
- Khi muốn tắt màn hình và đưa về chế độ nghỉ, bắt buộc phải hoàn tác các cài đặt này.

## Quy trình chuẩn hạ nhiệt và tắt màn hình toàn farm

```bash
# 1. Tắt dịch vụ giữ sáng USB
svc power stayon false
settings put global stay_on_while_plugged_in 0

# 2. Tắt Always On Display (AOD)
settings put system aod_mode 0

# 3. Rút ngắn thời gian tự tắt màn hình về 15s
settings put system screen_off_timeout 15000

# 4. Ép tắt màn hình 1 chiều bằng KEYCODE_SLEEP
input keyevent 223
```

## Kiểm tra trạng thái thành công
```bash
adb shell "dumpsys power | grep -E 'Display Power:|mWakefulness='"
# Kỳ vọng:
# mWakefulness=Asleep (hoặc Dozing mà Display Power=OFF)
# Display Power: state=OFF
```
