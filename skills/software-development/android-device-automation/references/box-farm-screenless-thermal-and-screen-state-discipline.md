# Box Farm Screenless (Mainboard-Only) Thermal & Screen State Discipline

## 1. Bản chất phần cứng Box Farm (Samsung S7 / SM-G930)
- Thiết bị chạy trong box farm thực chất chỉ gồm **bo mạch chủ (mainboard / PCB)** cắm cụm trong khung chassis, hoàn toàn **không có tấm nền màn hình vật lý (AMOLED/LCD)**.
- Mọi hình ảnh quan sát được trên PC thực chất là luồng stream ảo (Scrcpy, Total Control, hoặc mirroring tool qua ADB).
- Vì không có màn hình thật, thiết bị không lo cháy bóng (burn-in) hay hư đèn nền.

## 2. PC View / Screen Mirroring vs Tải Phần Cứng
- **Tác hại của việc bật PC View liên tục khi chạy batch:**
  - Để PC hiển thị màn hình, chip Exynos 8890 trên mainboard phải liên tục kích hoạt bộ giải/mã hóa video phần cứng (VPU) và render SurfaceFlinger ở tốc độ cao rồi đẩy qua bus USB.
  - Khiến nhiệt độ SoC tăng thêm **3°C – 7°C**. Với môi trường box farm kín khí chứa 20–40 main san sát nhau, nhiệt độ cao là nguyên nhân hàng đầu gây:
    1. Hở chân chip BGA (rụng RAM/CPU).
    2. Chai hoặc cháy IC nguồn (PMIC).
    3. Suy hao tuổi thọ chip nhớ flash eMMC/UFS.
  - Gây nghẽn băng thông bus USB controller của PC điều khiển.
- **Quy tắc:** Chỉ mở view PC khi cần debug máy đơn lẻ. Khi bot/cron chạy batch tự động, **BẮT BUỘC tắt toàn bộ cửa sổ view màn hình**.

## 3. Quản lý trạng thái màn hình: Idle vs Active Automation
- **Khi máy NGHỈ (Idle / Chờ cron / Giữa các ca):**
  - **NÊN để màn hình tắt (Display Sleep / Asleep):** GPU và SurfaceFlinger dừng vẽ khung hình 60 FPS $\rightarrow$ GPU nghỉ hoàn toàn, CPU hạ xung nhịp (DVFS frequency scaling), giảm tải nhiệt và hao mòn linh kiện.
- **Khi máy ĐANG CHẠY BOT (Active Automation):**
  - Cần màn hình ở trạng thái sáng (`screen_on=True`) để UIAutomator dump XML không bị đen, không bị timeout và các lệnh `input tap` ăn khớp với app foreground.
  - **Không cần lo lắng về việc máy đang tắt màn:** Trong `automation-core` (`startup.py` và `device.py`), mọi kịch bản trước khi thao tác đều tự động kích hoạt chuỗi preflight:
    1. Kiểm tra trạng thái nguồn qua `dumpsys power` (`_read_wake_unlock_state`).
    2. Nếu `screen_on is False`: Gửi `keyevent 224` (`KEYCODE_WAKEUP`) + `keyevent 82` (`KEYCODE_MENU`) để đánh thức.
    3. Tự động giải phóng Keyguard (`wm dismiss-keyguard` và swipe mở khóa).
    4. Nạp cấu hình giữ màn hình sáng xuyên suốt phiên (`configure_stay_on`):
       - `svc power stayon true`
       - `settings put global stay_on_while_plugged_in 7`
       - `settings put system screen_off_timeout 1800000`
       - `settings put secure lockscreen.disabled 1`

## 4. Đối soát 100% Kịch Bản Farm Hiện Hữu (7/7 Repos)
Toàn bộ 7 repo cốt lõi trên farm đã được kiểm tra và xác nhận 100% tuân thủ hợp đồng Preflight của `automation-core`:
1. `register gmail` (`gmail_reg_v10.py`): gọi `prepare_android_for_automation` (wake + unlock) và `require_android_vpn`.
2. `tiktok-follow` (`run_follow.py` / `adapter.py`): gọi `prepare_android_for_automation` + `prepare_device` và `require_android_vpn`.
3. `tiktok-luot nuoi acc` (`run_tiktok.py`): gọi `prepare_device(wake=True, swipe_unlock=True)` và `require_android_vpn`.
4. `Tiktok-video` (`tiktok_workflow/state_machine.py`): gọi `prepare_android_for_automation` và `require_android_vpn`.
5. `Tiktok_Reg` (`tiktok_reg_live_email_v1.py` / `social_reg_v1.py`): gọi `prepare_android_for_automation` và `require_android_vpn`.
6. `tiktok-add-bao-mat-f2a` (`run_batch_live_2fa.py`): gọi `prepare_device(wake=True, swipe_unlock=True)` và `require_android_vpn`.
7. `tiktok-log-in` (`live_adapter.py`): gọi `prepare_device(wake=True, swipe_unlock=True)` và `require_android_vpn`.

## 5. Cạm Bẫy Android & Quy Chuẩn Tắt Màn Hình / Đặt Timeout 10 Phút (2026-09-13)

### Cạm bẫy 1: Cài đặt Developer Options `stay_on_while_plugged_in = 7`
- Khi cắm nguồn sạc/USB từ box, Android kích hoạt cờ sạc không tắt màn hình nếu `stay_on_while_plugged_in != 0`.
- **Hậu quả:** Dù đã đặt `screen_off_timeout 600000` (10 phút) hay gọi `svc power stayon false`, bộ đếm thời gian của Android PowerManager **bị đóng băng hoàn toàn**, màn hình không bao giờ tự tắt.
- **Khắc phục:** BẮT BUỘC gán `settings put global stay_on_while_plugged_in 0`.

### Cạm bẫy 2: Lệnh `input keyevent 26` (Nút Nguồn) là Toggle
- `keyevent 26` bật nếu đang tắt, tắt nếu đang bật. Khi máy đang trong trạng thái chuyển tiếp (transition/dozing), gửi 26 có thể vô tình đánh thức màn hình sáng trở lại.
- **Khắc phục:** Dùng lệnh ép ngủ 1 chiều `input keyevent 223` (`KEYCODE_SLEEP`).

### Cạm bẫy 3: Always On Display (AOD) của Samsung
- Trên Samsung S7, tắt màn hình thường chuyển sang chế độ Dozing để hiển thị đồng hồ AOD (`com.samsung.android.app.aodservice`). Màn hình vẫn gửi frame về tool view PC.
- **Khắc phục:** Gán `settings put system aod_mode 0`.

### Cạm bẫy 4: Chuỗi lệnh shell Android bị đứt đoạn
- Tránh dùng dấu `;` ghép lệnh shell ADB vì lỗi một lệnh có thể khiến các lệnh quan trọng phía sau bị bỏ qua. Sử dụng `&&` để đảm bảo chuỗi lệnh nguyên tử.

### Lệnh Chuẩn Atom Để Tắt Màn Hình & Thiết Lập Timeout 10 Phút:
```bash
adb -s <SERIAL> shell "settings put global stay_on_while_plugged_in 0 && \
svc power stayon false && \
settings put system aod_mode 0 && \
settings put system screen_off_timeout 600000 && \
input keyevent 223"
```
- **Không lo mất hiện trường lỗi:** Khi app crash hoặc dính popup giữ hiện trạng, sau 10 phút màn hình tắt nhưng tiến trình app và trạng thái UI trong RAM **vẫn được bảo lưu 100%**, Android không hề kill app.
- **Tự động thức dậy khi chạy Canary:** Khi script mới chạy hoặc AI chạy canary reproduce, `automation-core` luôn tự động gửi `input keyevent 224` (bật màn) và `wm dismiss-keyguard` (mở khóa) để tiếp tục thao tác bình thường.
