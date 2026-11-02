# Multi-Hop Network Architecture Drift & Anti-Speculative Diagnosis

## 1. Bối Cảnh Sự Cố & Hiện Tượng (Incident 2026-11-02)
- **Hiện tượng**: Dàn Farm Admin (M201-M280) chạy ca nuôi feed trưa (12:00) có 40 máy thành công, nhưng 29 máy bị chặn dừng ở bước preflight với lỗi `blocked-proxy-vpn` (`dial tcp 192.168.110.2:202xx: connect: network is unreachable`).
- **Phản ứng sai lầm thường gặp (Speculative Blaming)**: Khi thấy kiểm tra `192.168.110.2:202xx` timeout, Agent vội vàng kết luận do router upstream từ xa (R3G Thái Bình) bị rớt mạng hoặc sập các port `5143, 5151, 5152`. Khi kiểm tra thực tế, toàn bộ 16 port của R3G `tb.taadaa.click:5141..5158` đều đang LIVE 100%.

## 2. Bản Chất Lỗi Kỹ Thuật (Dual Architectural Gap)
Trong các kiến trúc mạng proxy đa chặng (`S7 Phone -> MikroTik Singbox LAN -> Upstream WAN/Tunnel -> TikTok`):

1. **Singbox Outbound Drift (Lệch cấu hình chặng trung gian)**:
   - Khi chuyển đổi kiến trúc mạng từ **Tailscale Relay** sang **Direct WAN**, router R3G ở đầu xa đã được mở port và nạp DDNS Cloudflare + Anti-Scan Whitelist.
   - Tuy nhiên, cấu hình Singbox trên MikroTik (`docker/config/config.json`) vẫn giữ nguyên các outbounds `proxy_m203..proxy_m272` trỏ vào trạm trung gian cũ: `server: 192.168.110.119` (PC Admin PortProxy via Tailscale).
   - Khi Tailscale không còn duy trì, PC Admin từ chối/timeout chuyển tiếp, khiến Singbox trên MikroTik bị tắc nghẽn ở toàn bộ dải port `202xx`.

2. **Dư Chấn Cờ Cách Ly (Quarantine State Hang in SSOT)**:
   - Trong quá trình điều tra sự cố trước đó, script cách ly `quarantine_r3g_machines.py` đã ghi chuỗi `QUARANTINE_R3G_INVESTIGATION` vào `PROXYgandienthoai.xlsx` và `farm_master.db`.
   - Chuỗi này không có định dạng `host:port`, dẫn đến script nạp proxy ADB trên điện thoại (`set_proxy_farm_admin_adb.py`) bỏ qua không nạp cho 32 máy S7, khiến máy thiếu cấu hình proxy và bị cơ chế an toàn ngắt mạch.

## 3. Quy Trình Cô Lập Từng Chặng (Hop-by-Hop Isolation Protocol)
Tuyệt đối không đoán mò nguyên nhân khi luồng proxy đa chặng gặp sự cố. Bắt buộc đo đạc theo thứ tự ngược từ ngoài vào trong:

```text
[Chặng 3: Upstream WAN Endpoint] (tb.taadaa.click:51xx)
  -> Kiểm tra curl từ PC Kibe xem port có mở và trả về Public IP sạch hay không.
  -> Nếu LIVE: Tuyệt đối KHÔNG đổ lỗi cho upstream hay nhà mạng.

[Chặng 2: Intermediate Router/Bridge] (192.168.110.2:202xx / Singbox Container)
  -> Kiểm tra file cấu hình Singbox xem outbounds đang trỏ về đâu (Direct WAN hay IP trung gian cũ).
  -> Kiểm tra container status và firewall input/forward rules trên MikroTik.

[Chặng 1: SSOT Ledger & Phone Device State]
  -> Kiểm tra PROXYgandienthoai.xlsx và SQLite farm_master.db có bị dính cờ QUARANTINE không.
  -> Kiểm tra thực tế trên điện thoại: `adb shell settings get global http_proxy`.
```

## 4. Checkpoint Nghiệm Thu Trước Khi Mở Batch
Trước khi thông báo "hệ thống đã sẵn sàng cho máy chạy bình thường", Coordinator bắt buộc phải hoàn thành trọn gói 4 bước:
1. **Clear Quarantine**: Xóa cờ cách ly trong Excel và SQLite, trả về dải IP LAN hợp lệ (`192.168.110.2:202xx`).
2. **Sync Outbound**: Trỏ toàn bộ outbounds của Singbox sang endpoint mới và restart container.
3. **Provision Phones**: Bắn lệnh ADB đồng loạt nạp proxy vào toàn bộ thiết bị online.
4. **End-to-End Canary Probe**: Bắn 1 request thực tế từ 1 máy S7 thật (`adb shell curl http://api.ipify.org`) xác nhận trả về đúng IP của upstream trước khi nhả batch cho cronjob.
