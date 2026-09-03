# Account Switcher Drawer & Bottom Navigation Collision Pitfall

## Triệu chứng
Script dừng giữ hiện trường với lỗi:
`navigation target profile not found in XML`

## Cơ chế gốc rễ
1. Khi script chuẩn bị session feed, preflight cần chuyển đúng tài khoản theo workbook (`verify_and_switch_profile`).
2. Script mở drawer / bottom sheet **"Chuyển đổi tài khoản"**.
3. Nếu tài khoản mục tiêu **đã active sẵn** (được đánh dấu `selected="true"` hoặc icon dấu kiểm `ffv`):
   - Thao tác tap lại tài khoản không làm drawer tự đóng trên TikTok UI.
   - Drawer che kín nửa dưới màn hình (từ Y=420..850 đến Y=1920).
4. Bước kế tiếp (`_navigate_profile_for_preflight`) quét cây UI XML tìm tab **"Hồ sơ"** ở thanh bottom navigation (`bounds [864,1794][1080,1920]`).
5. Vì drawer che phủ toàn bộ bottom bar, parser XML không tìm thấy node tab Profile $\rightarrow$ Fail-closed giữ hiện trường.

## Giải pháp chuẩn hóa
- **Kiểm tra trạng thái `selected/checked` trước khi tap**:
  Nếu node account trong switcher đã `selected="true"` hoặc `checked="true"`, không tap lại mà gửi lệnh `input keyevent 4` (phím BACK) để thu hồi drawer ngay lập tức.
- **Xử lý popup bảo mật "Cập nhật tài khoản"**:
  Khi xuất hiện prompt *"Tài khoản của bạn cần được cập nhật / Để tăng cường tính bảo mật..."*, handler phải bắt đúng nút **"Để sau"** để giải phóng màn hình trước khi định vị tab Profile.
- **Luôn tuân thủ XML-First**: Cấm sử dụng tọa độ cứng để đóng hay tap tab điều hướng.
