# Cross-Workflow Empty Row & Stale Lock Triage (Feed Session Failure Cascades)

## 1. Bối Cảnh Hiện Tượng
Khi người vận hành báo "Lướt feed fail gần một nửa" hoặc "Lỗi lắm v" trên farm:
Thống kê manifest thường báo tỷ lệ thành công thấp bất thường (ví dụ: chỉ 25/80 máy thành công), với hàng chục máy ghi nhận `final_status: config-error` hoặc `skipped-device-locked`.

## 2. Quy Trình Điều Tra O(1) (Cấm Scan Rộng)
Thay vì grep mò mẫm hay viết script probe, Coordinator truy xuất trực tiếp:
1. Đọc file `run_manifest.json` của đợt chạy tại:
   `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-<R>-<HHMMSS>/<RUN_ID>/run_manifest.json`
2. Bóc tách 2 khối dữ liệu cấu trúc:
   - `blocker_taxonomy_summary`: Tổng hợp nhanh theo danh mục (`script blocker`, `focus/device issue`, `manual-needed popup`, `pass/degraded acceptable`).
   - `multi_machine_summary`: Xem chi tiết từng máy với `stop_reason`.

## 3. Ba Nguyên Nhân Cốt Lõi Thường Gặp
### A. Hiệu ứng dây chuyền hàng trống (Cross-Workflow Empty Row Config-Error)
- **Dấu hiệu**: Hàng loạt máy dính `config-error` với `stop_reason: account row X is empty (no username) for machine Y, skipping`.
- **Nguyên nhân gốc rễ**: Trước ca lướt feed Row X, ca **Reg bù / Reconcile Row X** đã chạy nhưng thất bại trên các máy đó, khiến ô tài khoản trên sheet Excel bị trống. Feed runner kiểm tra workbook không thấy username nên bắt buộc phải skip an toàn.
- **Nguyên nhân phụ tại ca Reg**:
  - `MACHINE_FULL_8_ACCOUNTS`: Máy thật đã đủ 8 nick trên Switcher nhưng Excel bị lệch (trống), script cố nạp thêm nick thứ 9 thì bị chặn bởi trần an toàn.
  - `BLOCKED_GMAIL_OTP_TIMEOUT`: Chờ OTP Gmail quá thời gian.
  - ADB / UI XML timeout trên thiết bị.

### B. Khóa mồ côi (Stale Dead-Owner Device Locks)
- **Dấu hiệu**: Máy bị `skipped-device-locked` kèm thông tin `pid=XXXXX ... reservation`.
- **Nguyên nhân**: Tiến trình trước đó bị crash, kill, hoặc timeout nhưng chưa giải phóng lock file trong `C:\Users\Kibe\.codex\device-locks\`.
- **Xử lý**: Kiểm tra PID bằng `tasklist | grep <PID>`. Nếu tiến trình đã chết, kích hoạt cron `reap-dead-owner-locks` hoặc watchdog dọn dẹp để thu hồi lock an toàn.

### C. Mất Focus App & Lỗi Runtime Thiết Bị
- **Dấu hiệu**: `manual-needed | focused package unavailable` hoặc `TikTok focus lost to launcher`.
- **Xử lý**: Kiểm tra service ATX (port 7912), force-stop launcher và đưa TikTok về foreground.

## 4. Trình Tự Khắc Phục Cuốn Chiếu
1. **Bước 1**: Phân tách rõ ràng giữa:
   - Số máy **bỏ qua hợp lệ** (do thiếu nick trong Excel).
   - Số máy **bỏ qua do lock** (cần dọn lock).
   - Số máy **lỗi thật lúc chạy feed** (UI, launcher, gesture).
2. **Bước 2 (JIT Reconcile)**: Với các máy dính `MACHINE_FULL_8_ACCOUNTS`, chạy JIT Reconcile qua Switcher để đồng bộ ngược nick trên máy thật về Excel, tránh reg đè.
3. **Bước 3 (Reg bù chính xác)**: Chỉ dispatch reg bù cho các máy thực sự thiếu tài khoản sau khi đã đối soát.
