# TikTok Login Reconcile & Missing Account Recovery Patterns

## 1. Cạm bẫy đối soát tài khoản và nhầm lẫn Serial
- Khi nhiều máy chạy đồng thời (multi-machine / batch), log của các máy có thể bị xen lẫn vào cùng một file log (ví dụ: `social_reg_log.txt`).
- **Bài học xương máu**: TUYỆT ĐỐI KHÔNG vội vàng kết luận "máy A ngậm nhầm dàn nick của máy B" chỉ dựa vào việc nhìn thấy danh sách nick trong log chung. Luôn dùng ADB trực tiếp trên serial của máy (`adb -s <serial> exec-out screencap -p` hoặc dump UI) để kiểm tra màn hình Switcher thực tế.

## 2. Kịch trần 8 tài khoản trên App TikTok
- Khi app TikTok trên thiết bị đã đủ 8 nick đăng nhập, nút **"Thêm tài khoản"** (`Add account`) sẽ bị ẩn hoàn toàn khỏi giao diện bottom sheet.
- Bất kỳ script nào cố gắng tìm nút "Thêm tài khoản" sẽ bị timeout hoặc văng lỗi `MACHINE_FULL_8_ACCOUNTS`.
- Kiểm tra danh sách nick hiện có trên máy xem có nick nào chưa đủ điều kiện cần logout/dọn dẹp trước khi nạp nick mới.

## 3. Tự động gọi Engine Login từ Upload Workflow
- Script cầu nối: `D:/Taadaa/tools/recover_missing_tiktok_login.py`.
- Lệnh gọi chuẩn:
  ```bash
  python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <user> --ss --allow-parent-lock
  ```
- **Kế thừa lock**: Bắt buộc có cờ `--allow-parent-lock` để không bị kẹt `DeviceLockNeedsUserDecision` khi session mẹ (`tiktok-luot nuoi acc` hoặc batch runner) đang giữ lock thiết bị.
