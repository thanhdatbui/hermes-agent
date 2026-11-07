---
name: r3g-boot-race-condition-and-watchdog-resilience
description: Khắc phục triệt để lỗi Boot Race Condition và cài đặt Watchdog tự phục hồi 16 port Tinyproxy trên Router OpenWrt Xiaomi R3G sau khi khởi động lại.
---
# R3G OpenWrt Boot Race Condition & Auto-Heal Watchdog Architecture

## 1. Triệu chứng sự cố & Nguyên nhân gốc rễ (Root Cause)
- **Triệu chứng**: Router R3G sau khi mất điện hoặc reboot, phần cứng vẫn online (`ubus` báo interfaces PPPoE `up: true`, Cloudflare DDNS update thành công), nhưng toàn bộ các cổng proxy `5141..5158` bị `CLOSED / connection refused` hoặc `502 Bad Gateway`.
- **Nguyên nhân cốt lõi (Boot Race Condition)**:
  - File `/etc/rc.local` chỉ đặt độ trễ cố định `sleep 30` rồi gọi `/root/generate_all_proxies.sh`.
  - Trên thực tế, 16 line PPPoE của Viettel cần 45-75 giây mới hoàn tất bắt tay PADO/PPPoE và nhận IPv4.
  - Tại giây thứ 30, toàn bộ các interface `pppoe-wan` và `pppoe-wan_sub*` chưa có IP, script in `[skip] port XXXX: dev has no IPv4` và kết thúc mà không có cơ chế retry.
  - Sau khi skip, không có tiến trình `tinyproxy` nào chạy trên router, dẫn tới sập proxy toàn bộ.

## 2. Giải pháp cơ giới hóa 2 lớp (Dual-Layer Resilience)

### Lớp 1: Khắc phục triệt để Boot Race Condition tại `/etc/rc.local`
Thay thế `sleep 30` mù quáng bằng vòng lặp kiểm tra có điều kiện (`while loop`), đợi đến khi ít nhất 1 line PPPoE có IP mới khởi chạy sinh proxy:
```sh
# Auto generate proxies with retry loop until PPPoE has IPv4
(
    i=0
    while [ $i -lt 30 ]; do
        sleep 10
        i=$((i + 1))
        if ip -4 addr show dev pppoe-wan 2>/dev/null | grep -q 'inet ' || ip -4 addr show dev pppoe-WAN2 2>/dev/null | grep -q 'inet '; then
            sleep 5
            /root/generate_all_proxies.sh >/var/log/generate_all_proxies.log 2>&1
            break
        fi
    done
) &
```

### Lớp 2: Watchdog tự động phục hồi trong Crontab (`/root/r3g_watchdog.sh`)
Cài đặt script giám sát định kỳ mỗi 5 phút trong `/etc/crontabs/root`:
```sh
#!/bin/sh
# Lưu ý: Busybox OpenWrt trên R3G không có lệnh pgrep và syntax grep '[t]inyproxy'
# có thể trả về 0. Bắt buộc dùng cú pháp chuẩn Busybox: ps | grep tinyproxy | grep -v grep | wc -l
RUNNING=$(ps | grep tinyproxy | grep -v grep | wc -l)
if [ "$RUNNING" -lt 16 ]; then
    echo "[$(date)] Tinyproxy degraded ($RUNNING running). Restarting..." >> /var/log/r3g_watchdog.log
    /root/generate_all_proxies.sh >> /var/log/r3g_watchdog.log 2>&1
fi
```
Lịch crontab:
```text
*/5 * * * * /bin/sh /root/r3g_watchdog.sh >/dev/null 2>&1
```

*Cơ chế Rotate IP độc lập*: Watchdog này TUYỆT ĐỐI KHÔNG tự động redial / change IP hay làm đổi IP Public của line Viettel; nó chỉ canh giữ tiến trình phần mềm `tinyproxy` luôn sống đủ 16 port. Cơ chế đổi IP chỉ chạy qua `/root/rotate_proxy.sh <sub_interface>` khi có lệnh chủ động của Operator hoặc Runner ca nuôi.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
