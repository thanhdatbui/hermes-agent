# Admin Cluster Slot Mapping & Preflight Reg Parity

## 1. Bối cảnh & Nguyên tắc Parity Tuyệt đối (Cross-Farm Parity)
- Farm có 2 cụm máy chính:
  + **Kibe Farm**: Máy 1 – 80 (80 thiết bị local ADB `127.0.0.1:5037`). Workbook: `D:\OneDrive\TaadaaData\kibe`. Host config: `D:\Taadaa\machine-config\kibe.yaml`.
  + **Admin Farm**: Máy 201 – 280 (80 thiết bị remote ADB `tcp:192.168.110.119:5037`). Workbook: `D:\OneDrive\TaadaaData\admin`. Host config: `D:\Taadaa\machine-config\admin.yaml`.
- **Nguyên tắc Invariant**: Cụm Kibe có tính năng tự động gì thì cụm Admin bắt buộc phải có tính năng tương đương. CẤM TUYỆT ĐỐI hardcode bỏ qua Admin (`if cluster_name == "kibe"`).

---

## 2. Preflight Dual-Cluster trong `tiktok_runner.py`
Trước mỗi ca chạy (window), `tiktok_runner.py` phải kiểm tra số lượng tài khoản của Row sắp chạy và tự động gọi `ensure_row_accounts.py` reg bù nếu phát hiện thiếu:
1. **Marker Scoped theo Cluster**:
   - Marker file đặt tên: `.preflight_{cluster_name}_{window_key}` trong thư mục `state_dir` của cluster đó.
   - Tránh việc 1 cluster chạy xong tạo marker chung làm cluster còn lại bị skip oan.
2. **Environment Routing**:
   - Khi chạy cho Admin, bắt buộc inject:
     * `TAADAA_HOST_CONFIG = "D:/Taadaa/machine-config/admin.yaml"`
     * `ADB_SERVER_SOCKET = "tcp:192.168.110.119:5037"`
3. **Fail-Open Lifecycle cho Marker**:
   - Nếu tiến trình `ensure_row_accounts.py` bị lỗi (returncode != 0 hoặc exception), BẮT BUỘC xóa marker (`marker.unlink(missing_ok=True)`).
   - Điều này đảm bảo tick 15 phút tiếp theo của cron runner có cơ hội thử lại, thay vì bị kẹt "đã chạy" suốt cả ca 3 tiếng.

---

## 3. Công thức Ánh xạ STT Tik (Folder Video) & Slot
Mỗi máy hỗ trợ tối đa 8 tài khoản (Slot 1..8, tương ứng Folder Video modulo 8):
- **Cụm Kibe (Máy 1..80)**:
  `expected_tik = (m - 1) * 8 + slot` (Dải giá trị: 1 .. 640)
- **Cụm Admin (Máy 201..280)**:
  `expected_tik = (m - 201) * 8 + slot` (Dải giá trị: 1 .. 640)
- **Hàm chuẩn hóa canonical**:
  ```python
  def get_expected_tik(m: int, slot: int) -> int:
      return (m - 201) * 8 + slot if m >= 201 else (m - 1) * 8 + slot
  ```

---

## 4. Xử lý Workbook Động (Dynamic Append) vs Workbook Tĩnh
- `taikhoan_dat_v2_updated .xlsx` của Kibe được dàn sẵn 640 dòng (80 máy x 8 slot).
- `taikhoan_dat_v2_updated .xlsx` của Admin là workbook khởi tạo động, chỉ có dòng khi tài khoản được nạp vào.
- **Quy tắc khi merge kết quả reg (`apply_results`)**:
  - Tra cứu theo cặp `(c1 == m and c2 in (expected_tik, slot))`.
  - Nếu `target_row is None`: Với Admin hoặc máy ngoài dải 1..80, **TUYỆT ĐỐI KHÔNG ĐƯỢC BỎ QUA**. Phải tự động append vào cuối file:
    ```python
    target_row = ws_trk.max_row + 1
    appended_count += 1
    print(f"[ensure_row] [telemetry] STT {m} Slot {slot} appended to new row {target_row} with expected_tik={expected_tik}")
    ```
  - Bổ sung telemetry metric vào artifact:
    ```python
    metrics = {
        "applied": applied_count,
        "appended": appended_count,
        "rejected_duplicate_uid": rejected_uid_count,
        "rejected_duplicate_mail": rejected_mail_count,
        "skipped": skipped_count,
        "timestamp": dt.now().isoformat()
    }
    ```

---

## 5. Reviewer Sol Auditor / Closeout Gate Invariant
- Mọi thay đổi logic tính toán index dòng hoặc mapping STT Tik trong file nhạy cảm (`ensure_row_accounts.py`) BẮT BUỘC phải đi kèm unit tests bao phủ:
  1. `test_admin_expected_tik_mapping`: Xác minh công thức cho cả m=201..280 và m=1..80.
  2. `test_apply_results_admin_dynamic_append`: Kiểm chứng auto-append vào cuối workbook và cập nhật `appended` metric.
  3. `test_admin_adb_socket_telemetry`: Kiểm chứng fallback tự trỏ `ADB_SERVER_SOCKET` sang `tcp:192.168.110.119:5037`.
- Không có test bao phủ các nhánh này -> Sol Auditor sẽ đánh rớt với Overall Score < 85.
