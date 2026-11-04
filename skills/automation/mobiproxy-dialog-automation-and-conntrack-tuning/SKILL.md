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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
