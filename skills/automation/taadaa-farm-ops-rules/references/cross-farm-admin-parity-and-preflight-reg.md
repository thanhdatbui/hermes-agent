# Cross-Farm Admin Parity, Preflight Auto-Reg, and Workbook Dynamic Mapping

*Date: 2026-09-24 | Author: Hermes Coordinator*

## 1. Nguyên Tắc Bất Biến: Parity 100% Kibe & Admin
- **Quy tắc**: Mọi cơ chế tự động hoá, preflight check, watchdog kiểm tra sức khoẻ, nạp tài khoản và reg bù có trên cụm Kibe (máy 1–80) **BẮT BUỘC PHẢI ÁP DỤNG TƯƠNG ĐƯƠNG CHO CỤM ADMIN (máy 201–280)**.
- **Cấm tuyệt đối**: Hardcode điều kiện chặn cục bộ như `if cluster_name == "kibe":` trong bất kỳ runner hoặc watchdog nào.
- **Cluster Parameterization**: Mọi hàm điều phối runner (`tiktok_runner.py`) phải nhận object `cluster`, truyền đúng `host_config` và `adb_server_socket`.

## 2. Định Tuyến Mạng & ADB Server Cụm Admin
- **Môi trường**: Cụm Admin (80 máy) kết nối qua ADB Server từ xa tại `tcp:192.168.110.119:5037`.
- **Cấu hình**:
  - `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml"`
  - `ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"`
- **Auto-Routing trong Tool**: Khi tool (`ensure_row_accounts.py`, `_run_all_targets.py`) chạy cho `HOST_ID == "admin"` từ máy Kibe (hostname không chứa 'admin'), phải tự động cấu hình fallback `ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"` và ghi telemetry log:
  ```python
  if HOST_ID == "admin" and "ADB_SERVER_SOCKET" not in env:
      try:
          import socket
          if "admin" not in socket.gethostname().lower():
              env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
              print(f"[telemetry] Auto-configured ADB_SERVER_SOCKET={env['ADB_SERVER_SOCKET']} for host {HOST_ID}")
      except Exception:
          pass
  ```

## 3. Mapping Workbook & Cơ Chế Dynamic Append (Admin vs Kibe)
- **Kibe (máy 1–80)**: Workbook `taikhoan_dat_v2_updated .xlsx` có cấu trúc lưới cố định 640 dòng. Hàng tương ứng với máy `m` và slot `slot` có thể tính bằng `(m - 1) * 8 + slot`.
- **Admin (máy 201–280)**:
  - Công thức STT Tik: `expected_tik = (m - 201) * 8 + slot`.
  - Workbook Admin là file động, chỉ gồm các hàng tài khoản đã tạo thực tế (không có sẵn hàng trống cho mọi slot).
  - **Dynamic Append Rule**: Trong hàm `apply_results`, khi tra cứu không thấy `target_row` đã có sẵn trong sheet cho cặp `(m, slot)`, **BẮT BUỘC tự động append vào cuối sheet**:
    ```python
    expected_tik = (m - 201) * 8 + slot if m >= 201 else (m - 1) * 8 + slot
    # Tra cứu hàng hiện có...
    if target_row is None:
        target_row = ws_trk.max_row + 1
        appended_count += 1
        print(f"[telemetry] STT {m} Slot {slot} appended to new row {target_row} with expected_tik={expected_tik}")
    ```
  - **CẤM TUYỆT ĐỐI** bỏ qua (`skipped_count += 1; continue`) khi không tìm thấy hàng tĩnh, vì sẽ làm mất kết quả reg thành công của các máy Admin.

## 4. Vòng Đời Preflight Marker & Cơ Chế Fail-Open (Chống Deadlock)
- **Marker theo cụm**: Tách biệt file marker để hai cụm không chặn nhau: `.preflight_{cluster_name}_{window_key}`.
- **Marker Payload có cấu trúc (JSON)**:
  ```json
  {
    "timestamp": "2026-09-24T04:15:00",
    "cluster": "admin",
    "row": 5,
    "status": "running"
  }
  ```
- **Fail-Open Lifecycle**:
  - Khi bắt đầu: ghi marker với `status: "running"`.
  - Nếu lệnh subprocess hoàn tất thành công (`returncode == 0`): cập nhật `status: "success"` và `completed_at`.
  - Nếu lệnh subprocess thất bại (`returncode != 0`) hoặc dính Exception: **BẮT BUỘC xóa marker (`marker.unlink(missing_ok=True)`)** để ca/tick tiếp theo tiếp tục thử lại.
  - *Cấm tuyệt đối để marker tồn tại khi lệnh thất bại, vì sẽ gây kẹt deadlock preflight suốt cả khung giờ.*

## 5. Reviewer Sol Auditor Criteria Checklist
Trước khi chốt phiên có thay đổi liên quan đến mapping hoặc preflight:
1. `Logic Correctness`: Helper tính `expected_tik` phải xử lý mượt cả `m <= 80` và `m >= 201`.
2. `Test Evidence`: Bắt buộc viết unit test bao phủ:
   - Ánh xạ `expected_tik` cho dải admin (`m=201 -> 5`, `m=202 -> 13`).
   - Dynamic append vào workbook khi sheet rỗng/thiếu hàng và kiểm tra telemetry `appended == 1`.
   - Auto-config ADB server socket khi chạy admin trên máy Kibe.
   - Fail-open cleanup marker khi subprocess fail (`returncode != 0`).
3. `Telemetry & Observability`: In log `[telemetry]` rõ ràng và xuất metric ra file JSON (`last_merge_metrics.json` gồm `applied`, `appended`, `rejected_duplicate_uid`, `skipped`).
