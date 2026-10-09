# Singbox Local Wrapper DNS Stalling on MikroTik PPPoE Outage & Avatar Headroom Triage (2026-10-09)

## 1. Hiện tượng sự cố tại bước Preflight Avatar Runner
Khi chạy avatar upload đơn lẻ trên máy thật (ví dụ Máy 16 - Tik 7 `@vothitram9184`):
```
Máy 16: LỖI (exit=2, verified=False, reason=[PREFLIGHT_VPN_BLOCKED] required Android VPN is not connected: 
interface=wlan0 tun_up=False vpn_connected=True error=global proxy (192.168.110.2:20016) egress IP verification failed: 
Get "http://ifconfig.me/ip": context deadline exceeded)
```

## 2. Quy trình chẩn đoán phân tầng O(1) để cô lập nguyên nhân
1. **Kiểm tra Upstream MobiProxy trực tiếp từ Host:**
   - Cổng upstream tương ứng (ví dụ Máy 16 ánh xạ tới `test.taadaa.click:5118`, auth `mobi18:TaadaaMobi#2026!`).
   - Chạy probe HTTP GET có auth từ Host: nếu trả về IP public hợp lệ (ví dụ `171.224.138.29`) và latency ~115ms $\to$ Upstream 4G MobiProxy hoàn toàn sống và khỏe mạnh.
2. **Kiểm tra Router MikroTik (`192.168.110.2:9090`):**
   - Đọc `/interface/pppoe-client`: kiểm tra số đường PPPoE đang `running`.
   - Nếu `0/60 running` và log router ghi nhận:
     ```
     script,warning PPPoE-Watchdog: pppoe-outXX not running -> Resetting...
     pppoe-outXX: terminating... - disconnected
     container,info,debug ERROR ... lookup test.taadaa.click: context deadline exceeded
     ```
   - **Bản chất lỗi:** Toàn bộ đường truyền WAN PPPoE FPT trên router MikroTik đang bị rớt kết nối hoặc đang trong chu kỳ reset hàng loạt. Router mất default route ra ngoài Internet, khiến container `veth-singbox` không thể gửi UDP query tới `8.8.8.8` để phân giải domain `test.taadaa.click`. Cổng local proxy `192.168.110.2:200xx` vẫn mở TCP socket nhưng mọi HTTP request forward đều bị timeout.
3. **Kỷ luật xử lý hàng đợi (Queue Discipline):**
   - Không được revert ảnh trên đĩa hay đánh dấu FAIL/DONE trong SQLite.
   - Giữ nguyên `status = 'PENDING'` trong `avatar_replace_queue` (`tiktok_tracker.db`).
   - Khi PPPoE trên MikroTik kết nối lại bình thường, watchdog hoặc batch runner kế tiếp sẽ tự động bốc và đẩy avatar mới lên máy.

## 3. Quy chuẩn trích xuất Avatar Headroom từ Video nguồn
- Khi avatar cũ bị cắt lẹm (chỉ thấy miệng/cổ, mất mắt và trán như folder 127 cũ):
- Bắt buộc dùng OpenCV Haar Cascade với công thức crop vuông Headroom:
  ```python
  box_size = int(fh * 2.4)
  box_size = min(box_size, w, h)
  cx = fx + fw // 2
  x1 = max(0, min(cx - box_size // 2, w - box_size))
  y1 = max(0, fy - int(fh * 0.55))  # Giữ trán và tóc phía trên
  if y1 + box_size > h:
      y1 = max(0, h - box_size)
  cropped = frame[y1:y1+box_size, x1:x1+box_size]
  ```
- Luôn tạo ảnh đối chiếu composite (Old vs New) có vẽ viền tròn đỏ/xanh mô phỏng avatar TikTok, soi mắt qua Vision API trước khi gửi `MEDIA:` cho Operator.
