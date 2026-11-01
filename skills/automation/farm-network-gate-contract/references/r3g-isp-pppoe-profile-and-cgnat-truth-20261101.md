# Phân Tích Thực Tế 2 Line PPPoE Thái Bình (tamnhb0 vs tamnhb1) & Bản Chất Kỹ Thuật Dải CGNAT

## 1. Hiện Trường Kỹ Thuật Đã Chứng Minh (100% Read-back Từ Flash R3G)
Khi đối soát trực tiếp từ `/etc/config/network` và `network.interface dump` của router Xiaomi R3G qua LuCI / ubus RPC:
- **Line 1 (Cổng giữa `lan1`):**
  - **Tài khoản PPPoE:** `hyn_gftth_tamnhb0` (pass: `N5WU2A`).
  - **Interface:** `wan` (và 7 sub-interfaces `wan_sub11..wan_sub17` qua `mvl11..mvl17`).
  - **IP nhận được từ BRAS Viettel:** `117.5.61.229`, `117.5.62.126`, `117.5.183.211`, `116.107.116.183`, `116.104.210.119`, `116.104.220.235`, `116.104.217.152`, `116.107.112.230`.
  - **PTP Gateway của trạm:** `27.68.227.150`.
  - **Kết luận:** **100% IP Public thật, độc lập hoàn toàn.**
- **Line 2 (Cổng ngoài `lan2`):**
  - **Tài khoản PPPoE:** `hyn_gftth_tamnhb1` (pass: `PWTEM1`).
  - **Interface:** `WAN2` (và 7 sub-interfaces `wan_sub1..wan_sub8` qua `mvl1..mvl8`).
  - **IP nhận được từ BRAS Viettel:** `100.77.27.98`, `100.77.97.108`, `100.77.158.53`, `100.77.51.90`, `100.77.107.177`, `100.77.187.40`, `100.77.77.150`, `100.77.6.239`.
  - **PTP Gateway của trạm:** `100.77.0.2` (Dải `100.64.0.0/10` chuẩn CGNAT Carrier-Grade NAT).

## 2. Bản Chất: Phản Bác Quan Điểm "Tuỳ Vào Lúc Restart"
- **Không có chuyện quay số hên xui lúc restart:**
  Nhà mạng Viettel gán profile đường truyền trực tiếp trên hệ thống trạm OLT / BRAS theo từng Account thuê bao (`hyn_gftth_*`):
  - Hợp đồng `tamnhb0` được gán vào **Pool Non-CGNAT (Public Dynamic Pool)**.
  - Hợp đồng `tamnhb1` bị thợ khi khởi tạo dịch vụ gán nhầm vào **Pool CGNAT (Shared Carrier Pool)**.
- Khi một account đã nằm trong Pool CGNAT của trạm:
  - Dù router có reboot 1.000 lần, ngắt kết nối PPPoE quay số lại bao nhiêu lần đi nữa, trạm BRAS vẫn **100% cấp IP trong dải `100.77.x.x` (Gateway `100.77.0.2`)**, không bao giờ tự động "bốc trúng" IP Public thật.
- AI Agent cấm tuyệt đối lừa dối User bằng lập luận "reconnect vài lần để thử vận may".

## 3. Quy Trình Khắc Phục Duy Nhất Chuẩn Xác (Tầng ISP Provisioning)
1. **Liên hệ nhà mạng Viettel (18008119 hoặc thợ kéo cáp tại trạm Thái Bình):**
   - Đọc chính xác mã đường truyền bị lỗi: **`hyn_gftth_tamnhb1`**.
   - Yêu cầu kỹ thuật: *"Kiểm tra profile đường truyền trên BRAS/OLT, ghim tài khoản này sang Pool IP Public động (bỏ CGNAT / mở NAT camera) giống hệt như đường `hyn_gftth_tamnhb0` kế bên."*
2. **Nghiệm thu sau khi kỹ thuật trạm cập nhật:**
   - Trên router R3G, ngắt kết nối và quay lại `WAN2` (`ifdown WAN2 && ifup WAN2`).
   - Kiểm tra `ip -4 addr show dev pppoe-WAN2`: IP phải đổi sang dải `117.5.x.x` hoặc `116.10x.x.x` (Gateway khác `100.77.0.2`).
   - Khi đó, cả 8 sub-interface `wan_sub1..wan_sub8` sẽ đồng loạt nhận 8 IP Public Viettel độc lập, hoàn tất 16 IP Public toàn router.
