# Telegram Split Dispatch & Dual-Farm Safe Workbook Invariants

## 1. Telegram Multi-Channel Dispatch Separation Invariant

### Ngữ cảnh & Nguyên tắc cốt lõi:
Hệ thống báo cáo nuôi nick TikTok phân chia độc quyền theo 3 nhóm Telegram:
- **Nhóm Tiktok Luot Nuoi Acc (`-5377611430`)**: CHỈ nhận báo cáo Lướt Feed qua stdout cronjob.
- **Nhóm Tiktok Follow (`-5127276494`)**: Nhận độc quyền toàn bộ block Follow chéo (Success, Nhả follow, Cầu dao IP, Bỏ qua, v.v.).
- **Nhóm Tiktok Video (`-5435853713`)**: Nhận độc quyền toàn bộ block Đăng Video (Success, Timeout, Lỗi script, Bỏ qua, v.v.).

### Cấm tuyệt đối:
- **CẤM append dòng tóm tắt Follow/Upload vào nhóm Feed**: Tuyệt đối không append `fl_s[0]` hay `up_s[0]` vào `feed_p` trong `dispatch_split_reports()`. Nhóm `Tiktok Luot Nuoi Acc` phải 100% sạch sẽ, không chứa các dòng header cụt lủn làm người dùng nhầm lẫn rằng follow bị ném sai nhóm.
- **CẤM nuốt lỗi dispatch ở kênh phụ**: Khi gửi bản tin sang `-5127276494` và `-5435853713`, không được nuốt exception trong khối `try...except` một cách im lặng. Phải có cơ chế retry tối thiểu 3 lần (timeout 15s) và ghi log telemetry `[WATCHDOG_TELEGRAM_DISPATCH_FAIL]` khi rớt kết nối.

---

## 2. Dual-Farm OneDrive Conflict & Safe Workbook Invariant

### Hiện tượng OneDrive Sync Conflict:
- Khi cả hai máy Master Kibe (`DESKTOP-3PFPGQC`, 1-80) và Farm Admin (`Admin-PC`, 201-280) cùng đồng bộ vào thư mục chia sẻ `D:\OneDrive\TaadaaData\admin\`, OneDrive có thể tự động sinh ra các bản sao xung đột dạng `taikhoan_run_safe-Admin-PC-XX.xlsx` hoặc `taikhoan_run_safe-DESKTOP-3PFPGQC-XX.xlsx`.
- Hậu quả: File gốc `taikhoan_run_safe.xlsx` bị đổi tên hoặc không tồn tại trên đĩa local.
- Khi `tiktok_runner.py` kích hoạt: Đọc thấy file safe không tồn tại -> `valid_count == 0` -> Skip ca chạy của cụm Admin.

### Quy tắc an toàn bắt buộc:
1. **Kiểm tra liveness của file đích (Safe Target Liveness)**:
   - Trong `hermes_taikhoan_sync_cron.py`, không được chỉ kiểm tra `source_sig` không đổi để thoát sớm (`return 0`).
   - Bắt buộc kiểm tra `output.exists()`. Nếu file safe đích bị mất hoặc bị conflict đổi tên, phải cưỡng bức chạy lại `sync-safe-workbook.py` để tái tạo ngay lập tức.
   - Cấm dùng `if not output.exists(): continue` trong vòng lặp cập nhật.
2. **Quy tắc hiển thị Watchdog toàn Farm (Full Cluster Visibility)**:
   - Trong `feed_session_watchdog.py`, khi một cụm (như Admin) chưa có folder ngày hoặc không có session chạy, watchdog BẮT BUỘC phải ghi nhận block thông báo:
     ```text
     🏢 【FARM ADMIN - MÁY 201-280】
     • Trạng thái: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)
     ```
   - CẤM TUYỆT ĐỐI `if not os.path.exists(date_live): continue` âm thầm bỏ qua cluster, làm cụm Admin biến mất hoàn toàn khỏi báo cáo tổng kết.
