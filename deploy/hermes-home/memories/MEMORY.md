Guard_media_vision_gate chặn DIRTY_AVATAR_EVIDENCE, cấm leak DEGRADED ra chat; kiểm tra contradiction phổ quát cho mọi loại ảnh để chống AI bịa đặt thành công khi ảnh hiển thị lỗi.
§
Nạp Web reverse (:20129): trần 2 acc/IP; pass random lưu Excel; pre-validate Graph; cấm base64. Khi acc web lỗi (401/Sentinel), CẤM set is_active=0 hoặc xóa khỏi combo; BẮT BUỘC set rate_limited_until dạng ISO UTC (+30m/+24h) để router tự động cooldown và tự phục hồi; combo đặt disableSessionStickiness=true và failoverBeforeRetry=true. Nạp Gemini Web qua CDP lấy __Secure-1PSID kẹp proxy 1:1. Benchmark worker bắt buộc timeout 360s.
§
TikTok Farm: Chu kỳ 3 ngày cày liên tục (Ca 1: {1,2,7}, Ca 2: {3,4,8}, Ca 3: {5,6} + Dyn Ngày 3; bỏ Ngày 4). Lệch pha độc lập vì pool nick rời nhau 100%. Gate cooldown 48h (_is_account_follow_cooldown) chặn cấm bấm follow nếu acc vừa cày < 48h. Quota max cap 40 fl/ngày (2 phiên >=120m); used>0 streak=1; 3 quy trình Feed-Follow-Upload độc lập; Quota [cap-2, cap], bóp trần = last_failed - 2; Máy Lẻ (Nhóm A bám trần + hồi phục 1,2), Máy Chẵn (Nhóm B max 20 fl/phiên, used>0 dừng nhận fl đã ăn, used=0 mới cooldown).
§
Tool 2FA và cron xen ca: JIT lock từng máy (cấm bulk pre-reserve); freeze_targets bọc retry 5 nhịp backoff + dọn lock mồ côi ~$*.xlsx né xung đột cron sync 5m; Batch 2FA Admin qua SSH bắt buộc --adb-path r"C:\Program Files (x86)\xiaowei\tools\adb.exe"; sau sửa 2FA bắt buộc chạy sync_2fa_to_admin.py.
§
GuardGate (D:/Taadaa/tools/guardgate) là Protection Regression Gate cơ giới hóa cho code diff repo (Closeout Step 2.5); infra_regression_gate.py chỉ kiểm tra riêng 4 file config hạ tầng Hermes/OmniRoute.
§
Dashboard TikTok (1905, tiktok_dashboard.py) độc lập 100% với Farm runner (tiktok_runner.py); cấm suy diễn lỗi Dashboard sang Farm. Watchdog restart service Windows phải kill cả cây pythonw.exe + python.exe để tránh đụng socket SO_REUSEADDR gây treo/sập.
§
Canary visual: cấm dùng ảnh spinner ('Quá trình này có thể mất...', loading); mtime ảnh >= mtime UI dump. OCR ảnh Telegram bắt buộc bốc đúng exact hash từ prompt [Image attached at: ...\img_<hash>.jpg], cấm quét mtime trên image_cache tránh nhặt nhầm ảnh session khác.