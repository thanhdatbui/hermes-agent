# Index of References for tiktok-feed-session

See specific topic references under this directory for detailed guides, triage notes, and incident writeups:
- `4ca-2phien-upload-follow-rules.md`: Kiến trúc 4 Ca x 2 Phiên (HCMC), phân định quyền Phiên 1 (Feed only) vs Phiên 2 (Feed + Upload hook), cổng an toàn Follow hook (nick >= 5 video), thực tế chạy song song 160 máy độc lập (8 phiên/máy/ngày, ~60-64p screen-on), phân định Cố định Vĩ mô (Persona Schedule) vs Random Vi mô (Jitter phút start ca ±3-7p, Stagger 2-8s, dwell time), và quy chuẩn báo cáo chốt phiên 3 trụ cột.
- `natural-feed-follow-watch-time-gate-and-watchdog-metrics.md`: Watch Time Gate (ngâm xem 8-12s) chống TikTok nhả follow tự nhiên khi lướt feed, phân tách cổng follow chéo vs follow tự nhiên và đưa chỉ số Follow Tự Nhiên vào báo cáo Ca của feed_session_watchdog.
- `watchdog-premature-reporting-and-follow-cooldown-mechanics-20260915.md`: Race condition watchdog chốt báo cáo sớm khi Feed xong nhưng Follow hook chưa kịp ghi (báo ảo 0 lượt follow), bản chất cơ chế `fail_streak` / cooldown và lỗi switcher lệch Display Name vs Username.
- `alert-dedupe-one-per-machine-session.md`: Deduplication logic cho Farm Alerts theo từng máy và phiên chạy.
- `rotation-preparation-timeout.md`: Khắc phục timeout xoay màn hình chân dung trên S7.
- `alert-trigger-vs-terminal-state.md`: Phân biệt giữa trigger lỗi UI và trạng thái terminal khi thu hồi hiện trường.
- `tiktok-public-profile-screen-classification-fi2.md`: Heuristic phân loại màn hình public profile qua chevron `:id/fi2` và nút tin nhắn trong `classifier.py`.
- `deadline-exceeded-partial-feed-session-classification.md`: Phân loại trạng thái khi chạm deadline (`RunPlanDeadlineExceeded`): ghi nhận `degraded`/`success` nếu đã hoàn thành lượt lướt (`completed > 0`), ngăn chặn false alert và đảm bảo cleanup máy.
- `false-positive-manual-challenge-feed-caption-and-batch-alert-20260919.md`: Quy chuẩn khắc phục 2 tầng (Classifier & Batch Aggregator) chống false-positive `manual-needed:manual_challenge` do caption feed / `verify-bar-close` và chuẩn hóa cảnh báo batch.
- `gemphone-verify-bar-close-false-manual-challenge-20260919.md`: Phân tích tác nhân GemPhoneFarm inject `verify-bar-close` gây cảnh báo giả mất phiên và quy trình kiểm chứng canary O(1) qua WinRT OCR.
- `profile-verification-focus-lost-vs-captcha-false-alarm-and-switcher-missing-20260923.md`: Phân biệt lỗi mất focus khi verify profile với Captcha/Challenge thật (tránh false alert `CẢNH BÁO XÁC MINH`), và triage lỗi `ACCOUNT_MISSING` do bảng Switcher chưa kịp bung trên S7.
- `fast-auto-login-parent-lock-and-wifi-dead-service-reboot.md`: Kế thừa device lock (`--allow-parent-lock`) khi feed session gọi fast auto-login bù nick thiếu trên máy, và cơ chế Guarded Auto-Reboot trong `vpn_preflight.py` khi subsystem Wi-Fi của Android Framework bị crash ngầm (`Can't find service: wifi`).
- `empty-following-feed-and-foreign-profile-recovery.md`: Cơ chế Graceful Tab Fallback tự động quay về For You (FYP) và hạ trạng thái `DEGRADED` khi tab Following/Friends rỗng hoặc báo lỗi mạng ảo trên nick mới, và loại trừ profile người lạ (`is_foreign_profile`) trong `calibrate_screens.py`.
- `account-switcher-manual-row-reason-propagation.md`: Lan truyền chính xác `switch_reason` từ `switcher_manual_row` thay vì hardcode string chung chung, và lưu ý mock `_capture_xml_text` đủ vòng settling/retry tránh `StopIteration`.
- `share-sheet-and-contact-suggestion-pitfalls.md`: Khắc phục lỗi bắt nhầm từ khóa rộng ("mời bạn") trên TikTok LIVE stream/comments, và xử lý dứt điểm Bottom Sheet "Gửi đến" (Share sheet) bằng phím Android BACK thay vì vuốt màn hình.
- `admin-cluster-remote-upload-and-canary-discipline.md`: Khắc phục lỗi false-positive "Hết video" trên cụm Admin (Remote PC) khi Kibe là Controller, kiến trúc SSH remote execution thay vì share SMB, và kỷ luật wakeup chạy canary không thoái thác.

