# Fail-Safe Firewall Hardening & Dead Man's Switch on Headless Tailscale Nodes

## 1. Bối cảnh & Rủi ro chí mạng
Khi quản trị các thiết bị mạng từ xa (OpenWrt, Linux server, Raspberry Pi) qua kết nối Tailscale / WireGuard mà không có cổng console OOB (Out-of-Band) vật lý:
- Một thay đổi sai trong firewall (`/etc/config/firewall`, `iptables`, `nftables`) hoặc reload fw3/fw4 khi chưa bind đúng interface VPN sẽ khiến router ngay lập tức **DROP toàn bộ kết nối quản trị**.
- Thiết bị bị cô lập hoàn toàn, trở thành "cục gạch từ xa" (bricked remotely), buộc phải nhờ người tại hiện trường rút nguồn hoặc can thiệp cáp mạng.

## 2. Quy trình "Dead Man's Switch" (Auto-Rollback hẹn giờ)
Trước khi thực thi bất kỳ lệnh sửa đổi firewall hoặc network nào trên node headless, **BẮT BUỘC** kích hoạt tiến trình hẹn giờ phục hồi tự động trong nền (background subshell):

### A. Chuẩn bị bản sao lưu an toàn
```sh
cp /etc/config/firewall /etc/config/firewall.safe_bak
```

### B. Kích hoạt Dead Man's Switch (120 giây)
```sh
( sleep 120 && cp /etc/config/firewall.safe_bak /etc/config/firewall && /etc/init.d/firewall restart && /etc/init.d/tailscale restart ) >/dev/null 2>&1 &
ROLLBACK_PID=$!
echo "Dead Man's Switch armed with PID: $ROLLBACK_PID"
```

### C. Áp dụng thay đổi & Kiểm chứng
- Áp dụng rule mới (ví dụ mở port WAN, cấu hình IP whitelist).
- Kiểm tra kết nối từ máy client:
  - Nếu ping/SSH qua Tailscale vẫn thông suốt VÀ dịch vụ mới hoạt động đúng:
    ```sh
    kill $ROLLBACK_PID
    uci commit firewall
    echo "Changes confirmed and committed. Rollback disarmed."
    ```
  - Nếu mất kết nối: Không cần hoảng loạn hay làm phiền người tại chỗ. Đúng 120 giây sau, subshell nền sẽ tự động phục hồi file `.safe_bak`, khởi động lại firewall và Tailscale, router tự động online trở lại.

## 3. Kiến trúc Anti-Scan (Scan Guard) Whitelist an toàn trên OpenWrt
Học hỏi từ cơ chế Scan Guard của MobiProxy: Mở port trực tiếp ra WAN nhưng không mở cho cả thế giới quét botnet:

1. **Không mở mù toàn bộ WAN INPUT:**
   - Cổng WAN mặc định vẫn là `zone_wan_input` $\to$ `REJECT` / `DROP`.
2. **Whitelist theo IP nguồn chỉ định (Client Farm):**
   - Chỉ cho phép các IP Public đã biết (ví dụ IP WAN MikroTik, IP host farm) kết nối vào dải port proxy (ví dụ `5141..5158`).
   - Mọi IP lạ từ Internet (botnet Shodan, scanner) đều bị DROP tại tầng kernel (iptables raw/mangle/filter), không tiêu tốn RAM hay CPU của router.
3. **Bảo vệ tuyệt đối interface Tailscale (`tailscale0`):**
   - Zone chứa `tailscale0` bắt buộc phải có `input ACCEPT`, `output ACCEPT`.
   - Cổng UDP `41641` (WireGuard peer-to-peer của Tailscale) trên WAN luôn luôn phải được ACCEPT để duy trì kết nối với các node khác.
