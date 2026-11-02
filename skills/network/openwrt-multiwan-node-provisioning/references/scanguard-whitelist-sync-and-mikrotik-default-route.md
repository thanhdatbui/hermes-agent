# Scan Guard Whitelist Synchronization Architecture: MikroTik Default Route Sing-box Outbound & Dynamic IP Sync

## 1. Bản Chất Kỹ Thuật: Vì Sao Chỉ Cần Whitelist Đúng 1 IP WAN Của MikroTik Đà Nẵng?

Trong các hệ thống phone farm tập trung (MikroTik RouterOS đặt tại trung tâm điều khiển, router vệ tinh/proxy box đặt tại các địa phương như MobiProxy, Xiaomi R3G):

### Sơ Đồ Luồng Kết Nối:
```text
[Samsung S7 Farm]
       │ (1) Kết nối Wi-Fi nội bộ
       ▼
[MikroTik RouterOS 192.168.110.2:200xx]
       │ (2) Container Sing-box Outbound
       ▼
[Nhân Linux RouterOS: Chọn cổng Egress theo Routing Table]
       │ (3) Luôn đi qua DEFAULT ROUTE (0.0.0.0/0) -> pppoe-out1 (IP WAN chính)
       ▼
[Internet công cộng]
       ▼
[Proxy Node vệ tinh: tb.taadaa.click / test.taadaa.click : 5141..5158]
       │ (4) Scan Guard (iptables / Tinyproxy Allow ACL)
       │     Chỉ nhìn thấy địa chỉ Source IP gửi đến = IP của pppoe-out1!
```

### Điểm Cốt Tử:
- MikroTik có thể quay **35 sessions PPPoE (`pppoe-out1..pppoe-out35`)** để cấp mạng cho từng điện thoại, **nhưng container Sing-box chạy trên chính MikroTik kết nối ra ngoài Internet theo DEFAULT ROUTE của RouterOS**.
- Default Route của RouterOS bấy lâu nay luôn được gán cố định vào cổng chính: **`pppoe-out1`** (ví dụ `116.110.212.30`).
- Do đó, dù có hàng trăm thiết bị gửi lưu lượng qua Sing-box, proxy node vệ tinh (MobiProxy, R3G) **chỉ nhìn thấy duy nhất 1 địa chỉ IP nguồn gửi tới là IP của `pppoe-out1`**.
- Vì vậy, whitelist trên proxy node chỉ cần:
  1. **IP WAN `pppoe-out1` của MikroTik** (nuôi toàn bộ dàn phone farm qua Sing-box).
  2. **IP WAN của máy Controller/PC Kibe** (để máy quản trị và tool test kết nối trực tiếp kiểm tra).

---

## 2. Kiến Trúc Đồng Bộ Whitelist Tự Động: Tích Hợp Vào Chung 1 Cronjob

### Vì sao phải tích hợp vào chung `update_mikrotik_scan_guard.py` thay vì tách script riêng?
1. **Cùng chung nguồn dữ liệu kiểm tra:** Cả MobiProxy lẫn R3G đều cùng chờ 2 địa chỉ IP động (`pppoe-out1` và `api.ipify.org`). Nếu tách làm 2 cronjob độc lập, hệ thống sẽ gửi 2 lần request hỏi router MikroTik và ipify, gây lãng phí tài nguyên và tăng nguy cơ rate-limit.
2. **Nguyên tắc "Single Source of Truth":** Khi MikroTik hoặc Kibe đổi IP, cả cụm MobiProxy lẫn Xiaomi R3G cần được cập nhật đồng thời trong cùng 1 chu kỳ để tránh lệch trạng thái.

### Mẫu Code Đồng Bộ Chuẩn Xác Cho Cả MobiProxy & R3G:
```python
def update_r3g_scan_guard(allowed_ips):
    """Cập nhật whitelist IP cho Tinyproxy trên router Xiaomi R3G."""
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect("117.5.62.126", port=22, username="root", password="password", timeout=5)

        cmds = [
            "sed -i '/^Allow /d' /etc/tinyproxy/instances/tp_51*.conf /root/generate_all_proxies.sh",
            "sed -i '/^Listen /a Allow 127.0.0.1' /etc/tinyproxy/instances/tp_51*.conf /root/generate_all_proxies.sh",
            "sed -i '/^Listen /a Allow 192.168.0.0/16' /etc/tinyproxy/instances/tp_51*.conf /root/generate_all_proxies.sh"
        ]
        for ip in allowed_ips:
            if ip and ip.strip():
                cmds.append(f"sed -i '/^Listen /a Allow {ip.strip()}' /etc/tinyproxy/instances/tp_51*.conf /root/generate_all_proxies.sh")

        cmds.extend([
            "killall -HUP tinyproxy 2>/dev/null || (killall tinyproxy && sleep 1 && /bin/sh /root/generate_all_proxies.sh)"
        ])
        ssh.exec_command("; ".join(cmds))
        ssh.close()
        print(f"[OK] R3G Scan Guard updated: {allowed_ips}")
    except Exception as e:
        print(f"[WARN] Failed to update R3G Scan Guard: {e}", file=sys.stderr)
```
