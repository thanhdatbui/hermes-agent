Cronjob on-demand/helper kích hoạt batch ngầm BẮT BUỘC cờ deliver='local' để chống Hermes scheduler tự động đổ stdout (telemetry/log) spam vào Telegram chat.
§
Khi TikTok Switcher thiếu account (ACCOUNT_MISSING), BẮT BUỘC kích hoạt auto-login / Thêm tài khoản (recovery_handler=tiktok_login); CẤM phân biệt máy trắng acc hay viện cớ an toàn / lệch nhịp farm để dừng máy fail-closed.
§
Khi nhận cảnh báo pool degraded/error, cấm chỉ báo cáo cô lập is_active=0; bắt buộc test trực tiếp endpoint, fix proxy/config để cứu và reactivate acc nếu token còn sống.
§
Khi pool OmniRoute (ChatGPT-Web/Codex) lỗi: BẮT BUỘC đối soát proxy_registry (credentials port) và test trực tiếp /api/providers/{cid}/test trước khi kết luận; token còn sống phải bật is_active=1 ngay thay vì chỉ thụ động cô lập.
§
Cơ chế nuôi TikTok Dynamic theo Ca: Ca 1 {1,2,7}, Ca 2 {3,4,8}, Ca 3 {5,6}+Row Động. Bốc tuần tự theo độ khỏe: Khỏe -> Đề xuất -> Hồi phục 2 -> Hồi phục 1 -> Nhả -> Yếu, chạy hết pool mới quay vòng để đi đủ 8 nick/máy. Cooldown follow 48h chỉ tính khi nick đã từng follow; fail-closed khi lỗi file state và bắt buộc báo cáo lỗi lên watchdog.
§
Watchdog đối soát TikTok Web (SQLite snapshots) BẮT BUỘC đối chiếu theo Account ID / Username thay vì Row máy; runner khi gặp timeout BẮT BUỘC salvage follow từ state file thay vì gán 0.
§
TikTok Farm chu kỳ nuôi: Ca 1 {1,2,7}, Ca 2 {3,4,8}, Ca 3 ngày 1-2 {5,6}, riêng Ca 3 ngày 3 là ca dynamic chuyên nuôi/tăng trust (ưu tiên đề xuất -> nhả -> yếu). Phễu chọn: Khỏe -> Đề xuất -> Hồi phục 2 -> Hồi phục 1 -> Nhả -> Yếu; nick chạy lỗi phải được ưu tiên chạy lại phiên sau cho đến khi SUCCESS mới chuyển nick tiếp theo trong pool. Cooldown 48h CHỈ áp dụng riêng cho quyền ĐI FOLLOW (và tuân thủ streak phạt của từng nick); nuôi feed và up video chạy theo ca bình thường không dính cooldown 48h.