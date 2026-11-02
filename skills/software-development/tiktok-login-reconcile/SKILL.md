---

name: tiktok-login-reconcile

description: >

  Debug and fix TikTok login reconcile/inventory failures on Android devices.

  Covers VPN preflight integration, UI compatibility handling (popups, image

  navigation fallbacks), automation-core API migration patterns, and the

  required docs/ui-compatibility.md audit trail.

---
# TikTok Login Reconcile — Debug & Fix Patterns

- **Bẫy Nhận Diện Nhầm Màn Cài Đặt Là Form Đăng Nhập & Bẫy TRACKING_ROW_CHANGED Khi Trùng Credentials (2026-10-21)**: (1) Màn hình "Cài đặt và quyền riêng tư" chứa header "Đăng nhập" khiến `_tiktok_login_modal_present()` match false positive chuỗi `"dang nhap"`, làm `tap_add_account` nhảy cóc bỏ qua việc bấm nút thêm tài khoản rồi crash ở bước chọn email. Khắc phục: Bắt buộc guard loại trừ `"cai dat va quyen rieng tu"` / `"settings and privacy"`. (2) `upsert_tracking_account()` ném lỗi `TRACKING_ROW_CHANGED` khi ô đã có sẵn ID/pass dù trùng khớp 100% với tài khoản đang nạp bù. Khắc phục: Cho phép ghi khi `row_id` và `row_pass` trùng khớp với chính credentials của target account. Chi tiết: `references/login-modal-settings-false-positive-and-tracking-upsert-reconcile-20261021.md`.
- **Bẫy Trùng Tên Deferred Result Khác Timestamp & Nhận Diện Lỗi "Mật Khẩu Sai" (2026-10-21)**: Khi cứu hộ credentials từ deferred result JSON, nếu có nhiều file `tracking_result_stt<STT>_*.json` qua các run timestamps khác nhau (do tái dùng Hotmail), BẮT BUỘC đối soát trường `written_at` với cột Ngày tạo trong Workbook để tránh lấy nhầm pass của run khác. Đồng thời bổ sung `"mat khau sai"` vào `WRONG_PASS_HINTS` trong `tiktok_login_v1.py` để fail-fast tức thì thay vì treo flow. Chi tiết: `references/deferred-result-timestamp-collision-and-wrong-pass-ocr-20261021.md`.
- **CẤM TỰ TIỆN PAUSE CRON/WATCHDOG, KỶ LUẬT CANH NHẢ LOCK & REAP DEAD-OWNER (User Correction 2026-10-21)**: Khi chạy nạp bù nick (`tiktok_login_v1.py`) gặp device lock từ tiến trình khác (`NEEDS_USER_DECISION: device lock active ... project=tiktok-rename`), CẤM TUYỆT ĐỐI tự ý pause hay kill cronjob/watchdog của User. User chốt: *"Mày canh nó làm xong thì mày vào làm. Tự tiện vc"*. Quy trình chuẩn: (1) Kiểm tra tiến trình bằng `tasklist /FI "PID eq <PID>"`, chờ tiến trình kết thúc tự nhiên; (2) Nếu PID đã chết mà lock còn tồn đọng, chạy `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py"` để reap lock tự động; (3) Xác nhận sạch lock rồi mới tái khởi động nạp bù. Chi tiết: `references/cron-cooperative-wait-reap-locks-and-safe-point-return-20261021.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
