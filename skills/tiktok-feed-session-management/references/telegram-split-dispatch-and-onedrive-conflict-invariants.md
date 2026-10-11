# Telegram Split Dispatch & Dual-Farm Safe Workbook Invariants

## 1. Telegram Multi-Channel Dispatch Separation Invariant

### Ngữ cảnh & Nguyên tắc cốt lõi:
Hệ thống báo cáo nuôi nick TikTok phân chia độc quyền theo 3 nhóm Telegram:
- **Nhóm Tiktok Luot Nuoi Acc (`-5377611430`)**: CHỈ nhận báo cáo Lướt Feed qua stdout cronjob.
- **Nhóm Tiktok Follow (`-5127276494`)**: Nhận độc quyền toàn bộ block Follow chéo (Success, Nhả follow, Cầu dao IP, Bỏ qua, v.v.).
- **Nhóm Tiktok Video (`-5435853713`)**: Nhận độc quyền toàn bộ block Đăng Video (Success, Timeout, Lỗi script, Bỏ qua, v.v.).

### Cấm tuyệt đối:
- **CẤM append dòng tóm tắt Follow/Upload vào nhóm Feed**: Tuyệt đối không append `fl_s[0]` hay `up_s[0]` vào `feed_p` trong `dispatch_split_reports()`. Nhóm `Tiktok Luot Nuoi Acc` phải 100% sạch sẽ, không chứa các dòng header cụt lủn làm người dùng nhầm lẫn rằng follow bị ném sai nhóm. Lọc `f_s` bắt buộc loại bỏ triệt để: `not l.startswith("• Follow chéo") and not l.startswith("• Đăng Video")`.
- **CẤM nuốt im lặng phần "Đối soát TikTok Web" (Silent Return Invariant)**:
  * Trong `reconcile_cluster_following()`, khi mở file workbook `taikhoan_run_safe.xlsx` (dễ dính lock do OneDrive sync), BẮT BUỘC có retry tối thiểu 3 lần (sleep 1s):
    ```python
    ws = None
    for _ in range(3):
        try:
            import openpyxl
            ws = openpyxl.load_workbook(wb_path, read_only=True).active
            break
        except Exception:
            time.sleep(1)
    if ws is None:
        return [f"  + Đối soát TikTok Web: Không đọc được workbook ({wb_path})"]
    ```
  * TUYỆT ĐỐI CẤM `return []` im lặng khi có máy follow phát sinh trong ca. Nếu đọc workbook thất bại sau retry hoặc không map được username (`if not m_to_user:` khi `target_machines` có máy follow), BẮT BUỘC xuất dòng cảnh báo rõ ràng `+ Đối soát TikTok Web: Không đọc được workbook (...)` hoặc `+ Đối soát TikTok Web: Không tìm thấy username trong workbook cho {len(target_machines)} máy follow` thay vì âm thầm bỏ qua, tránh làm bốc hơi toàn bộ mục đối soát web đã thiết kế chuẩn.
  * Nhóm Follow (`-5127276494`) BẮT BUỘC nhận trọn vẹn khối: `• Follow chéo` -> `+ Thành công` -> `+ Đối soát TikTok Web` -> `+ Nhả follow` -> `⚡ Cầu dao tự ngắt IP` -> `+ Lỗi script/xác minh` -> `+ Bỏ qua`.
- **Đồng bộ 2 chiều Repo <-> Cron Runner (Cron Deployment Invariant)**:
  * Cron job watchdog chạy script từ thư mục script của hệ thống.
  * Mã nguồn phát triển nằm tại repo `tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`.
  * Sau khi sửa và test xanh trên repo, BẮT BUỘC đồng bộ sang thư mục script thực thi của cron để phiên tự động tiếp theo lập tức áp dụng logic mới nhất, không để tình trạng repo đã vá nhưng cronjob vẫn chạy bản cũ.
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

---

## 3. Safe Workbook Row Count & Machine Slicing Invariant (640 vs 688 Pitfall)

### Nguy cơ nhầm lẫn số dòng (688 rows vs 640 rows):
- **Cụm Admin (201-280)**: 80 máy × 8 slot = **Đúng chính xác 640 dòng dữ liệu** (không tính header).
- **Cụm Kibe (1-80)**: 80 máy × 8 slot = 640 dòng base + 48 dòng từ `EXTRA_MACHINES` (máy 75-80) = **688 dòng dữ liệu**.
- **Nguyên nhân bug 688 row ở Admin**:
  - Trong `sync-safe-workbook.py`, biến `ACTIVE_EXTRA_MACHINES` kiểm tra `_is_kibe_host()`.
  - Nếu chạy script đồng bộ Admin mà không set `TAADAA_HOST_ID=admin`, hàm sẽ mặc định coi là host Kibe và nhét thêm 48 dòng của máy 75-80 vào file Admin, làm phình lên 688 dòng rác!
- **Invariant bất biến**:
  - File `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx` BẮT BUỘC phải có đúng **640 data rows**. Bất kỳ khi nào đếm ra 688 rows nghĩa là đã bị nhiễm `EXTRA_MACHINES` của Kibe.
  - Khi đồng bộ file Admin, BẮT BUỘC chạy qua `hermes_taikhoan_sync_cron.py` (đã truyền `TAADAA_HOST_ID=admin`) hoặc chạy script với cờ môi trường chuẩn.

---

## 4. Kiến trúc vận hành Dual-Farm (Kibe điều phối Admin)

### Bản chất kết nối:
- Cụm Kibe (`DESKTOP-3PFPGQC`, máy 1-80): chạy trực tiếp với local ADB.
- Cụm Admin (`Admin-PC`, máy 201-280): được Kibe điều phối từ xa qua **Remote ADB Server Socket (`tcp:192.168.110.119:5037`)**.
- Các thao tác bảo trì hệ thống/sync file giữa Kibe và Admin sử dụng SSH (`ssh admin-farm`) và thư mục chia sẻ OneDrive `D:\OneDrive\TaadaaData\admin\`.
- Khi runner báo skip Admin (0 account hợp lệ), nguyên nhân thường KHÔNG PHẢI do đứt SSH hay hỏng socket ADB, mà do OneDrive sync conflict làm mất file `taikhoan_run_safe.xlsx` trên đĩa. Luôn kiểm tra file workbook trước khi nghi ngờ hạ tầng mạng.

---

## 5. Pytest Duplicate Module Collision Invariant (`--import-mode=importlib`)

### Hiện tượng lỗi:
- Khi chạy `closeout_gate.py` hoặc pytest tổng hợp cho các module watchdog:
  ```text
  import file mismatch:
  imported module 'test_feed_session_watchdog' has this __file__ attribute:
    D:\Taadaa\tiktok-luot nuoi acc\tests\test_feed_session_watchdog.py
  which is not the same as the test file we want to collect:
    D:\Taadaa\tiktok-luot nuoi acc\python_runner\tests\test_feed_session_watchdog.py
  HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
  ```
- Nguyên nhân: Repo có 2 thư mục test (`tests/` và `python_runner/tests/`) cùng chứa file test có tên trùng nhau (`test_feed_session_watchdog.py`). Mặc định cơ chế import của pytest là `prepend` làm đè namespace module.

### Quy tắc xử lý chuẩn:
- Trong `pytest.ini` tại root repo, bắt buộc cấu hình:
  ```ini
  [pytest]
  asyncio_default_fixture_loop_scope = function
  addopts = --import-mode=importlib
  ```
- Chế độ `importlib` cô lập module theo từng path file độc lập, loại bỏ triệt để lỗi import file mismatch mà không cần đổi tên test file hay xóa `__pycache__` tạm bợ.
- `closeout_gate.py` ở Step 3 chạy quét đồng thời cả 2 file test; nếu thiếu option này sẽ fail gate ngay lập tức vì collection error.

---

## 6. Watchdog Cron Deployment & Drift Verification Checklist

1. **Vị trí script Cronjob:** Cron job `1d62cb3562e0` (`tiktok-feed-session-watchdog`) thực thi script từ `%LOCALAPPDATA%/hermes/scripts/feed_session_watchdog.py`.
2. **Kiểm tra đồng bộ sau khi vá repo:**
   - Sau khi commit/patch trên `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`, BẮT BUỘC copy đè sang `%LOCALAPPDATA%/hermes/scripts/feed_session_watchdog.py`.
   - Kiểm tra SHA-256 / byte hash để xác nhận hai file trùng khớp hoàn toàn (`Identical: True`).
   - Chạy `python -m py_compile "$LOCALAPPDATA/hermes/scripts/feed_session_watchdog.py"` đảm bảo không có lỗi cú pháp.
3. **Tuyệt đối không bỏ sót bước copy:** Nếu chỉ sửa trong repo mà quên copy sang `%LOCALAPPDATA%`, cronjob vẫn chạy code cũ và tiếp tục gửi report sai format hoặc nuốt đối soát.
