---
name: farm-anti-overengineering
description: >-
  Kỷ luật thực thi chống over-engineering cho Hermes Coordinator & Worker trên hệ thống Taadaa Phone Farm.
  Áp dụng cho mọi tác vụ debug, sửa script, sửa flow và kiểm thử: giới hạn ngân sách tool calls (max 15-20),
  chặn đứng phân tích lan man (analysis paralysis), cấm test inflation, cấm simulation thừa mứa.
---

# Farm Anti-Overengineering Discipline (Taadaa Phone Farm)

References:
- `references/in-app-popup-attribution-and-allowlist-work-package-case-m78.md` — Bài học hiện trường Máy 78: Tránh ảo giác nguồn popup (đoán mò app YouTube chen vào TikTok), kiểm tra O(1) dumpsys window/ping mạng và chuẩn hóa WORK_PACKAGE bounded (<= 8 calls) cho popup allowlist (06/09/2026).
- `references/open-goal-dispatch-paralysis-and-synchronous-pool-stall-case-m14.md` — Bài học sự cố kéo dài 1.5 giờ: Cạm bẫy giao goal mở khi alert đã có triệu chứng, worker analysis paralysis đốt sạch 35 turns, nghẽn đồng bộ delegation pool và cơ chế giữ lock 1h chứng minh qua log Canary (06/09/2026).
- `references/account-switch-feed-drift-and-zero-delay-dispatch.md` — Sự cố lỗi `profile username still mismatched after switch` do drift về Feed sau khi đổi nick (Case Máy 79), cơ chế re-tap Profile vô điều kiện và kỷ luật Zero-Delay Dispatch khi bị nghi vấn Coordinator điều tra chậm (06/09/2026).
- `references/multi-component-broad-reconnaissance-trap-and-pipelined-slices.md` — Kỷ luật thực thi cắt lát độc lập (Pipelined Vertical Slices): xử lý triệt để từng thành phần (Read -> Patch -> Compile) trước khi sang file tiếp theo, chống bẫy khảo sát diện rộng (Broad Reconnaissance Trap) làm kiệt quệ ngân sách tool calls trên task đa thành phần (06/09/2026).
- `references/profile-username-mismatch-and-latest-run-resolution.md` — Tra cứu O(1) run mới nhất tránh bẫy thiếu symlink `.ai-runs/latest`, cấm grep trong `python_runner` dính timeout 900s và xử lý lỗi `profile username still mismatched after switch` (06/09/2026).
- `references/anti-regression-defense-and-preflight-gate.md` — Kiến trúc phòng thủ chống Regression 4 lớp (Pyright `reportPossiblyUnbound`, `diff_guard.py` AST caller check, hermetic module pack, Coordinator contract & `preflight.py` < 15s) (06/09/2026).
- `references/cron-log-audit-and-bugfix-regression-statistics.md` — Quy chuẩn quét log cron dài ngày, phân tầng truy xuất O(1) summary.txt, đối chiếu commit/cases và phương pháp luận phân biệt True Regression vs New Variant (06/09/2026).
- `references/transient-focus-drop-recovery-and-screencap-corrupt-guard.md` — Multi-tier fallback cứu transient focus drop sau navigation tap / chuyển view (Case 125, 127), bẫy thụt lề fallback UnboundLocalError (Case 126) và kiểm tra 8 magic bytes PNG cho ADB screencap buffer (Case 128) (06/09/2026).
- `references/claude-cli-quota-hard-guard-and-lockout-cache.md` — Sự cố vi phạm chạm trần 100% Claude Pro, bài học thất bại của luật mềm và giải pháp Hard Guard Tầng 0 chặn đứng vật lý trong `farm-coordinator-guard` (06/09/2026).
- `references/fsm-failed-state-masking-and-subagent-patch-verification.md` — Giải mã lỗi failed_at_state_FAILED do FSM mất dấu state gốc, bẫy worker báo cáo patch ảo chưa ghi đĩa, menu ngữ cảnh nổi che caption và chuyển dọn nháp thành non-fatal (06/09/2026).
- `references/coordinator-guard-git-flag-and-batch-lock-pitfall.md` — Cạm bẫy cờ `git -C <dir>` bị Coordinator Guard chặn nhầm trong pha `WORKER_RUNNING` (ưu tiên dùng `workdir` của tool terminal) và phân biệt stale lock máy đơn lẻ khi batch mẹ multi-machine vẫn còn PID (06/09/2026).
- `references/canary-pass-scope-lock-and-review-creep-trap-case-m39.md` — Cạm bẫy Review Scope Creep sau khi Canary đã Pass khiến phiên Alert kéo dài 3 tiếng (Case Máy 39), kỷ luật đóng băng scope (Canary Pass = Freeze Scope) và trần thời gian worker (06/09/2026).
- `references/case-90-camera-template-hub-3-layer-hard-lock.md` (trong `tiktok-upload-ui-recovery`) — Case 90 (Máy 39): Khóa cứng 3 tầng chống kẹt CapCut Template Hub / LIVE khi mở camera TikTok (Tab Normalizer Gate, Template Early-Exit Guard, Negative Spatial Gate Y: 15-75% & Strict Left Priority) (06/09/2026).
- `references/draft-cleanup-non-fatal-and-select-all-variants.md` (trong `tiktok-upload-ui-recovery`) — Case Draft Cleanup: Selector đa biến thể Chọn tất cả/Select all, hạ cấp draft cleanup thành non-fatal tránh huỷ upload video và quy trình áp Patch Contract tinh gọn 5 calls (06/09/2026).
- `references/prompt-misattributed-file-and-unbounded-git-log-timeout.md` — Xử lý cạm bẫy Prompt Misattribution (chỉ định nhầm file lỗi), cấm quét đĩa diện rộng, bẫy `git log -S -p` timeout 900s và lỗi path `/d/...` của search_files (06/09/2026).
- `references/watchdog-worker-running-false-alarm-and-permission-retry.md` — Khắc phục báo động giả Watchdog ở Phase WORKER_RUNNING, Windows PermissionError Retry khi đọc JSON và cảnh báo timeout lock (06/09/2026).
- `references/caption-fill-text-selection-occlusion-and-failed-state-masking.md` (trong `tiktok-upload-ui-recovery`) — Case 89: Khắc phục lỗi `failed_at_state_FAILED` do FSM transition ghi đè terminal state vào `report.json`, menu ngữ cảnh Text Selection ("CẮT | CHÉP | DÁN") che màn hình Composer và cạm bẫy grep diện rộng gây timeout 900s (06/09/2026).
- `references/focused-package-unavailable-xml-recovery-and-patch-contract-case-127.md` — Case 127: Khôi phục focused package unavailable qua UI XML, xử lý stale device lock khi master batch còn sống, và bài học thực chiến Patch Contract (134s vs 40m analysis paralysis) (06/09/2026).
- `references/in-flight-diff-scoping-and-diverged-amend-recovery.md` — In-flight diff scoping chống diff rỗng khi worker đã commit trước Gate 1 Plan-Review & quy trình 3 bước phục hồi bằng `git reset --soft origin/<branch>` khi amend làm diverged nhánh remote (06/09/2026).
- `references/navigation-tap-focus-recovery-and-switcher-indentation-trap.md` — Phục hồi focus 2 lớp (dumpsys top resumed activity / UI XML) cho navigation tap và cạm bẫy thụt lề UnboundLocalError recaptured_xml trong verify_and_switch_profile (06/09/2026).
- `references/patch-contract-watchdog-semantic-divergence-and-unbound-canary.md` — Bài học thực thi Patch Contract bounded (<= 8 calls): xử lý test semantic divergence khi đổi luật watchdog lease release, tránh bẫy search_files os error 3 trên Windows và ghi nhận UnboundLocalError recaptured_xml trên Canary máy 36 (06/09/2026).
- `references/focused-package-unavailable-xml-fallback-and-dumpsys-recents.md` — Giải pháp 2 lớp fallback khi focused package unavailable: fallback regex & dumpsys recents trong `observe.py` và phục hồi an toàn từ UI XML marker trong `safety.py` repo `tiktok-luot nuoi acc` (06/09/2026).
- `references/video-pick-create-entry-capcut-template-and-surfaceflinger-secure.md` (trong `tiktok-upload-ui-recovery`) — Phân tích lỗi VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED, cơ chế tap lại Create button sau khi dismiss CapCut template/hub, đồng bộ signature trong recovery handoff ledger và xử lý cạm bẫy SurfaceFlinger FB protected (12-byte null screencap).
- `references/follow-friends-popup-profile-guard-and-back-fallback.md` — Giải pháp 2 lớp Profile Guard chống false-positive popup kết bạn trên Profile/Feed & Navigation Fallback (header back / Back key) kèm đồng bộ `current_root = after_root` trong `benign_popup.py` (06/09/2026).
- `references/adb-keyevent-timeout-redaction-and-stale-lock.md` — Giải mã `<redacted>` trong log ADB (`KEY` sensitive word), bọc an toàn try/except cho `keyevent 4` trong feed session, xử lý stale device lock và chuẩn cờ `-Run` / `-SkipAccountWorkbookSync` khi chạy canary (06/09/2026).
- `references/canary-patch-budget-exhaustion-and-feed-guard-pattern.md` — Sự cố kiệt quệ 35 tool calls khi đọc dump XML lớn thay vì patch trực tiếp, bài học Lean Canary Execution và giải pháp 3 lớp Feed Guard chống false-positive popup trên TikTok Main Feed (06/09/2026).
- `references/adb-redacted-keyevent-timeout-and-grep-trap.md` — Giải mã log `adb command timed out: ... shell input <redacted> 4` (do 'KEY' trong SENSITIVE_WORDS redact 'keyevent'), cơ chế timeout phím Back trên Samsung S7 và cạm bẫy grep -rn 900s (06/09/2026).
- `references/powershell-log-probe-pathnotfound-and-grep-timeout.md` — Sự cố `PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand` trong launcher PowerShell (`run_parallel.ps1`), cạm bẫy hardcode log path trong pipeline caller và bẫy timeout 900s khi grep diện rộng (06/09/2026).
- `references/large-file-reading-exhaustion-and-direct-script-patching-20260906.md` — Sự cố kiệt quệ 35 tool calls khi worker đọc context phân trang trên file mã nguồn khổng lồ (>22.000 dòng như feed_swipe_smoke.py), giải pháp Direct Script Patching và chỉ thị cưỡng chế cho Coordinator (06/09/2026).
- `references/coordinator-stall-and-zero-delay-dispatch-lesson-20260906.md` — Bài học đắt giá sự cố ngâm phiên 4 tiếng (06/09/2026): cấm Coordinator tự sửa code/grep diện rộng dính timeout 900s, bắt buộc Zero-Delay Dispatch và tuân thủ thứ tự B3 Patch trước -> B4 Canary sau.
- `references/runaway-worker-case-study.md` — Phân tích thực tế sự cố runaway worker 150 tool calls kéo dài 2 tiếng ngày 05/09/2026 và bài học đúc kết.
- `references/farm-coordinator-guard.md` — Kiến trúc PreToolUse Hook & FSM Phase Gate (tư vấn bởi Claude Opus) khóa cứng Coordinator ở Phase Alert và mở terminal ở Phase Closeout.
- `references/claude-cli-bounded-review-loop.md` — Quy trình điều phối review chéo với Claude CLI (tối đa 3 vòng lặp) và kỹ thuật gọi Python subprocess chống lỗi bash escaping.
- `references/config-and-plugin-repo-sync.md` — Bắt buộc đồng bộ toàn bộ config và custom plugin (như farm-coordinator-guard) vào git repo khi sửa ở local runtime.
- `references/atomic-workbook-fallback-pattern.md` — Chuẩn triển khai 3 lớp cho atomic update file Excel trong môi trường farm đa tiến trình (locking, stale TTL, Windows PermissionError retry).
- `references/atomic-workbook-fallback-and-windows-locking.md` — 5 cạm bẫy atomic workbook fallback, Windows file locking PermissionError retry và concurrency protection (Claude review 05/09/2026).
- `references/cross-consumer-runner-delegation-and-fail-safe-cleanup.md` — Cấm tự code tay vòng lặp swipe/jitter khi runner chuyên trách (`run_tiktok.py`) đã có sẵn; kỹ thuật cô lập subprocess (`PYTHONPATH`, device lock dir) và bảo đảm đóng app về Home trên mọi nhánh fail/abort.
- `references/terminal-powershell-pythonpath-leak-and-canary-timeout.md` — Xử lý rò rỉ biến môi trường `PYTHONPATH` gây xung đột C-extension PIL (`_imaging`) và quy trình 4 bước kiểm chứng Canary khi dính timeout 300s của terminal tool.
- `references/canary-random-swipes-and-zero-delay-dispatch.md` — Quy chuẩn Canary Swipes Random (2–4 swipes qua Get-Random), xử lý lỗi profile mismatch và bài học Zero-Delay Dispatch khi nhận lệnh sửa code "Rồi sửa đi" (06/09/2026).
- `references/claude-opus-patch-contract-and-large-file-coordination.md` — Chuẩn hóa Patch Contract, Uniqueness Check (grep -c == 1), Escape Hatch điều tra và Rollback Canary khi điều phối Worker trên monolith file lớn (tư vấn Claude Opus CLI 06/09/2026).
- `references/multi-file-monolith-dispatch-trap-and-patch-contract-lesson-20260906.md` — Cạm bẫy giao task đa file mở trên monolith khiến worker kiệt quệ 35 lượt gọi (Máy 27), bài học xác thực đĩa vật lý và quy trình 2 pha bắt buộc Patch Contract (06/09/2026).
- `references/navigation-tap-unknown-focus-lost-and-python-runner-grep-trap.md` — Giải mã lỗi 'TikTok focus lost after navigation tap: unknown' trên màn hình Profile/Home, bẫy timeout 900s khi grep trong python_runner chứa thư mục runs/ và giải pháp xác thực foreground 3 lớp (06/09/2026).
- `references/claude-opus-max-watchdog-audit-and-per-session-heartbeat.md` — Quy chuẩn Reviewer (OmniRoute combo vs Claude CLI Opus Max), bài học kiến trúc từ audit Claude Opus Max và chuẩn hóa Heartbeat Per-Session Watchdog (06/09/2026).
- `references/silent-freeze-dispatch-receipt-and-stuck-watchdog.md` — Sự cố "Treo im lặng 1 tiếng", cấm tuyệt đối token `[SILENT]` khi dispatch worker, quy tắc Dispatch Receipt 1 tin duy nhất, tách bạch 2 pha Patch Code vs Device Canary và cơ chế Silent Watchdog ("chỉ hú khi thực sự treo" > 5 phút) (tư vấn Claude Sonnet CLI 06/09/2026).
- `references/worker-tool-gate-and-analysis-paralysis-prevention.md` — Cơ chế WorkerToolGate (READ_BUDGET=3, WRITE_DEADLINE=4), chuẩn hóa WORK_PACKAGE triệt tiêu Analysis Paralysis và tự động dọn Stale Device Lock / PYTHONPATH (06/09/2026).

Quy tắc tối thượng: **Nhanh, Trúng, Gọn, Không Thừa Mứa.**
Hệ thống farm cần script chạy thực chiến trên máy thật, không cần các bộ test hàn lâm hay mô phỏng lý thuyết kéo dài hàng tiếng đồng hồ.

**TRẦN CỨNG HỆ THỐNG (config.yaml):** `delegation.max_iterations = 35` — Khóa cứng vĩnh viễn trong Hermes config, chặn tuyệt đối worker runaway. Mọi worker BẮT BUỘC hoàn thành dưới 15 phút và <= 20 tool calls.

---

## 1. PHÂN LOẠI TASK & THANG NGÂN SÁCH LINH HOẠT (DYNAMIC TIER BUDGET)

Không cào bằng mọi task. Ngân sách tool call và thời gian được tính theo cấp độ lỗi:

| Cấp độ Task (Tier) | Phạm vi & Bản chất lỗi | Giới hạn Tool Calls | Thời gian tối đa | Quy định kiểm thử & xử lý |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 0: Inspect / Read-only / OCR** | Đọc log, OCR ảnh hiện trường, giải mã lỗi, tra cứu trạng thái máy. | **<= 10 calls** | **< 5 phút** | **CẤM TUYỆT ĐỐI sửa code, commit, hoặc chạy test suite.** Chỉ trả về kết quả phân tích / OCR và kết thúc ngay. CẤM reverse-engineer toàn bộ process tree hoặc mở rộng điều tra lan man. |
| **Tier 1: Hotfix / Minor (T1)** | Sửa 1 hàm cụ thể, format chuỗi, regex, cú pháp, chỉnh selector/text UI, thêm timeout/flag. | **<= 10 calls** | **<= 5 phút** | CẤM viết test mới đồ sộ. CẤM tạo probe script trong `%TEMP%`. Chỉ sửa file, chạy 1 focused test hoặc py_compile (<30s). |
| **Tier 2: Flow Fix / Medium (T2)** | Flow bị kẹt bước, popup mới, lệch luồng điều hướng, logic retry/recovery đa bước trong script. | **<= 20 calls** | **<= 12 phút** | Sửa đúng flow, chạy đúng test runner của flow đó. |
| **Tier 3: Live Canary ADB (T3 Canary)** | Chạy thực chiến trên máy thật sau khi code đã được vá & py_compile qua kiểm chứng. | **<= 8 calls** | **<= 10 phút** | Chạy random swipes `(Get-Random -Minimum 2 -Maximum 5)` qua runner script chính thức. |
| **Tier 4: Major / Architectural** | Sửa kiến trúc đa repo (core + consumer), thay đổi DB/workbook, sửa giao thức socket/ATX. | **Chia Phase Milestone** | Mỗi phase **< 20 calls** | **CẤM chạy 1 lèo 100+ turns.** Bắt buộc chia nhỏ thành từng Phase độc lập. |

---

## 2. QUY TẮC CHECKPOINT (MILESTONE CHECKPOINT)

- **Mục đích:** Ngăn chặn Worker rơi vào vòng lặp sinh test / mô phỏng vô tận (Runaway Loop).
- **Cơ chế Checkpoint:** 
  - Nếu task phức tạp chạm mốc **20 – 25 tool calls** mà chưa xong, Worker dừng lại và xuất báo cáo Checkpoint:
    * Đã xác định được nguyên nhân gì?
    * Đã sửa được những file nào?
    * Khúc mắc/blocker còn lại là gì? Cần thêm bao nhiêu bước để hoàn tất?
  - Không cho phép worker chạy âm thầm quá 35 turns mà không có điểm dừng.

---

## 3. CHU TRÌNH 4 BƯỚC TINH GỌN (LEAN 4-STEP LOOP)

1. **Bước 1: Đọc đúng log lỗi (1 – 2 calls)**
   - Đọc 50 dòng cuối của `reg_log.txt`, `social_reg_log.txt`, hoặc `summary.txt`.
   - Nắm chính xác exception traceback, tên file và số dòng gây lỗi.
   - **CẤM:** Không đọc lan man sang các repo hay file không liên quan khi đã có traceback rõ ràng.

2. **Bước 2: Sửa đúng vị trí dòng code (1 call)**
   - Dùng `read_file` đọc đúng đoạn code chứa lỗi.
   - Sửa bằng `patch` hoặc `write_file` đúng tối thiểu phần cần sửa (minimal diff).
   - Không refactor code xung quanh.

3. **Bước 3: Kiểm tra nhanh cú pháp & logic tối thiểu (1 – 2 calls, < 30s)**
   - Chạy `python -m py_compile <file_da_sua>` để chắc chắn không lỗi cú pháp.
   - Nếu là hàm logic thuần túy (như xử lý chuỗi/regex): chỉ chạy đúng 1 test case liên quan qua `python -c "..."` hoặc pytest trên đúng 1 test file.
   - **CẤM:** Không chạy lại toàn bộ test suite 100+ tests của cả repo nếu thay đổi chỉ mang tính cục bộ.

4. **Bước 4: Báo cáo & Chạy Canary (nếu áp dụng)**
   - Báo cáo kết quả gọn (Chuẩn B5 Closeout): Báo cáo file/hàm đã sửa + kết quả canary (CẤM paste tràn diff code dài dòng gây loãng ngữ cảnh chat/Telegram).
   - Nếu có máy thật bị kẹt: kích hoạt canary trên đúng máy đó để kiểm chứng.

---

## 4. BẢNG ĐIỀU CẤM TUYỆT ĐỐI (DENYLIST)

| Hành vi vi phạm (Anti-Pattern) | Hậu quả gây lãng phí | Quy định bắt buộc |
| :--- | :--- | :--- |
| **In-App Popup Attribution Hallucination & External App Blaming** (Đoán mò popup của app khác hoặc đổ lỗi rớt Wi-Fi khi TikTok gặp popup nội bộ - Case Máy 78) | Khi TikTok hiện dialog tính năng mới (như "Tự động tải video về qua Wi-Fi để xem ngoại tuyến?"), Coordinator/Worker đoán mò do app ngoài (YouTube, hệ thống) chen vào hoặc đổ lỗi rớt mạng. Gây bức xúc tột độ cho user (*"Nghe vô lí vc đang ở trong tiktok mắc gì youtube nhảy vào. Đọc log kĩ coi"*), dẫn dắt sai hướng điều tra và làm phân tán nguồn lực. | **XÁC THỰC O(1) PACKAGE BẰNG DUMPSYS WINDOW & KIỂM TRA MẠNG THẬT.** BẮT BUỘC kiểm tra `dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'` để xác định 100% package đang foreground (TikTok `com.ss.android.ugc.trill`) và ping `8.8.8.8` trước khi kết luận. CẤM TUYỆT ĐỐI suy đoán cảm tính popup thuộc app thứ ba khi không có bằng chứng dumpsys. Khóa cứng WORK_PACKAGE (<= 8 calls) cho popup allowlist. Chi tiết: `references/in-app-popup-attribution-and-allowlist-work-package-case-m78.md`. |
| **Interactive ADB Probing Loop** ("Mò bấm tay" từng lệnh ADB trên terminal) | Worker chạy `python -c` lặp lại 80–110+ turns gửi `input tap/swipe`, mò toạ độ trên máy farm. Gây timeout 900s và làm loạn UI điện thoại. | **CẤM TUYỆT ĐỐI điều khiển ADB rời rạc.** Mọi luồng UI BẮT BUỘC đóng gói thành hàm Python hoàn chỉnh trong file script vật lý. |
| **Open-Goal Investigation on Known-Symptom Alerts & Synchronous Delegation Stall** (Giao goal mở khi alert đã rõ triệu chứng khiến worker kiệt quệ 35 calls & nghẽn session chính 1.5 tiếng - Case Máy 14) | Khi alert đã có ảnh hiện trường và log lỗi cụ thể (như popup khảo sát quảng cáo), Coordinator lại giao worker "điều tra root cause và sửa code". Worker sa vào bẫy đọc lặp lại 35 tool calls (mất 37,6 phút), đặc biệt khi pool delegation đầy khiến worker chạy Synchronous làm Coordinator bị đơ hoàn toàn. Hậu quả: phiên kéo dài hơn 1 tiếng rưỡi mới xong việc, gây nghi vấn báo cáo láo. | **CẤM GIAO GOAL MỞ KHI ALERT ĐÃ CÓ TRIỆU CHỨNG / SCREENCAP RÕ RÀNG.** Coordinator BẮT BUỘC nhận diện ngay dạng lỗi (Hotfix/Registry), giao thẳng Patch Contract với chỉ thị áp đặt (<= 8 calls, ghi đĩa ngay turn 3, chạy canary). Tuyệt đối không để worker tự do điều tra ngược vào `automation-core` khi triệu chứng đã rõ ràng. Chi tiết: `references/open-goal-dispatch-paralysis-and-synchronous-pool-stall-case-m14.md`. |
| **Missing Device Lock / Preemption** (Bỏ quên khóa máy khi can thiệp UI) | Can thiệp ADB máy farm mà không khóa máy $\rightarrow$ Cron nuôi acc (TikTok / GemPhone) chạy nền giật lại màn hình, swipe đè, làm worker kẹt vòng lặp. | **BẮT BUỘC bọc `acquire_device_lock(force_preempt=True)`** để tạm dừng cron nuôi acc. Luôn bấm HOME (`keyevent 3`) trước khi nhả lock. |
| **Broad Disk Scan For Known Serials/Config** (Quét đĩa tìm serial/config/code) | Tự viết `python -c "os.walk(...)"`, `glob(recursive=True)` quét cả repo/ổ đĩa tìm serial hay cờ config/code thay vì đọc trực tiếp các file flow đích đã biết (`feed_swipe_smoke.py`, `multi_machine_feed_session.py`, `run_tiktok.py`). Gây treo I/O và dính timeout 900s. | **CẤM TUYỆT ĐỐI quét đĩa diện rộng.** Dùng thông tin Coordinator cấp, file mapping cố định (`PROXYgandienthoai.xlsx`, `taikhoan_run_safe.xlsx`) hoặc đọc thẳng file flow liên quan. |
| **Prompt Misattribution Panic & Unbounded `git log -S -p`** (Hoang mang khi prompt chỉ định nhầm file rồi quét đĩa / git diff sâu) | Prompt chỉ định file A nhưng biến/lỗi thực tế nằm ở file B hoặc đã được commit trước đó sửa xong. Agent không thấy biến trong file A liền hoang mang chạy `os.walk('D:/Taadaa')` hoặc `git log -S <symbol> -p` trên monolith repo không chỉ định path, dẫn tới nghẽn I/O và dính timeout 900s liên tiếp. | **XÁC THỰC O(1) FILE ĐÍCH VÀ KIỂM TRA COMMIT GẦN NHẤT.** Nếu biến không có trong file A: DỪNG LẠI NGAY, cấm quét đĩa. Chạy `git log -n 5 --oneline` hoặc `session_search` để đối chiếu context. Nếu cần tìm commit qua `git log -S`, BẮT BUỘC dùng `--oneline` hoặc chỉ định rõ file (`-- <file>`), CẤM TUYỆT ĐỐI dùng `-p` diện rộng. Chi tiết: `references/prompt-misattributed-file-and-unbounded-git-log-timeout.md`. |
| **Broad Grep/Find in Repo Root, Runtime & Env Dirs** (`D:/Taadaa/<repo>`, `D:/CodexRuntime`, `.codex-work`, `runs`, `.ai-runs`, `python-envs`, `python_runner/runs`) | Chạy `grep -rn`, `find "D:/Taadaa/..."` hoặc glob đệ quy trên root repo, runtime/runs, `python-envs` hoặc `python_runner/` (chứa `python_runner/runs/` với hàng vạn file JSON/logs) gây timeout 900s và tiêu tốn toàn bộ ngân sách turn. Tool `search_files` trên đường dẫn ổ D có dấu cách/tiếng Việt cũng có thể dính lỗi IO error / os error 3. | **CẤM quét đệ quy toàn bộ thư mục gốc repo, runtime/runs, `python-envs/` hoặc thư mục `python_runner` chứa runs.** Khi tìm trong `python_runner`, BẮT BUỘC chỉ grep đích danh các file hoặc thư mục code (`flows/*.py`, `core/*.py`) hoặc dùng `--exclude-dir=runs`. CẤM dùng `find "D:/Taadaa/..." -name ...` (gây timeout 900s). Khi đọc file trong repo đã biết tên, đọc trực tiếp bằng `read_file` hoặc tìm dòng bằng `terminal` `grep -n "<chuỗi>" "<file_đích>"`. Khi gặp `ModuleNotFoundError`, test trực tiếp bằng `python -c "import ..."` thay vì grep cả repo tìm nơi import. |
| **Unhandled PowerShell Log Reading under Stop Preference** (`Get-Content` không bọc `try/catch`) | Khi `$ErrorActionPreference = 'Stop'`, lệnh `Get-Content` trên file log chưa flush hoặc có race condition ném lỗi terminating `PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand` làm crash toàn bộ batch. | **BẮT BUỘC bọc `try/catch` với `-ErrorAction Stop` quanh mọi lệnh `Get-Content` đọc log worker trong launcher PowerShell.** |
| **PowerShell Runner Dot-Source Execution on Fleet** (Dot-source script runner chạy bừa bãi toàn bộ batch trên máy farm) | Khi agent/worker dot-source file runner PowerShell (`. 'D:\Taadaa\...\run_parallel.ps1'`) để test 1 hàm helper, do script không có guard chặn dot-sourcing, PowerShell thực thi toàn bộ code top-level và kích hoạt chạy thật trên 17+ máy farm cùng lúc, xung đột với cron nuôi acc. | **BẮT BUỘC chèn guard `if ($MyInvocation.InvocationName -eq '.') { return }`** ngay sau các khai báo hàm trong mọi runner PowerShell. CẤM TUYỆT ĐỐI dot-source runner script khi chưa kiểm tra guard. |
| **Test Inflation** (Đẻ thêm test suite đồ sộ) | Mất 30–60 phút viết 8–10 test cases cho 1 hàm phụ trợ đơn giản. | **CẤM tự viết file test mới** trừ khi user yêu cầu rõ bằng văn bản. |
| **Monte Carlo / Data Simulation** | Chạy lặp 10.000 lần sinh dữ liệu đo xác suất/entropy. | **CẤM chạy simulation hàng ngàn vòng lặp.** Kiểm tra 1–2 mẫu đại diện là đủ. |
| **Multi-Component Broad Reconnaissance Trap** (Khảo sát/đọc toàn bộ các file và probe terminal trước khi patch bất kỳ file nào) | Khi nhận task gồm 3-5 thành phần (helper class, caller state machine, launcher PowerShell, Excel migration), agent đi đọc và probe toàn bộ các file/sheet trước khi sửa. Gây tiêu tốn 25-32 tool calls và chạm trần lượt gọi trước khi kịp hoàn thành ghi đĩa. | **BẮT BUỘC THỰC THI PIPELINED VERTICAL SLICES (CẮT LÁT ĐỘC LẬP).** Hoàn tất dứt điểm từng thành phần: Đọc hẹp -> Patch -> py_compile -> xong mới chuyển sang thành phần kế tiếp. CẤM đọc trước thành phần B khi thành phần A chưa ghi đĩa xong. Ngân sách <= 3 tool calls cho mỗi thành phần. Chi tiết: `references/multi-component-broad-reconnaissance-trap-and-pipelined-slices.md`. |
| **Tạo Probe Script tạm trong `%TEMP%`** | Viết file `hermes-verify-check-*.py`, chạy rồi xóa lắt nhắt. | **CẤM tạo probe script tạm.** Chỉ dùng `python -c "..."` hoặc pytest trực tiếp. |
| **Re-run Full Test Suite lặp đi lặp lại** | Chạy 100+ tests mất nhiều phút mỗi lần sửa 1 dòng code. Chạy toàn bộ file test chứa nhiều ca kiểm thử tích hợp có `time.sleep` (như `test_device_prepare.py` chạy 25 tests mất gần 2 phút). | **CHỈ chạy test file liên quan hoặc focused test qua `pytest -k "<tên_test>"` để hoàn thành dưới 5 giây.** CẤM chạy full file/suite khi chỉ cần verify 1 hàm đơn lẻ. |
| **Worker Analysis Paralysis & Tool Gate Exhaustion (Worker đọc lặp lại 35 turns mà 0 lần ghi code)** | Worker lặp đi lặp lại việc đọc XML, grep regex, suy diễn trong đầu 35 turns (>30-40 phút, ngốn >2M tokens làm lag model) mà không ghi đĩa. Coordinator dispatch mù không có WORK_PACKAGE khiến worker sau lặp lại vết xe đổ worker trước. | **KHÓA CỨNG TOOLSET BẰNG CODE (WORKER TOOL GATE v2.1):** Worker chỉ được tối đa 3 lần đọc (`READ_BUDGET = 3`). Turn 4 bắt buộc phải write (`WRITE_DEADLINE = 4`), nếu chưa write sẽ bị khóa cứng toàn bộ tool đọc. Coordinator BẮT BUỘC cung cấp `WORK_PACKAGE` (file, hàm, line hint, patch intent) trước khi dispatch. Tự động dọn stale device lock và cô lập `$env:PYTHONPATH` trước khi canary. Chi tiết: `references/worker-analysis-paralysis-and-tool-gate-enforcement-20260906.md`. |
| **Sequential Chunk-by-Chunk Reading Paralysis (Đọc lắt nhắt nhiều turn dù đã có số dòng)** | Khi prompt hoặc traceback đã chỉ rõ số dòng lỗi (ví dụ: dòng 265-267 trong `run_parallel.ps1`, dòng 707 trong `run_night_chain_pipeline.py`), agent lại đi đọc từng đoạn 50-70 dòng khắp file (từ đầu đến cuối), đào sâu sang cả caller/subsystem không liên quan, làm cạn kiệt ngân sách lượt gọi trước khi kịp thực hiện lệnh patch. | **Đọc đúng 1 chunk hẹp và patch ngay:** Khi đã có số dòng rõ ràng, chỉ dùng `read_file` đọc duy nhất 1 chunk (`offset = line - 10, limit = 40`), patch ngay trong turn tiếp theo rồi chạy py_compile / test kiểm chứng. Tuyệt đối không đọc tuần tự lan man khắp các phần khác của file. |
| **Large-File Reading Exhaustion / Tool Call Depletion in Massive Source Files (Đọc lan man trong file khổng lồ > 20.000 dòng làm kiệt quệ Tool Calls)** | File `feed_swipe_smoke.py` dài tới 22.300 dòng (~630 KB). Khi worker subagent được dispatch với directive chung chung, worker theo quán tính gọi `read_file` với `limit=100` để "đọc context" từng đoạn một. Cần hơn 220 calls chỉ để đọc hết file! Kết quả: worker chạm trần `max_iterations = 35` (15-20 phút) mà chưa hề chạm vào đĩa để patch code. User ở session chính bức xúc: *"Clg lâu thế. Mày lại đi grep quét cả ổ đĩa phải k"* và *"Tool call v k đủ đọc context à"*. | **CẤM WORKER GỌI `read_file` PHÂN TRANG TUẦN TỰ TRÊN FILE LỚN > 2.000 DÒNG.** Coordinator BẮT BUỘC trích xuất trước chuỗi `old_string` / `new_string` chính xác và phạm vi dòng cụ thể. ÉP WORKER CHỈ DÙNG SCRIPT PYTHON THAY THẾ CHUỖI TRỰC TIẾP QUA TERMINAL (HOẶC PATCH DUY NHẤT 1 LẦN). Worker không được đọc file, mà chạy script Python `pathlib.Path(...).read_text().replace(...)` hoặc lệnh patch trong đúng 1-2 tool calls, sau đó chạy ngay `python -m unittest` hoặc focused test kiểm chứng. Tổng số tool calls của worker BẮT BUỘC <= 5 calls, hoàn thành dưới 60 giây! Chi tiết: `references/large-file-reading-exhaustion-and-direct-script-patching-20260906.md`. |
| **Full XML Dump Inspection on Narrow Patch Tasks (Đọc dump XML khổng lồ gây kiệt quệ Tool Budget)** | Khi task đã chỉ rõ hàm và file cần sửa kèm lệnh canary, agent đọc nguyên file XML dump (>66.000 ký tự) để kiểm chứng cấu trúc feed thay vì patch ngay. Gây chạm trần 35 turns trước khi ghi đĩa hoặc chạy canary. | **THỰC HIỆN 4 BƯỚC LEAN CANARY NGAY:** Đọc đúng vị trí hàm -> Patch code -> `python -m py_compile` -> Kích hoạt canary test ngay lập tức. CẤM đọc toàn bộ XML dump chỉ để khảo sát. Xem: `references/canary-patch-budget-exhaustion-and-feed-guard-pattern.md`. |
| **Inspect Task Scope Creep (Biến việc đọc/inspect thành sửa code lan man)** | Giao task chỉ đọc log/OCR ảnh nhưng worker tự ý phân tích ngược toàn bộ cây tiến trình mẹ-con (PID), đào sâu module imports, tự nhảy vào sửa flow và chạy lại test suite cả tiếng đồng hồ (115 tool calls). | **Khi task là Read/Inspect/OCR: BẮT BUỘC chỉ đọc và trả kết quả ngay trong <= 10 calls.** Nếu phát hiện bug cần sửa, PHẢI báo cáo về Coordinator để Coordinator tạo task sửa code riêng biệt, CẤM tự ý sửa trong task inspect. |
| **Runtime Module Shadowing (Thư mục tĩnh site-packages đè file `.pth` editable)** | Thư mục tĩnh `automation_core/` trong `site-packages` đè lên file `__editable__...pth` khiến sửa code trong repo nhưng runtime vẫn chạy code cũ; tiến trình đang chạy trong RAM không tự reload code mới. | **BẮT BUỘC kiểm tra và xóa sạch thư mục tĩnh trong `site-packages`** khi dùng `-e .`. Kiểm tra `module.__file__` và đối chiếu PID/thời điểm khởi động tiến trình để tránh hiểu lầm "sửa code rồi mà vẫn lỗi". |
| **Redundant Preflight Loops (Trùng lặp tiền kiểm tra)** | Dành 25–35 calls đọc hàng loạt file tham chiếu, test lại kết nối ADB, GPM API, IMAP, kiểm tra Excel... chạm trần `max_iterations = 35` trước khi sửa code hoặc chạy batch. | **CẤM kiểm tra lại môi trường đã được Coordinator xác nhận.** Khi hạ tầng đã được kiểm chứng trong context, Worker BẮT BUỘC thực thi ngay: 1. Sửa/Patch file $\rightarrow$ 2. `py_compile` $\rightarrow$ 3. Chạy script $\rightarrow$ 4. Báo cáo. |
| **Workbook Atomic Fallback Bypass (Bỏ quên lock enforcement & stale lock)** | Viết fallback workbook update thiếu `raise TimeoutError` khi hết hạn, không phá stale lock (`> 2x timeout`), hoặc không bắt Windows `PermissionError` retry khi `replace(p)`. | **BẮT BUỘC:** (1) `raise TimeoutError` nếu không acquire được lock; (2) Break stale lock nếu `time.time() - st_mtime > 2 * timeout`; (3) Retry 5 lần kèm `sleep(0.5)` khi `replace()` trên Windows. Chi tiết tại `references/atomic-workbook-fallback-and-windows-locking.md`. |
| **Worker Self-Report Credulity & Phantom Diff (Tin tưởng mù quáng summary subagent / Báo diff ảo chưa ghi đĩa)** | Worker subagent báo cáo "đã sửa xong file X, hàm Y", thậm chí in cả block unified diff hoàn chỉnh nhưng thực tế không gọi tool `patch` hoặc `write_file` khiến file trên đĩa vẫn nguyên bản. Nếu Coordinator không verify đĩa mà vội chốt phiên hoặc chạy Canary, hệ thống sẽ chạy lại code cũ hoặc crash. | **CẤM TIN TƯỞNG SUMMARY SUBAGENT KHI CHƯA STAT ĐĨA.** Ngay khi worker trả về, Coordinator BẮT BUỘC kiểm tra byte thay đổi thực tế qua `git status -s` hoặc `python -c "..."`. Nếu phát hiện worker báo cáo ảo chưa ghi đĩa: DỪNG LẠI NGAY, Coordinator lập tức soạn Patch Contract chuẩn xác (`old_string` verify `grep -c == 1` $\rightarrow$ `new_string`), dispatch 1 Worker tinh gọn với chỉ thị rõ ràng 4 bước (`patch` $\rightarrow$ `write_file` test $\rightarrow$ `unittest` $\rightarrow$ `git status`), giải quyết triệt để trong <= 4 tool calls! |
| **Patch Tool Phantom Match on Giant Windows Files (Công cụ patch báo diff nhưng không ghi đĩa)** | Trên Windows với file mã nguồn lớn (như `feed_swipe_smoke.py` 22.000+ dòng) hoặc file có CRLF / dòng trống xen kẽ, công cụ `patch` có thể in unified diff giả lập thành công kèm warning pagination nhưng thực tế byte KHÔNG hề được ghi xuống đĩa, làm test chạy ra kết quả cũ và gây phí turn lặp lại. | **BẮT BUỘC verify đĩa ngay sau khi patch:** Chạy `git diff <file>` để xác nhận thay đổi vật lý. Nếu `git diff` rỗng / patch không ghi xuống đĩa, chuyển ngay sang script Python trực tiếp (`python -c "with open(...) as f: ... f.write(...)"`) để find-and-replace chính xác theo chuỗi byte UTF-8 và chạy `python -m py_compile` kiểm tra trước khi chạy pytest. |
| **Coordinator Self-Investigation Loop (Tự điều tra bằng file tools hoặc lọt guard do race condition)** | Coordinator nhận Farm Alert nhưng không dispatch ngay, mà tự gọi hàng chục lượt `read_file`, `search_files` hoặc `terminal` (do guard v1 bị alert dồn dập đè mất `session_id`). UI Telegram hiện `⚙️ Working — X min — iteration N/200, <tool>` với $N > 1$. | **CẤM COORDINATOR TỰ ĐIỀU TRA Ở SESSION CHÍNH.** Nhận biết qua UI: nếu thấy iteration counter tăng và gọi `terminal`/`read_file` nghĩa là session chính đang tự làm sai quy trình. BẮT BUỘC dùng guard v2.0 (state per-session, check DB `parent_session_id`, khóa cứng toàn bộ `read_file`, `search_files`, `patch`, `write_file`, `execute_code` ở Phase ALERT). Coordinator chỉ được chạy đúng 1 lệnh inspect O(1) rồi bắt buộc gọi `delegate_task`. |
| **Runtime-Only Config/Plugin Modification (Sửa runtime quên đồng bộ Git Repo)** | Nâng cấp plugin (`$LOCALAPPDATA/hermes/plugins/`) hoặc đổi config nhưng chỉ giữ ở local runtime, báo cáo "Local-only runtime" khi chốt phiên mà không đồng bộ vào repo Git (`D:/Taadaa/Hermes/deploy/hermes-home/` và `D:/Taadaa/AI-Tools/config/hermes/`). Khi bootstrap lại trên máy khác sẽ mất trắng. | **BẮT BUỘC ĐỒNG BỘ TOÀN BỘ CONFIG & PLUGIN VÀO GIT REPO.** Mọi sửa đổi trên runtime Hermes BẮT BUỘC phải copy vào `deploy/hermes-home/plugins/` và `hermes_config_template.yaml`, redact 100% API key (`api_key: «redacted:sk-…»`) và commit/push lên git. Chi tiết tại `references/config-and-plugin-repo-sync.md`. |
| **Self-Review Simulation & Model Downgrade (Tự review giả mạo hoặc tự ý hạ cấp Claude model)** | Khi user yêu cầu "Review lại X...", "Tóm lại review workflow..." hay "kêu claude kiểm tra", Coordinator tự đọc code/tài liệu rồi tự tổng hợp mà KHÔNG chạy CLI; HOẶC user yêu cầu gọi Claude CLI nhưng Coordinator lại tự ý hạ xuống Sonnet làm giảm năng lực suy luận sâu. | **BẮT BUỘC TUÂN THỦ 2 TẦNG REVIEWER:** (1) Review/Audit plan bình thường: dùng combo OmniRoute review (`:20129`) theo chuỗi đã setup (Opus -> Sonnet -> GPT OSS -> Nemotron -> AG; cấm tự review); (2) Ca khó hoặc khi user chủ động ra lệnh "gọi claude cli": BẮT BUỘC gọi Claude CLI native (app CLI, cấm nhầm với OmniRoute) **Opus High** (`claude -p "..." --model opus --effort high`). CẤM tự ý hạ xuống Sonnet. Mở đầu báo cáo bằng: *"Đã gọi Claude CLI (`claude -p --model opus --effort high`) và nhận được kết quả audit sau: ..."*. Chi tiết tại `references/claude-cli-bounded-review-loop.md` và `references/claude-opus-max-watchdog-audit-and-per-session-heartbeat.md`. |
| **Quét đĩa diện rộng tìm script (`os.walk(r'D:\Taadaa')` gây Timeout 900s Trap)** | Khi cần tìm vị trí 1 script, file run hay module, Coordinator tự viết Python `os.walk(r'D:\Taadaa')`. Ổ D chứa hàng trăm ngàn file (node_modules, venvs, runs, git objects), chắc chắn bị treo và dính timeout 900s (15 phút làm đơ toàn bộ session). | **CẤM TUYỆT ĐỐI `os.walk(r'D:\Taadaa')`.** BẮT BUỘC dùng tra cứu O(1) qua `cronjob(action='list')` (trường `script`, `workdir`, `prompt_preview`) hoặc kiểm tra trực tiếp các thư mục quy ước đã biết (`D:/Taadaa/Tiktok-video/scripts/`, `D:/Taadaa/tiktok-luot nuoi acc/scripts/`, `~/AppData/Local/hermes/scripts/`). |
| **Worker Distraction by Pre-existing Dirty Git Files (Worker bị phân tâm bởi file dirty có sẵn)** | Khi delegate worker subagent vào 1 repo đang có file modified/untracked sẵn từ trước, Worker thấy `git status` bị bẩn liền tự ý nhảy vào sửa hoặc test các file đó thay vì tập trung vào file được giao, dẫn đến cạn kiệt ngân sách 35 turns mà không xong việc. | **CẢNH BÁO PRE-EXISTING DIRTY FILES TRONG CONTEXT.** Trong directive của `delegate_task`, Coordinator BẮT BUỘC ghi rõ: *"Repo đang có các file dirty sẵn ngoài scope, CẤM TUYỆT ĐỐI đụng chạm hay revert các file này. CHỈ ĐƯỢC PHÉP sửa duy nhất file X."* |
| **Reinventing Existing Runner / Handwritten Telemetry Loops (Tự code tay vòng lặp swipe/jitter thừa thãi)** | Khi cần nuôi feed / telemetry nhẹ sau đăng ký hoặc thao tác phụ, agent tự viết vòng lặp `for idx in range(...)`, tự tính toán tọa độ `_jitter`, `time.sleep` thủ công trong script mẹ thay vì gọi runner chuyên trách có sẵn (`run_tiktok.py` trong repo `tiktok-luot nuoi acc`). Dẫn đến phình to code, thiếu các cơ chế popup/dismiss an toàn, và gây phản ứng gay gắt từ user (*"Random jitter video quần què gì thế cái đó có trong script lướt feed rồi..."*). | **TÁI SỬ DỤNG RUNNER CHUYÊN TRÁCH QUA SUBPROCESS.** BẮT BUỘC gọi trực tiếp script chính thức (`run_tiktok.py`) qua subprocess với `--mode feed-session-smoke --max-swipes <random 4-8> --cleanup-on-stop`. Phải cô lập môi trường: xóa `PYTHONPATH` (chống xung đột binary PIL/thư viện của venv host) và đặt `CODEX_DEVICE_LOCK_DIR` riêng biệt. |
| **App Left Hanging on Error / Abort (Để app treo khi script fail)** | Script đăng ký, login hoặc tương tác UI gặp ngoại lệ (CAPTCHA, missing handle, timeout, duplicate) nhưng không có cơ chế dọn dẹp ở khối `finally`, bỏ mặc điện thoại treo ở màn hình lỗi làm nghẽn toàn bộ cron hoặc batch tiếp theo. | **LUÔN ĐÓNG APP VỀ HOME KHI FAIL (FAIL-SAFE CLEANUP).** Mọi điểm dừng, exception hay abort BẮT BUỘC phải đi qua khối `finally:` gọi cleanup (`shell am force-stop` + `keyevent 3` về Home). Tuyệt đối không để màn hình treo ở trạng thái dở dang. |
| **Flakiness Excuses & Manual Offloading (Đổ lỗi "chập chờn" & Đẩy việc sang làm tay)** | Khi automation gặp lỗi timeout, kẹt flow hoặc chưa xử lý được popup UI/challenge, Coordinator/Worker tự kết luận "do mạng/hệ thống chập chờn" và quay sang đề xuất user làm thủ công bằng tay ("bạn mở trình duyệt bấm 1 chạm..."). Gây bức xúc tột độ cho user. | **CẤM TUYỆT ĐỐI ĐỔ LỖI "CHẬP CHỜN" VÀ CẤM ĐỀ XUẤT LÀM TAY.** Mọi lỗi timeout đều có nguyên nhân logic cụ thể (sai selector, sai tọa độ tap, chưa bắt đúng event notification, kẹt vòng lặp chưa nhả dialog, thiếu nút submit). BẮT BUỘC inspect O(1) hiện trường XML/screencap, tìm đúng root cause kỹ thuật và dispatch worker sửa triệt để code tự động hóa. |
| **Sequential Single-Machine Crawl on Multi-Device Fleets (Chạy lắt nhắt từng máy đơn lẻ khi đã qua Canary)** | Chạy tuần tự từng con một trên dàn thiết bị độc lập làm kéo dài thời gian vô ích (15-30 phút cho vài máy), gây ức chế tột độ cho user (*"Sao làm từng con lâu v? Tăng worker lên? Mà đang làm task gì"*). | **BẮT BUỘC XẢ WORKER SONG SONG NGAY SAU KHI CANARY PASS.** Canary Gate CHỈ chạy trên đúng 1 máy đầu tiên để kiểm chứng flow và selector. Ngay khi Canary thành công 100%, BẮT BUỘC xả song song các máy còn lại qua `delegate_task(tasks=[...])` (tối đa 3-4 workers song song, phân chia theo từng máy/serial độc lập). CẤM chạy tuần tự từng con một khi các máy có phần cứng và proxy độc lập. Tại mỗi turn giao tiếp, BẮT BUỘC nêu rõ 3 ý: (1) Mục tiêu/tác vụ đang làm, (2) Kết quả bước vừa hoàn tất, (3) Bước tiếp theo / blocker. |
| **Hermes Terminal PYTHONPATH Leak (Xung đột PIL `_imaging` khi chạy farm runner)** | Chạy script launcher PowerShell (`run-feed-session.ps1`) hoặc Python consumer trực tiếp từ terminal của Hermes mà không bỏ `PYTHONPATH`, khiến Python con nạp site-packages của Hermes venv và crash `ImportError: cannot import name '_imaging' from 'PIL'`. | **BẮT BUỘC CHẠY KÈM `env -u PYTHONPATH`.** Mọi lệnh chạy launcher PowerShell hay Python consumer từ terminal BẮT BUỘC phải dùng `env -u PYTHONPATH <lệnh>` để bảo đảm cô lập môi trường thực thi. |
| **Stale Fast-Fail Device Lock Block on Canary (Bị kẹt device lock phiên lỗi cũ khi kích hoạt Canary)** | Khi máy farm dừng do Fast-Fail, runner giữ device lock 1h (`.lock.json`) để phục vụ inspect. Khi lệnh Canary được kích hoạt, runner từ chối chạy vì `device lock active: path=... pid=...`, khiến worker hiểu nhầm máy đang có ca chạy khác và dừng kiểm thử. | **KIỂM TRA PID VÀ GIẢI PHÓNG STALE LOCK TRƯỚC KHI CANARY.** Kiểm tra xem PID ghi trong file lock có còn sống hay không. Nếu PID cũ đã dừng (tiến trình dừng phiên đã kết thúc), xóa ngay file `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` rồi kích hoạt lệnh Canary. |
| **Worker Scope Drift & Out-of-Scope Code Injection (Worker tiện tay thêm class/hàm/feature mới)** | Worker khi được giao sửa bug (ví dụ bọc try/except) tự ý thêm ~55 dòng code tính năng mới (`SwitchOption`, `_find_user_placeholder_switch_option`, fallback rẽ nhánh trong `verify_and_switch_profile`) có bare `except: pass`, không unit test, không docs. Khiến Plan-Review Gate 1 lập tức REJECTED toàn bộ candidate, làm tốn thêm vòng lặp và nguy cơ gây hồi quy nghiêm trọng trên farm. | **CẤM WORKER CHÈN CODE NGOÀI PHẠM VI TASK (SCOPE LOCK).** Chỉ sửa đúng các dòng code phục vụ mục tiêu bugfix. Mọi bổ sung tính năng mới, class mới, helper mới BẮT BUỘC phải qua task/PR riêng biệt có unit test và documentation. Coordinator phải audit diff trước review, revert sạch phần code ngoài scope nếu worker tự ý thêm vào. |
| **Canary Pass Scope Creep & Review Over-Engineering (Bới thêm lỗi ngoài scope sau khi Canary đã Pass làm kéo dài phiên 3 tiếng - Case Máy 39)** | Sau khi Canary Test B4 đã pass 100% trên máy thật (video đã đăng, workbook đã cập nhật), Coordinator lại ném diff cho reviewer soi xét các module phụ không liên quan (draft cleanup, hashtag threshold), kéo theo worker sửa lan, gãy mock test suite và kéo dài phiên hơn 3 tiếng (*"vkl mày làm cái đéo gì 3 tiếng k xong"*). | **CANARY PASS = FREEZE SCOPE NGAY LẬP TỨC.** Canary trên máy thật là bằng chứng tối thượng (Ground Truth). Khi Canary đã pass: CẤM TUYỆT ĐỐI nhận thêm góp ý review mở rộng phạm vi ra ngoài lỗi ban đầu. Giữ diff tối thiểu, verify focused test và chốt phiên 6 Gate ngay. Chi tiết: `references/canary-pass-scope-lock-and-review-creep-trap-case-m39.md`. |
| **Accidental Farm Media Auto-Upload via Bare Path (Gửi nhầm video 4MB từ kho nuôi nick lên Telegram do đường dẫn trần)** | Coordinator báo cáo text chứa path Windows trần (ví dụ `D:\TIKTOK-videonuoinick\306\5.mp4`) không bọc backtick khiến Hermes Gateway tự động bốc video 4MB gửi native media lên Telegram, gây lãng phí băng thông và vi phạm bảo mật kho nick (*"ủa gửi video t chi v... Tại sao lại đi gửi video trong kho nuôi nick?"*). | **BẮT BUỘC BỌC BACKTICK MỌI ĐƯỜNG DẪN VÀ CHỈ GỬI SCREENCAP THIẾT BỊ.** (1) Mọi đường dẫn file dữ liệu farm (`D:\TIKTOK-videonuoinick`, `D:\video goc`, `D:\OneDrive`) bắt buộc phải bọc trong inline code backtick; (2) Nghiệm thu farm CHỈ ĐƯỢC GỬI ẢNH CHỤP MÀN HÌNH (`MEDIA:<screencap_path>`), CẤM TUYỆT ĐỐI gửi file media từ kho farm; (3) Khóa cứng 3 tầng: config `auto_deliver_local_files: false`, denylist `_FARM_DENIED_ROOTS` trong `base.py`. Chi tiết: `references/hermes-gateway-bare-path-leak-and-farm-media-isolation.md` (trong `taadaa-farm-ops-rules`). |
| **Premature Abort on Canary 300s Timeout (Tưởng timeout terminal là canary fail rồi chạy đè lệnh)** | Lệnh canary (`run-feed-session.ps1`) chạy hết 300s default timeout của tool terminal nên bị ngắt, agent kết luận sai là lỗi rồi chạy lệnh mới đè lên làm xung đột lock và loạn UI điện thoại. | **KIỂM TRA TIẾN TRÌNH & ĐỌC ARTIFACTS O(1).** Feed session cần 6–9 phút. Khi terminal dính 300s timeout, kiểm tra `Get-Process python` xem tiến trình còn chạy không; theo dõi đuôi `log.jsonl` và đọc các file kết quả (`run_manifest.json`, `recovery_lock_handoff.json`, `summary.txt`) để lấy trạng thái thực tế trước khi kết luận. |

---

## 5. CHỈ THỊ CHO COORDINATOR KHI DISPATCH WORKER

Khi Coordinator gọi `delegate_task(goal=..., context=...)`, **BẮT BUỘC** đính kèm directive sau vào `context`:

```text
[BUDGET & ANTI-OVERENGINEERING DIRECTIVE]:
- Khóa cứng hệ thống: trần max_iterations = 35 (trong config.yaml).
- Phân loại task:
  + Task Read-only / Inspect / OCR: CẤM tự ý sửa code / CẤM chạy test suite / CẤM commit. Trả kết quả ngay trong <= 10 tool calls (< 10 phút).
  + Task Fix Code: Sửa ĐÚNG file/module chỉ định (Scope Lock), viết focused test <30s, hoàn tất trong <= 20 tool calls (< 15 phút). CẤM over-engineer viết test đồ sộ.
  + Task trên file lớn (>2.000 dòng như feed_swipe_smoke.py): CẤM TUYỆT ĐỐI dùng read_file/search_files phân trang. Bắt buộc dùng 1 lệnh patch duy nhất hoặc script Python find-and-replace trực tiếp qua terminal, hoàn tất trong <= 3-5 calls (< 60s).
- WorkerToolGate cưỡng chế cứng (v2.1): READ_BUDGET = 3 (quá 3 lần đọc bị khóa), WRITE_DEADLINE = 4 (turn 4 chưa ghi đĩa bị khóa đọc toàn bộ). Coordinator BẮT BUỘC cung cấp WORK_PACKAGE (target, patch_intent), CẤM dispatch mù.
- Checkpoint: Chạm mốc 20 tool calls chưa xong phải dừng xuất báo cáo checkpoint.
- Quy trình: 1. Đọc đúng dòng lỗi (<= 2 calls) -> 2. Sửa đúng dòng code (turn 3-4) -> 3. Kiểm tra py_compile hoặc 1 focused test tối thiểu (<30s).
- CẤM TUYỆT ĐỐI: Không mò bấm tay ADB qua terminal (bắt buộc đóng gói hàm vào file script), không can thiệp S7 khi chưa bọc acquire_device_lock(force_preempt=True) tránh cron nuôi acc đè màn hình, không os.walk / glob quét đĩa tìm serial/config (dùng prompt hoặc file map), không grep/find đệ quy trong runtime/runs hoặc python-envs (D:/CodexRuntime, .codex-work, .ai-runs, python-envs), không test inflation (đẻ test suite đồ sộ), không simulation ngàn vòng lặp, không tạo file probe tạm trong %TEMP%, không chạy full test suite cả repo nhiều lần, không lặp lại tiền kiểm tra (preflight checks) môi trường/ADB/IMAP/GPM khi Coordinator đã xác nhận sẵn trong context (thực thi ngay: Patch -> py_compile -> Run -> Report), không dot-source file runner PowerShell chưa có guard (dẫn tới chạy thật cả batch trên farm máy), chạy lệnh terminal launcher/consumer luôn kèm env -u PYTHONPATH tránh xung đột binary PIL.
- Tập trung sửa đúng nguyên nhân gốc rễ và báo cáo ngay.
```

---

## 6. KỶ LUẬT PHÂN VAI BẮT BUỘC: COORDINATOR vs WORKER

1. **Session chính LÀ COORDINATOR DUY NHẤT:**
   - **Chức trách cho phép:** Đọc log, inspect hiện trường O(1) qua `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc direct ADB read-only, phân tích nguyên nhân gốc rễ từ XML/screencap, lập mục tiêu và dispatch worker subagent.
   - **Quy tắc chuyển tiếp tức thì (Zero-Delay Dispatch):** Khi nhận Farm Alert đã có sẵn thông tin (ảnh hiện trường / Serial / Nick), HOẶC khi nhận lệnh sửa phát sinh từ user (ví dụ: *"Rồi sửa đi"*, *"mở rộng range X"*): CẤM TUYỆT ĐỐI Coordinator nán lại chạy chuỗi lệnh `read_file`, grep hay probe trong session chính (tránh đếm turn làm dấy lên nghi vấn *"Đang sửa trực tiếp hay gọi agent?"*). BẮT BUỘC khóa scope thật nhanh và dispatch worker subagent qua `delegate_task(goal=..., context=...)` ngay lập tức!
   - **CẤM TUYỆT ĐỐI tại session chính:** Không tự viết script Python probe (`python -c "..."`), không tự import module codebase để thử nghiệm logic/phân loại, không tự sửa code, không tự chạy unit test. Luôn chạy Canary với số swipes ngẫu nhiên `(Get-Random -Minimum 2 -Maximum 5)` thay vì cố định 2 swipes để tránh telemetry footprint bị TikTok gắn cờ bot.
2. **MỌI TÁC VỤ SỬA CODE, VIẾT TEST, PROBE & CHẠY BATCH/AUTOMATION DÀI:**
   - **BẮT BUỘC** dispatch worker subagent qua `delegate_task(goal=..., context=...)`.
   - Áp dụng cho: Sửa codebase, viết focused test, chạy thử nghiệm, VÀ **mọi script chạy batch dài** (upload batch `run_tiktok_upload_batch.ps1`, batch reg Gmail/TikTok, batch GPM 2FA, batch checklive 226 mail).
   - **Lý do:** Tránh block session chính 10-25 phút và tránh Context Bloat (xả log tràn context kích hoạt compaction làm rơi rụng chỉ thị).
3. **Canary & Chốt phiên:**
   - Sau khi worker báo cáo file/hàm đã sửa và kết quả test/canary xanh (không xả diff dài dòng), Coordinator kiểm tra ngắn gọn bằng `git status --short` và `git diff` để xác nhận diff vật lý trên đĩa khớp allowlist (khôi phục ngay file ngoài scope nếu worker sửa lan man).
   - Kích hoạt lệnh canary thực tế trên máy thật (`run-follow.ps1` hoặc tương đương) và thực hiện trực tiếp các bước closeout 6 Gate tại session chính (Gate 0 Canary -> Gate 0.5 Docs -> Gate 1 Plan-Review -> Gate 2 Test & Commit -> Gate 3 Rebase -> Gate 4 Push & Remote Verify).
4. **Cơ chế cưỡng chế vật lý 3 trục (Three-Tier Hard Guard - Plugin `farm-coordinator-guard` v2.1):**
   - Không phụ thuộc vào kỷ luật tự giác bằng prompt của LLM.
   - **PreToolUse Hook** (`~/.hermes/plugins/farm-coordinator-guard/`):
     + **Trục 1 - State Guard (Phase ALERT / WORKER - Session-Scoped):**
       * Phase `ALERT`: Khóa toàn bộ investigative tools (`read_file`, `search_files`, `patch`, `write_file`, `execute_code`). Cấp đúng `inspect_budget = 1` cho duy nhất 1 lệnh inspect O(1) (`inspect_machine.py <N>` hoặc `adb devices`). Lệnh terminal thứ 2 trở đi bị Hook chặn đứng vật lý (`action: block`) $\rightarrow$ Ép Coordinator bắt buộc phải gọi `delegate_task`.
       * Phase `WORKER_RUNNING`: Chặn terminal probe tại session chính trong lúc worker đang chạy nền (auto-expire 20m).
       * Phase `CLOSEOUT`: Tự động mở toàn quyền terminal tại session chính khi user gõ "chốt phiên" / "/closeout" để thực hiện quy trình 6 Gate (G0 $\rightarrow$ G4, auto-expire 2h).
     + **Trục 2 - Action Guard (Long-Runners Denylist & Claude Quota Guard - Luôn kích hoạt kể cả khi IDLE):**
       * Tầng 0 (Claude CLI Quota Hard Guard): Chặn đứng vật lý (`action: block`) bất kỳ lệnh nào gọi `\bclaude\b` nếu `claude_lockout.json` đang active (bị khóa limit) HOẶC usage 5h window chạm trần 85% (38/45 weighted calls), ép fallback sang OmniRoute Review `:20129`.
       * Tầng 1 (Allowlist): Cho qua ngay các lệnh O(1) an toàn (`git`, `psutil`, `adb devices`, `inspect_machine.py`, `py_compile`, `claude -p` khi chưa chạm 85%).
       * Tầng 2 (Escape Token v2.0): Subagents chỉ được nhận diện chính xác qua truy vấn `parent_session_id` từ SQLite `state.db` HOẶC cờ `TAADAA_WORKER=1` trong môi trường tiến trình. Quản lý FSM state độc lập theo từng session trong dictionary `sessions` của `farm_coordinator_phase.json` (kèm auto-cleanup stale sessions > 2h). CẤM DÙNG so sánh phủ định `session_id != coord_session` để tránh bị alert dồn dập đè mất quyền chặn.
       * Tầng 3 (Denylist): Tự động chặn đứng các script chạy dài (`run_*batch*`, `.ps1`, `upload_video`, `checkmail`, `reg_*`, `playwright`, `gpm`) nếu Coordinator chạy đồng bộ ở session chính $\rightarrow$ Bắn lỗi và ép gọi `delegate_task`.
     + **Trục 3 - Worker Tool Gate (Chống Analysis Paralysis cho Worker Subagents v2.1):**
       * Quản lý trạng thái theo `session_id` trong `worker_state`: đếm `read_count` (`read_file`, `search_files`), `write_count` (`write_file`, `patch`), và tổng `call_count`.
       * **Quy tắc 1 (READ_BUDGET = 3):** Nếu `tool_name in ("read_file", "search_files")` và `read_count >= 3`, chặn đứng vật lý (`⛔ [WORKER TOOL GATE - READ BUDGET EXHAUSTED]`) ép worker phải gọi `write_file`/`patch` ngay.
       * **Quy tắc 2 (WRITE_DEADLINE = 4):** Nếu `call_count >= 4` và `write_count == 0`, khóa cứng toàn bộ công cụ đọc (`⛔ [WORKER TOOL GATE - WRITE DEADLINE]`) ép worker phải ghi bản vá.
       * Cho phép không giới hạn các công cụ kiểm thử (`terminal` py_compile/pytest, `git diff`) sau khi ghi code để worker verify artifact.
   - **Dấu hiệu nhận biết vi phạm trên UI Telegram:** Counter `⚙️ Working — X min — iteration N/200, <tool>` (terminal/read_file/search_files) là bằng chứng trực tiếp cho thấy session chính đang tự điều tra thay vì dispatch worker subagent. Chi tiết tại `references/farm-coordinator-guard.md`.

---

## 7. KỶ LUẬT GIAO VIỆC COORDINATOR ↔ WORKER CHO REPO FILE LỚN (>= 5.000 DÒNG) — CLAUDE OPUS PLAYBOOK

*(Được đúc rút từ tư vấn Claude Opus CLI sau sự cố 40 phút Máy 25 và bài học Case 120)*

1. **Coordinator BẮT BUỘC giao Patch Contract, CẤM giao Goal điều tra mở:**
   - Trong các monolith file lớn (`feed_swipe_smoke.py` 22k dòng, `benign_popup.py` 5k dòng...), CẤM TUYỆT ĐỐI dispatch worker với goal chung chung ("Sửa lỗi X", "Tìm nguyên nhân Y").
   - Worker nhận goal mở sẽ rơi vào **Death Loop**: dùng `read_file` phân trang 35 lần liên tục chỉ để dò cấu trúc và cạn kiệt toàn bộ tool calls trước khi kịp sửa code.
   - **Quy tắc vàng:** **Coordinator chỉ được dispatch khi đã có `old_string` và `new_string` chính xác trong tay.**
   - Coordinator dùng `grep -n` và `read_file` (đúng 20-40 dòng quanh điểm lỗi) để định vị và trích xuất diff trong 2 phút, sau đó đóng gói thành Patch Contract gửi Worker.

2. **Cấu trúc Patch Contract chuẩn cho Worker:**
   - `goal`: "Áp 1 patch đã soạn sẵn + chạy 1 test. KHÔNG điều tra, KHÔNG đọc thăm dò."
   - `context`:
     + File path + số dòng ước lượng.
     + `old_string`: Đoạn code cũ duy nhất (10-15 dòng có mốc neo).
     + `new_string`: Đoạn code mới thay thế.
     + `verify_command`: Lệnh chạy unit test cụ thể (`pytest ...`).
     + `rules`: Cấm `read_file` quá 2 lần; budget <= 8 tool calls; hoàn tất < 60s.

3. **3 Khuyến nghị nâng cấp bổ sung từ Claude Opus CLI:**
   - **Xác nhận tính duy nhất (Uniqueness Check):** Coordinator bắt buộc kiểm tra `grep -c` cho `old_string` đảm bảo bằng đúng 1 trước khi dispatch, chống patch nhầm vị trí hoặc phantom match trên Windows.
   - **Escape Hatch (Investigation Mode):** Nếu sau 2 phút ở B1 Coordinator không thể localize được dòng lỗi, chuyển sang Investigation Mode: dispatch 1 worker dạng read-only với budget giới hạn riêng (<= 10 calls, < 5 phút), tuyệt đối không đoán mò hoặc ép soạn patch mù.
   - **B5 (Rollback khi Canary Fail):** Nếu Canary ở B4 fail, lập tức revert patch (`git checkout <file>`), mở lại alert và lưu artifact hiện trường để phân tích tiếp, tuyệt đối không để lại code hỏng trên farm.

4. **Playbook 5 Bước Chuẩn Hóa Cho Farm Alert (Dưới 12 Phút - 1 Worker Duy Nhất):**
   - **B0 (Coordinator - 90s):** Nhận alert, inspect hiện trường O(1) (`inspect_machine.py <N>`, dump XML, screencap).
   - **B1 (Coordinator - 2 phút):** Dùng `grep -n` định vị hàm/dòng lỗi, trích `old_string` 10-15 dòng, verify `grep -c == 1`.
   - **B2 (Coordinator - 2 phút):** Soạn `new_string` xử lý bug và xác định lệnh test (`pytest ...`).
   - **B3 (Worker duy nhất - 4 phút):** Dispatch 1 Worker áp patch và chạy unit test. Budget <= 8 calls.
   - **B4 (Coordinator - 2 phút):** Chạy Canary live 2-4 swipes ngẫu nhiên trên máy farm và đóng alert (hoặc rollback ngay nếu Canary fail).
   - Chi tiết: `references/claude-opus-patch-contract-and-large-file-coordination.md`.

---

## 8. PHÒNG CHỐNG TREO IM LẶNG (SILENT FREEZE), DISPATCH RECEIPT & SILENT WATCHDOG

*(Tư vấn bởi Claude Sonnet CLI sau sự cố im lặng 1 tiếng ngày 06/09/2026)*

1. **Cấm tuyệt đối `[SILENT]` khi Dispatch Worker (Banned Dispatch Token):**
   - **BANNED TOKEN:** Cấm tuyệt đối emit `[SILENT]` khi Coordinator dispatch worker subagent.
   - Khi Coordinator gọi `delegate_task(goal=..., context=...)`, **BẮT BUỘC** gửi đúng 1 Dispatch Receipt ngắn gọn trước khi dispatch:
     `🚀 Đang giao việc: [Mục tiêu ngắn gọn]. Phạm vi: [File/Module]. Dự kiến: [Thời gian/Canary].`
   - Tuyệt đối không emit `[SILENT]` khiến khung chat Telegram rơi vào trạng thái đóng băng giả.

2. **Hai Pha Tách Bạch (Two-Phase Pipeline):**
   - **Pha 1 (Worker Patch):** Worker sửa code đúng scope, kiểm tra cú pháp qua `python -m py_compile` (<= 3 phút). Báo cáo ngay khi xong.
   - **Pha 2 (Canary Live):** Coordinator kích hoạt chạy thực chiến trên máy farm thật (`(Get-Random -Minimum 2 -Maximum 5)` swipes). Lúc này user đã biết rõ máy đang chạy thật.

3. **Cơ chế Silent Stale Watchdog v2.2 (Per-Session Heartbeat & Canary Pre-Hook):**
   - Không spam tin nhắn tiến độ định kỳ làm loãng chat Telegram.
   - **Hook `pre_tool_call` & `post_tool_call` (`farm-coordinator-guard` v2.2):**
     * **Pre-hook (`pre_tool_call`):** Bắt ngay thời điểm bắt đầu chạy tool. Nhận diện Canary qua regex `r'\b(canary|recoverytestswipes|run-feed-session)\b'`. Ghi nhận ngay vào `watchdog_state.json`: `current_tool = tool_name`, `current_tool_start = time.time()`, `is_canary = is_canary`, `status = "running"`. Nếu tool bị chặn bởi State/Action Guard, lập tức chuyển `status = "blocked"`.
     * **Post-hook (`post_tool_call`):** Cập nhật `last_beat = time.time()`, `status = status`, xóa `current_tool = None`, `current_tool_start = None`.
     * **Cấu trúc `watchdog_state.json` per-session:** Quản lý phân cấp theo `sessions: { <session_id>: { last_beat, last_beat_iso, current_tool, current_tool_start, is_canary, status, parent_session_id } }` kèm khóa file `_watchdog_lock()` và ghi atomic qua `os.replace`. Tự động dọn session cũ > 2h.
   - **Script `hermes_stale_watchdog.py`:** Chạy định kỳ độc lập qua cron/watchdog, đối chiếu `watchdog_state.json` và `farm_coordinator_phase.json`:
     * **Ép UTF-8 stdout & Windows PermissionError Retry:** `sys.stdout.reconfigure(encoding="utf-8")` chống lỗi mã hóa console Windows; `_load_json()` retry 3 lần kèm `sleep(0.05)` tránh crash do race condition `os.replace` trên Windows.
     * **Khắc phục báo động giả Phase `WORKER_RUNNING`:** Khi Coordinator ở `WORKER_RUNNING`, Coordinator đang im lặng hợp pháp chờ subagent. BẮT BUỘC ưu tiên tìm child session (`parent_session_id == sid`). Nếu có child session, theo dõi beat của worker (ngưỡng 600s thường / 1500s canary). Nếu CHƯA CÓ child session (worker mới spawn), áp dụng ngưỡng `WORKER_TIMEOUT_SECONDS = 1200.0` (20 phút) tính từ `dispatched_at` để không bao giờ báo giả trước khi worker hết hạn. Phase `ALERT` áp dụng ngưỡng 600s cho Coordinator trực tiếp.
     * **Đo thời gian trễ:** Nếu session có `current_tool_start`: `elapsed = now - current_tool_start`. Nếu không có: `elapsed = now - last_beat`.
     * **Ngưỡng treo:** Thao tác thường (code fix / inspect): **> 600s (10 phút)**; Canary máy thật (`is_canary=True`): **> 1500s (25 phút)**; Worker spawn chờ lệnh: **1200s (20 phút)**.
     * **Anti-spam cache per-session (`stale_alert_sent.json`):** Quản lý theo từng `session_id`, mỗi sự cố chỉ cảnh báo 1 lần duy nhất! Tự động xóa cache khi session có beat mới hoặc hoàn tất.
     * **Im lặng tuyệt đối:** Khi `elapsed <= threshold` hoặc hệ thống IDLE bình thường, script exit 0 với STDOUT hoàn toàn trắng.
     * Khi vượt ngưỡng, bắn cảnh báo chỉ rõ session:
       ```text
       ⚠️ [CẢNH BÁO HERMES TREO]
       Session `{session_id}` đang im lặng {elapsed_minutes:.0f} phút (vượt ngưỡng {threshold_minutes:.0f}m)!
       - Tool: {tool}
       - Chế độ: {Canary máy thật | Thao tác thường}
       - Session ID: {session_id}
       Vui lòng kiểm tra terminal hoặc can thiệp nếu cần.
       ```

---

## 9. KIẾN TRÚC CHỐNG REGRESSION (SỬA B LÀM VỠ A) & PREFLIGHT GATE

*(Đúc rút từ thống kê 21 ngày log cron farm 24.000 events từ 17/08 đến 06/09/2026 và tư vấn kiến trúc chuyên sâu cùng Claude CLI Opus Max)*

0. **Quy Tắc Phân Biệt Lỗi & Phạm Vi Thắt Chặt (User Clarification):**
   - **Cùng 1 lỗi ở 2 màn khác nhau / TikTok đổi UI:** Là diễn biến bình thường (New Variant / UI Drift), xử lý tuần tự bằng cách bổ sung selector hoặc đăng ký case mới, KHÔNG PHẢI regression.
   - **Sửa lỗi này làm phát sinh lỗi kia (True Regression):** Do biến chưa gán ở mọi nhánh rẽ (Possibly-Unbound) hoặc đổi hàm mà bỏ sót caller/wrapper. ĐÂY LÀ ĐỐI TƯỢNG DUY NHẤT BẮT BUỘC THẮT CHẶT bằng Preflight Gate.
   - **Hậu kiểm tra độc lập:** Sau khi hoàn thiện tool, kiến trúc phòng thủ hoặc fix core, BẮT BUỘC gọi Claude CLI native qua app CLI (`claude -p --model opus --effort high`, cấm nhầm với OmniRoute) kiểm tra / audit độc lập.

1. **Hai Nhóm Lỗi Bản Chất Gây Ra Regression Trên Farm:**
   - **Nhóm 1 - Possibly-Unbound (Biến không chắc chắn được gán ở mọi nhánh rẽ):** Điển hình là Case 124 (`recaptured_xml`) và sự cố 30/08 (`loop_start`). Worker chỉ test nhánh lỗi (failure path), không test nhánh chạy bình thường (happy path). Linter thường (`ruff`, `pyflakes`) không bắt được vì biến có xuất hiện trong scope.
   - **Nhóm 2 - Signature-Change & Guard Omission (Sót Caller / Sót Điểm Gọi):** Điển hình là Case 125/127 (đổi `safety_check` nhưng sót wrapper `safety_check_attempt`) và sự cố Máy 36 (bọc ATX recovery ở navigation nhưng sót `_sponsored_present`).

2. **Hệ Thống Phòng Thủ 4 Lớp Tích Hợp (`tools/preflight.py` < 15s):**
   - Thay vì cấm chạy full test suite 15 phút rồi thả nổi không kiểm tra, toàn bộ 4 lớp được gộp vào **1 lệnh duy nhất** tốn đúng 1 tool call của Worker:
     ```bash
     python tools/preflight.py [--base HEAD]
     ```
   - **Lớp 1 (Ruff Check < 0.5s):** Bắt lỗi cú pháp, undefined names (F821), imports hỏng.
   - **Lớp 2 (Pyright Gate < 2s):** Bật duy nhất `reportPossiblyUnboundVariable: "error"` trong `pyrightconfig.gate.json` (chế độ basic với các rule type khác đặt none). Chặn đứng 100% các lỗi `UnboundLocalError` và biến chưa khởi tạo trước khi ra máy thật mà không cần chạy test.
   - **Lớp 3 (`diff_guard.py` < 1s):** Quét AST trên git diff kết hợp `git ls-files "*.py"` (tốc độ < 0.1s, không rglob dính runs/). Báo lỗi `[caller-omission]` nếu đổi signature hàm mà các caller/wrapper không nằm trong diff (bắt buộc sửa caller hoặc gắn `# regress-ok: <lý do>`). Lọc bỏ attribute method thông dụng trên driver/device object tránh false-positive.
   - **Lớp 4 (Hermetic Module Pack < 15s):** Chạy unit test logic thuần (mock ADB qua `conftest.py`). Tự động lọc file tồn tại `(ROOT / f).is_file()` chống fail giả khi xóa file. Bắt buộc có >= 1 test Happy Path và self-test gác cổng Pyright ("test the tester").

3. **In-Code Anchors & Regression Contract:**
   - Tại các hàm nóng hay bị sửa (như `verify_and_switch_profile`, `safety_check`), đặt comment block `REGRESSION-GUARD` nêu rõ các Invariant bắt buộc bảo toàn.
   - Khi dispatch worker, Coordinator bắt buộc nhồi Regression Contract vào prompt.
   - **Definition of Done:** Báo cáo hoàn thành của Worker bắt buộc phải dán output máy sinh kết thúc bằng token `PREFLIGHT: PASS`. Thiếu token này, Coordinator từ chối nhận việc và yêu cầu Worker khắc phục ngay.
   - **Thẩm định độc lập:** Đã thẩm định và đạt **`VERDICT: APPROVED`** từ Claude CLI Opus Max (`claude -p --model opus --effort max`). Chi tiết tại `references/anti-regression-defense-and-preflight-gate.md`.


