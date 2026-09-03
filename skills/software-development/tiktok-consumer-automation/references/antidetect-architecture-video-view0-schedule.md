# Anti-detection architecture: video pipeline, view-0 diagnostics, scheduling (2026-08-09)

## Repo map — video gen
- Repo THẬT của video gen: `D:\Taadaa\Tiktok-video` (KHÔNG phải `D:\CodexRuntime\tiktok-video` — cái đó chỉ chứa runtime artifacts: assignments, logs, lock backups, screenshot evidence).
- Pipeline: `scripts/random_ffmpeg_builder.py` (build FFmpeg filter), `scripts/randomize_preset.py` (random hóa visual params + voice profile), `scripts/random_batch_render.py` (batch renderer), `scripts/randomize_profile.py`.
- Mỗi render random: zoom, brightness, contrast, saturation, gamma, color_temp, gblur, vignette, unsharp, noise, speed (setpts), phase_invert, reverb, chorus. Voice profile: treble/normal/bass theo slot (6-acc machine cycle 0-5) để acc liền kề khác fingerprint giọng.
- Seed deterministic: `compute_seed(run_id|machine_id|slot|seq|seed_offset)` → 2 video không bao giờ giống nhau, kể cả cùng source.
- **Anti-trùng hash đã xử lý ở tầng render** — không cần thêm dedup khi đăng; không tư vấn thêm công cụ gen video ngoài (xem middleware bên dưới).

## Workbook source-of-truth (feed vs upload — đừng trộn)
- Feed/lướt: `taikhoan_run_safe.xlsx` (D:\OneDrive\codex_gmail_debug\tiktok-luot nuoi acc\data\) — sync từ tracking workbook qua `sync-safe-workbook.py`; đọc qua `-AccountWorkbook`/env `TIKTOK_ACCOUNT_WORKBOOK`.
- Upload: `Tik1.xlsx`/`Tik2.xlsx` (workflow riêng: Folder Video, Video Đã Đăng = monotonic cursor không regression, Hashtag Pool) — KHÔNG đọc taikhoan_run_safe ở upload flow.
- `Taikhoan_dat_v2_updated.xlsx` = **account/credential** — KHÔNG dùng làm nguồn lịch/schedule.
- Alias: `ID` ≈ `ID TikTok`; account row hợp lệ cần: device ID + ID TikTok + Folder Video + Hashtag Pool. Máy thiếu ID TikTok (73/75/77-80) → skip, không phải lỗi chung.

## Bổ sung chống trùng hash khi đăng lẻ (ngoài render seed)
- Cùng video đăng lần 2: đổi đuôi mp4 (hash khác), chèn 1 frame đen đầu video, crop 2-5%, zoom nhẹ, speed 1.0→1.05.
- Caption/hashtag unique từng acc — không dùng chung 1 bộ caption toàn farm.
- Cadence: 1-2 post/ngày/acc tối đa, giờ post khác nhau từng máy, stagger 5-15' ngẫu nhiên.

## View 0 diagnostics (khác ban/shadowban)
- Video view 0 NHƯNG video sau lên 1-200 view = KHÔNG phải ban. Ban/shadowban thật dính MỌI video sau, không lên lại được.
- Nguyên nhân view 0: (1) cold start — không có engagement trong 1-2h đầu → không push (~10-20% kể cả acc sạch); (2) giờ đăng chết (follower không online); (3) flag nội dung đơn lẻ (không phải acc).
- Xử lý đúng: KHÔNG retry/đăng lại video 0-view (seed khác = video mới, đăng video khác); track tỷ lệ 0-view theo acc — <20% bình thường, >30-40% liên tục → đổi khung giờ đăng + check source pool/voice profile acc đó; theo dõi trong workbook.

## Middleware reality-check (Postiz / Genviral / n8n / TikTok Symphony)
- **Postiz**: đăng qua API/OAuth từ IP datacenter + thiếu device fingerprint quen thuộc = tín hiệu lạ với acc burner, dễ verify thiết bị. Giữ đăng trên device app bằng ADB UI automation (xem skill tiktok-upload-ui-recovery) = an toàn nhất.
- **Genviral**: AI faceless video, trả phí (subscription ~$19-49/tháng hoặc lifetime deal); video sinh từ server chung = fingerprint style giống nhau giữa acc — tệ hơn pipeline ffmpeg local.
- **n8n**: orchestrator low-code kéo-thả — thêm 1 điểm chết + 1 thứ phải bảo trì; flow ADB farm + lock + recovery ladder n8n không mạnh. Không cần (Hermes + consumer repos đã cover orchestration).
- **TikTok Symphony Agent**: tool chính chủ cho brand/ads (content gen, digital avatar, Creative API). Dùng API official cho acc burner = bẻ stealth (fingerprint lạ). Chỉ cân nhắc nếu có nhánh acc business chính chủ riêng.

## Scheduling: Windows Task Scheduler vs Hermes cron
- Windows Task Scheduler GIỮ phần wake + execution: `TikTokSchedulerWake` 6:00, `GmailSchedulerWake` 8:00, `TikTokAllSchedulerTray` 9:30, `TikTokScheduler` (logon, tiktok-luot nuoi acc), `TikTokScheduleRecovery` + `TikTokScheduleRecoveryHealth` (lease-fenced watcher).
- **Wake timers đánh thức máy đang sleep — Hermes cron KHÔNG wake được máy** → không thay thế được Task Scheduler ở lớp này.
- Hermes cron chỉ dùng cho lớp quyết định/báo cáo: đọc manifests sau batch → quyết recovery máy nào → gửi 1 báo cáo Telegram gọn. Không chuyển nguyên cục schedule qua Hermes.
- Cadence = nhịp đăng (tần suất + thời điểm mỗi acc, vd 1-2 video/ngày cách giờ nhau), không phải nội dung. Post 60 máy cùng lúc = cadence đồng loạt = signature dễ phát hiện.
