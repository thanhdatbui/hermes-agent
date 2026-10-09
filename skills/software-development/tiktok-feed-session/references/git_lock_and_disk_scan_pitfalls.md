# Pitfalls: Git Index Lock & Broad Disk Scan trong TikTok Farm Workflows

## 1. Tránh Quét Đĩa Diện Rộng (Broad Disk Scan)
- **Vấn đề:** Chạy `os.walk('D:/Taadaa')`, `glob(recursive=True)` hoặc `find` trên thư mục gốc `D:/Taadaa` sẽ duyệt qua hàng trăm nghìn file (node_modules, python venv, logs, artifacts khổng lồ). Điều này dẫn tới:
  - Command timeout (900s).
  - Cạn kiệt số lượt gọi tool (tool turn budget limit) của agent trước khi kịp hoàn thành nhiệm vụ chính.
- **Giải pháp:**
  - Định vị chính xác đường dẫn file hoặc thư mục cần tìm thay vì quét cả ổ/cả cây thư mục cha.
  - Sử dụng lệnh kiểm tra tập trung: `python D:/Taadaa/tools/inspect_machine.py <N>`.

## 2. Xử Lý Sự Cố Git Index Lock & Staged Index
- **Hiện tượng:**
  `fatal: Unable to create 'D:/Taadaa/tiktok-luot nuoi acc/.git/index.lock': File exists.`
- **Nguyên nhân:**
  - Có một tiến trình git chạy ngầm bị treo hoặc phiên terminal trước bị kill đột ngột để lại file lock 0 byte.
- **Cách khắc phục nhanh:**
  1. Kiểm tra tiến trình git chạy ngầm: `ps aux | grep git`
  2. Kill tiến trình treo: `kill -9 <PID>`
  3. Xóa lock file tồn đọng: `rm -f .git/index.lock`
  4. Luôn kiểm tra `git status -u` để biết file đang ở staged (`Changes to be committed`) hay unstaged trước khi chạy `git checkout -- <file>` hoặc `git restore --staged <file>`.
