Cronjob on-demand/helper kích hoạt batch ngầm BẮT BUỘC cờ deliver='local' để chống Hermes scheduler tự động đổ stdout (telemetry/log) spam vào Telegram chat.
§
Khi TikTok Switcher thiếu account (ACCOUNT_MISSING), BẮT BUỘC kích hoạt auto-login / Thêm tài khoản (recovery_handler=tiktok_login); CẤM phân biệt máy trắng acc hay viện cớ an toàn / lệch nhịp farm để dừng máy fail-closed.
§
Khi nhận cảnh báo pool degraded/error, cấm chỉ báo cáo cô lập is_active=0; bắt buộc test trực tiếp endpoint, fix proxy/config để cứu và reactivate acc nếu token còn sống.
§
Khi pool OmniRoute (ChatGPT-Web/Codex) lỗi: BẮT BUỘC đối soát proxy_registry (credentials port) và test trực tiếp /api/providers/{cid}/test trước khi kết luận; token còn sống phải bật is_active=1 ngay thay vì chỉ thụ động cô lập.
§
Cơ chế nuôi TikTok theo Ca: Ca 1 {1,2,7}, Ca 2 {3,4,8}, Ca 3 ngày 1-2 {5,6}, Ca 3 ngày 3 là ca dynamic tăng trust (tắt follow). Bốc theo độ khỏe: Khỏe -> Đề xuất -> Hồi phục 2 -> Hồi phục 1 -> Nhả -> Yếu, chạy hết pool mới quay vòng; nick lỗi ưu tiên chạy lại phiên sau. Cooldown 48h CHỈ áp dụng riêng cho đi follow (tính khi nick đã từng follow), nuôi feed/up video chạy bình thường.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
Tool 2FA và cron xen ca chạy cả ngày BẮT BUỘC dùng Just-In-Time (JIT) lock từng máy (cấm bulk pre-reserve giữ lock hàng loạt trong queue) và bọc predicate né khung giờ reboot/đệm trước ca cron.
§
Thang luân chuyển worker code-fix: Sol Worker (Tier 1 mặc định) -> Agy CLI (Tier 2 khi Sol fail) -> Claude Worker (Tier 3 khi cả 2 fail hoặc lệnh User On-Demand). haiku_worker.py tự động rewire sang dispatch_worker.py nếu thiếu cờ on-demand.