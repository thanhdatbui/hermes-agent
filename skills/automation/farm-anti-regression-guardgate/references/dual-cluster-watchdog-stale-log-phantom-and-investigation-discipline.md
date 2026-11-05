# Dual-Cluster Watchdog Stale-Log Phantom Merging & Investigation Ground Truth

## 1. Bản chất sự cố (Incident Ground Truth)
Khi phân tích báo cáo Farm tổng hợp từ 2 cụm máy (Kibe Local + Admin Remote SSH):
* **Lỗi 1 (Đoán mò / Ảo giác lý thuyết):** Khi thấy báo cáo lặp lại nhiều lần, Coordinator tự vẽ ra lý thuyết "hệ thống thấy fail nên thông minh tự chạy vét đợt 2" mà không kiểm tra timestamp thực tế của thư mục log trên đĩa.
* **Lỗi 2 (Bẫy Stale-Log Phantom Merging):** Trong script watchdog (`cron_night_tiktok_2fa_watchdog.py`), hàm `read_admin_gmail_summary_remote` truy vấn file `summary.json` mới nhất trên máy Admin nhưng **thiếu bộ lọc thời gian tối thiểu của ca hiện tại (`min_mtime`)**.
  - Khi Admin không chạy (ví dụ thiếu file thực thi `gmail_reg_v10.py` trên Admin), truy vấn SSH trả về file `summary.json` của ngày hôm trước (04/11).
  - Watchdog trên Kibe lấy kết quả mới của Kibe cộng dồn với kết quả cũ của Admin, tạo ra số liệu ảo, che giấu sự thật là Admin đã offline/crash toàn bộ ca đêm.

## 2. Kỷ luật điều tra bắt buộc (Investigation Discipline)
1. **Kiểm tra Mtime thật trước khi kết luận:** BẮT BUỘC dùng lệnh kiểm tra `created_at` hoặc `LastWriteTime` của từng file `summary.json` trên cả 2 máy (Kibe và Admin) trước khi đưa ra nhận định.
2. **Không tự bịa lý thuyết điều phối:** Cấm suy diễn "chạy bù / chạy vét / tự retry" khi chưa thấy cờ logic tương ứng trong code (`already_ran_gmail_tonight` thực tế chỉ kiểm tra theo ngày).

## 3. Khóa cơ học PowerShell Remote Query
Câu lệnh truy vấn file kết quả từ Admin qua `admin_ssh.py` BẮT BUỘC:
1. Có bộ lọc chặn thời gian tối thiểu `min_mtime` được format sang `YYYY-MM-DD HH:MM:SS`.
2. Dùng pipeline an toàn, bắt đầu bằng `Get-ChildItem` (nằm trong allowlist):
   ```powershell
   Get-ChildItem -Path 'D:\CodexRuntime\codex_gmail_debug-register-gmail\logs_parallel_*\summary.json' -ErrorAction SilentlyContinue |
   Where-Object { $_.LastWriteTime -ge (Get-Date '<min_date_str>') } |
   Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content -Raw -Encoding UTF8
   ```
3. Tuyệt đối không bọc kiểu `Get-Content (...).FullName` vì nếu không có file nào thỏa điều kiện `Where-Object`, `(...)` trả về `$null` khiến `Get-Content` ném exception thay vì trả về chuỗi rỗng an toàn.
