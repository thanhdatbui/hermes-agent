# Kỷ luật Git Pull & Đồng bộ Đa Repo Farm Taadaa

## 1. Danh sách các Repo Cốt lõi Nuôi Acc & Vận hành Farm
Khi nhận yêu cầu cập nhật / pull code cho cụm nuôi acc hoặc hệ thống farm:
- `D:/Taadaa/tiktok-luot nuoi acc` (Feed runner & launcher — branch `master`)
- `D:/Taadaa/automation-core` (Shared control plane, lock, preflight — branch `master`)
- `D:/Taadaa/tiktok-follow` (Follow runner — branch `master`)
- `D:/Taadaa/tiktok-log-in` (Login consumer — branch `main`)
- `D:/Taadaa/Tiktok_Reg` (Đăng ký tài khoản — branch `main`)
- `D:/Taadaa/Tiktok-video` (Download, render, uploader — branch `main`)
- `D:/Taadaa/tiktok-add-bao-mat-f2a` (Batch 2FA & mật khẩu — branch `main`)
- `D:/Taadaa/tools` (Hạ tầng watchdog, dashboard, scripts chẩn đoán máy — branch `main`)
- Các repo liên quan khác: `D:/Taadaa/Hotmail` (`master`), `D:/Taadaa/register gmail` (`main`), `D:/Taadaa/Hermes` (`main`).

## 2. Pitfall Git trên Windows MSYS Bash (`git -C` vs `cd`)
- **Triệu chứng lỗi**: Chạy `git -C "/d/Taadaa/..."` báo:
  `fatal: cannot change to '/d/Taadaa/...': No such file or directory`
- **Nguyên nhân**: Binary `git.exe` của Windows không nhận dạng cú pháp đường dẫn MSYS POSIX `/d/...` khi nhận qua đối số `-C`.
- **Giải pháp chuẩn**: Luôn dùng subshell chuyển thư mục:
  ```bash
  (cd "$repo_dir" && git pull)
  ```
  hoặc truyền định dạng Windows path: `git -C "D:/Taadaa/..." pull`.

## 3. Pitfall Remote Fork vs Upstream (`D:/Taadaa/Hermes`)
- **Triệu chứng lỗi**: Chạy `git pull` trần tại `D:/Taadaa/Hermes` báo lỗi:
  `fatal: refusing to merge unrelated histories`
- **Nguyên nhân**: `D:/Taadaa/Hermes` cấu hình 2 remotes:
  - `origin`: Upstream repo chính (`NousResearch/hermes-agent.git`)
  - `fork`: Repo cá nhân của Farm (`thanhdatbui/hermes-agent.git`)
  Lệnh `git pull` không có tham số sẽ tự trỏ về `origin/main` thay vì fork.
- **Quy tắc**: BẮT BUỘC chỉ định rõ remote khi thao tác với Hermes:
  ```bash
  (cd "D:/Taadaa/Hermes" && git fetch fork && git merge fork/main)
  # hoặc
  (cd "D:/Taadaa/Hermes" && git pull fork main)
  ```

## 4. Quy trình Pull Đảm bảo An toàn Hệ thống Farm
1. Kiểm tra trạng thái dirty files và unpushed commits trước:
   ```bash
   (cd "$repo" && git status -uno)
   ```
2. Fetch trước để xác định độ lệch:
   ```bash
   (cd "$repo" && git fetch origin)
   ```
3. Nếu branch local có commit mới (ahead) hoặc working directory có chỉnh sửa dở dang cho ca nuôi/watchdog, tuyệt đối không dùng `git pull --rebase` mù quáng để tránh conflict làm treo cron nền.
