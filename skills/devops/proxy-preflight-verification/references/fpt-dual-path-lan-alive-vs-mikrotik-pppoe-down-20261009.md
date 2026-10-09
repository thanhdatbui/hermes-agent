# FPT Dual-Path Architecture: Mạng LAN Gia Đình Hoạt Động Bình Thường Nhưng MikroTik PPPoE Bị Ngắt (RX-Zero)

> **Mốc thời gian:** 2026-10-09  
> **Ngữ cảnh:** Operator thắc mắc gay gắt: *"ủa mạng LAN đang xài cục FPT đó bth mà?"* khi Coordinator báo modem FPT bị ngắt kết nối với MikroTik khiến runner upload avatar fail-closed tại preflight (`[PREFLIGHT_VPN_BLOCKED]`).

---

## 1. Bản Chất Kiến Trúc 2 Tuyến Độc Lập Trên Cùng 1 Modem FPT (Dual-Path Split)

Hạ tầng mạng farm Kibe chia sẻ cùng một thiết bị đầu cuối của nhà mạng FPT (Modem GPON / Converter như AC1000Z, G-97RG6M) nhưng vận hành theo **2 luồng vật lý và logic hoàn toàn tách biệt**:

```
                 ┌────────────────────────────────────────────────────────┐
                 │                 FPT Fiber Line (GPON)                  │
                 └───────────────────────────┬────────────────────────────┘
                                             │
                                   ┌─────────▼─────────┐
                                   │  Modem FPT GPON   │
                                   └────┬────────────┬─┘
                 Route Mode (NAT/DHCP)  │            │  Bridge Mode / PPPoE Relay
             (Cổng LAN 1 / LAN 2)       │            │  (Cổng LAN 4 / LAN 3)
                                        │            │
                           ┌────────────▼──┐     ┌───▼─────────────────────┐
                           │ Ruijie Router │     │  MikroTik x86 Router    │
                           │ 192.168.110.1 │     │ (192.168.110.2 / WAN1)  │
                           └───────┬───────┘     └───────────┬─────────────┘
                                   │                         │
                         ┌─────────▼────────┐      ┌─────────▼─────────────┐
                         │ LAN Gia Đình/PC  │      │ 60x PPPoE Multi-WAN   │
                         │ IP: 1.55.80.51   │      │ Sing-box (20001-20080)│
                         │ (SỐNG 100%)      │      │ (MẤT ROUTE / TIMEOUT) │
                         └──────────────────┘      └───────────────────────┘
```

### Luồng 1: Mạng Gia Đình & Kibe PC (Đang sống 100%)
* Modem FPT tự quay số 1 phiên PPPoE nội bộ, chạy chế độ **Route Mode (NAT)**.
* Cấp mạng trực tiếp cho router Ruijie `192.168.110.1`, phát Wi-Fi gia đình và cấp IP cho Kibe PC `192.168.110.123`.
* Người dùng lướt web, Telegram, YouTube bình thường qua IP Public của nhà mạng (`1.55.80.51`).

### Luồng 2: Cụm MikroTik Farm 60 Line (Đang bị ngắt kết nối)
* Cáp mạng nối từ modem FPT sang cổng `WAN1` (ether1) và `WAN4` (ether4) của router MikroTik `192.168.110.2`.
* Tuyến này **KHÔNG sử dụng chung mạng gia đình**, mà dùng cơ chế `macvlan1..60` để **quay số 60 phiên PPPoE độc lập** (`d511_gftth_khoind5`) lấy dải IP động phục vụ farm.

---

## 2. Tại Sao Mạng Nhà Vẫn Dùng Được Mà MikroTik Lại Bị RX = 0?

Khi người dùng thắc mắc: *"Mạng LAN đang xài bình thường mà kiểm tra lại coi"*, nguyên nhân kỹ thuật phân tích được qua `/tool/sniffer` và `/interface/ethernet`:

1. **Cắm lệch cổng LAN trên modem FPT:**
   * Kỹ thuật FPT chỉ mở **Bridge Mode / PPPoE Passthrough trên đúng 1 cổng LAN cố định** (thường là LAN 4 hoặc LAN 3).
   * Các cổng LAN còn lại bị cô lập, chỉ cấp mạng NAT gia đình và **chặn sạch 100% các gói tin PADI/LCP** của giao thức PPPoE.
   * Nếu sợi cáp từ MikroTik `WAN1` bị cắm sang cổng LAN thường: Tầng vật lý PHY vẫn nhận link (`status: link-ok, rate: 1Gbps`), MikroTik liên tục bắn gói tìm server (`TX = 2.800 bytes`), nhưng modem FPT drop sạch không trả lời (`RX = 0 bytes`).
2. **Modem FPT bị tắt Bridge Mode sau khi khởi động lại / TR-069 push config:**
   * Khi modem FPT tự reboot hoặc đài trạm FPT tự động nạp lại cấu hình mặc định (qua TR-069 ACS), tính năng cho phép thiết bị phụ quay PPPoE (PPPoE Passthrough) bị tắt.
   * Hậu quả: Mạng gia đình vẫn chạy vèo vèo, nhưng toàn bộ 60 phiên PPPoE trên MikroTik bị văng lỗi `LCP lowerdown` và không thể kết nối.

---

## 3. Hiệu Ứng Domino Lên Singbox Container & Fail-Closed Preflight

1. **MikroTik Mất Default Route:**
   * Mọi route `0.0.0.0/0` trên MikroTik đều gắn với các gateway `pppoe-out1..60` trong từng bảng định tuyến `WAN1..40`.
   * Khi toàn bộ PPPoE rớt (`0/60 running`), bảng định tuyến `main` của MikroTik hoàn toàn **không có default gateway ra ngoài Internet**.
2. **Container Singbox Không Ra Được Internet:**
   * Singbox (`172.17.0.2` trên Docker bridge của MikroTik) quản lý các cổng proxy `192.168.110.2:20001..20080`.
   * Mặc dù các cổng Kibe (như M16 `20016`) trỏ ra MobiProxy 4G bên ngoài (`test.taadaa.click:5118` - vốn đang SỐNG 100%), nhưng bản thân container Singbox trên MikroTik **không thể kết nối ra ngoài Internet để forward traffic sang server 4G** do MikroTik mất gateway.
3. **Fail-Closed Preflight Chặn Đứng Tại Cửa:**
   * Runner `run_tiktok_upload_avatar.ps1` chạy hàm `require_android_vpn` kiểm tra egress IP qua cổng `192.168.110.2:20016`.
   * Kết nối timeout $\to$ Runner fail-closed lập tức (`[PREFLIGHT_VPN_BLOCKED]`), ngắt phiên ngay trước khi chạm vào app TikTok để bảo vệ tài khoản không bị lộ IP gốc FPT gia đình.

---

## 4. Quy Trình Giải Thích & Triage Chuẩn Cho Operator

Khi Operator thắc mắc về việc mạng LAN vẫn sống:

1. **Xác nhận ngay lập tức:** Thừa nhận mạng nhà và PC Kibe vẫn sống 100% (tránh làm Operator hoang mang hoặc tranh cãi).
2. **Phân tách 2 luồng rõ ràng:** Giải thích ngắn gọn mạng nhà dùng luồng NAT của modem FPT, còn sợi dây sang MikroTik dùng để quay 60 line PPPoE riêng.
3. **Cung cấp telemetry thực tế:**
   * Cáp MikroTik có cắm (Link 1Gbps).
   * Chiều gửi TX có chạy, nhưng chiều nhận RX từ cục FPT về bằng đúng 0 bytes.
4. **Hướng dẫn xử lý phần cứng:**
   * Kiểm tra dây nối từ cổng `WAN1` MikroTik đang cắm vào cổng LAN mấy trên modem FPT.
   * Cắm thử sang cổng **LAN 4** (cổng bridge chuẩn của FPT).
   * Rút nguồn modem FPT 10 giây cắm lại để xả treo chip xử lý L2.
