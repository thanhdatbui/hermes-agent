# Cold-Backup Host Sync Cadence & Git Lock Prevention

## Bối cảnh Kiến trúc (Kibe Master vs Admin Cold Backup)
- **Vai trò thực tế:** Kibe là Master điều phối toàn bộ 160 máy Farm (cả dải Kibe 1–80 và Admin 201–280 qua remote ADB). Hermes trên Admin chỉ đóng vai trò **Cold Backup** (dự phòng ngoại tuyến, chỉ kích hoạt khi Kibe gặp sự cố phần cứng).
- **Nguyên lý nhịp đồng bộ:** Khi máy phụ chỉ là backup, đồng bộ hạ tầng (skills, memories, SOUL, jobs) KHÔNG ĐƯỢC chạy với tần suất dồn dập của môi trường real-time.

## Tác hại của Tần suất Sync Dày (5m / 15m) trên Master Kibe
1. **Tranh chấp Git Index Lock (`.git/index.lock`):**
   - Khi cron `sync-hermes-skills-and-brain-to-git` chạy mỗi 5 phút (`git add`, `git commit`, `git push`), nó liên tục khóa repository `D:\Taadaa\Hermes`.
   - Nếu Coordinator hoặc Worker đang thực hiện commit, diff hoặc chạy `closeout_gate.py`, tiến trình sẽ va chạm lock và crash ngay lập tức.
2. **Nghẽn I/O Ổ đĩa (Disk Contention):**
   - Script gọi `robocopy` quét đệ quy hơn 4.500 thư mục/file skills mỗi 300 giây. Quét sâu liên tục cạnh tranh băng thông I/O với các tác vụ farm nặng (render clip, download video, đọc receipt).
3. **Quá tải Mạng & Treo Tiến trình (Push Exhaustion):**
   - Đẩy code 288 lần/ngày (`git push fork main`) tăng tỷ lệ rớt mạng, socket timeout, làm tiến trình PowerShell bị ngậm nền và kích hoạt báo động sai ở `hermes-stale-watchdog`.
4. **Xung đột Khóa File OneDrive:**
   - Việc ghi đè file `jobs.json` và scripts vào thư mục `D:\OneDrive\Taadaa_Sync_Shared\` mỗi 15 phút dễ bị tiến trình OneDrive sync client lock tạm thời để tải lên cloud, gây lỗi `PermissionError` hoặc conflict file rác.

## Quy chuẩn Phân cấp Nhịp Đồng bộ (Sync Cadence Governance)

| Loại Tác Vụ Sync | Mục Đích | Tần Suất Chuẩn | Ghi Chú |
|---|---|---|---|
| **Hạ tầng Hermes (`skills`, `SOUL.md`, `memories`)** | Backup não trợ lý lên Git | **Mỗi 6 tiếng (`0 */6 * * *`)** hoặc **1 lần/ngày (04:00 sáng)** | Triệt tiêu xung đột git lock, giảm 96% số lần robocopy đĩa. |
| **Watchdog Sync Cron/Scripts (`cron_sync_watchdog.py`)** | Đồng bộ jobs và script sang Deploy / OneDrive | **Mỗi 6 tiếng (`0 */6 * * *`)** | Giảm thiểu xung đột lock file trên OneDrive Shared. |
| **Dữ liệu Vận hành Máy Thật (`taikhoan_run_safe_sync`)** | Đồng bộ Excel chia ca nuôi nick realtime | **Mỗi 5 phút (`*/5 * * * *`)** | BẮT BUỘC giữ nguyên 5 phút vì phục vụ chia slot nuôi acc máy thật. |
