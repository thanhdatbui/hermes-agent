# Box LAN (P30), Custom ROMs (LineageOS vs Stock Patch), Battery Thermal Warning & TikTok Anti-Fraud

## 1. Bối cảnh & Hiện tượng
Khi mở rộng hoặc chuyển đổi hạ tầng Farm điện thoại (Samsung Galaxy S7, Note 8, J7...) từ Box USB sang Box LAN (P20, P30, P40 tháo pin):
- **Hiện tượng 1:** ROM gốc khi cắm vào Box P30 tháo pin liên tục hiện popup cảnh báo hệ thống: *"Nhiệt độ pin quá thấp. Không thể sạc pin"* / *"Battery temperature too low"*.
- **Hiện tượng 2:** Một số vendor cung cấp ROM Mod LineageOS (AOSP Android 8) hỗ trợ cắm dây LAN trực tiếp và mở sẵn port ADB 5555. Nhưng khi đem nuôi TikTok thì tài khoản bị gắn cờ, 0 view, hoặc đi follow bị nhả hàng loạt (Action Block ngầm).
- **Hiện tượng 3:** Dùng ROM Stock Patch Kernel bỏ pin (chỉ Wi-Fi) cắm Box P30 nhưng khi đi follow vẫn bị nhả.

---

## 2. Bản chất kỹ thuật: Cảnh báo "Nhiệt độ pin quá thấp" trên Samsung

### A. Cơ chế phần cứng (Hardware Thermistor NTC)
- Chân socket pin Samsung gồm: `VBAT` (+), `GND` (-), `BATT_TEMP / TH` (chân cảm biến nhiệt độ), và `BATT_ID`.
- Trong ruột cell pin zin Samsung có một điện trở nhiệt nghịch **NTC (Negative Temperature Coefficient)** nối giữa `BATT_TEMP` và `GND` (ở $25^\circ\text{C}$ tiêu chuẩn, trở kháng thường là $10\text{k}\Omega$ hoặc $47\text{k}\Omega$).
- Khi tháo pin cắm vào Box P30, các vỉ mạch nguồn giả làm ẩu chỉ câu 2 cực `VBAT` và `GND`, để hở chân `BATT_TEMP` (Open Circuit $\rightarrow R = \infty$).

### B. Phản ứng dây chuyền ở Kernel & OS
1. Bộ chuyển đổi ADC của chip quản lý nguồn (PMIC / Fuel Gauge IC) đo $R = \infty$ và tính toán ra nhiệt độ cực âm ($-20^\circ\text{C}$ đến $-40^\circ\text{C}$).
2. Kernel kích hoạt cơ chế bảo vệ phần cứng khẩn cấp (tránh nổ tinh thể Lithium khi sạc âm độ): bắn tín hiệu `uevent` lên Android Framework, liên tục ném Dialog `SYSTEM_ALERT` lên UI.
3. **Thermal Throttling:** Daemon quản lý nhiệt (`sec-thermal`) bóp xung nhịp CPU xuống mức đáy (Lowest Frequency, ~300MHz) $\rightarrow$ Máy giật lag nghiêm trọng.
4. **Thermal Shutdown:** Nếu cảnh báo kéo dài, PMIC sẽ kích hoạt ngắt nguồn cưỡng chế (Trip Shutdown).

### C. CẠM BẪY TỰ SÁT: "Dùng Script ADB/Python bấm tắt popup"
- **Tuyệt đối không dùng script bắt popup dập đi**:
  - Popup chiếm quyền Window Focus liên tục $\rightarrow$ Cướp tương tác của TikTok/Accessibility $\rightarrow$ Vỡ luồng automation 100%.
  - Script không thể giải quyết được việc CPU bị bóp xung về 300MHz và nguy cơ máy tự tắt nguồn.
  - **Quy tắc:** Lỗi phần cứng/Kernel bắt buộc phải sửa ở tầng Phần cứng hoặc Kernel.

---

## 3. So sánh 2 loại ROM Box Farm trên thị trường

| Tiêu chí | Loại 1: ROM Stock Patch Kernel (Chỉ Wi-Fi) | Loại 2: ROM LineageOS / AOSP (Hỗ trợ LAN) |
| :--- | :--- | :--- |
| **Bản chất** | ROM gốc Samsung, dev bung `boot.img` sửa driver `samsung-battery.c` (hardcode `temp = 250` tức 25°C, pin 100%). | ROM AOSP mã nguồn mở, kernel thoáng không check NTC, build sẵn driver USB-to-Ethernet (RTL8152) và mở sẵn port ADB 5555. |
| **Mạng** | Bắt buộc dùng **Wi-Fi** (hoặc proxy qua Wi-Fi). | Nhận trực tiếp dây mạng **LAN RJ45** từ Box qua giao tiếp USB-to-Ethernet. |
| **Điểm Trust TikTok** | **CỰC KỲ CAO (Sạch).** Giữ nguyên Samsung Framework (`com.samsung.android.*`), TouchWiz, Knox signature. | **CỰC KỲ THẤP (Dễ chết).** Lộ AOSP, `test-keys`, rớt Play Integrity, lộ card mạng dây `TRANSPORT_ETHERNET` (`eth0`). |
| **Phù hợp** | Nuôi acc TikTok, Shopee, Gmail chất lượng cao. | Cày view, cày node, app nhẹ không quét sâu native security. |

---

## 4. Tại sao LineageOS / Box LAN bị TikTok trảm? (Anti-Fraud Vectors)
TikTok SDK (bộ native C/C++ `libmetasec_ml.so`, `bd_protector`) quét cực sâu vào hệ thống:
1. **Lộ `TRANSPORT_ETHERNET`:** Smartphone người dùng bình thường dùng `TRANSPORT_WIFI` hoặc `TRANSPORT_CELLULAR`. Việc traffic đi qua `eth0` không có sóng di động/Wi-Fi là cờ hiệu bất thường cấp 1.
2. **Framework Mismatch:** Khai báo model Samsung `SM-G930F` trong `build.prop` nhưng Runtime không có các service độc quyền của Samsung $\rightarrow$ Định danh là máy mod / giả lập.
3. **Mất Play Integrity:** Unlock bootloader khiến Knox nhảy `0x1`, rớt `MEETS_BASIC_INTEGRITY`.
4. **Sensor & Pin phẳng lì:** Gia tốc kế bất động $[0,0,9.8]$ không có vi rung (micro-jitter) của tay người cầm; pin cứng ngắc 100% không chu kỳ sạc xả.

---

## 5. Triage: Tại sao dùng ROM Stock Patch Battery đi Follow vẫn bị nhả?
Hiện tượng **Follow bị nhả (Silent Drop / Action Restriction)** hầu hết (85-90%) do **quy trình vận hành và kiểm thử**, nhưng cũng có phần do **bản chất ROM Patch**:

### A. Hai hệ quy chiếu thẩm định (Tránh ngộ nhận)
- **Hệ quy chiếu 1 (So sánh tương đối giữa các loại ROM Farm):** ROM Stock Patch Kernel là lựa chọn "đỡ tệ nhất" so với LineageOS/AOSP vì giữ được Framework Samsung (`com.samsung.android.*`) và không lộ interface mạng dây `TRANSPORT_ETHERNET` (`eth0`).
- **Hệ quy chiếu 2 (So sánh tuyệt đối với TikTok Anti-Fraud & Máy thật):** ROM Stock Patch vẫn là firmware đã bị mổ xẻ (Tampered):
  - Unlock Bootloader $\rightarrow$ Knox nhảy `0x1`, mất Hardware Keystore Attestation.
  - Tắt `dm-verity` để flash kernel mod.
  - **Tử huyệt Nhiệt động học (Battery Telemetry):** Dev gán cứng `temp = 250` (25.0°C) và `capacity = 100%` vĩnh viễn. TikTok SDK lấy mẫu chu kỳ thấy CPU gánh tải cao cày video liên tục 24/7 mà nhiệt độ phẳng lì không dao động $0.1^\circ\text{C}$ $\rightarrow$ Vi phạm định luật vật lý, bị gắn cờ máy farm ngay lập tức.

### B. 4 nguyên nhân quy trình vận hành phổ biến:
1. **IP Collision:** Cắm hàng chục máy chung 1 dải IP Wi-Fi nhà mạng hoặc Proxy Datacenter bẩn $\rightarrow$ TikTok kích hoạt chế độ hạn chế ghi trên toàn subnet.
2. **Acc Cold-start / Yếu:** Acc mới login hoặc mới reg chưa qua giai đoạn làm ấm (lướt feed tích lũy consumer telemetry) đã đi follow dồn dập $\rightarrow$ Backend tự rollback follow.
3. **Automation Signature:** ADB click tọa độ tĩnh với `Pressure = 0`, `Size = 0` $\rightarrow$ Định danh bot.
4. **Hở Root / Chưa giấu Bootloader:** Bản patch kernel chưa cài Zygisk / Play Integrity Fix để ẩn cờ Knox `0x1`.

---

## 6. Cạm bẫy "ROM Auto ADB" (Tưởng tiện nhưng là bẫy ban acc)

### A. Bản chất kỹ thuật của "ROM Auto ADB"
- Để flash ROM xong tự nhận ADB mà không cần chạm tay vào màn hình bấm popup RSA *"Cho phép gỡ lỗi USB từ máy tính này"*:
  - Dev can thiệp vào `default.prop` trong `boot.img` hoặc `init.rc`.
  - Set cờ tử thần: **`ro.adb.secure=0`** (vô hiệu hóa hoàn toàn xác thực khóa RSA) và `persist.service.adb.enable=1`.
- **Hệ lụy bảo mật:**
  - Thiết bị thương mại của người dùng thật (`user build`) bắt buộc **100% phải có `ro.adb.secure=1`**. Cờ `ro.adb.secure=0` chỉ có trên bản `eng`/`userdebug` của kỹ sư nội bộ hoặc ROM bị hack.
  - Google Play Integrity API đọc cờ này và lập tức đánh rớt `MEETS_DEVICE_INTEGRITY = false`.
  - TikTok SDK (Metasec) và các app bảo mật quét thấy `ro.adb.secure=0` sẽ lập tức liệt thiết bị vào diện môi trường kiểm thử/hack, tụt điểm Trust Score về đáy.

### B. Thực tế trên ROM Stock nguyên bản: KHÔNG CẦN ROM AUTO ADB
- Trên ROM gốc Samsung, chỉ cần thao tác thủ công đúng **1 LẦN DUY NHẤT**:
  1. Bật *Tùy chọn nhà phát triển $\rightarrow$ Gỡ lỗi USB*.
  2. Cắm cáp vào PC, popup RSA hiện lên: Tích chọn **"Luôn cho phép từ máy tính này" (Always allow from this computer)** $\rightarrow$ Bấm OK.
  3. Host PC public key sẽ được lưu vĩnh viễn vào `/data/misc/adb/adb_keys`.
- **Sau đó khởi động lại máy 1.000 lần thì kết nối ADB vẫn tự động nhận ngay lập tức mà không bao giờ hỏi lại.**
- *Quy tắc:* Tuyệt đối không vì lười thao tác 30 giây lúc setup ban đầu mà cài ROM Auto ADB (`ro.adb.secure=0`), đánh mất hoàn toàn tính toàn vẹn thiết bị.

---

## 7. Giải pháp khuyến nghị cho Farm Production
- **Ưu tiên phần cứng:** Nếu muốn dùng ROM gốc 100% không patch, hàn 1 con điện trở **$10\text{k}\Omega$ hoặc $47\text{k}\Omega$ NTC** từ chân `TH` sang `GND` trên socket nguồn giả Box P30.
- **Nếu dùng Box USB chập chờn:** Thay vì vội vã chuyển sang Box LAN đổi lấy rủi ro chết dàn acc TikTok, hãy nâng cấp Hub USB công nghiệp có cấp nguồn rời (5V 2A-3A/port) và thay dàn cáp chất lượng cao để triệt tiêu 90% lỗi rớt kết nối.
