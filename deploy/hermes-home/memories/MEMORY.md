Guard_media_vision_gate chặn DIRTY_AVATAR_EVIDENCE, cấm leak DEGRADED ra chat; kiểm tra contradiction phổ quát cho mọi loại ảnh để chống AI bịa đặt thành công khi ảnh hiển thị lỗi.
§
Nạp Web reverse (:20129): trần 2 acc/IP; pass random lưu Excel; pre-validate Graph; cấm base64. Khi acc web lỗi (401/Sentinel), CẤM set is_active=0; BẮT BUỘC set rate_limited_until UTC (+30m/+24h) để tự phục hồi; combo disableSessionStickiness=true & failoverBeforeRetry=true. Nạp Gemini Web qua CDP lấy __Secure-1PSID kẹp proxy 1:1; Argon 4 pool map model 'gemini-web'. Worker timeout 360s.
§
TikTok Farm: Chu kỳ 3 ngày cày liên tục (Ca 1: {1,2,7}, Ca 2: {3,4,8}, Ca 3: {5,6} + Dyn Ngày 3; bỏ Ngày 4). Lệch pha độc lập vì pool nick rời nhau 100%. Gate cooldown 48h (_is_account_follow_cooldown) chặn cấm bấm follow nếu acc vừa cày < 48h. Quota max cap 40 fl/ngày (2 phiên >=120m); used>0 streak=1; 3 quy trình Feed-Follow-Upload độc lập; Quota [cap-2, cap], bóp trần = last_failed - 2; Máy Lẻ (Nhóm A bám trần + hồi phục 1,2), Máy Chẵn (Nhóm B max 20 fl/phiên, used>0 dừng nhận fl đã ăn, used=0 mới cooldown).
§
Tool 2FA và cron xen ca: JIT lock từng máy; sync code Admin qua OneDrive D:\OneDrive\TaadaaData\admin\ (cấm stream Base64 qua SSH); single_writer workbook fallback ID + protected_parts=None khi add text né WORKBOOK_PROTECTED_PART_DRIFT. Master Excel Admin: 101/630 có 2FA.
§
GuardGate: Protection Regression Gate cho repo; infra_regression_gate.py kiểm tra 4 file config Hermes/OmniRoute. Model Picker Telegram: tin nhắn /model cũ freeze state model trong RAM; thêm model bắt buộc restart gateway & gửi /model mới hoặc /model <id>.
§
Dashboard TikTok (1905, tiktok_dashboard.py) độc lập 100% với Farm runner (tiktok_runner.py); cấm suy diễn lỗi Dashboard sang Farm. Watchdog restart service Windows phải kill cả cây pythonw.exe + python.exe để tránh đụng socket SO_REUSEADDR gây treo/sập.
§
Canary visual: cấm dùng ảnh spinner ('Quá trình này có thể mất...', loading); mtime ảnh >= mtime UI dump. Bắt buộc bốc đúng exact hash từ prompt, cấm glob/mtime trên image_cache. SQLite daily_account_actions là nguồn sự thật lịch sử follow.