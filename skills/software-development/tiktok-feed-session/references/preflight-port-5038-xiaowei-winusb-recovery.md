# Pre-flight Port 5038 XiaoWei WinUSB Recovery Pattern

## 1. Bản Chất Hiện Tượng
- Khi ứng dụng Tiểu Vi (`xiaowei.exe`) chạy ngầm, nó khởi chạy ADB daemon độc quyền tại cổng `5038`.
- Windows gán các WinUSB endpoints của farm điện thoại cho tiến trình cổng `5038`, khiến server ADB chính thức cổng `5037` mất kết nối với hàng loạt thiết bị (báo lỗi giả "Mất kết nối >40 máy").

## 2. Quy Trình Pre-flight Tiêu Chuẩn Trong Runner
1. **Kiểm tra trạng thái cổng 5038:**
   - Dùng socket probe hoặc `Get-NetTCPConnection -LocalPort 5038 -State Listen`.
   - Bắt buộc lọc danh tính tiến trình (chỉ can thiệp khi PID sở hữu hoặc đường dẫn thuộc `xiaowei` hoặc `adb`).
2. **Giải phóng và phục hồi:**
   - Thực thi `kill-server` trên cổng 5038: `& "C:\Program Files (x86)\xiaowei\tools\adb.exe" -P 5038 kill-server`.
   - Trì hoãn 1-2 giây cho driver WinUSB nhả hoàn toàn.
3. **Cơ chế Fail-Closed:**
   - Nếu sau khi giải phóng cổng 5038 vẫn bị chiếm dụng, runner phải ném lỗi `PREFLIGHT_PORT_5038_BLOCKED` và dừng phiên ngay lập tức để bảo vệ an toàn farm, tránh chạy mù vào trạng thái thiết bị chập chờn.
