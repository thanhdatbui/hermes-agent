---
name: farm-alert-autonomous-recovery
description: Taadaa Farm Alert recovery to closeout.
---
# Farm Alert Autonomous Recovery

> Core Refs: `upload-hook-auto-login-recovery-and-canary-gate-wiring.md`, `canary-receipt-expiry-and-safe-push-pre-commit.md`, `recovery-proof-and-operator-closeout.md`, `anti-performative-alert-handling-and-immediate-code-fix.md`, `missing-account-switcher-vs-auto-login-fail-closed.md`, `admin-cluster-remote-adb-socket-injection-and-welcome-back-switcher.md`, `run-artifacts-extraction-and-session-dedup.md`, `upload-batch-alert-triage-and-flop-reporting-separation.md`, `blank-workbook-id-cross-file-recovery-and-create-button-tokens.md`.

## UI evidence: target screen only

> Ref: `references/report-routing-and-workbook-shape-20261011.md`.
- Duyệt hiện trường qua `MEDIA:<path>`. CẤM gửi ảnh Home/Launcher sau teardown/lỗi.
- Bắt buộc chụp in-app (Profile/Settings/Popup/Switcher) TRƯỚC KHI teardown.

## 🛑 TRIAGE LỖI CÁP VẬT LÝ ADB (CM_PROB_PHANTOM)
- Khi nhận alert máy offline / `[01_open]` mà ADB báo `device not found` hoặc `offline`:
  Chạy lệnh PowerShell:
  `Get-PnpDevice | Where-Object { $_.InstanceId -like "*<serial>*" } | Select-Object FriendlyName, Status, Present, Problem`
- Nếu `Present: False` hoặc `Problem: CM_PROB_PHANTOM`: Lỗi cáp USB/nguồn. DỪNG NGAY, chuyển L3 BLOCKED.

## QUY CHUẨN THIẾT KẾ WATCHDOG & BÁO CÁO ĐỊNH KỲ (CHỐNG SPAM ALERT)
Mọi cronjob / watchdog / script tự động (cũ lẫn mới tạo) bắt buộc tuân thủ nghiêm ngặt:
1. **Auto-Healer / Maintenance Watchdog (Ngầm):** Cấu hình `deliver: "local"`. Áp dụng Silent Pattern: khi bình thường hoặc tự sửa/tự vá thành công -> ghi log ngầm vào file `D:\Taadaa\runtime\...`, **`stdout` BẮT BUỘC RỖNG 100% (`sys.exit(0)`)**. CẤM TUYỆT ĐỐI dùng `print()` thông báo kết quả thành công để tránh kích hoạt Hermes gửi tin nhắn spam về Telegram. Chỉ in ra `stdout` khi gặp lỗi nghiêm trọng (`errors`) không thể tự sửa cần người can thiệp. Giãn nhịp cron hợp lý (cuối ngày hoặc theo ca, tránh `*/5`).
2. **Scheduled Summary Report (Định kỳ):** Chỉ gửi đúng kênh chỉ định vào đúng khung giờ quy định (kết thúc ca, 6h/lần, 07:00 sáng). BẮT BUỘC chuẩn hóa schema: Header rõ ràng, số liệu tổng hợp (Tổng | Pass | Fail | Tỷ lệ %), danh sách cô đọng. CẤM dump raw log/terminal hoặc xả chi tiết vụn vặt.
3. Chi tiết xem tại: `references/watchdog-silent-and-reporting-standard.md` và `references/adb-transport-two-phase-healing.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
