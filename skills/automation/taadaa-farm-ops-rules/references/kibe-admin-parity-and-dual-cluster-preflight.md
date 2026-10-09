# Kibe & Admin Multi-Cluster Parity & Dual-Cluster Preflight Operations

## 1. Bất biến Parity 100% giữa Kibe và Admin (Multi-Cluster Parity)
- **Quy tắc tối cao:** "Cái nào Kibe có thì Admin cũng phải có". Toàn bộ tính năng tự động hóa, preflight kiểm tra tài khoản, tự động reg bù, nuôi feed, upload, follow, healing và sync workbook của cụm Kibe (`machines 1-80`) BẮT BUỘC phải hoạt động tương đương trên cụm Admin (`machines 200+`).
- **Cấm viện cớ an toàn giả định:** Tuyệt đối cấm Coordinator tự ý viện cớ "tác vụ reg dài", "nguy cơ lag/xung đột" để bỏ qua hoặc vô hiệu hóa các bước kiểm tra / tự động hóa trên cụm Admin. Mọi cụm đều phải được vận hành bình đẳng theo đúng kiến trúc multi-cluster.

## 2. Kiến trúc Dual-Cluster Runner Preflight (`tiktok_runner.py`)
Khi thiết kế và vận hành cron runner quét qua nhiều cụm (`CLUSTERS = [kibe, admin]`):
1. **Không hardcode cluster check:** CẤM `if cluster_name == "kibe": _preflight_ensure_accounts()`. Hàm preflight phải nhận `cluster` làm tham số và chạy cho toàn bộ các cluster được định nghĩa.
2. **Cluster-Scoped Marker Files:**
   - Dùng `.preflight_{cluster_name}_{window_key}` thay vì marker chung để tránh tình trạng một cluster chạy trước tạo marker làm cluster sau bị skip oan.
3. **Environment Injection theo từng Cluster:**
   - Cụm `kibe`: `TAADAA_HOST_CONFIG = D:\Taadaa\machine-config\kibe.yaml`, `ADB_SERVER_SOCKET = None` (local port 5037).
   - Cụm `admin`: `TAADAA_HOST_CONFIG = D:\Taadaa\machine-config\admin.yaml`, `ADB_SERVER_SOCKET = tcp:192.168.110.119:5037` (kết nối remote ADB daemon qua mạng LAN).

## 3. Quy chuẩn Auto-Provisioning & Dynamic Workbook Append (`ensure_row_accounts.py`)
Khi tự động mua mail và reg bù TikTok cho cụm Admin:
1. **Tính toán STT Tik / Slot cho máy 200+:**
   - Với máy Kibe (`1 <= m <= 80`): `expected_tik = (m - 1) * 8 + slot`.
   - Với máy Admin (`m >= 201`): `expected_tik = (m - 201) * 8 + slot`.
2. **Cơ chế Dynamic Append:**
   - Khác với master workbook của Kibe (đã cố định 640 dòng), workbook tracking của Admin là dạng phát triển động (`taikhoan_dat_v2_updated .xlsx`).
   - Trong `apply_results()`: Nếu không tìm thấy target row có sẵn cho `(machine, slot)`, BẮT BUỘC tự động ghi vào dòng mới cuối bảng (`target_row = ws_trk.max_row + 1`), TUYỆT ĐỐI CẤM bỏ qua (`skipped`) làm thất lạc thông tin tài khoản đã đăng ký thành công trên thiết bị.
3. **Remote ADB Routing:**
   - Khi chạy script từ Kibe PC nhưng xử lý máy Admin (`HOST_ID == "admin"`), script phải đảm bảo `ADB_SERVER_SOCKET = "tcp:192.168.110.119:5037"` được truyền vào môi trường subprocess của `_run_all_targets.py` và `social_reg_v1.py`.
