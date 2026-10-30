---
name: farm-alert-autonomous-recovery
description: Taadaa Farm Alert recovery to closeout.
---
# Farm Alert Autonomous Recovery

> Core Refs: `feed-tab-fallback-canary-gap-and-target-bound-validation-20261030.md`, `gate-abc-and-6gates-canary-watchdog-monitoring-20261030.md`, `crystallize-step26-invariant-and-watchdog-12gates-20261030.md`, `dynamic-feed-row0-starvation-and-contiguous-video-triage-20261029.md`, `dynamic-feed-row0-starvation-and-ssh-stderr-masking-20261029.md`, `upload-hook-auto-login-recovery-and-canary-gate-wiring.md`, `canary-receipt-expiry-and-safe-push-pre-commit.md`, `recovery-proof-and-operator-closeout.md`, `anti-performative-alert-handling-and-immediate-code-fix.md`, `missing-account-switcher-vs-auto-login-fail-closed.md`, `admin-cluster-remote-adb-socket-injection-and-welcome-back-switcher.md`, `run-artifacts-extraction-and-session-dedup.md`, `upload-batch-alert-triage-and-flop-reporting-separation.md`, `blank-workbook-id-cross-file-recovery-and-create-button-tokens.md`, `feed-batch-alert-triage-and-cold-start-transient-20261029.md`.

## UI evidence: target screen only

> Ref: `references/report-routing-and-workbook-shape-20261011.md`.
- Duyệt hiện trường qua `MEDIA:<path>`. CẤM gửi ảnh Home/Launcher sau teardown/lỗi.
- Bắt buộc chụp in-app (Profile/Settings/Popup/Switcher) TRƯỚC KHI teardown.
- **KỶ LUẬT SOI MẮT ẢNH CỤC BỘ QUA BROWSER VISION:** Khi nghiệm thu ảnh local (`D:/Taadaa/reports/*.png`), dùng `browser_navigate(url="file:///<path>")` để nạp ảnh vào trình duyệt, sau đó gọi `browser_vision` soi mắt kiểm tra (profile, username, avatar, không popup/đen màn hình) TRƯỚC KHI đính kèm `MEDIA:<path>`.
- **CANARY RUNNER TIMEOUT & BACKGROUND EXECUTION:** Quy trình chạy Canary trên thiết bị thật (Galaxy S7) thường mất 2-4 phút. Lệnh `terminal` foreground mặc định sẽ bị trần 60s kill ngang tiến trình. BẮT BUỘC chạy `canary_runner.py` với `terminal(background=True, notify_on_complete=True)` và quản lý bằng `process(action='wait', timeout=...)`.

## 🛑 FEED TAB FALLBACK & IMMEDIATE RECOVERY
- Khi tab Friends/Following gặp lỗi mạng (`manual-needed:network`) hoặc trống (`manual-needed:empty`): Cơ chế `_tab_fallback_reason` phải lập tức kích hoạt chuyển về For You feed (Graceful Fallback), không được chờ đợi consecutive manual guard >= 2 khiến phiên dừng sớm. BẮT BUỘC bảo vệ bằng GuardGate rule `case_invariant_prohibit_guarded_friends_feed_fallback` trong `rules.json` và test kiểm chứng ALLOW/DENY để chống agent sau phá. Chi tiết xem: `references/feed-tab-fallback-and-immediate-network-recovery-20261029.md`.
- **ĐỒNG BỘ TRẠNG THÁI FALLBACK BẮT BUỘC:** Khi gọi Graceful Fallback về For You, BẮT BUỘC cập nhật đồng thời bộ 3 biến trạng thái: `confirm["detected"] = FEED_TYPE_FOR_YOU`, `confirm["feed_type"] = FEED_TYPE_FOR_YOU`, và `expected_label = _expected_feed_label(FEED_TYPE_FOR_YOU)`. Nếu bỏ sót, hàm `_is_navigation_mismatch_row` sẽ so sánh `detected` cũ vs `next_feed_type` mới -> false mismatch -> rơi vào retry với stale `expected_label` gây sập hàng loạt máy lỗi `detector-miss:feed not confirmed`.
- **BẪY CANARY HÌNH THỨC TRÊN TAB NAVIGATION:** Sửa logic tab navigation/fallback mà chỉ chạy generic `--recovery-test-swipes 2` sẽ KHÔNG BAO GIỜ kích hoạt fallback (do `videos_until_tab_decision` khởi tạo 3-8 nên 2 swipes đầu chỉ lướt thuần For You). BẮT BUỘC ép phân bổ tab (`--feed-distribution '{"for-you": 0.2, "following": 0.4, "friends": 0.4}'` hoặc `--max-swipes 5`) và hậu kiểm `log.jsonl` có event `action: fallback_feed_tab` mới được công nhận Canary Pass. Chi tiết xem: `references/feed-tab-fallback-canary-gap-and-target-bound-validation-20261030.md`.
- **SEMANTIC CANARY ENGINE (GẮN NÃO LLM CHỐNG CANARY HÌNH THỨC):** `canary_plan.py --semantic` gọi LLM phân tích trực tiếp `git diff` để sinh `target_flow`, `cli_args_override` (ép cờ CLI kích hoạt đúng nhánh code), và `log_assertions` (`required_patterns` + `forbidden_patterns`). Thang Planner kế thừa 100% chuẩn Gate B (`gate_b_planner.py`): (1) Gemini Web qua :20129 -> (2) Sol Worker qua :20129 -> (3) Claude CLI local qua stdin. `canary_runner.py` nạp cờ ép chạy máy thật và hậu kiểm cơ học file log (`log.jsonl`/`summary.txt`); nếu thiếu pattern bắt buộc hoặc dính lỗi cấm lập tức ĐÁNH RỚT CANARY, diệt tận gốc bệnh chạy lướt feed 2 cái lấy lệ. Chi tiết xem: `references/semantic-canary-engine-and-anti-performative-discipline-20261030.md`.
- **KỶ LUẬT CƠ GIỚI HÓA BẮT BUỘC (CLOSEOUT STEP 2.6):** Mọi fix bug/script từ Farm Alert BẮT BUỘC phải kết tinh thành Invariant Rule trong repo `rules.json` (hoặc waiver hợp lệ) ngay trong turn để vượt qua Closeout Gate Step 2.6 (`crystallize.py`). CẤM sửa chay chỉ nộp code mà không đóng đinh rule, CẤM lưu memory suông, CẤM để chờ User nhắc. Nếu rule gây false-positive, sử dụng quy trình Ratchet `rule.py amend` kèm `--fp-diff` để nới lỏng an toàn.
- **GIÁM SÁT GATE A-B-C & GATE 6 CANARY (WATCHDOG 14 GATES):** Toàn bộ quy trình Gate A (Điều tra: bắt `subagent_edit_blocked`), Gate B (Lập Plan: `SOL_PLAN_ID`), Gate C (Worker Dispatch), cùng 6 Gates Điều Phối (với Gate 6 Canary trên máy thật: bắt `BLOCKED_CANARY_REQUIRED` khi trốn Canary) đã được đưa vào `gate_compliance_watchdog.py` quét tự động mỗi 6h. Chi tiết xem: `references/gate-abc-and-6gates-canary-watchdog-monitoring-20261030.md`.
- **UNIFIED PATCH PIPELINE (NỐI XÍCH CƠ HỌC GATES 1-6):** S0 Precheck (RepoLock + Scope Lock) -> S1 Plan O(1) (`gate_b_planner.py` Gemini 120s / Claude 150s / Sol 120s) -> S2 Patch (`dispatch_worker.py` Qoder T0 / Sol T1) + Hậu kiểm độc lập -> S3 Test -> S4 Canary Gate 6 máy thật -> S5 Hold (Ký HMAC state, bind diff hash, xuất `MEDIA:`, dừng tiến trình chờ User). Chốt phiên chỉ mở khi User gõ `Done` kích hoạt `confirm`. Lỗi ở bất kỳ khâu nào lập tức kích hoạt `full_rollback()` dọn sạch đĩa. Chi tiết xem: `references/unified-patch-pipeline-and-gates-1-to-6-automation-architecture.md`.

## 🛑 TRIAGE LỖI CÁP VẬT LÝ ADB (CM_PROB_PHANTOM)
- Khi nhận alert máy offline / `[01_open]` mà ADB báo `device not found` hoặc `offline`:
  Chạy lệnh PowerShell:
  `Get-PnpDevice | Where-Object { $_.InstanceId -like "*<serial>*" } | Select-Object FriendlyName, Status, Present, Problem`
- Nếu `Present: False` hoặc `Problem: CM_PROB_PHANTOM`: Lỗi cáp USB/nguồn. DỪNG NGAY, chuyển L3 BLOCKED.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
