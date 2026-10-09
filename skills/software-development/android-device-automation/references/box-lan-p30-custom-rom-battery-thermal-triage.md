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
Hiện tượng **Follow bị nhả (Silent Drop / Action Restriction)** hầu hết (85-90%) do **quy trình vận hành và kiểm thử**, không phải do ROM Stock Patch:
1. **IP Collision:** Cắm hàng chục máy chung 1 dải IP Wi-Fi nhà mạng hoặc Proxy Datacenter bẩn $\rightarrow$ TikTok kích hoạt chế độ hạn chế ghi trên toàn subnet.
2. **Acc Cold-start / Yếu:** Acc mới login hoặc mới reg chưa qua giai đoạn làm ấm (lướt feed tích lũy consumer telemetry) đã đi follow dồn dập $\rightarrow$ Backend tự rollback follow.
3. **Automation Signature:** ADB click tọa độ tĩnh với `Pressure = 0`, `Size = 0` $\rightarrow$ Định danh bot.
4. **Hở Root / Chưa giấu Bootloader:** Bản patch kernel chưa cài Zygisk / Play Integrity Fix để ẩn cờ Knox `0x1`.

### Quy trình A/B Test cô lập biến số (5 phút)
1. Lấy chính con máy trong Box P30 đó.
2. Tắt Wi-Fi chung farm, phát 4G từ điện thoại cá nhân (IP sạch 100%).
3. Dùng tay thật lướt feed 2-3 video, bấm follow 1 kênh lớn.
4. Kiểm tra lại sau 5 phút:
   - **Vẫn giữ follow:** $\rightarrow$ ROM và Box vô tội; thủ phạm là Proxy/IP bẩn hoặc do script click thô.
   - **Bị nhả:** $\rightarrow$ Do độ trust của acc quá thấp, hoặc ROM bị hở Root làm rớt Play Integrity.

---

## 6. Giải pháp khuyến nghị cho Farm Production
- **Ưu tiên phần cứng:** Nếu muốn dùng ROM gốc 100% không patch, hàn 1 con điện trở **$10\text{k}\Omega$ hoặc $47\text{k}\Omega$ NTC** từ chân `TH` sang `GND` trên socket nguồn giả Box P30.
- **Nếu dùng Box USB chập chờn:** Thay vì vội vã chuyển sang Box LAN đổi lấy rủi ro chết dàn acc TikTok, hãy nâng cấp Hub USB công nghiệp có cấp nguồn rời (5V 2A-3A/port) và thay dàn cáp chất lượng cao để triệt tiêu 90% lỗi rớt kết nối.
