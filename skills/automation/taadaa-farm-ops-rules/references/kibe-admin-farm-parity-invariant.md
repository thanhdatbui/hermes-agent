# Invariant Parity Toàn Farm: Đồng Bộ Tính Năng Tuyệt Đối Giữa Kibe & Admin

## 1. Nguyên Tắc Cốt Lõi (Parity Invariant)
- **Quy tắc tuyệt đối:** "Cái nào Kibe có thì Admin cũng phải có."
- **Cấm ngụy biện / tự suy diễn:** CẤM Coordinator/Worker tự ý suy diễn các lý do "an toàn", "tác vụ dài", "sợ lag ADB" để phân biệt đối xử hoặc tắt tính năng tự động (reg bù, auto-heal, sync, preflight...) giữa các cụm farm.
- Mọi logic scheduler, cron runner (`tiktok_runner.py`), watchdog, preflight check PHẢI loop qua danh sách tất cả các cluster (`CLUSTERS = [kibe, admin]`) với logic giống hệt nhau.

## 2. Tiêu Chuẩn Thực Thi Dual-Cluster Runner & Preflight
Khi triển khai logic tiền kiểm / reg bù tự động (`_preflight_ensure_accounts`):
1. **Marker Phân Tách Theo Cluster:**
   - Dùng `.preflight_{cluster_name}_{window_key}` trong thư mục state tương ứng (`runtime/kibe/cron-state` vs `runtime/admin/cron-state`).
   - Tuyệt đối không dùng marker chung không có tiền tố cluster khiến cụm chạy trước chặn cụm chạy sau.
2. **Context & Environment Kèm Theo Cluster:**
   - Cụm Kibe: `TAADAA_HOST_CONFIG = D:/Taadaa/machine-config/kibe.yaml`, ADB socket mặc định (local).
   - Cụm Admin: `TAADAA_HOST_CONFIG = D:/Taadaa/machine-config/admin.yaml`, `ADB_SERVER_SOCKET = tcp:192.168.110.119:5037` (hoặc socket remote tương ứng).
3. **Tool Level Routing (`ensure_row_accounts.py`):**
   - Khi chạy trên host Kibe nhưng mục tiêu là cluster Admin (`HOST_ID == "admin"`), script con (`_run_all_targets.py`) bắt buộc phải nhận `ADB_SERVER_SOCKET` trỏ sang máy Admin qua mạng để điều khiển thiết bị chính xác.
