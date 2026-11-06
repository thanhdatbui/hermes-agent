# Bài Học Thực Chiến: Lỗ Hổng 21.5GB Forward Direct & Chặn Đứng Tại RAW Prerouting (2026-11-06)

## 1. Hiện Trường Sự Cố & Vạch Trần Lỗ Hổng 21.5GB Trên MikroTik
Trong quá trình vận hành, App TikTok trên các máy S7 vẫn tiếp tục load video khi proxy nội bộ (cổng 20204 / MobiProxy / R3G) bị chết hoặc nghẽn timeout.
Kiểm tra chi tiết qua MikroTik REST API (`192.168.110.2:9090`) phát hiện:
1. **Lỗ hổng Filter rule `*10` (`ALLOW_FARM_ADMIN_FORWARD_FPT_LAN`):**
   - Đang cấu hình `chain=forward action=accept src-address-list=FPT_LAN` nhưng **`dst-port=None`** (không giới hạn port).
   - Vì danh sách `FPT_LAN` bao gồm cả dải `192.168.110.0/24`, rule này đã cho phép điện thoại bypass proxy và forward direct ra ngoài tới **21.5 GB / 360 triệu packets**!
2. **Rule Killswitch QUIC bị vô hiệu hóa:**
   - Rule `*9` (`KILLSWITCH_FARM_QUIC_UDP`) trong Filter FORWARD đang ở trạng thái `disabled=true`.
3. **Mangle gán `routing-mark` ra WAN:**
   - Các rule Mangle cũ gán nhãn `WAN8..WAN35` cho từng máy. Khi có rule accept rộng hoặc fasttrack, traffic direct bay thẳng ra các line WAN cáp quang Viettel gốc.

## 2. Thẩm Định Của Hội Đồng Cố Vấn (Claude CLI & Gemini Web Argon)
- **Vị trí chốt chặn tối thượng:** Đặt tại **`/ip firewall raw` (chain=prerouting)**.
  - RAW Prerouting nằm ở tầng đầu tiên của RouterOS Packet Flow, chạy **trước** Connection Tracking, Mangle, FastTrack và Routing Decision.
  - Chặn tại RAW là stateless, triệt tiêu ngay lập tức gói tin bypass (UDP 443 QUIC) trước khi Mangle kịp gán cờ `routing-mark` hay đẩy ra WAN.
- **Nguyên tắc Filter FORWARD:** Bắt buộc duy trì **Default-Deny** cho mọi lưu lượng direct ra WAN từ dải Farm.

## 3. Quy Chuẩn Cấu Hình RouterOS Khóa Cứng Fail-Closed 100%

### Bước 1: Vô hiệu hóa lỗ hổng forward direct
Vô hiệu hóa hoặc xóa bỏ rule accept forward không giới hạn port:
```routeros
/ip firewall filter disable [find comment~"ALLOW_FARM_ADMIN_FORWARD_FPT_LAN"]
```
Chỉ cho phép `FPT_LAN` đi qua các port proxy hợp lệ:
```routeros
/ip firewall filter add chain=forward action=accept src-address-list=FPT_LAN protocol=tcp dst-port=10001-10035,20001-20280 comment="ALLOW_FPT_LAN_PROXY_PORTS"
```

### Bước 2: Bật lại Drop QUIC UDP 443 ở Filter FORWARD
```routeros
/ip firewall filter set [find comment~"KILLSWITCH.*QUIC"] disabled=no src-address=192.168.0.0/16 out-interface-list=WAN action=drop
```

### Bước 3: Nạp chốt chặn Stateless tại RAW Prerouting (Bắt buộc)
```routeros
/ip firewall raw add chain=prerouting src-address=192.168.0.0/16 protocol=udp dst-port=443 action=drop comment="RAW_KILLSWITCH_DROP_QUIC_UDP443"
```

## 4. Kiểm Chứng Thực Tế Tầng Socket (Khi Màn Hình Tắt / AOD)
- Trên các máy Samsung S7, khi màn hình tắt hoặc chạy Always-On Display (`aodservice`), lệnh `screencap` của ADB bốc framebuffer trả về ảnh đen (RGB=0).
- Tuân thủ Invariant Visual Gate 6: CẤM gửi ảnh đen đối phó.
- **Bằng chứng kiểm chứng thay thế chuẩn mực:** Kiểm tra bảng socket kernel của Android:
  - `cat /proc/net/tcp6`: Socket tới proxy nội bộ kẹt ở trạng thái `SYN_SENT` (state `02`), hoàn toàn không có socket `ESTABLISHED` (state `01`) ra ngoài.
  - `cat /proc/net/udp` / `udp6`: Không có socket UDP 443 hoạt động.
  - Kiểm tra counter trên MikroTik: Rule drop tăng packet, traffic direct bị triệt tiêu hoàn toàn.
