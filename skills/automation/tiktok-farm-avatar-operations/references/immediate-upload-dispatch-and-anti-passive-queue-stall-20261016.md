# Bẫy Nằm Im Chờ Watchdog Khi User Đã Chốt Avatar (Anti-Passive-Queue-Stall Invariant)

## Bối cảnh sự cố (16/10/2026)
- **Tình huống:** Khi User phát lệnh "Chuẩn hoá acc này" và sau khi Coordinator gửi 2 phương án avatar, User phản hồi chốt "1".
- **Hành vi sai lầm của Coordinator:**
  * Đồng bộ file ảnh vào $F_{src}$ và $F_{out}$.
  * Cắm marker `.manual_avatar_locked` và ghi registry `protected_folders`.
  * Cập nhật `avatar_replace_queue` sang `PENDING` trong SQLite.
  * **DỪNG LẠI và báo cáo:** *"Hệ thống đang chạy nền, watchdog sẽ tự động nạp ảnh trong chu kỳ 5 phút..."*.
- **Phản ứng gay gắt từ User:** *"Sao k up luôn mà phải chờ v"* (Tại sao không up luôn mà phải chờ?!).

## Nguyên tắc cốt lõi: Invariant End-to-End "Cấm Dừng Chờ Giục"
Quy trình Chuẩn hoá 3 Món (Ava - Hashtag - Pin) là một quy trình **Đóng Kín Dứt Điểm (End-to-End)**:
1. `Crop 512x512` -> Soi mắt 2 phương án.
2. User chốt phương án -> `Sync files & Lock markers`.
3. **KÍCH HOẠT RUNNER NẠP APP NGAY LẬP TỨC (MANDATORY IMMEDIATE DISPATCH):** Tuyệt đối CẤM dừng lại ở bước nạp queue chờ cronjob/watchdog định kỳ. Phải gọi ngay runner upload avatar của Farm cho đúng số máy vừa chốt.
4. Chụp ảnh màn hình Profile nghiệm thu thực tế -> Soi mắt kiểm định qua `browser_vision` -> Gửi `MEDIA:<path>` cho User.

## Lệnh Kích Hoạt Runner Upload Avatar Tức Thì

### 1. Cụm Kibe Local (Máy 1 - 80):
Gọi PowerShell launcher chính thức của Farm qua runner script hoặc background process:
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1" `
  -Tik <tik_slot> `
  -ForceAvatarMachineList "<machine_id>" `
  -MaxParallel 1 `
  -HostConfigPath "D:\Taadaa\machine-config\kibe.yaml"
```
*Lưu ý:* Khi gọi qua Python subprocess, truyền stdin input `b"RUN\r\n"` hoặc `input="RUN\n"` để vượt qua bước xác nhận tương tác.

### 2. Cụm Admin Remote (Máy 201 - 280):
Kích hoạt trực tiếp trên host Admin qua `admin_ssh.py` (tránh chạy local bị ngắt kết nối USB/ADB):
```bash
python D:/Taadaa/tools/admin_ssh.py "python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <tik_slot> --machine <machine_id>"
```

## Checklist Chống Bẫy Nằm Im Chờ Watchdog
- [ ] User gửi tin nhắn chốt số phương án (`1`, `2`, `PA1`...).
- [ ] Sao chép avatar đã chọn vào $F_{src}$, $F_{out}$, cắm marker `.manual_avatar_locked`.
- [ ] Cập nhật trạng thái `PENDING` vào SSOT (`Tik<N>.xlsx` và `avatar_replace_queue`).
- [ ] **Lập tức dispatch worker hoặc background process kích hoạt runner `run_tiktok_upload_avatar.ps1`**.
- [ ] Báo User: *"Đang nạp trực tiếp avatar lên app TikTok Máy N..."* (Kèm lệnh runner đang thực thi).
- [ ] Chờ runner hoàn tất, screencap màn hình Profile thực tế, soi mắt kiểm định và gửi `MEDIA:`.
