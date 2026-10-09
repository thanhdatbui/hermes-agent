# XiaoWei Screen Mirror (Con Gấu) & Admin ADB Triage Guide

## 1. Bản chất công cụ "Con Gấu" (XiaoWei / 小微安卓投屏 / Muwei)
- **Thư mục cài đặt**: `C:\Program Files (x86)\xiaowei\`
- **Tiến trình chính**: `xiaowei.exe`
- **File log chẩn đoán**: `C:\Program Files (x86)\xiaowei\logs\app_rCURRENT.log`
- **ADB chuẩn đi kèm**: `C:\Program Files (x86)\xiaowei\tools\adb.exe` (v34.0.1)

## 2. Hiện tượng "Phone disconnected, please check" & Cơ chế văng
- **Triệu chứng**: Giao diện XiaoWei hiện một loạt ô màu cam có biểu tượng điện thoại dấu hỏi `?` và dòng chữ *"Phone disconnected, please check"*.
- **Nguyên nhân cốt lõi trong log Rust/Tauri (`client.rs` & `client_center.rs`)**:
  ```text
  ERROR: conn_and_check_dummy_byte: <serial>, 连接手机异常: (os error 10061)
  ERROR: 连接断开或是超过15秒未连接
  ERROR: kill_reverse_all_ports err serial: <serial>, err: Adb("adb error: closed")
  ```
- **Hành vi bất đối xứng (Cực kỳ quan trọng)**:
  - Khi một máy bị nghẽn I/O hoặc delay socket quá 15 giây, client thread của slot đó trên XiaoWei sẽ tự terminate và khoá cứng tile ở trạng thái disconnected.
  - **XiaoWei KHÔNG CÓ CƠ CHẾ AUTO-RECONNECT**: Kể cả khi người dùng rút cáp cắm lại điện thoại, `adb devices` đã nhận lại trạng thái `device` và shell phản hồi bình thường, ô hiển thị trên XiaoWei **vẫn giữ nguyên màu cam "Phone disconnected"**.
  - **Khắc phục**: Bắt buộc tắt và mở lại XiaoWei (`xiaowei.exe`) để khởi tạo lại toàn bộ 80 luồng stream.

## 3. Xung đột ADB Port 5037 & Lệch Version (Admin 192.168.110.119)
- **Rủi ro thường gặp**: Các tool can thiệp firmware (như `SamFwTool.exe`) khởi động trước và chiếm port 5037 bằng bản ADB cũ:
  - SamFwTool ADB: `C:\SamFwTool\data\adb.exe` (v29.0.6 từ năm 2019).
  - XiaoWei ADB: `C:\Program Files (x86)\xiaowei\tools\adb.exe` (v34.0.1).
- **Hậu quả**:
  - Bản ADB cũ không chịu tải nổi 80 kết nối stream đồng thời, gây nghẽn socket I/O.
  - Tồn đọng hàng nghìn socket ở trạng thái `TIME_WAIT`.
  - Các lệnh `adb shell` chạy song song từ xa (`-H 192.168.110.119 -P 5037`) bị timeout hàng loạt, mặc dù thiết bị phần cứng không hỏng.
  - Chạy tuần tự trực tiếp trên máy Admin thì phản hồi bình thường.

## 4. Checklist chẩn đoán O(1) khi Admin Farm báo rớt máy
1. **Kiểm tra tiến trình đang chiếm ADB port 5037**:
   ```bash
   ssh admin-farm "wmic process where \"name='adb.exe'\" get ProcessId,ExecutablePath,CommandLine"
   ```
   Nếu ExecutablePath không phải của `xiaowei\tools\adb.exe` (ví dụ `SamFwTool`), cần tắt tool xung đột.

2. **Kiểm tra danh sách thiết bị thực tế qua ADB**:
   ```bash
   python D:/Taadaa/tools/inspect_machine.py
   # hoặc trực tiếp trên Admin:
   ssh admin-farm "\"C:\Program Files (x86)\xiaowei\tools\adb.exe\" devices"
   ```
   - Nếu đa số máy là `device` mà XiaoWei màu cam: Lỗi hiển thị XiaoWei, chỉ cần khởi động lại XiaoWei.
   - Nếu máy báo `offline` hoặc `not found`: Lỗi phần cứng/cáp/nguồn thật sự (đặc biệt Hub 20 cổng dải M261-M280).

3. **Thao tác phục hồi chuẩn**:
   - Bước 1: Rút/cắm lại các máy mất kết nối vật lý hoặc chập chờn (`offline`/`not found`).
   - Bước 2: Tắt ứng dụng xung đột (`SamFwTool.exe` nếu không dùng).
   - Bước 3: Đóng hẳn `xiaowei.exe` và khởi động lại để reload 80 màn hình.
