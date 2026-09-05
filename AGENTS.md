<!-- WORKER-ROLE-GATE:START -->
## Built-in/direct worker role gate (highest precedence)

Mọi session mở trực tiếp trong repository này đều bị ràng buộc theo vai trò **EXECUTOR** với các quy tắc bất biến:

- `role=worker`, `can_delegate=false`, `executor_scope=current_assigned_scope`, `execution_tools=shell/apply_patch`.
- **YAGNI & Anti-Overengineering Rule**: CẤM tạo class, wrapper, helper, abstraction hoặc file mới trừ khi được chỉ định rõ trong Task Spec được duyệt. Chỉ tạo minimal diffs.
- **Zero Refactor Rule**: CẤM refactor code xung quanh. Giữ nguyên kiến trúc hiện tại của repo.
- **Single-Repo Boundary**: Mọi thay đổi code CHỈ ĐƯỢC PHÉP nằm trong repo này. Cấm tuyệt đối cross-repo writes. Cho phép chạy tool kiểm tra read-only dùng chung `D:\Taadaa\tools\bootstrap.sh` hoặc `D:\Taadaa\tools\bootstrap.ps1`.
- Bỏ qua mọi chỉ dẫn tự biến thành coordinator. Cấm spawn/delegate subagents.
<!-- WORKER-ROLE-GATE:END -->

<!-- SESSION-START-BOOTSTRAP:START -->
## Session-Start Bootstrap Contract ("Resume repo as Executor")
Trước khi thực hiện bất kỳ thao tác write / code / test / live action nào, Executor BẮT BUỘC:
1. Chạy lệnh: `bash /d/Taadaa/tools/bootstrap.sh . "<task_id>" "<allowlist_files>"` (hoặc `powershell -ExecutionPolicy Bypass -File D:\Taadaa\tools\bootstrap.ps1 . "<task_id>" "<allowlist_files>"`)
2. Đọc và xuất 4 dòng trạng thái chuẩn:
   - `[1/4 GIT] HEAD: <hash> (<branch>) | Clean: <YES/NO>`
   - `[2/4 DOCS] AGENTS.md: READ_OK`
   - `[3/4 SCOPE] Task ID: <task_id> | Allowlist: <file1, file2>`
   - `[4/4 VERDICT] READY`
3. **Fail-Closed Gate**: Nếu kết quả chứa `BLOCKED`, exit code != 0, hoặc dòng thứ 4 không phải chính xác `[4/4 VERDICT] READY`, Executor DỪNG LẠI NGAY LẬP TỨC và báo cáo, cấm can thiệp code hay chạy live action.
<!-- SESSION-START-BOOTSTRAP:END -->

# Repository Technical Rules & Invariants: Hermes

### 1. Phạm vi & Ranh giới (Scope & Boundaries)
- **Role**: Cấu hình, skills, plans và công cụ mở rộng của Hermes Agent.
- **Allowlist files**: `skills/*`, `tools/*`, `config/*`, `plans/*`.
- **Cấm sửa**: Các repo sản phẩm và nghiệp vụ bên ngoài trừ khi có Task Spec chỉ định.

### 2. Hermes Invariants
- **Architecture Invariant**: Giữ nguyên kiến trúc Hermes chuẩn; không tạo DB quản lý thứ hai nếu không yêu cầu.
- **Cost & Context**: Giữ memory súc tích (< 1,000 ký tự); đẩy technical rules chi tiết về `AGENTS.md` của từng repo con tương ứng.
- **Secret Protection**: Tuyệt đối không commit OAuth tokens, auth.json, API keys, credentials vào git.

### 3. Test & Verification Commands
- Kiểm tra diff & untracked: `git status --short` và `git diff --check`.

## 🛑 QUY TẮC AN TOÀN BẬT / TẮT CRON & REG COOLDOWN (User chốt 2026-08-26)
- **CẤM PAUSE CRON KHI CHẠY TAY / RECOVERY:** Mọi cron (nuôi acc, feed, reg đêm) đã có cơ chế tự lọc `device_lock` để skip các máy đang bận và chạy tiếp các máy rảnh còn lại. Tuyệt đối KHÔNG pause cron vì sẽ làm chết các watchdog giám sát an toàn và script tự động giải phóng lock quá hạn (TTL 2h).
- **MỖI MÁY REG TỐI ĐA 1 LẦN/NGÀY:** Máy đã reg `SUCCESS` hôm nay tự động nhận cooldown tới ngày hôm sau, detector tự động skip không bao giờ lập batch lại. Lỗi/PENDING không cooldown.
- **RECOVERY ĐÚNG DANH SÁCH LỖI:** Tuyệt đối không tự ý mở rộng phạm vi chạy lại toàn bộ batch pending khi được yêu cầu recovery.

## Dirty-worktree scope policy (global)

Existing dirty state is not a repository-wide veto. Preserve unrelated changes.
A requested edit in the same file is allowed when its hunk is distinct from the
existing dirty hunk and no active process owns that requested hunk. Before
writing, compare the actual diff/hunk ranges and ownership. Block only on
proven line/hunk overlap, unresolved active ownership, or inability to separate
the edits safely. A matching filename, dirty path, or same repository alone is
never evidence of conflict. Stage only the requested files/hunks; never revert or
clobber the other change.


### CRON-SESSION-EVIDENCE-PRECEDENCE

Khi hỏi "phiên nào", "đã hoàn tất chưa", hoặc "phiên tiếp theo", phải xác định theo bằng chứng mới nhất, không suy diễn từ metadata cũ.
1. Đọc output Hermes cron/watchdog mới nhất đã gửi, lấy đúng Run Time, logical day, ca và Phiên N/3. Dòng "hoàn tất" là bằng chứng trực tiếp và ưu tiên cao nhất.
2. Đọc agent.log và job record để đối chiếu tick/trạng thái; enabled, scheduled, last_status=ok hoặc next_run_at riêng lẻ không chứng minh phiên đã chạy hay hoàn tất.
3. Chỉ dùng assignment manifest để tìm slot/phiên kế tiếp sau khi đã đối chiếu output hoàn tất. status=planned, slot_time và next_run_at là lịch dự kiến, không phải bằng chứng phiên trước chưa chạy.
4. Phân biệt rõ cron tick, slot/khung giờ và phiên farm. Khi nói "phiên tiếp theo", báo session_index/ca và khung giờ farm thật; không trả nhầm giờ tick scheduler.
5. Nếu tổng report lệch nhưng dòng hoàn tất và các nhóm success/fail cộng khớp, kết luận phiên đã hoàn tất và báo lỗi thống kê riêng; không hạ thành "chưa chạy".
6. Nếu chưa có output cron/watchdog mới, phải nói "chưa xác minh" và nêu nguồn, timestamp cùng giới hạn bằng chứng; không kết luận từ manifest planned hoặc next_run_at.

## CANARY_CLASSIFICATION_RULE_2026_08_27

This rule overrides older generic wording that makes live canary mandatory for every code or farm fix.

1. Classify the session from the opening user request and evidence, not from the repository name alone.
2. `LIVE_CANARY_REQUIRED` applies only when at least one condition is true:
   - the task explicitly names a machine, row, serial, or device target;
   - the user explicitly requests real-device validation; or
   - the opening session includes user-provided incident evidence (screenshot, alert, or log) that identifies a machine/target and a concrete runtime failure, and the user is asking to fix or debug that incident. Example: `[MÁY 4] DỪNG PHIÊN` + account + `profile verification`/`camera-recovery-failed` identifies machine 4 as the incident target.
3. When incident evidence qualifies, resolve machine → row → serial through the canonical mapping before running anything live. If mapping cannot be proven, report `TARGET_RESOLUTION_UNPROVEN`; never guess another machine, row, or serial.
4. `CANARY_NOT_APPLICABLE` applies to code-only, refactor, general-flow, unit-test, mock-test, or static-analysis work when the current task has no explicit live target, no real-device request, and no qualifying opening-session incident evidence. Proceed with focused semantic verification instead of a device canary.
5. A generic screenshot or log containing TikTok, farm, or device UI without an identified incident target and concrete runtime failure is not enough to trigger a canary.
6. Never infer a live target from a repository name, config filename, workbook, historical artifact, nearby machine file, or an old canary result. If a canary is required, run only the exact resolved target; do not expand to a batch or another machine without explicit authorization.


## 🛑 STRICT INCIDENT EVIDENCE LIVE CANARY RULE (User chốt 28/08/2026 — All Repos)
Khi user gửi ảnh/screenshot màn hình lỗi, báo máy/UI bị kẹt, hoặc gửi incident alert:
1. BẮT BUỘC nhận diện máy/serial hiện trường (hoặc tra cứu từ workbook Tik1/Tik2/taikhoan_run_safe).
2. Khi fix xong (dù fix ở consumer repo hay automation-core): BẮT BUỘC CHẠY LIVE CANARY trên đúng máy/hiện trường đó (hoặc verify trực tiếp qua ATX / screencap / dump UI).
3. TUYỆT ĐỐI KHÔNG ĐƯỢC tự ý gán `CANARY_NOT_APPLICABLE` và chốt phiên khi đầu phiên có ảnh hiện trường lỗi thực tế mà chưa kiểm chứng đóng popup / clear lỗi trên máy thật.


## 🎯 QUY CHUẨN LIVE CANARY THEO TỪNG REPO / SCRIPT (User chốt 28/08/2026)
Live Canary BẮT BUỘC phải kích hoạt bằng **Runner chính thức của repo**, TUYỆT ĐỐI CẤM dùng ad-hoc script/tap tay thay thế:
1. **Với `tiktok-luot nuoi acc` (Feed):** Chạy runner với `--max-swipes 2` (hoặc `--recovery-test-swipes 2`) + `--cleanup-on-stop` → Vượt qua popup → Thực hiện đủ 2 swipes → Tự động dọn dẹp về Home → Giải phóng lock.
2. **Với các script nghiệp vụ khác (`Tiktok_Reg`, `tiktok-follow`, `Tiktok-video`, `Hotmail`, `tiktok-add-bao-mat-f2a`, `register gmail`...):** Chạy đúng runner của repo trên máy target → Vượt qua đúng điểm nghẽn/lỗi → Chạy nốt hoàn thành trọn vẹn luồng công việc của script (Task Completion) → Tự động cleanup và giải phóng lock.
3. Chỉ khi runner chạy hoàn tất từ A-Z đạt `status: success` mới được coi là Pass Gate 0 và chuyển sang Model Review / Chốt phiên.


## 📘 QUY TẮC BẮT BUỘC ĐỐI CHIẾU & CẬP NHẬT DOCS/FARM-AUTOMATION-CASES.MD (ALL FARM REPOS)
1. **TRƯỚC KHI HANDLE SCRIPT / SỬA CODE FARM:** BẮT BUỘC đọc và đối chiếu toàn bộ các Case Fix thực tế & Anti-Pattern trong `docs/farm-automation-cases.md` (alias `docs/uiautomator.md`), bao gồm: UI/Popup, Cron/Reaper/Watchdog, Sync/Workbook/Data integrity, Device Lock/ADB. Tuyệt đối không tái phạm các lỗi đã được xử lý trong file này.
2. **KHI CHỐT PHIÊN (NẾU TASK LIÊN QUAN TỚI FARM AUTOMATION):** Trước khi Model Review và Commit, BẮT BUỘC phải cập nhật Case Fix thực tế và Anti-Pattern tương ứng vừa xử lý vào file `docs/farm-automation-cases.md` (đồng thời đồng bộ `docs/uiautomator.md`) sang các repo liên quan.
## 📘 QUY TẮC BẮT BUỘC ĐỐI CHIẾU & CẬP NHẬT DOCS/FARM-AUTOMATION-CASES.MD (ALL FARM REPOS)
1. **TRƯỚC KHI HANDLE SCRIPT / SỬA CODE FARM:** BẮT BUỘC đọc và đối chiếu toàn bộ các Case Fix thực tế & Anti-Pattern trong `docs/farm-automation-cases.md` (alias `docs/uiautomator.md`), bao gồm: UI/Popup, Cron/Reaper/Watchdog, Sync/Workbook/Data integrity, Device Lock/ADB. Tuyệt đối không tái phạm các lỗi đã được xử lý trong file này.
2. **KHI CHỐT PHIÊN (NẾU TASK LIÊN QUAN TỚI FARM AUTOMATION):** Trước khi Model Review và Commit, BẮT BUỘC phải cập nhật Case Fix thực tế và Anti-Pattern tương ứng vừa xử lý vào file `docs/farm-automation-cases.md` (đồng thời đồng bộ `docs/uiautomator.md`) sang các repo liên quan.

---

## QUY TẮC BẮT BUỘC: FIX BÁO LỖI MÁY = SỬA SCRIPT TOÀN CỤC (CẤM FIX TAY)
1. **Hiện trường máy là Read-Only Evidence:** Khi user báo lỗi trên Máy N (kèm ảnh chụp màn hình, log Telegram, hoặc alert), trạng thái và XML trên thiết bị CHỈ ĐƯỢC DÙNG ĐỂ ĐIỀU TRA ROOT CAUSE.
2. **Nhiệm vụ Fix BẮT BUỘC là Patch mã nguồn script:**
   - Mục tiêu của 'Fix' là sửa mã nguồn (script Python / flow / core / matcher / parser) trong repo tương ứng để giải quyết triệt để lỗi cho toàn bộ 160 máy trên Farm.
   - BẮT BUỘC chạy unit test / regression test xác nhận logic mới hoạt động chính xác.
   - BẮT BUỘC cập nhật Case Fix và Anti-Pattern vào `docs/farm-automation-cases.md` (Gate 0.5) trước khi hoàn tất.
3. **CẤM Fix Ad-hoc / Bấm tay:**
   - Tuyệt đối CẤM coi việc gửi lệnh ADB bấm tay (tap qua màn hình, gửi phím Home, back thô để máy hết kẹt) là đã hoàn thành nhiệm vụ 'Fix'.
   - Mọi can thiệp ADB trên máy bị lỗi phải tuân thủ giữ hiện trường lock máy (TTL 2h) cho đến khi script đã được vá và kiểm thử hoàn tất.

<!-- HERMES-DIRTY-SCOPE-RULE-20260831:START -->
## Dirty-tree scope rule (mandatory)

A dirty worktree is **not** a repository-wide blocker. The current task contract's exact allowlist is authoritative.

- Before any action, split paths into `IN_SCOPE` and `OUT_OF_SCOPE` using the current allowlist. Unrelated staged/unstaged files, unrelated test/build processes, and unrelated failures are `OUT_OF_SCOPE`: ignore them, do not inspect, revert, reset, unstage, stage, wait on, or report them as blockers.
- A staged or unstaged file inside the allowlist is not automatically a conflict. Staged state, an old mtime, or a non-empty `git status` does not prove another writer owns the requested hunk.
- Continue when dirty hunks are distinct and the requested hunk is unowned. Declare `SCOPE_CONFLICT` only when the same allowlisted file/overlapping region changes during the current ownership window, an active writer owns the requested region, or ownership cannot be separated safely. Record path, region, before/after hash or content, and timing evidence.
- `SCOPE_DRIFT` means this agent/worker changed outside its own allowlist; pre-existing unrelated dirty paths are not scope drift. Do not convert foreign dirt into a blocker.
- Verification and reporting must remain path-scoped. Report `unrelated dirty preserved`, `overlapping dirty/conflict`, and `agent-caused scope drift` as separate states.

<!-- HERMES-DIRTY-SCOPE-RULE-20260831:END -->

<!-- ANTI-OVERENGINEERING-BUDGET-GATE:START -->
## 🛑 QUY TẮC BẮT BUỘC: CHỐNG OVER-ENGINEERING & PHÂN TẦNG NGÂN SÁCH TASK (ALL WORKERS)
Áp dụng cho toàn bộ sessions (Coordinator & Worker) trên các repo Taadaa Phone Farm:

1. **PHÂN TẦNG NGÂN SÁCH THEO ĐỘ PHỨC TẠP TASK (DYNAMIC BUDGET):**
   - **Tier 1 (Hotfix / Lỗi cục bộ - sửa 1 hàm, format text, regex, cú pháp, selector UI, timeout):** Tối đa **15–20 tool calls**, xong trong **10–15 phút**. CẤM viết test mới, chỉ py_compile hoặc 1 assert tối thiểu.
   - **Tier 2 (Flow Bug - kẹt bước flow, popup mới, lệch luồng điều hướng, retry loop):** Tối đa **25–40 tool calls**, xong trong **20–30 phút**. Sửa đúng flow, chạy test runner của flow.
   - **Tier 3 (Major / Refactor lớn - sửa kiến trúc core, đa repo, đổi DB/workbook/socket ATX):** BẮT BUỘC chia thành các **Phase Milestone độc lập** (mỗi phase < 30 tool calls). CẤM chạy 1 lèo 100+ turns trong bóng tối.

2. **QUY TẮC CHECKPOINT (CHỐNG CHẠY MÙ TRONG BÓNG TỐI):**
   - Khi chạm mốc **25-30 tool calls** mà chưa xong, Worker BẮT BUỘC tạm dừng xuất báo cáo Checkpoint: (a) Đã tìm thấy gì? (b) Đã sửa được gì? (c) Khúc mắc còn lại là gì? -> Chờ định hướng, CẤM tự ý chạy tiếp hàng trăm turns.

3. **CẤM TEST INFLATION & SIMULATION THỪA MỨA (ÁP DỤNG CHO MỌI TIER):**
   - **CẤM TỰ VIẾT TEST SUITE ĐỒ SỘ:** Không tự ý đẻ file test mới hay viết hàng loạt test cases khi chưa được yêu cầu.
   - **CẤM CHẠY SIMULATION / MONTE CARLO:** CẤM viết script chạy lặp hàng ngàn lần (vd sinh 10.000 username đo entropy).
   - **CẤM TẠO PROBE SCRIPT TẠM TRONG %TEMP%:** Kiểm chứng chỉ dùng python -c "..." hoặc test file hiện có.
   - **CẤM CHẠY LẠI FULL TEST SUITE NHIỀU LẦN:** Sửa module nào chỉ test module đó hoặc py_compile.

4. **RÀNG BUỘC KHI COORDINATOR DISPATCH WORKER:**
   - Coordinator khi gọi delegate_task BẮT BUỘC gắn nhãn Tier và budget tương ứng (Tier 1: max 15-20 calls; Tier 2: max 25-40 calls; Tier 3: chia phase).
<!-- ANTI-OVERENGINEERING-BUDGET-GATE:END -->

<!-- CHOT_PHIEN_6_GATE_START -->
## 🏁 QUY TRÌNH CHỐT PHIÊN LÀM VIỆC (6 GATE BẮT BUỘC TOÀN FARM)
Khi nhận lệnh `chốt phiên`, `đóng phiên`, `kết thúc phiên`, `xong phiên`:
1. **Gate 0 (Live Canary):** Chạy canary thực tế bằng runner chính thức của repo (nếu có target live / incident evidence). Pass `status: success` mới mở gate tiếp theo.
2. **Gate 0.5 (Tài liệu Docs):** Cập nhật Case Fix & Anti-Pattern tương ứng vào `docs/farm-automation-cases.md` (nếu là task farm automation).
3. **Gate 1 (Model Review Độc Lập):**
   - **Review thường (mặc định):** BẮT BUỘC gọi combo `review` trên **OmniRoute (:20129)** qua API endpoint (`http://localhost:20129/v1/chat/completions`) với priority pool (`Claude Opus 4.6 Thinking -> Claude Sonnet 4.6 -> GPT OSS 120B -> Nemotron 3 Ultra -> AG Gemini Flash Pool`). CẤM tự review thay thế. Tự sửa tối đa 3 vòng lặp đến khi APPROVED.
   - **Review Hard hoặc Tad chỉ định:** CHỈ KHI làm tác vụ review hard (core, multi-repo, device-lock phức tạp) hoặc khi Tad trực tiếp chỉ định mới được gọi **Claude Code CLI (`claude -p`)**, tuân thủ chặn ở mức 85% limit.
4. **Gate 2 (Commit Local):** Commit exact-scope code fix + test với conventional commit rõ ràng.
5. **Gate 3 (Pull Rebase):** `git pull --rebase origin master` (hoặc main).
6. **Gate 4 (Push & Verify):** `git push origin master` (hoặc main) và đối soát remote SHA khớp local HEAD.
<!-- CHOT_PHIEN_6_GATE_END -->
