# Nguyên Tắc Parity 100% Kibe ↔ Admin & Vận Hành Reg Bù Dual-Cluster

## 1. Luật Bất Biến: Parity 100% (Kibe có gì, Admin phải có nấy)
- **User Correction Invariant (2026-09-24):** CẤM TUYỆT ĐỐI Coordinator tự suy diễn hoặc bịa lý do (như lo ngại timeout, kẹt lock) để phân biệt đối xử giữa dàn Kibe (máy 1–80) và dàn Admin (máy 201–280).
- Mọi cơ chế tự động hóa của hệ thống Farm:
  - Tự động kiểm tra slot trống trước ca nuôi feed (`_preflight_ensure_accounts`).
  - Tự động mua bù mail (`buy_hotmail.py`) và kiểm chứng Microsoft Graph token.
  - Tự động kích hoạt batch reg (`ensure_row_accounts.py` -> `_run_all_targets.py`).
  - Tự động cập nhật tracking workbook và sync sang safe workbook.
  **BẮT BUỘC phải chạy bình đẳng cho CẢ HAI CỤM Kibe và Admin.**

## 2. Kỹ Thuật Định Tuyến Dual-Cluster trên Runner & Preflight
Khi thiết kế hoặc cập nhật runner (`tiktok_runner.py`):
1. **Loại bỏ hardcode cluster filter:**
   - ❌ SAI: `if cluster_name == "kibe": _preflight_ensure_accounts(row, window_key)`
   - ✅ ĐÚNG: `_preflight_ensure_accounts(row, window_key, cluster=cluster)`
2. **Inject đầy đủ biến môi trường theo Cluster:**
   - Cụm `kibe`: `TAADAA_HOST_CONFIG = D:/Taadaa/machine-config/kibe.yaml`
   - Cụm `admin`: `TAADAA_HOST_CONFIG = D:/Taadaa/machine-config/admin.yaml`, `ADB_SERVER_SOCKET = tcp:192.168.110.119:5037`
3. **Marker Scope độc lập:**
   - Dùng `.preflight_{cluster_name}_{window_key}` lưu tại `runtime/<cluster>/cron-state/` để Kibe và Admin kiểm tra độc lập, không bị tình trạng cụm này chạy trước ghi marker làm cụm kia bị bỏ qua.
4. **ADB Socket Auto-Routing trong Tool Reg (`ensure_row_accounts.py`):**
   - Khi chạy từ Kibe PC (`hostname != admin`) với `HOST_ID == "admin"`, script phải tự động export `ADB_SERVER_SOCKET = "tcp:192.168.110.119:5037"` trước khi dispatch `_run_all_targets.py` để kết nối điều khiển 80 máy Admin qua mạng.

## 3. Bản Chất Follow Chéo Hiển Thị 0 Lượt & Skip Video < 10
- **Hiện tượng:** Báo cáo watchdog Telegram ghi nhận `Follow chéo (0 lượt follow) [Module 2 (Anchor): 0 | Module 1 (Bù): 0]` và `Bỏ qua (N): Chưa đủ 10 video`.
- **Cơ chế:**
  - `multi_machine_feed_session.py` áp dụng Hard Gate: Nick có `video_count < 10` (như nick mới nạp ở Row 5) bị chặn an toàn ngay từ khâu Feed (`under-10-videos-follow-disabled`), không được khởi chạy script follow chéo để chống bị TikTok quét nhả.
  - Khi chưa đủ 10 video, script follow không chạy nên cả Module 2 và Module 1 đều ghi nhận 0 lượt thành công.

## 4. Công Thức Ánh Xạ STT Tik (Folder Video) & Dynamic Workbook Append
1. **Công thức ánh xạ STT Tik (1..8) theo cụm:**
   - Kibe (1..80): `expected_tik = (m - 1) * 8 + slot` (Dải 1..640)
   - Admin (201..280): `expected_tik = (m - 201) * 8 + slot` (Dải 1..640)
   - Hàm chuẩn:
     ```python
     def get_expected_tik(m: int, slot: int) -> int:
         return (m - 201) * 8 + slot if m >= 201 else (m - 1) * 8 + slot
     ```
2. **Cơ chế Dynamic Append Workbook Admin (`apply_results`):**
   - Kibe dùng file tĩnh 640 dòng sẵn (`taikhoan_dat_v2_updated .xlsx`).
   - Admin là file động, chỉ tạo dòng khi có acc. Khi merge kết quả reg, nếu `target_row is None` (không tìm thấy hàng khớp STT & Slot):
     + **CẤM TUYỆT ĐỐI bỏ qua làm mất nick đã reg.**
     + BẮT BUỘC tự động append vào cuối sheet: `target_row = ws_trk.max_row + 1`.
     + Ghi nhận telemetry: `appended_count += 1` và in log:
       `[ensure_row] [telemetry] STT {m} Slot {slot} appended to new row {target_row} with expected_tik={expected_tik}`.
     + Lưu vào telemetry artifact `last_merge_metrics.json` trường `"appended": appended_count`.

## 5. Fail-Open Marker Lifecycle trong Runner
- Trong `_preflight_ensure_accounts`: Marker file `.preflight_{cluster_name}_{window_key}` tạo ra nhằm chống spam lặp lại mỗi 15 phút.
- **Fail-Open Invariant:** Nếu lệnh `ensure_row_accounts.py` thất bại (exit code != 0) hoặc dính exception:
  BẮT BUỘC xóa marker (`marker.unlink(missing_ok=True)`) để tick cron 15p tiếp theo có thể thử lại, tránh kẹt toàn bộ ca 3 tiếng. Chỉ giữ marker khi returncode == 0.

## 6. Reviewer Sol Auditor / Closeout Gate Invariant
- Thay đổi logic tính toán index workbook, mapping dải máy Admin hoặc fallback phải luôn đi kèm unit test focused:
  * `test_admin_expected_tik_mapping`
  * `test_apply_results_admin_dynamic_append`
  * `test_admin_adb_socket_telemetry`
- Nếu thiếu test hoặc thiếu telemetry cho các nhánh fallback -> Sol Auditor sẽ đánh rớt (Score < 85). Có test và telemetry đầy đủ sẽ đạt Score >= 85 (APPROVED) ngay lập tức.
