Guard_media_vision_gate chặn DIRTY_AVATAR_EVIDENCE, cấm leak DEGRADED ra chat; kiểm tra contradiction phổ quát cho mọi loại ảnh để chống AI bịa đặt thành công khi ảnh hiển thị lỗi.
§
Nạp Web (:20129): trần 2 acc/IP; pre-validate Graph; cấm base64. Acc lỗi set rate_limited_until UTC; disableSessionStickiness=true & failoverBeforeRetry=true. Nạp Gemini Web CDP lấy __Secure-1PSID kẹp proxy 1:1; Argon 4 pool map 'gemini-web'. Worker timeout 360s.
§
TikTok: Cấm cào realtime. Dual Gate Follow: age >= 30d & video >= 10 mới cấp budget follow (<10 video budget = 0). Anchor luôn đủ, auto-fallback Mode 1. CẤM bịa giả thuyết hết anchor. Watchdog UNPROVEN do lệch baseline T0 (>4h); cào T0 cần creationflags 0x08000000 và sync 4 tầng. M17: @lyhoan.music. Check nhả follow vuốt reload 3.5s.
§
Nối xích unified_patch_pipeline.py là ENTRYPOINT DUY NHẤT khi có lệnh Fix Code / Fix lỗi: S0 Precheck RepoLock -> S1 Plan (Gate B) -> S2 Patch qua dispatch_worker -> S3 Test -> S4 Canary Gate 6 -> S5 Hold Awaiting User kèm MEDIA:. Lỗi tự full_rollback(). BỎ HẲN HMAC/SHA256 ký local; dùng TLIS v1 (Plain JSON, atomic os.replace, OS RepoLock). Chốt phiên User gõ 'Done' chạy closeout_v2.py (0.05s). Bị chặn/fail phải ném log thật. CẤM làm tay.
§
R3G Thái Bình (100.115.94.49, tb.taadaa.click): Cổng giữa (lan2, tamnhb1) chạy 8 proxy 5141-5148. Cổng ngoài (lan1, tamnhb0) mac 02:11:22:33:44:10 chạy 8 proxy 5151-5158. TỔNG 16/16 PROXY LIVE (8 port/line là trần cứng BRAS Viettel TBH8001BRA01). MobiProxy (test.taadaa.click) đủ 32/32 proxy. Đã thêm DNS A record tb.taadaa.click trên Cloudflare.
§
Reg Gmail Admin (201-280): Lỗi [05_create] do máy fresh 0 acc bị Google ép Sign-in Only từ setup_addresses. Khắc phục bằng Intent trực tiếp. Khi gọi run_all.ps1 bắt buộc truyền manifest register-gmail.json & workerId 'taadaa-writer-admin-farm'. Đồng bộ code qua Base64 chunking SSH + SHA256; file Excel sổ cái phải kiểm tra nạp openpyxl không bị mismatched tag XML.