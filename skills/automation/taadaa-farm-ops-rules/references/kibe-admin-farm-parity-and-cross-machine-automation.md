# Parity 100% Kibe ↔ Admin & Cross-Machine Farm Automation

## 1. Nguyên Tắc Cốt Lõi: Cái Gì Kibe Có, Admin Phải Có
- **Bình đẳng tính năng tuyệt đối giữa 2 cụm Farm:**
  - Dàn **Kibe** (Máy 1–80, `D:\OneDrive\TaadaaData\kibe`) và dàn **Admin** (Máy 201–280, `D:\OneDrive\TaadaaData\admin`) đều là tài sản vận hành ngang hàng.
  - Bất kỳ tính năng tự động nào được triển khai cho Kibe (ví dụ: preflight reg bù tài khoản khi thiếu slot `_preflight_ensure_accounts`, đổi pass, upload avatar, nuôi feed, dọn cache...) **BẮT BUỘC PHẢI CHẠY ĐỒNG BỘ CHO ADMIN**.
  - **CẤM TUYỆT ĐỐI** Coordinator tự ý bịa đặt lý do "quy chuẩn an toàn", ngụy tạo case ảo hoặc viện cớ thời gian chạy dài/PortProxy để né chạy, tắt tính năng hoặc phân biệt đối xử với dàn Admin.

## 2. Loại Bỏ Hardcode Phân Biệt Cluster
- **CẤM hardcode `if cluster_name == "kibe":`**:
  - Không được chặn các hook tự động hóa chỉ chạy cho một cụm đơn lẻ.
  - Schedulers và runners (`tiktok_runner.py`) phải lặp qua danh sách `CLUSTERS`, nạp đúng context của từng cụm:
    ```python
    for cluster in CLUSTERS:
        cluster_name = cluster["name"]
        cluster_wb = cluster["account_workbook"]
        cluster_host_cfg = cluster.get("host_config")
        cluster_adb_socket = cluster.get("adb_server_socket")
        
        # Preflight hook chạy cho mọi cluster
        _preflight_ensure_accounts(row, window_key, cluster=cluster)
    ```

## 3. Kỹ Thuật Cross-Machine Automation (Kibe PC điều khiển máy Admin)
1. **ADB Server Socket Routing:**
   - Máy Admin chạy daemon ADB từ xa qua PortProxy LAN: `tcp:192.168.110.119:5037`.
   - Khi chạy script công cụ (như `ensure_row_accounts.py`, `_run_all_targets.py`) trên PC Kibe targeting máy Admin (`HOST_ID == "admin"`):
     Bắt buộc cấu hình biến môi trường:
     ```bash
     export TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml"
     export ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"
     ```
2. **Namespace State & Markers:**
   - Để tránh việc preflight hoặc watchdog của cụm này hiểu nhầm hoặc chặn cụm kia, các marker file và state file phải scoped theo cluster:
     `cluster_state_dir / f".preflight_{cluster_name}_{window_key}"`
   - Nhờ đó, Kibe chạy xong preflight của Kibe sẽ không vô tình đánh dấu hoàn thành cho Admin.
