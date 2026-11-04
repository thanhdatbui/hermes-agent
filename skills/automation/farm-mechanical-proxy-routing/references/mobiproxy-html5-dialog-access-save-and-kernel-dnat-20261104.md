# Bẫy Thao Tác HTML5 Dialog trên MobiProxy Web v3 và Kiến Trúc Kernel DNAT

## 1. Bản Chất Kỹ Thuật Form HTML5 Dialog (`method="dialog"`) trên MobiProxy Control
- **Hiện tượng:** Khi click vào form hoặc nút submit thông thường (`form.submit()` hoặc click `button[type="submit"]`), web không lưu trạng thái đổi xác thực (vẫn giữ nguyên `auth strong`), gói tin proxy vẫn văng lỗi `407 Proxy Authentication Required`.
- **Cơ chế ẩn của giao diện:**
  - Khối popup `Truy cập proxyXX` là một phần tử `<dialog>` chuẩn HTML5 với `<form method="dialog">`.
  - Nút lưu thực sự có ID duy nhất: `button#access-save` (`value="save"`).
  - Phía trên combobox chọn chế độ xác thực có 2 thẻ `<select name="mode">`: Một thẻ ẩn (thuộc form khác) và một thẻ hiển thị thực sự (`offsetParent !== null`).
- **Quy trình tự động hóa Playwright chuẩn xác:**
  1. Mở thẻ `<details>` của hàng proxy: `details.open = true`.
  2. Click nút mở modal: `button[data-action="proxy-access"]`.
  3. Định vị chính xác thẻ select hiển thị:
     ```javascript
     const selects = Array.from(document.querySelectorAll('select[name="mode"]'));
     const visibleSelect = selects.find(s => s.offsetParent !== null);
     visibleSelect.value = 'none'; // 'none' cho Không xác thực, 'iponly' cho Danh sách IP
     visibleSelect.dispatchEvent(new Event('change', {bubbles: true}));
     ```
  4. Bắt buộc kích hoạt sự kiện click trên nút ID chuyên dụng:
     ```javascript
     document.querySelector('#access-save').click();
     ```
  5. Đợi API phản hồi `200 http://test.taadaa.click/api.php?action=proxy.access`.
  6. Kiểm tra lại cột `XÁC THỰC` trên bảng: Nhãn chuyển từ `strong` sang `none` (xám) là thành công 100%.

## 2. Kernel DNAT trên MikroTik x86 cho MobiProxy (Sau Khi Bỏ Pass)
- **Tạo Rule DNAT phần cứng:**
  ```routeros
  /ip firewall nat add chain=dstnat protocol=tcp dst-port=20002 action=dst-nat to-addresses=171.224.65.132 to-ports=5102 comment="CANARY_DNAT_M2_TO_MOBIPROXY_5102"
  ```
- **Vị trí bắt buộc:** Đẩy rule lên TRƯỚC rule gom container Singbox (`*30E`):
  ```routeros
  /ip firewall nat move numbers=*33F destination=*30E
  ```
- **Hiệu quả đo kiểm thực tế:**
  - Độ trễ phản hồi giảm từ ~1.2s xuống còn **`0.46s`**.
  - Gói tin chạy wire-speed ở tầng L4 Kernel, CPU MikroTik không tốn tài nguyên xử lý context-switch L7.
- **Fail-Closed an toàn khi Proxy chết:**
  - Điện thoại S7 gặp TCP timeout/RST sẽ tự động hiện dấu chấm than mất mạng.
  - Bộ 3 Killswitch trên MikroTik (`KILLSWITCH_BLOCK_FARM_DIRECT_WAN`, `KILLSWITCH_FARM_DNS_UDP`, `KILLSWITCH_FARM_QUIC_UDP`) chặn đứng 100% không cho S7 đi direct qua IP gốc Đà Nẵng.

## 3. R3G Multi-PPPoE DNS Trap & Phạm Vi Áp Dụng
- R3G OpenWrt chạy 16 PPPoE con không có password từ đầu (`Allow <mikrotik_ip>`), nhưng bị lỗi nghẽn phân giải DNS trên các sub-interface PPPoE (`Could not retrieve info / no entity`).
- Cụm 80 máy Kibe (MobiProxy) là nguồn lưu lượng chính đốt 90% CPU -> Chuyển sang Kernel DNAT.
- Cụm 32 máy Admin non (R3G) lưu lượng thấp -> Tạm thời tiếp tục định tuyến qua Singbox để bypass bẫy DNS 16 PPPoE mà vẫn an toàn kết nối SSH.
