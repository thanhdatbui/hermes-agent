Guard_media_vision_gate chặn DIRTY_AVATAR_EVIDENCE, cấm leak DEGRADED ra chat; kiểm tra contradiction phổ quát cho mọi loại ảnh để chống AI bịa đặt thành công khi ảnh hiển thị lỗi.
§
Nạp Web (:20129): trần 2 acc/IP; pre-validate Graph; cấm base64. Acc lỗi set rate_limited_until UTC; disableSessionStickiness=true & failoverBeforeRetry=true. Nạp Gemini Web CDP lấy __Secure-1PSID kẹp proxy 1:1; Argon 4 pool map 'gemini-web'. Worker timeout 360s.
§
TikTok Upload & Dashboard Audit: Cấm cào web realtime verify trong luồng upload. Nick thiếu nút Sửa hồ sơ: lưu tạm Bio mở khóa dòng Bio, tap vào Bio để vào trang 'Sửa hồ sơ' đổi Username @. Follow mode 2 nhả follow ảo 35 máy do OCR Anchor 1.0s quá ngắn. M17 đã đổi thành @lyhoan.music.
§
Advisor, Gate A-B-C & Unified Pipeline: Cấm Coordinator tự vẽ plan. Gate B (gate_b_planner.py: Gemini 120s -> Sol 120s -> Claude 150s). Gate C: Qoder T0 (DeepSeek-Flash) -> Sol -> Agy -> Haiku. Nối xích unified_patch_pipeline.py: S0 Precheck RepoLock -> S1 Plan -> S2 Patch + Hậu kiểm O(1) -> S3 Test -> S4 Canary Gate 6 -> S5 Hold Awaiting User kèm MEDIA:. Lỗi tự full_rollback() (quét scope + baseline drift + git index reset). BỎ HẲN HMAC/SHA256 ký local; dùng TLIS v1 (Plain JSON, atomic os.replace, OS RepoLock). Chốt phiên User gõ 'Done' chạy closeout_v2.py (0.05s). Bị chặn/fail phải ném log thật.
§
R3G Thái Bình: lan2 (WAN2, tamnhb1) đang giữ mạng chính & Tailscale (100.115.94.49, ping 8.8.8.8 28ms). Đã dựng 8 MACVLAN proxy (5101-5108). Cổng lan1 (Line 0, tamnhb0) đang disabled tạm do modem 0 chưa bridge / PADO timeout. CẤM can thiệp lan2 gây văng Tailscale.
§
TikTok nhả follow là REJECT thật từ backend phát hiện qua Path B Verify (profile nút vẫn Follow), cấm suy đoán delay mạng khi chưa tra log follow_result.json. Đổi username layout mới: lưu tạm bio -> tap dòng bio mở 'Sửa hồ sơ' đổi handle @. M17: @lyhoan.music.
§
Canary Semantic: canary_plan.py chuẩn hóa thang Gate B (Gemini :20129 -> Sol :20129 -> Claude CLI) đọc diff sinh cli_args_override và log_assertions. canary_runner.py hậu kiểm log.jsonl, chống canary hình thức.