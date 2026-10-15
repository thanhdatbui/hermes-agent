Chu kỳ 4d: Parity 96h (N1 lẻ, N2 chẵn), N3(R7,8), N4(dưỡng 0fl+up). Starve 108h. CẤM xóa cooldown. Dưỡng động: healing_selector.py; S2 bám S1; schema 1.0. 3 ca (6,12,18h). Đêm 21h30-5h15 (né cache 4h) cho 2FA/Ava; báo 6h; cấm báo ảo.
§
Auto-resume: MAX(msg ts)<=60m; locks==0.
§
Worker: claude_worker.py (worker=Haiku 8t hard-cap 15t, planner/reviewer=Sonnet <=6t/4t read-only); cấm raw claude -p; fallback ag_cli; CAM omni-worker. Sol Web/Advisor: model suy luận, streaming idle timeout, cấm cắt ngang. Closeout: cấm commit test-only chạy gate (telemetry=0); diff lớn bị truncate, commit thin-slice.
§
TikTok Follow: (máy,row) độc lập; Quota 10-15/ca; Hồi phục 1&2; clean>=2 tốt nghiệp; Canary +10%; like 80%. Path B ko commit; slot (folder-1)%8+1. Mode 2: anchor >= 150 fl; cuộn sâu. Cron: follow_watchdog.
§
Hotmail: CẤM mail cá nhân; sinh @fviainboxes.com đọc OTP API. Write-Through: ghi ngay Excel Cột 3,4,5 & G farm. CDP đóng ko mất cookie. Dual-farm ~1280 acc.
§
Proxy: SoT PROXYgandienthoai.xlsx. OmniRoute Web: 1-1 proxy_assignments host:port, cấm random/direct. Vision assert mCurrentFocus+OCR. Ava/2FA né ca nuôi & cache 4h. Chuẩn hoá kênh: kiểm đủ Ava/Hashtag/Pin. Lock kép: Avatar & Hashtag. Ghim: monkey start.
§
Farm Dispatch: Sửa code dùng haiku_worker.py O(1) 6-15s (guard_dispatch_contract chặn cứng delegate_task EDIT; fallback ag_cli 7 Pro accs; van xả áp: WORKER_CLI_EXHAUSTED/ALLOW_SUBAGENT_CODE_EDIT). delegate_task chỉ INVESTIGATE <=5 calls. S7: recover_stuck_s7.py; max_reboots=2.
§
GPM: Kibe chạy, stop API kèm _kill_gpm_chrome; max 5 wkr. Hotmail: qua HOTMAIL_LOGIN giữ cookie, cấm ngâm ảo 7d; MS landing check is_auth trước challenge; MS ép mail @fviainboxes; ghi Excel (C5,4,3+G) trước signout.
§
Stale Upload: draft trap, xóa sạch (_delete_all_profile_drafts). Revert flop: quét ledger lấy video gốc; TikWM tải CDN; xóa render trước khi làm mới. Cào video: max 60 clip/channel, cấm cào full.
§
Cô lập Kibe vs Admin: Kibe(1-80, F1-640) và Admin(201-280, F1-640) cào nguồn riêng, video riêng, niche riêng. CẤM TUYỆT ĐỐI dùng DB Kibe ghi đè Niche/Hashtag sang Admin. Cấm sync chéo. CẤM gán 1 tik cùng niche hàng loạt; phân bổ xen kẽ máy.