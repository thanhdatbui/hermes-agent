# MobiProxy HTML5 Dialog Automation, Conntrack Tuning & Kernel DNAT Offload

## 1. Context & Background
- **Hiện trạng Farm:** Cụm Farm gồm 80 máy Kibe chạy qua MobiProxy 4G (Thái Bình) và 32 máy Admin non chạy qua R3G OpenWrt (Thái Bình).
- **Vấn đề cốt tử:** Container Singbox chạy Docker trên MikroTik x86 RouterOS bị ép gánh 112 máy cày TikTok, lưu lượng đạt 66.000 – 127.000 pps (97 – 122 Mbps), đẩy 4 nhân CPU của Mini PC kẹt cứng ở mức 95% – 98% do chi phí context-switching và netfilter conntrack qua card ảo `veth-singbox`.

## 2. Key Learnings & Pitfalls Overcome

### A. Zombie Connection Storm trong Conntrack
- Khi điện thoại S7 tắt TikTok về màn hình Home, CPU MikroTik vẫn kẹt ở 93% – 97%.
- **Nguyên nhân:** Thông số mặc định `tcp-established-timeout: 1d` (24 giờ) giữ tới 102.864 kết nối ma trong RAM và bảng hash-table của RouterOS.
- **Khắc phục O(1):** Nạp qua REST API `/ip/firewall/connection/tracking/set`:
  ```json
  {
    "tcp-established-timeout": "1h",
    "generic-timeout": "2m",
    "udp-stream-timeout": "1m",
    "udp-timeout": "10s"
  }
  ```
  Giúp thu hồi ngay lập tức 17.000 kết nối ma và duy trì bảng conntrack sạch sẽ, an toàn tuyệt đối cho các ca cày sau (do TCP keep-alive hợp lệ tự động reset timer).

### B. MobiProxy Web v3 Modal Access Automation
- Form "Áp dụng cho tất cả proxy" trên web quản trị MobiProxy (`http://test.taadaa.click/index.php#security`) bị lỗi backend (silent drop), không thực sự nạp lại cấu hình 3proxy.
- **Phương pháp chuẩn xác:** Phải thao tác từng hàng trên bảng danh sách:
  1. Click vào `summary` của thẻ `<details class="action-menu">` ở cột cuối cùng (`•••`).
  2. Click button `Cấu hình truy cập` (`button[data-action="proxy-access"]`) $\rightarrow$ Modal bung ra.
  3. Chọn `select[name="mode"]` đang visible thành `'none'` (Không xác thực).
  4. BẮT BUỘC click đúng button có ID `#access-save` trong form dialog:
     ```javascript
     const saveBtn = document.querySelector('#access-save');
     if (saveBtn) saveBtn.click();
     ```
  5. Sau khi lưu, cột XÁC THỰC trên web chuyển thành công sang nhãn xám `none`, cổng proxy phản hồi HTTP 200 mà không còn dính lỗi `407 Proxy Authentication Required`.

### C. Triển khai Kernel DNAT thay thế Singbox cho Cụm Kibe
- Khi 32 port MobiProxy đã mở khóa sang chế độ `No-Auth` (được bảo vệ bằng Whitelist IP `171.231.180.189` của Scan Guard):
- Tạo 32 rule Kernel DNAT trên MikroTik:
  ```routeros
  /ip firewall nat add chain=dstnat protocol=tcp dst-port=20001-20032 to-addresses=IP_MOBIPROXY to-ports=5101-5132 comment="DNAT_KIBE_M..._TO_MOBIPROXY_..."
  ```
- Đẩy toàn bộ 32 rule này lên trước rule Singbox (`*30E`).
- **Kết quả đo kiểm thực tế:**
  - Tải CPU MikroTik x86 rơi thẳng từ **`97.6% ➔ 1.8%`** (mát rượi, wire-speed).
  - Băng thông trên `veth-singbox` rơi từ `127.114 pps` xuống `284 pps`.
  - Độ trễ phản hồi proxy giảm từ `1.5s` xuống `0.46s`.
  - Cơ chế Fail-Closed bảo vệ chống lộ IP hoạt động hoàn hảo 100% (proxy sập thì S7 hiện dấu chấm than mất mạng, rule drop forward chặn đứng leak IP gốc Đà Nẵng).
