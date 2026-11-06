---
name: mobiproxy-license-recovery-and-lan1-governance
description: Kỷ luật an toàn tuyệt đối khi thao tác box MobiProxy, cơ chế Hardware License Anchor tại LAN 1 (proxy01) và quy trình xử lý lỗi 'Không đọc được license từ proxy01'.
version: 1.0.0
category: automation
tags: [mobiproxy, license, lan1, proxy01, fail-closed, hardware-governance, farm-safety]
---
# MobiProxy License Recovery & LAN 1 Hardware Governance

Use this skill when managing, diagnosing, or recovering MobiProxy 4G/PPPoE boxes (v3.x by proxy4gs.com), especially when configuring LAN ports, PPPoE credentials, or handling license errors.

## 1. Tử Huyệt Kiến Trúc: Hardware License Anchor trên LAN 1 (`proxy01`)
- **Nguyên lý hoạt động ngầm của MobiProxy (v3.0.67):**
  * Nhà cung cấp thiết bị (`proxy4gs.com` - Thành Phùng Văn) ghim file License bản quyền của thiết bị trực tiếp vào vị trí **`proxy01`** (kết nối đầu tiên của LAN 1).
  * Backend kiểm tra ngầm license key trên `proxy01` trước khi kích hoạt daemon quay số (`pppd`) và mount proxy (`3proxy`).
  * **Mối quan hệ nhân quả sống còn:** Bắt buộc LAN 1 phải quay số PPPoE thành công và nổ IP Public thì hệ thống mới trích xuất được thông tin thiết bị / nạp license hợp lệ. Từ license của `proxy01`, backend mới cấp phép kích hoạt daemon quay số cho LAN 2, LAN 3, LAN 4.

## 2. Cạm Bẫy Hủy Diệt: Nút "Xóa Cài Đặt LAN" & API `network.plan`
- **Hành vi phá hoại:**
  * Việc bấm nút màu đỏ *"Xóa cài đặt LAN 1"* hoặc gọi API `network.plan` / `network.delete_lan` trên LAN 1 sẽ xóa sạch file license / cấu hình của `proxy01`.
  * Trong JavaScript của box (`app.js`) có cảnh báo rõ:
    > *"Kết nối đầu tiên có thể ảnh hưởng thông tin license của thiết bị."*
- **Hậu quả thực tế:**
  * Góc trên màn hình báo đỏ: `Không đọc được license từ proxy01`.
  * Backend tự hủy bỏ tiến trình quay số PPPoE (`pppd`) trên LAN 1. Dù điền đúng 100% tài khoản Viettel (`hyn_gftth_datlp3 / 2TJFUO`), backend vẫn drop lệnh, đèn LAN 1 không sáng nhấp nháy, không bao giờ lấy được IP Public.
  * Toàn bộ 32 cổng proxy của Farm bị sập dây chuyền theo.

## 3. Quy Trình Cứu Hộ & Xử Lý Khi Dính Lỗi License
1. **DỪNG MÒ MẪM & CẤM BẤM XOAY LIÊN TỤC:**
   - Việc rút điện hay bấm xoay IP liên tục không thể phục hồi được vì file license trong OS đã bị xóa mất.
2. **Xác Định Đúng Trình Tự Khởi Tạo Box (Theo Video Chuẩn Của Hãng):**
   - Phải cài LAN 1 trước $\rightarrow$ Nhập đúng PPPoE $\rightarrow$ Lên IP Public $\rightarrow$ Box nhận diện license $\rightarrow$ Mới được cài tiếp LAN 2, LAN 3, LAN 4.
3. **Kích Hoạt Hỗ Trợ Từ Nhà Cung Cấp:**
   - Khi dính lỗi `Không đọc được license từ proxy01`, bắt buộc phải liên hệ nhà cung cấp (anh Thành Phùng Văn - `fb.com/vthanh.info`) qua UltraViewer để họ dùng quyền root (SSH/Terminal) chạy script nạp lại file bản quyền cho `proxy01`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
