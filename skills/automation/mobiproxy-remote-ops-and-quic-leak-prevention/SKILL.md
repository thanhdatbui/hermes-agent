---
name: mobiproxy-remote-ops-and-quic-leak-prevention
description: "Vận hành an toàn MobiProxy từ xa, phòng chống ngắt kết nối Default WAN Gateway và cơ chế Killswitch L3/L4 chống rò rỉ IP qua UDP/QUIC trên TikTok."
version: 1.0.0
category: automation
tags: [mobiproxy, killswitch, quic, udp, fail-open, mikrotik, openwrt]
---
# MobiProxy Remote Operations & QUIC Anti-Leak Architecture

Dùng khi vận hành, thay đổi cấu hình hạ tầng mạng trên cụm MobiProxy 4G (`test.taadaa.click`) hoặc khắc phục sự cố rò rỉ IP direct trên Android Phone Farm.

## References
- `references/mobiproxy-remote-disconnection-and-quic-failopen-leak-rca-20261105.md` — Bài học xương máu: sự cố tự ngắt WAN cổng 1 MobiProxy OpenWrt và cơ chế TikTok Fail-Open bypass proxy chạy UDP 443 làm lộ IP mạng gốc.

## 1. Kỷ Luật Vận Hành Thiết Bị Remote (Out-of-Band Safety Invariant)
- **CẤM TUYỆT ĐỐI** gọi các API thay đổi hoặc ngắt kết nối mạng (`delete_lan`, `interface disable`, `reboot`, `reset_all`) trên thiết bị remote từ xa khi **chỉ có duy nhất 1 đường IP WAN Internet để quản trị**.
- Cổng WAN chính / Default Route (như cổng LAN 1 trên MobiProxy) là **VÙNG CẤM BẤT KHẢ XÂM PHẠM**.
- **Quy tắc Action Mandate:** Mọi hành vi có nguy cơ làm gián đoạn đường truyền remote bắt buộc phải đưa ra phương án đề xuất và dừng lại xin phép User, cấm tự ý gọi lệnh ngầm.

## 2. Bản Chất Lỗ Hổng "Fail-Open" Của TikTok App (Rò Rỉ IP Gốc)
- Cài đặt `settings put global http_proxy` trên Android chỉ ép luồng **TCP HTTP/HTTPS**.
- App TikTok (`TTNet / Cronet`) ưu tiên truyền video qua **QUIC / HTTP/3 (UDP Port 443)** và truy vấn DNS qua **UDP Port 53**.
- Khi proxy TCP bị timeout, TikTok kích hoạt cơ chế **Fail-Open**: lén bỏ qua proxy và đẩy trực tiếp gói tin UDP 443 / DNS 53 ra Default Gateway của Wi-Fi (`192.168.110.1`), làm lộ IP mạng gốc nhà mạng.

## 3. Khóa Cứng L3/L4 Hardware Killswitch Trên MikroTik
Trên Router MikroTik (`192.168.110.2`), bắt buộc duy trì Rule Drop trước các rule Accept:
```text
chain: forward | src-address: 192.168.110.0/24 | out-interface-list: WAN | action: DROP
(KILLSWITCH_BLOCK_FARM_DIRECT_WAN)
```
Tường lửa router sẽ vứt bỏ toàn bộ gói tin direct/UDP từ dải máy farm, triệt tiêu 100% rủi ro lộ IP cáp quang.

## 4. Quy Chuẩn Ánh Xạ Cổng MobiProxy Phẳng (1:1)
MobiProxy có 32 cổng 4G chia làm 4 card vật lý: `5101..5108`, `5111..5118`, `5121..5128`, `5131..5138` (các cổng `5109, 5110, 5119, 5120, 5129, 5130` không cắm modem).
- Client/Điện thoại farm: Dùng cổng phẳng `20000 + M` (M1 ăn 20001, M9 ăn 20009, M20 ăn 20020, M32 ăn 20032).
- Tầng DNAT trên MikroTik chịu trách nhiệm ánh xạ nhảy cóc qua các cổng thừa:
  * M1..M8 ➔ `5101..5108`
  * M9..M16 ➔ `5111..5118`
  * M17..M24 ➔ `5121..5128`
  * M25..M32 ➔ `5131..5138`
