# Pre-Session Device Readiness Gate & Subprocess Machines Binding (2026-10-21)

## 1. Bối Cảnh Sự Cố & Hiện Trường
- **Sự cố Máy 74 treo ADB 3 tuần:** Daemon `adbd` trên thiết bị rơi vào trạng thái zombie/socket hang, lệnh `settings get global http_proxy` bị block 15s. Lệnh `adb.reconnect()` trong preflight không cứu được máy vì nằm sau điểm treo. Kết quả là Máy 74 bị bỏ mặc suốt 3 tuần, tích tụ 4 post receipts dở dang và bỏ đói 5 tài khoản.
- **Idempotency Receipt Trap (Máy 4 kẹt 16-20 ngày):** Các post-attempt receipt kẹt ở trạng thái `intent_pending`, `verification_pending`, `UNKNOWN` không có TTL tự động dọn dẹp, khiến state machine liên tục ép vào `VERIFY_POST` rồi dừng ở `MANUAL_REVIEW`.

## 2. Kiến Trúc 2 Trụ Cột Đã Được Khép Kín
1. **Trụ cột 1 — Stale Receipt Auto-Reconciler (`reconcile_stale_post_receipts.py` & Cronjob):**
   - Quét và archive an toàn các receipt > 24.0 giờ vào `archived_stale/`.
   - Cơ chế non-blocking retry 3 lần x 0.5s khi gặp `PermissionError` (chống race condition với runner đang ghi).
   - Cronjob `hourly-stale-post-receipts-reconcile` chạy mỗi giờ (`20 * * * *`), định tuyến chuẩn xác về Telegram channel của repo `Tiktok-video` (`-5435853713`), tuyệt đối cấm gửi về DM riêng của Operator (`deliver='origin'`).
2. **Trụ cột 2 — Pre-Session Device Readiness Gate (`pre_session_device_gate.py`):**
   - Fast probe ADB `get-state` với timeout cứng 3.0s (sử dụng `run_subprocess` có cờ `CREATE_NO_WINDOW` chống giật nháy console khi Operator chơi game).
   - Tự động gọi phân tầng cứu hộ `recover_stuck_s7.py` (Level 1 reconnect -> Level 3 USB hub reset) để kéo máy lên xanh trước ca chạy.
   - Guard an toàn giờ Reboot: Tự động né cửa sổ `05:20`, `11:20`, `17:20` $\pm 10$ phút chống reboot loop.
   - Cung cấp kill-switch tức thời `AUTO_RECOVERY_ENABLED=0`.

## 3. Bài Học Closeout Reviewer & Ràng Buộc Danh Sách Máy Khỏe
- **Phát hiện của Sol Reviewer (76 -> 79 điểm):** Ban đầu, Coordinator chỉ chèn gate để lấy log `healthy_machines` nhưng không làm thay đổi luồng spawn. Reviewer chỉ ra lỗi kiến trúc nghiêm trọng: *"Danh sách thiết bị khỏe không ảnh hưởng đến quyết định spawn. Gate hiện tại chủ yếu tạo log, chưa thực thi chính sách readiness."*
- **Quy chuẩn thi công dứt điểm (82 điểm APPROVED):**
  1. *Skip tick khi 0 máy sẵn sàng:* Nếu `row_machines` có máy nhưng `len(healthy_machines) == 0`, bắt buộc ghi log warning, xuất thông báo và `continue` bỏ qua tick hiện tại, cấm spawn batch vào các máy chết.
  2. *Ràng buộc tham số `-Machines` vào tiến trình con:* Cập nhật `_spawn_feed_session(..., machines=healthy_machines)`. Khi `machines` được truyền vào, thêm tham số `-Machines <sorted_unique_ids>` vào câu lệnh gọi `run-feed-session.ps1` để PowerShell launcher chỉ khởi chạy các thiết bị đạt chuẩn, cách ly hoàn toàn các máy đang lỗi phần cứng.
  3. *Bọc Fail-Safe Try/Except:* Nếu module gate gặp sự cố nạp hoặc runtime crash, ghi warning log và fallback spawn an toàn để không làm tê liệt toàn bộ ca nuôi.

## 4. Bản Đồ Kênh Telegram Theo Repo (Tránh Hallucination)
- `Tiktok-video` (Render & Upload video TikTok): `-5435853713` (CẤM gọi nhầm là "Farm Admin").
- `tiktok-luot nuoi acc` (Nuôi lướt feed TikTok): `-5377611430`.
- `Farm Alerts` (Sự cố phần cứng, cứu hộ máy, cảnh báo farm): `-5373649734`.
- `Tiktok_Reg` (Đăng ký nick TikTok): `-5494641602`.
- `tiktok-log-in` (Đăng nhập nick TikTok): `-5145780745`.
