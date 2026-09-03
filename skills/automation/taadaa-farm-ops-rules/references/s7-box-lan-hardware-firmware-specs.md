# Box LAN Samsung S7 (Android 8) Technical Specifications & Acceptance Standards

Tài liệu tham chiếu chuẩn hóa phần cứng, firmware, cấu hình mạng và quy trình nghiệm thu (ISO 2859-1:1999) cho Box LAN Samsung S7 (Exynos/Snapdragon).

## 1. Phần cứng & Cấp nguồn
- **Điện áp tại Socket Pin:** 4.10V ± 0.05V tĩnh (dải tải 4.00V - 4.20V DC), sụt áp dây <= 0.10V @ 3A.
- **Bảo vệ:** OVP ngắt tại 4.35V ± 0.05V (không vượt quá 4.40V tuyệt đối của PMIC S2MPS15 / PM8996), OCP ngắt tại 4.0A - 4.5A.
- **Cách ly VBUS USB-OTG:** IC Load Switch (RT9742 / TPS22918) có True Reverse Current Blocking, chống dòng back-feed vào mainboard S7.
- **Mạch giả lập Pin (NTC):** Điện trở nhiệt NTC chuẩn 10kΩ B=3950K tại 25°C nối chân `BATT_TEMP` xuống `GND`, kết hợp điện trở nhận diện `BATT_ID`. Giữ nguyên cơ chế Hardware Thermal Shutdown của PMIC/SoC.

## 2. Firmware, SELinux & ADB
- **ROM Base:** Custom Vendor ROM trên nền Stock Samsung Android 8.0 Oreo (`user`, `release-keys`, `ro.debuggable=0`, `ro.secure=1`).
- **SELinux:** Bắt buộc `Enforcing`. Zero fatal AVC denials trong 1h chạy tải thực tế.
- **ADB over TCP/IP:** Tự động mở cổng 5555 qua init trigger, `ro.adb.secure=1` với RSA key pre-provisioned.
- **Tường lửa cục bộ:** Chặn cổng 5555 trên Wi-Fi và IPv6 (`iptables -I INPUT 1 -i wlan+ -p tcp --dport 5555 -j DROP`).

## 3. Phân luồng mạng kép (Dual Interface)
- **Ethernet (`eth0` / `enx*`):** Chỉ chạy traffic nội bộ (ADB / ATX agent), không đặt default gateway và không cấp DNS.
- **Wi-Fi (`wlan0`):** Giữ vai trò Default Gateway cho 100% traffic Internet, Proxy và DNS.

## 4. Nghiệm thu ISO 2859-1:1999 (General Inspection Level II, Single Sampling)
- **Sàng lọc 100%:** Đo điện áp socket pin (4.05 - 4.15V), `dumpsys battery` nhiệt độ trong dải 200..350, `getenforce=Enforcing`, MAC/Serial độc nhất.
- **Lấy mẫu Stress Test 24h & Power-cycle 10 chu kỳ:**
  - Lot 51-90 (Code E, n=13): Major AQL 1.0 (Ac=0, Re=1), Minor AQL 4.0 (Ac=1, Re=2).
  - Lot 91-150 (Code F, n=20): Major AQL 1.0 (Ac=0, Re=1), Minor AQL 4.0 (Ac=2, Re=3).
