Cronjob on-demand/helper kích hoạt batch ngầm BẮT BUỘC cờ deliver='local' để chống Hermes scheduler tự động đổ stdout (telemetry/log) spam vào Telegram chat.
§
Khi TikTok Switcher thiếu account (ACCOUNT_MISSING), BẮT BUỘC kích hoạt auto-login / Thêm tài khoản (recovery_handler=tiktok_login); CẤM phân biệt máy trắng acc hay viện cớ an toàn / lệch nhịp farm để dừng máy fail-closed.
§
Khi pool OmniRoute (ChatGPT-Web/Codex) lỗi: BẮT BUỘC đối soát proxy_registry (credentials port) và test trực tiếp /api/providers/{cid}/test trước khi kết luận; token còn sống phải bật is_active=1 ngay thay vì chỉ thụ động cô lập.
§
Cơ chế nuôi TikTok theo Ca: Ca 1 {1,2,7}, Ca 2 {3,4,8}, Ca 3 ngày 1-2 {5,6}, Ca 3 ngày 3 là ca dynamic tăng trust (tắt follow). Bốc theo độ khỏe: Khỏe -> Đề xuất -> Hồi phục 2 -> Hồi phục 1 -> Nhả -> Yếu, chạy hết pool mới quay vòng; nick lỗi ưu tiên chạy lại phiên sau. Cooldown 48h CHỈ áp dụng riêng cho đi follow (tính khi nick đã từng follow), nuôi feed/up video chạy bình thường.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
Tool 2FA và cron xen ca chạy cả ngày BẮT BUỘC dùng Just-In-Time (JIT) lock từng máy (cấm bulk pre-reserve giữ lock hàng loạt trong queue) và bọc predicate né khung giờ reboot/đệm trước ca cron.
§
Thang luân chuyển worker: Sol (Tier 1) -> Agy (Tier 2) -> Claude (Tier 3 on-demand). haiku_worker tự rewire về dispatch_worker. Sửa Telegram adapter ở D:/Taadaa/Hermes phải sync sang runtime venv và restart gateway mới có hiệu lực.
§
Triết lý Canary farm: Sửa/lỗi chỗ nào thì Canary nhắm trúng chỗ đó (Target-bound differential canary), cấm chạy generic full-flow bừa bãi. Các job/watchdog chạy cả ngày bắt buộc né khung giờ đệm trước/sau reboot máy để bảo toàn máy cho ca cron.
§
Watchdog & Cron report toàn farm tuân thủ chuẩn: vi phạm mới bắn ra, không vi phạm thì im lặng; riêng 00:00 UTC phát 1 nhịp Heartbeat 24h xác nhận hệ thống sống khỏe.