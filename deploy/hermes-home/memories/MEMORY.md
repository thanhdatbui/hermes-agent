Cronjob batch ngầm đặt deliver='local' chống spam stdout; Watchdog có deliver='local' BẮT BUỘC tự dispatch Telegram (cấm chỉ print). Hàm nạp token BẮT BUỘC tự đọc trực tiếp từ hermes/.env chống rớt dependency/import automation_core.
§
Khi TikTok Switcher thiếu account (ACCOUNT_MISSING), BẮT BUỘC kích hoạt auto-login / Thêm tài khoản (recovery_handler=tiktok_login); CẤM phân biệt máy trắng acc hay viện cớ an toàn / lệch nhịp farm để dừng máy fail-closed.
§
Khi pool OmniRoute (ChatGPT-Web/Codex) lỗi: BẮT BUỘC đối soát proxy_registry (credentials port) và test trực tiếp /api/providers/{cid}/test trước khi kết luận; token còn sống phải bật is_active=1 ngay thay vì chỉ thụ động cô lập.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
Tool 2FA và cron xen ca chạy cả ngày BẮT BUỘC dùng Just-In-Time (JIT) lock từng máy (cấm bulk pre-reserve giữ lock hàng loạt trong queue) và bọc predicate né khung giờ reboot/đệm trước ca cron.
§
Thang luân chuyển worker: Sol (Tier 1) -> Agy (Tier 2) -> Claude (Tier 3 on-demand). haiku_worker và claude_worker đều auto-rewire về dispatch_worker khi thiếu cờ on-demand. Sửa Telegram adapter ở D:/Taadaa/Hermes bắt buộc sync sang venv site-packages và restart gateway mới có hiệu lực. Cấm dùng LaTeX \textbf, \longrightarrow trong chat Telegram.
§
Triết lý Canary farm: Sửa/lỗi chỗ nào thì Canary nhắm trúng chỗ đó (Target-bound differential canary), cấm chạy generic full-flow bừa bãi. Các job/watchdog chạy cả ngày bắt buộc né khung giờ đệm trước/sau reboot máy để bảo toàn máy cho ca cron.
§
Triết lý Auto-Rewire: Gate DENY là kích hoạt tự sửa ngầm (Auto-Rewire/Pivot), cấm Hard Block hay đùn việc. Đo tần suất lỗi theo tổng vi phạm/turn chat thực tế (cấm ngụy biện '0 lỗi' theo khung giờ ngủ đông). Coordinator cấm tự sửa code bỏ qua Worker; Closeout Gate tự remediate 3-7p.
§
Cấm dùng cú pháp LaTeX math ($$, \\textbf{}, \\rightarrow, \\longrightarrow, \\implies) khi gửi tin Telegram; chỉ dùng Markdown chuẩn (**đậm**) và ký tự Unicode (→).