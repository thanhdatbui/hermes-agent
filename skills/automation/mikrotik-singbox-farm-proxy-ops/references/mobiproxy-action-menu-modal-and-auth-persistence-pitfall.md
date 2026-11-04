# MobiProxy Web v3.0.67 Action Menu Modal & Auth Persistence Pitfall (2026-11-04)

## 1. Hiện Trường Giao Diện MobiProxy Control (Web v3.0.67)
- **Địa chỉ quản trị:** `http://test.taadaa.click/index.php#proxies` (Password: `N0spam@23102025`).
- **Cột tác vụ cuối cùng:**
  - Trong mỗi hàng bảng danh sách proxy (`table tbody tr`), ô cuối cùng là menu tác vụ dạng thẻ HTML `<details class="action-menu">`.
  - Thẻ `<summary aria-label="Tác vụ proxyXX">•••</summary>` hiển thị biểu tượng 3 dấu chấm `•••`.
- **Menu bung ra khi click vào 3 chấm (`•••`):**
  1. `<button data-action="proxy-stop">Tắt interface</button>`
  2. `<button data-action="proxy-mac">Đổi MAC</button>`
  3. `<button data-action="proxy-access">Cấu hình truy cập</button>`

---

## 2. Thao Tác Mở Popup Modal "Truy cập proxyXX"
- Khi click nút `Cấu hình truy cập` (`button[data-action="proxy-access"]`), một popup modal `Truy cập proxyXX` bung ra giữa màn hình:
  - **`Chế độ xác thực` (`select[name="mode"]`):** Có 3 tùy chọn:
    1. `Không xác thực` (`value="none"`)
    2. `Tài khoản / mật khẩu` (`value="auth"`)
    3. `Danh sách IP` (`value="ip"`)
  - **`Mật khẩu proxy` (`input[name="password"]`)**
  - **`IPv4 được phép` (`input[name="allow_ips"]`)**
  - Các nút: `Hủy` và `Lưu thay đổi`.

---

## 3. Cạm Bẫy Kỹ Thuật (The Auth Persistence Trap)
- **Thao tác trên Web:**
  - Chọn `Chế độ xác thực: Không xác thực` (`value="none"`).
  - Bấm `Lưu thay đổi` $\rightarrow$ Web thông báo lưu thành công và đóng modal.
  - Bấm tiếp nút `Reset proxyXX` để modem khởi động lại.
- **Sự thật đo kiểm tại hiện trường:**
  - Gửi request không mật khẩu trực tiếp vào port (ví dụ `test.taadaa.click:5101`):
    $$\rightarrow \text{FAIL: HTTP 407 Proxy Authentication Required}$$
  - Kiểm tra lại cột **XÁC THỰC** trên bảng: vẫn hiển thị nhãn **`strong`**!
- **Nguyên nhân gốc rễ:**
  - Firmware MobiProxy v3.0.67 bị lỗi hoặc cố tình khóa cứng backend: tiến trình sinh cấu hình `3proxy` ngầm trong box tự động ép nạp lại template `auth strong` kèm User/Pass mặc định (`mobiX:TaadaaMobi#2026!`).
  - Giao diện web cho phép bấm đổi chế độ, nhưng backend không thực sự lưu hoặc rollback về chế độ mặc định khi tiến trình 3proxy nạp lại.

---

## 4. Bài Học Kiến Trúc Cho Farm TikTok 160 Phone
1. **Không thể bỏ Singbox bằng cách tắt pass trên web MobiProxy:** Vì box MobiProxy vẫn bắt buộc `HTTP Error 407`, các máy S7 trong mạng Wi-Fi không thể gửi gói tin raw IP thẳng vào modem 4G.
2. **Singbox L7 là bắt buộc:** Vai trò của Singbox là **bộ nạp User/Pass tự động ở tầng L7** cho 80 máy Kibe. Không có Singbox, MikroTik Kernel DNAT chỉ chuyển tiếp L3/L4 sẽ bị đứt kết nối tại cửa 407 của MobiProxy.
3. **Giải phóng tải RouterOS:**
   - Để hạ tải CPU 95% của MikroTik, giải pháp chuẩn công nghiệp là **đưa Singbox sang chạy trên Host độc lập (PC i5-8400 hoặc Ubuntu Server riêng)** thay vì chạy trong container veth của RouterOS.
