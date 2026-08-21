# Hermes Agent Instructions

This file is the always-loaded entrypoint for AI coding assistants. Keep it
short. Read the detailed development guide only when the task needs it.

## Startup

- Read this file first.
- Read `PROJECT_RULES.md` only when the task needs execution or safety rules.
- Read `HANDOFF.md` only when current repository state, blockers, or explicit
  continuation context matters.
- Read `PROJECT_STRUCTURE.md` only for architecture, runtime flow, or
  cross-file work.
- Read only the source files and tests directly relevant to the assigned task.
- If no task is assigned, stop after startup and wait.



## Scope And Safety

- Keep the change narrow and evidence-based.
- Preserve the upstream Hermes architecture: Kanban is the workflow engine;
  do not create a second orchestrator database or workflow engine.
- Do not run live messaging, browser, cron, billing, account, or provider
  actions unless the user explicitly authorizes them.
- Never read, print, edit, stage, or commit credentials, OAuth state, local
  sessions, user memory, `.env`, `.hermes`, logs, caches, or generated output.
- Use profile-aware Hermes paths such as `get_hermes_home()`; never hardcode
  `~/.hermes` in runtime code.
- On Windows, preserve explicit encodings and avoid POSIX-only assumptions.

## Context And Cost Invariants

- Preserve per-conversation prompt caching and strict message-role
  alternation.
- Do not rebuild the system prompt or mutate prior conversation context
  mid-session except in the existing context-compression lifecycle.
- Every core tool adds schema cost to every model call. Prefer existing code,
  CLI plus skill, service-gated tool, plugin, or MCP before a new core tool.
- Keep persistent memory concise and stable. Store task history in durable
  task state or artifacts, not in user memory or this file.
- For batch or isolated review work, use the existing `skip_memory` and
  toolset-filtering paths where the caller supports them.

## Work Loop

1. Confirm the expected behavior and inspect the relevant implementation.
2. Make the smallest safe change.
3. Run the narrowest meaningful test through `scripts/run_tests.sh` when
   applicable.
4. Review the diff for unrelated churn, secrets, generated files, and
   prompt-cache regressions.
5. Update `HANDOFF.md` only when the next session needs new state.

If the same error remains after two meaningful attempts, stop and hand off the
evidence instead of retrying blindly.

## Detailed References

- Full development and architecture guidance:
  `docs/ai/hermes-development-guide.md`
- Full historical handoff and prior decisions:
  `docs/ai/hermes-handoff-history.md`
- Stable architecture map: `PROJECT_STRUCTURE.md`
- Execution guardrails: `PROJECT_RULES.md`
- Context compression implementation: `agent/context_compressor.py`

## Merge / Cleanup Rule (bắt buộc, 2026-08-08)

Khi thực hiện merge nhánh về main hoặc dọn nhánh/tree quan trọng:
1. Coordinator lập kế hoạch tích hợp trước khi merge (không merge mù); không dùng worker thiếu quyền phù hợp làm planner/auditor/reviewer.
2. Worker chỉ thực thi merge/resolve sau khi chứng minh ownership của session hiện tại, exact allowlist, trạng thái clean/committed và independent review `APPROVED` cho candidate trước tích hợp.
3. Sau tích hợp, chạy audit/review và test lại trên exact final candidate; nếu SHA thay đổi thì lặp lại gate trước push.
4. Chỉ merge/remove khi có đủ evidence ownership của session hiện tại, exact allowlist, trạng thái clean/committed và independent review `APPROVED`; chỉ yêu cầu absorbed/superseded sau tích hợp trước khi remove. Unknown, dirty, hoặc concurrent-owned phải được giữ nguyên và báo `BLOCKED`.

<!-- WORKER-CHECKPOINT-TERMINATION-POLICY:START -->
## Worker checkpoint và gate dừng process (bắt buộc)

- Worker/background run phải ghi checkpoint và report riêng theo từng vòng: scope, thời điểm, phase, diff/test thật và điều kiện chờ kế tiếp; không chỉ ghi report ở cuối.
- Không suy luận code lỗi từ stdout đứng yên hoặc `exit code -15`. Chỉ được terminate khi có lỗi fatal/quota/transport machine-readable, hoặc sau ít nhất 3 quan sát cách nhau tối thiểu 30 giây (tổng >=90 giây) cùng chứng minh output/checkpoint/file mtime/process tree không tiến triển, không còn child code/test/tool hoạt động.
- Trước khi terminate phải lưu đầu/cuối log, process tree, mtime, `git status` và `git diff`; nếu worker có thể đã ghi code thì chạy hậu kiểm diff/test độc lập trước kết luận.
- Kill/exit bất thường phải phân loại `WORKER_TERMINATED_EXTERNALLY` hoặc `WORKER_EXITED_WITHOUT_REPORT`; không rollback mù, không tin report cũ, không chạy worker thay thế chồng. Reconcile exact scope và verifier độc lập trước replacement/commit.
- Quy tắc này bổ sung `agent-review-loops`; không cho phép bỏ qua gate riêng của repository hoặc mở rộng side effect/live scope.
<!-- WORKER-CHECKPOINT-TERMINATION-POLICY:END -->

## Canonical Script Reuse Rule (bắt buộc, 2026-08-12)

- Khi cùng một workflow/operation chỉ thay input data (ví dụ Tik1/Tik2/TikN, account row 1/2/N, machine list hoặc config path), PHẢI dùng lại canonical script/entrypoint đã chạy chuẩn.
- Chỉ thay tham số hoặc file dữ liệu qua CLI/config; KHÔNG tạo launcher/runner/script tạm mới và KHÔNG ghép shell loop/xargs để thay thế flow canonical.
- Nếu canonical script chưa nhận data variant cần thiết hoặc còn hardcode path cũ: sửa/build chính script đó theo hướng parameterized, giữ nguyên safety gate hiện có; ghi baseline rollback trước edit, test/preflight variant cũ + mới, audit/verify rồi mới chạy live.
- Chỉ tạo script mới khi workflow thực sự khác và user đã chốt rõ; phải ghi lý do vì sao entrypoint hiện tại không thể tái sử dụng.
- Trước launch phải ghi evidence gồm canonical script path và data path/row đã chọn; việc đổi data không được bypass lock, account/target verifier, confirmation, recovery hoặc report contract.

<!-- SESSION-START-CONTEXT:START -->
## Session-start context (bắt buộc mỗi session mới — CHỐNG PHÌNH CONTEXT)
- Khi session mới bắt đầu (vừa `/new`, resume, hoặc đổi máy): trước khi hỏi user hoặc tự làm gì, chạy đúng 4 bước có chọn lọc:
  1. Đọc file `AGENTS.md` này. Nếu có `HANDOFF.md`, CHỈ đọc phần `Current State / Blockers / Next Task` (nếu file >20KB thì không nạp toàn bộ lịch sử).
  2. Tìm trong `.hermes/plans/` (nếu có): CHỈ đọc **đúng 1 file `.md` mới nhất theo timestamp**. KHÔNG đọc toàn bộ thư mục plans.
  3. Kiểm tra git: `git status --short` + `git log --oneline -5`.
  4. Tổng hợp thành 1 báo cáo ngắn ("Task đang dở / bước kế tiếp / trạng thái git") rồi hỏi xác nhận TRƯỚC khi tiếp tục — CẤM tự đoán task và tự làm tiếp.
- Mục đích: chống phình context (không nạp hàng trăm KB startup), giữ mạch làm việc qua các lần /new và đổi máy.
<!-- SESSION-START-CONTEXT:END -->

## AUDIT / PLAN / REVIEW ROUTING MANDATE (chốt 2026-08-18, ALL repo)
- TUYỆT ĐỐI CẤM dùng delegate_task hoặc Flash/Worker để làm PLANNER / AUDITOR / REVIEWER.
- CẢ 3 VIỆC (PLAN, CODE REVIEW, AUDIT) ÁP DỤNG CHUNG 1 KHUNG CHUẨN KỊCH TRẦN REASONING:
  1. Cấp Thường / Vừa (UI, popup, video gate, feature 1 repo, helper):
     - 9Router HTTP API (http://127.0.0.1:20128/v1/chat/completions) với combo 'plan-review' (gpt-5.6-terra -> ag/claude-opus-4-6-thinking -> cmc/deepseek/deepseek-v4-pro) kèm reasoning kịch trần ("reasoning_effort": "max" / "high").
  2. Cấp Khó / Core / Nhạy cảm (Architecture, Scheduler, Manifest validation, Hashing, State machine, Lock, Recovery, Multi-repo):
     - Ưu tiên 1: 9Router HTTP combo 'plan-review-hard' (gpt-5.6-sol) kèm reasoning kịch trần ("reasoning_effort": "ultra" / "max").
     - Fallback (khi Sol lỗi/hết quota/429/404): Gọi Claude CLI print mode với model `claude-opus-5`, reasoning kịch trần, và chỉ quyền `Read`; truyền prompt qua stdin hoặc file redirect (không nội suy prompt vào shell argument), ví dụ `claude -p --model claude-opus-5 --effort max --allowedTools Read --max-turns 15 < review-prompt.txt`. Reviewer không được có quyền `Bash`, `Edit`, `Write`, Git mutation, network mutation hoặc push.
- Request body HTTP bắt buộc: tools: [], tool_choice: 'none', stream: false, Authorization: Bearer $NINEROUTER_API_KEY.
## 13. PREFLIGHT SCHEDULE CHECK (Bắt buộc trước mọi batch chạy tay/live — user chốt 2026-08-18)
Trước khi chạy bất kỳ batch tác vụ nào trên farm (Reg TikTok, Hotmail login, Add mail khôi phục, Register Gmail, Upload video, Reconcile...):
1. **TỰ ĐỘNG KIỂM TRA LỊCH CRON NUÔI ACC:** Agent BẮT BUỘC tự động kiểm tra manifest nuôi acc (`D:\Taadaa\runtime\kibe\cron-state\manifests\<ngày>\active_manifest.json` qua skill `farm-schedule-preflight-check`) TRƯỚC KHI KHỞI CHẠY.
2. **KHOẢNG ĐỆM AN TOÀN ≥ 1 TIẾNG:** Chỉ được chọn và chạy trên các máy hoàn toàn rảnh trong suốt thời gian chạy batch và **cách ca nuôi acc kế tiếp tối thiểu 60 phút**.
3. **CẤM CHẠY TRÙNG MÁY:** Tuyệt đối không khởi chạy batch trên các máy đang trong ca nuôi hoặc sắp vào ca < 60 phút.
4. **USER CHỈ CẦN BẢO "CHẠY SCRIPT XXX" → AGENT TỰ CHECK LỊCH RỒI CHẠY:** User không cần phải nhắc "kiểm tra lịch", agent tự động check máy rảnh -> lọc danh sách máy an toàn -> chạy. Khi gặp lỗi máy nào -> dừng máy đó, chụp ảnh gửi user, chỉ lock khi user yêu cầu để debug sau.

## 14. QUY TẮC CLOSEOUT TỰ ĐỘNG BẮT BUỘC

Chỉ lệnh đóng phiên rõ ràng ("chốt phiên", "chốt phiên đi", "đóng phiên", "kết thúc phiên", "xong phiên") mới kích hoạt closeout. Câu hỏi tiến độ chung như "xong chưa" hoặc "đã xong chưa" chỉ được trả lời trạng thái, không tự kích hoạt rebase, push hoặc thay đổi remote.

1. **ĐÓNG BĂNG VÀ TÍCH HỢP CÓ KIỂM SOÁT:** kiểm tra branch, upstream, merge-base, ownership, exact allowlist và conflict. Unknown, dirty hoặc concurrent-owned phải giữ nguyên và báo `BLOCKED_AT_WORKTREE_OWNERSHIP`.
2. **REVIEW/TEST CANDIDATE CUỐI:** sau tích hợp, chốt exact final candidate; dùng đúng route trong mục routing (multi-repo/core dùng `plan-review-hard`). Review phải độc lập, dòng verdict phải parse được là `APPROVED`, và test/lint/compile phải chạy trên chính candidate. SHA đổi thì lặp lại gate này.
3. **COMMIT ĐÚNG SCOPE:** stage exact allowlist, không dùng `git add -A`/`git add .`, không đưa backup, runtime, secret, workbook hoặc untracked artifact vào commit; xác minh `git show --name-status`.
4. **PULL-BEFORE-PUSH:** sau commit, xác minh upstream thực tế, chạy `git fetch <remote>` rồi `git pull --rebase <remote> <remote-branch>`. Nếu rebase đổi SHA/tree thì lặp lại review và test.
5. **PUSH VÀ XÁC MINH:** push explicit `HEAD:<remote-branch>` tới remote đã xác minh, không force-push; đọc `git ls-remote` và yêu cầu remote SHA == local HEAD.

Chỉ báo hoàn tất khi có đủ verdict exact candidate, test evidence, branch/worktree/upstream state, commit SHA và remote SHA. Thiếu gate nào phải báo `BLOCKED_AT_<STEP>`.

## CLOSE-SESSION HARD TRIGGER

Các câu "chốt phiên", "chốt phiên đi", "đóng phiên", "kết thúc phiên", "xong phiên" là lệnh thực thi closeout theo quy trình trên. Các câu hỏi tiến độ chung "xong chưa" và "đã xong chưa" không phải lệnh closeout; chỉ báo trạng thái. Không được nói "đã chốt/xong" nếu thiếu bất kỳ gate review, test, commit, rebase, push hoặc remote-SHA nào.
