# Bẫy Spoofing Pin (`dumpsys battery set`) vs TikTok Telemetry & Sức Khỏe Phần Cứng Farm

## 1. Bối cảnh
Người vận hành thường có thắc mắc:
*"Có nên random mức pin trước mỗi ca chạy TikTok không? Set pin ảo bằng `dumpsys battery set level <N>` để trông giống người dùng thật, tránh TikTok phát hiện dàn máy cắm sạc 24/7 báo 100% pin."*

## 2. TikTok Telemetry: TikTok có kiểm tra pin không?
**CÓ 100%.**
App TikTok tích hợp các bộ SDK thu thập telemetry và chống gian lận cấp sâu (Bytedance SecSDK, TTNet, BDUdid, AppLog). Các module này đăng ký lắng nghe `Intent.ACTION_BATTERY_CHANGED` và gọi trực tiếp `BatteryManager` của Android để thu thập:
- `EXTRA_LEVEL` (mức pin %)
- `EXTRA_SCALE` (thang đo, thường là 100)
- `EXTRA_STATUS` (1: Unknown, 2: Charging, 3: Discharging, 4: Not charging, 5: Full)
- `EXTRA_PLUGGED` (1: AC charger, 2: USB port, 4: Wireless)
- `EXTRA_VOLTAGE` (điện áp pin đo theo milliVolts - mV)
- `EXTRA_TEMPERATURE` (nhiệt độ pin đo theo 0.1°C)
- `EXTRA_HEALTH` (Good, Overheat, Dead, Over Voltage, Unspecified Failure)

Dữ liệu pin này được mã hóa và gửi định kỳ trong các gói tin `device_register`, `app_log` và session heartbeat về máy chủ Bytedance.

## 3. Tại sao CẤM TUYỆT ĐỐI fake pin bằng `dumpsys battery set`?

### Cạm bẫy 1: Mâu thuẫn cảm biến phần cứng (Sensor & Physics Inconsistency)
- Lệnh `dumpsys battery set level 45` chỉ ghi đè thuộc tính hiển thị `level` trong service Android Framework (`BatteryService`).
- **Nó HOÀN TOÀN KHÔNG thay đổi hoặc đồng bộ các chỉ số vật lý thật của chip quản lý nguồn (PMIC)**:
  * Khi máy đang cắm cáp USB vào PC host/hub, điện áp pin đo được từ phần cứng là mức điện áp sạc: `~4350 mV`.
  * Nếu phần mềm báo `level = 25%`, nhưng `voltage = 4350 mV` và `plugged = 2` (USB): Bytedance SecSDK sẽ phát hiện ngay sự phi logic vật lý (pin 25% không thể có điện áp bão hòa của pin đầy đang sạc).
  * Đây là chữ ký rõ ràng của việc can thiệp phần mềm / giả lập / root tweak / automation hook, khiến tài khoản lập tức bị gắn cờ bot/emulator.

### Cạm bẫy 2: Mù pin thật ➔ Sập nguồn cứng (Hard Power-off Crash) làm hỏng DB
- Các dòng máy farm Samsung Galaxy S7 (Exynos 8890) là thiết bị cũ, tuổi thọ pin cao, nhiều máy bị chai pin hoặc suy hao cell pin nghiêm trọng.
- Khi một máy bị lỏng cáp sạc, sụt áp hub, hoặc chân sạc micro-USB tiếp xúc kém: pin phần cứng thật sẽ bị tụt dốc nhanh chóng (ví dụ máy 47 tụt xuống 2%).
- Nếu hệ thống chạy script random pin lên 60%–80%:
  * Người vận hành và script watchdog hoàn toàn **MÙ** trạng thái pin thật của thiết bị.
  * Khi pin thật cạn về 0%, máy sẽ đột ngột **sập nguồn cứng (hard power-off)** ngay giữa lúc bot đang ghi dữ liệu SQLite của TikTok hoặc Android Framework.
  * Hậu quả: Corrupt dữ liệu, hỏng session đăng nhập, treo boot Samsung, hoặc làm hỏng phân vùng app.

### Cạm bẫy 3: Kích hoạt chế độ Tiết kiệm pin & Pop-up cảnh báo của Samsung
- Nếu thuật toán random vô tình set pin xuống dưới 15%:
  * Android 8 trên Samsung S7 sẽ tự động kích hoạt **Chế độ Tiết kiệm pin (Power Saving Mode)**: hạ xung nhịp CPU, giới hạn background tasks, ngắt kết nối mạng nền khi tắt màn hình.
  * Hệ thống Samsung văng pop-up toàn màn hình cảnh báo *"Pin yếu. Vui lòng kết nối bộ sạc"*, che kín giao diện TikTok. Bot automation không nhận diện được màn hình và bị kẹt phiên (`manual-needed`).

### Cạm bẫy 4: Mâu thuẫn trạng thái USB Data vs Discharging
- Dàn máy farm bắt buộc cắm cáp USB để duy trì kết nối ADB điều khiển tự động.
- Nếu fake `dumpsys battery set status 3` (Discharging - đang rút sạc dùng pin), trong khi kênh truyền USB PHY vẫn liên tục trao đổi dữ liệu với máy tính: SDK dễ dàng bắt được sự bất đối xứng giữa USB controller và BatteryManager.

## 4. Hành vi tự nhiên của người dùng thật (User Baseline)
- Hàng trăm triệu người dùng thật trên toàn cầu có thói quen vừa cắm sạc vừa lướt TikTok (xem video lúc nghỉ ngơi, cắm sạc qua đêm, đặt trên bàn làm việc).
- Việc một thiết bị Android duy trì mức pin 95%–100% kèm trạng thái `Charging` / `Full` là **hành vi hoàn toàn hợp lệ, tự nhiên và phổ biến**.
- TikTok không bao giờ phạt hay đánh dấu tài khoản là bot chỉ vì thiết bị đang cắm sạc!

## 5. Quy tắc vận hành chuẩn cho Taadaa Phone Farm
1. **DUY TRÌ `dumpsys battery reset`**: Luôn giữ trạng thái pin báo đúng theo phần cứng thật. Tuyệt đối không can thiệp lệnh fake pin bằng ADB hay Xposed/LSPosed hook.
2. **GIÁM SÁT PIN THẬT ĐỂ BẢO VỆ PHẦN CỨNG**: Sử dụng công cụ `inspect_machine.py` để theo dõi mức pin thật. Khi phát hiện máy có pin `< 10%` dù đang cắm hub (như M47 ở mức 2%): Operator cần kiểm tra ngay cổng cáp micro-USB hoặc nguồn cấp của box để chống sập nguồn máy.
