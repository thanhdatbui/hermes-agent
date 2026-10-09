# Cross-Farm Admin Reg Parity & Workbook Mapping Guide

## 1. Kiến Trúc Dual-Cluster & Kết Nối Thiết Bị
- **Cụm Kibe (Máy 1 - 80)**:
  - Host config: `D:/Taadaa/machine-config/kibe.yaml`
  - ADB Server: Local daemon `127.0.0.1:5037`
  - Workbook: `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx`
  - Projection: `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx`
- **Cụm Admin (Máy 201 - 280)**:
  - Host config: `D:/Taadaa/machine-config/admin.yaml`
  - ADB Server: Remote ADB PortProxy `tcp:192.168.110.119:5037`
  - Workbook: `D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx`
  - Projection: `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx`

## 2. Các Bẫy Sống Còn & Cách Xử Lý (Pitfalls)

### Bẫy 1: Runner Chặn Cục Bộ Cụm Admin (Hardcoded cluster filter)
- **Hiện tượng**: `tiktok_runner.py` có điều kiện `if cluster_name == "kibe": _preflight_ensure_accounts(...)` khiến cụm Admin không bao giờ được tự động reg bù khi thiếu nick.
- **Quy tắc Parity 100%**: Tuyệt đối không hardcode riêng cho Kibe. Cả 2 cụm đều phải chạy preflight trước mỗi ca:
  ```python
  _preflight_ensure_accounts(row, window_key, cluster=cluster)
  ```
- Phải inject đầy đủ `TAADAA_HOST_CONFIG` và `ADB_SERVER_SOCKET` tương ứng với từng cluster.

### Bẫy 2: Marker Preflight Xung Đột Giữa Các Cụm (Starvation)
- **Hiện tượng**: Marker đặt tên chung `.preflight_{window_key}`. Cụm nào chạy trước sẽ tạo marker, khiến cụm chạy sau bị skip hoàn toàn.
- **Khắc phục**: Bắt buộc marker phải scoped theo cluster:
  ```python
  marker = cluster_state_dir / f".preflight_{cluster_name}_{window_key}"
  ```

### Bẫy 3: Điều Tuyến ADB Socket Khi Chạy Reg Admin Từ PC Kibe
- **Hiện tượng**: Chạy `ensure_row_accounts.py` hoặc `_run_all_targets.py` trên PC Kibe nhưng nhắm vào máy 201-280 mà không truyền `ADB_SERVER_SOCKET` dẫn đến script kết nối vào ADB local của Kibe và báo `device not found` hoặc timeout.
- **Khắc phục**:
  Trong script wrapper/launcher, nếu `HOST_ID == "admin"` và `ADB_SERVER_SOCKET` chưa có, tự động gán:
  ```python
  if HOST_ID == "admin" and "ADB_SERVER_SOCKET" not in env:
      if "admin" not in socket.gethostname().lower():
          env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
  ```

### Bẫy 4: Ánh Xạ Row & Folder Video Trong Workbook Admin (201-280)
- **Kibe (1 - 80)**: Bảng tính có sẵn 640 dòng cố định (8 slot/máy).
  `expected_tik = (m - 1) * 8 + slot`
  Dòng đích: `target_row = (m - 1) * 8 + slot + 1`
- **Admin (201 - 280)**:
  `expected_tik = (m - 201) * 8 + slot`
  Workbook Admin là dạng bổ sung dòng động (dynamic append). Nếu duyệt qua toàn bộ sheet mà không thấy dòng trống khớp slot thì:
  **TUYỆT ĐỐI CẤM BỎ QUA** ("Không tìm thấy target row cho STT m Slot slot, bo qua").
  Bắt buộc tự động append vào cuối sheet:
  ```python
  if target_row is None:
      target_row = ws_trk.max_row + 1
  ```

### Bẫy 5: Follow Chéo 0 Lượt Do Safety Gate < 10 Video
- Trong ca nuôi feed (`multi_machine_feed_session.py`), tài khoản có `< 10` video đã đăng sẽ tự động kích hoạt chế độ an toàn `under-10-videos-follow-disabled` để tránh TikTok quét nhả follow hoặc checkpoint.
- Khi Telegram Watchdog báo cáo Module 1 & 2 là 0 lượt follow và liệt kê trong nhóm "Bỏ qua: Chưa đủ 10 video", đây là tính năng an toàn bình thường, không phải lỗi rớt mạng hay hỏng script.
