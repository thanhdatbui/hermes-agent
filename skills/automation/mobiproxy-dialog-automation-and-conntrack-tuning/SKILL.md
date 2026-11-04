---
name: mobiproxy-dialog-automation-and-conntrack-tuning
description: Automation patterns for MobiProxy Web HTML5 dialog per-port auth mode switching and MikroTik Conntrack zombie connection tuning.
version: 1.0.0
category: automation
tags: [mobiproxy, html5-dialog, conntrack, mikrotik, routeros, proxy-automation, farm-safety]
---
# MobiProxy Dialog Automation & MikroTik Conntrack Tuning

Use this skill when managing MobiProxy Web Control (v3.x) authentication settings or optimizing MikroTik RouterOS connection tracking for high-density phone farms (TikTok/automation).

## 1. MobiProxy Web v3.0.67: HTML5 `<dialog>` Modal Automation Pitfalls

### A. Broken Bulk Configuration Form
- Tab `⌾ Bảo mật & API` -> `Xác thực và mật khẩu hàng loạt`: Nút *"Áp dụng cho tất cả proxy"* bị lỗi backend (silent rollback về `auth strong` hoặc timeout 30s).
- **Quy chuẩn:** Bắt buộc cấu hình riêng lẻ từng port qua menu tác vụ trên bảng `#proxies`.

### B. Per-Port Context Menu & Modal Invocation
1. Mỗi hàng proxy có một thẻ `<details class="action-menu">` với `<summary aria-label="Tác vụ proxyXX">•••</summary>`.
2. Bên trong chứa nút `Cấu hình truy cập`: `button[data-action="proxy-access"]`.
3. Khi click, một cửa sổ HTML5 Native `<dialog>` sẽ bung ra với `formMethod="dialog"`.

### C. Precision Form Interaction Pattern (Playwright / CDP)
- **Cạm bẫy:** Có tới 12 thẻ `<select>` trên trang. Dùng selector chung `select` sẽ ăn vào thẻ ẩn hoặc dropdown bộ lọc.
- **Quy trình chuẩn:**
  ```javascript
  // 1. Mở modal của đúng hàng
  const row = Array.from(document.querySelectorAll('table tbody tr')).find(r => r.innerText.includes('proxyXX'));
  const details = row.querySelector('td:last-child details');
  details.open = true;
  details.querySelector('button[data-action="proxy-access"]').click();

  // 2. Chọn dropdown đang hiển thị
  const visibleSelect = Array.from(document.querySelectorAll('select[name="mode"]')).find(s => s.offsetParent !== null);
  visibleSelect.value = 'none'; // 'none' = Không xác thực, 'strong' = User/Pass, 'iponly' = Danh sách IP
  visibleSelect.dispatchEvent(new Event('change', {bubbles: true}));

  // 3. Bắt buộc click ID #access-save (CẤM dùng form.submit())
  document.querySelector('#access-save').click();
  ```
- **Xác nhận kết quả:** Gửi HTTP request trực tiếp tới port (ví dụ `5102`) không kèm User/Pass. Nhận HTTP 200 và IP Public là thành công (`auth none`).

---

## 2. MikroTik RouterOS: Bão Kết Nối Ma & Conntrack Zombie Tuning

### A. Hiện Tượng Quá Tải Ảo (Zombie Connection Accumulation)
- Khi hàng trăm điện thoại hoàn thành ca nuôi acc (về Home Launcher), RouterOS vẫn kẹt 95-98% CPU và đo được 50k-100k pps qua card mạng ảo container.
- **Nguyên nhân:** Mặc định `tcp-established-timeout: 1d` (24 giờ). Các kết nối TCP dở dang từ CDN/TikTok không gửi FIN/RST bị router giam giữ và liên tục polling trong RAM.

### B. Bộ Thông Số Tối Ưu Chuẩn Cho Farm
Nạp qua RouterOS REST API (`POST /ip/firewall/connection/tracking/set`) hoặc CLI:
- `tcp-established-timeout: 1h` (hạ từ 24h xuống 1h, tự động dọn dẹp các kết nối chết).
- `generic-timeout: 2m` (hạ từ 10m).
- `udp-stream-timeout: 1m` (hạ từ 3m).
- `udp-timeout: 10s` (hạ từ 30s).
- **Tính an toàn:** Các ứng dụng cày thật đều có nhịp tim (heartbeat) định kỳ. Gói tin hợp lệ đi qua sẽ tự động reset timer về mốc ban đầu, không bao giờ làm gián đoạn luồng cày đang chạy.

---

## 3. Kiến Trúc L3/L4 Kernel DNAT Wire-Speed Thay Thế L7 Proxy

- Singbox L7 Container chỉ bắt buộc khi proxy đầu xa đòi hỏi User/Pass (để tự động chèn auth).
- Khi proxy upstream (như MobiProxy) đã được bảo vệ bằng Whitelist IP (Scan Guard L3/L4) và đã gỡ mật khẩu (`auth none`), có thể chuyển sang dùng **Kernel DNAT (`/ip firewall nat add chain=dstnat action=dst-nat ...`)** chuyển tiếp gói tin ở tốc độ phần cứng, giải phóng hoàn toàn CPU cho Router/Mini PC.
