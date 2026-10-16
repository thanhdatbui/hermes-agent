# Pitfall: Đẻ script ad-hoc thay vì tái sử dụng Canonical Avatar Runner (2026-10-17)

## 1. Hiện tượng & Sai lầm
- Khi User yêu cầu đổi avatar một tài khoản cụ thể (ví dụ: `@vantieu11` trên Máy 59):
  - Agent thấy TikTok trên máy đang active tài khoản khác (`@thutuan4916`) liền hoảng loạn, sợ runner tự động đổi nhầm nick.
  - Agent tự ý viết ra script mới `D:/Taadaa/tmp/execute_m59_avatar.py` tự tap ADB để chuyển nick, sửa hồ sơ, chọn ảnh.
  - Sau đó điều phối subagent sửa đi sửa lại dính timeout 600s, bị User chất vấn: *"Ủa t nhớ có file up avatar r mà sao mày còn đi tạo cái ms. Ý tao là script m59_avatar.py là sao?"*.

## 2. Nguyên tắc & Công cụ chuẩn (SSOT Canonical Tooling)
- Trên Farm Taadaa, việc nạp và đổi avatar cho 1 máy hoặc danh sách máy **ĐÃ CÓ SẴN RUNNER CANONICAL**:
  ```bash
  python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Tik> --machine <Machine>
  ```
  Hoặc:
  ```powershell
  echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik <Tik> -MaxParallel 1 -HostConfigPath D:\Taadaa\machine-config\kibe.yaml -ForceAvatarMachineList "<Machine>"
  ```
- **Bộ máy chuẩn đã tự động xử lý toàn bộ các khâu:**
  1. `ACCOUNT_SWITCHER`: Tự động đọc workbook `Tik<N>.xlsx`, so khớp username và switch sang đúng nick mục tiêu an toàn qua `automation_core.tiktok.account_switcher`.
  2. `LAYOUT ADAPTER`: Tự nhận diện giao diện (Layout C bong bóng Note / Top-left pencil `(75, 150)` / Classic text) để mở Sửa hồ sơ.
  3. `CLEAN & PUSH`: Tự dọn sạch MediaStore cũ, push ảnh `avatar.jpg` và scan media.
  4. `VERIFY & REPORT`: Chụp ảnh `avatar-uploaded-confirmed.png` và cập nhật kết quả.

## 3. Quy trình chuẩn 2 bước dứt điểm (Zero-New-Script)
Khi nhận yêu cầu đổi avatar:
1. **Khâu 1 (Chuẩn bị ảnh chuẩn):**
   - Trích xuất frame nét từ video nuôi thực tế `D:/TIKTOK-videonuoinick/<folder>/<N>.mp4`.
   - Crop cận cảnh 512x512, tạo preview mask tròn, soi mắt qua `browser_vision` xác nhận chính chủ creator.
   - Ghi đè vào cả 2 đầu: `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg` và `D:/video goc/<folder>/avatar.jpg`.
2. **Khâu 2 (Chạy runner chuẩn):**
   - Chạy trực tiếp `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Tik> --machine <Machine>` qua `terminal(background=True, notify_on_complete=True)`.
   - CẤM TUYỆT ĐỐI viết thêm bất kỳ script `execute_*.py` hay `run_avatar_m<N>.py` nào mới!
