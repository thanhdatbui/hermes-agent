# PROJECT_RULES.md

Shared execution guardrails for AI assistants working in this Hermes checkout.

## Primary Goals

- Build Hermes toward this north star:
  **Hermes is a persistent, cost-aware AI orchestration system that turns
  high-level goals into verified outcomes by coordinating replaceable AI
  workers, long-running processes, isolated Git workflows, bounded retries,
  evidence-based verification, and selective escalation to expensive expert
  models.**
- Keep scope tight and evidence-based.
- Protect secrets, local Hermes state, generated runtime files, and operator setup.
- Follow upstream Hermes architecture: narrow core, capabilities at edges, prompt-cache stability.
- Stop cleanly when progress stalls instead of looping.

## Hermes North Star

Hermes is the boss above replaceable AI workers, not a new coding agent to
replace Codex, Claude Code, or DeepSeek. A user gives a high-level goal and
policy; Hermes should manage the work lifecycle: plan, split tasks, choose the
right model by cost and capability, run long jobs, capture logs/artifacts,
classify failures, retry within bounds, isolate branches/worktrees, verify,
commit, merge, audit, report, and recover next actions after context loss,
process death, API timeout, restart, or the user going away.

Default economic policy: cheap models do the routine labor; expensive models
act as experts, auditors, and escalation lanes. Do not hard-code workflows
around any one provider or agent. DeepSeek, OpenCode, Codex, Claude, local
models, and future cheaper models are interchangeable worker lanes behind the
orchestration policy.

Decision filter for every new task or feature: does it improve persistent
goal/workflow state, model routing, long-running process supervision,
evidence capture, root-cause classification, bounded retry, isolated Git
execution, verification, commit/merge control, expert audit, cost accounting,
or final reporting? If not, it is probably not on the main path.

## Required Read Order

1. `AGENTS.md`
2. The files directly involved in the task
3. `HANDOFF.md` only when current repository state, blockers, or explicit
   continuation context matters
4. `PROJECT_STRUCTURE.md` only for large, cross-file, risky, or
   architecture-sensitive work

## Default Execution Loop

For non-trivial changes:

1. Derive target outcome, scope, and acceptance criteria.
2. Inspect the relevant implementation and tests before editing.
3. Make the smallest safe change.
4. Run the smallest meaningful validation.
5. Review diff for unrelated churn, secrets, generated files, and Windows portability issues.
6. Report changed files, validation, skipped checks, and remaining risk.

## Hermes-Specific Rules

- Preserve prompt caching and strict user/assistant/tool role alternation.
- Do not mutate old conversation context or rebuild the system prompt mid-session unless implementing compression or an explicitly approved lifecycle change.
- Do not add new core model tools unless the capability cannot reasonably live as existing code, CLI plus skill, gated tool, plugin, or MCP server.
- User-facing behavioral settings belong in `~/.hermes/config.yaml`, not `.env`. `.env` is for secrets only.
- Use `get_hermes_home()` / profile-aware helpers instead of hardcoding `~/.hermes`.
- On Windows, avoid POSIX-only process, signal, permission, symlink, and shell assumptions. Read the Windows section in `CONTRIBUTING.md` before touching cross-platform code.
- Use explicit text encodings for file I/O.

## Validation Rule

- Use `scripts/run_tests.sh` for Python tests because it matches CI isolation.
- For narrow changes, run a targeted test path first, for example:
  `bash scripts/run_tests.sh tests/agent/test_example.py::test_case`
- For packaging/config changes, prefer metadata tests and import smoke checks.
- For TypeScript work, use the package/workspace scripts already present in `package.json` files.
- If validation cannot run on native Windows due to shell assumptions, say exactly what was skipped and why.

## Safety Boundaries

- Do not read, print, edit, stage, or commit real API keys, OAuth tokens, bot tokens, private keys, local auth files, session DBs, or user memories unless the user explicitly asks and the action is safe.
- Do not run live gateway, messaging, cron, browser, billing, account, or external-provider actions unless explicitly requested.
- Do not run broad destructive cleanup commands.
- Do not stage `.env`, `.ai-runs/`, `.hermes/`, logs, caches, build outputs, node_modules, venvs, or generated dist artifacts.

## Repeated-Blocker Rule

Make at most two meaningful attempts against the same error signature. If the same signature remains, stop and report `BLOCKED` with:

- task and phase
- commands tried
- changed files
- newest relevant logs/artifacts
- root-cause hypothesis
- risk of continuing
- recommended next owner/action

## Handoff Rule

Update `HANDOFF.md` when local state changes in a way the next session needs to know: setup status, blocker, artifact path, validated command, chosen provider/backend, or an active work boundary.

## Merge / Cleanup Rule (bắt buộc, 2026-08-08)

Khi thực hiện merge nhánh về main hoặc dọn nhánh/tree quan trọng:
1. Coordinator lập kế hoạch tích hợp trước khi merge (không merge mù); không dùng worker thiếu quyền phù hợp làm planner/auditor/reviewer.
2. Worker chỉ thực thi merge/resolve sau khi chứng minh ownership của session hiện tại, exact allowlist, trạng thái clean/committed và independent review `APPROVED` cho candidate trước tích hợp.
3. Sau tích hợp, chạy audit/review và test lại trên exact final candidate; nếu SHA thay đổi thì lặp lại gate trước push.
4. Chỉ merge/remove khi có đủ evidence ownership của session hiện tại, exact allowlist, trạng thái clean/committed và independent review `APPROVED`; chỉ yêu cầu absorbed/superseded sau tích hợp trước khi remove. Unknown, dirty, hoặc concurrent-owned phải được giữ nguyên và báo `BLOCKED`.

## COMMIT GATE (2026-08-10, user chốt)

- Commit + push KHI FULL TEST SUITE XANH (pytest tests/test_tiktok_workflow.py -q — 331 pass hiện tại), KHÔNG chờ live-run success.
- Live-run là bước verify TIẾP THEO (lỗi mới lộ ra thì fix tiếp, commit tiếp); không chặn release code.
- Fix sai trên máy thật → revert NGAY về bản git trước (git revert/checkout), nguyên trạng thái an toàn trong git.

## HANDOFF.md Trim Rule (bắt buộc, 2026-08-11)

- HANDOFF.md là tài liệu current-state: giữ MỤC ĐÍCH project, state đang dở, blocker thật, bước tiếp theo an toàn, safety rules quan trọng, pointer tới lịch sử (reports/ hoặc git history). KHÔNG tích lũy entry đã resolved.
- Ngưỡng trim: HANDOFF > ~250 dòng → task/session kế phải TRIM: giữ top current-state + pointer, xoá phần resolved cũ khỏi file (git đã giữ bản cũ, không mất gì).
- Khi append entry mới mà file sắp vượt ngưỡng: trim entry cũ đã resolved cùng lượt, không để HANDOFF phình vô hạn.
- Giữ EOL khi sửa HANDOFF (append/trim bằng python, không patch LF).

## Canonical Script Reuse Rule (bắt buộc, 2026-08-12)

- Khi cùng một workflow/operation chỉ thay input data (ví dụ Tik1/Tik2/TikN, account row 1/2/N, machine list hoặc config path), PHẢI dùng lại canonical script/entrypoint đã chạy chuẩn.
- Chỉ thay tham số hoặc file dữ liệu qua CLI/config; KHÔNG tạo launcher/runner/script tạm mới và KHÔNG ghép shell loop/xargs để thay thế flow canonical.
- Nếu canonical script chưa nhận data variant cần thiết hoặc còn hardcode path cũ: sửa/build chính script đó theo hướng parameterized, giữ nguyên safety gate hiện có; ghi baseline rollback trước edit, test/preflight variant cũ + mới, audit/verify rồi mới chạy live.
- Chỉ tạo script mới khi workflow thực sự khác và user đã chốt rõ; phải ghi lý do vì sao entrypoint hiện tại không thể tái sử dụng.
- Trước launch phải ghi evidence gồm canonical script path và data path/row đã chọn; việc đổi data không được bypass lock, account/target verifier, confirmation, recovery hoặc report contract.

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


## Task Contract and Scope Lock (MANDATORY)

This gate applies to every task, repository, worktree, skill, worker, and tool
sequence under `D:\Taadaa`.

- **Latest request wins.** The latest explicit user request is the only active
  task authority. A previous plan, summary, TODO, handoff, worker report,
  session context, or stale acceptance list is background only; it must not
  revive or widen the task without current user approval.
- **Contract before action.** Before the first state-changing action, record a
  compact task contract: `Goal`, exact `In-scope allowlist`, `Non-goals /
  forbidden scope`, `Acceptance criteria`, and `Stop condition`. If the user
  request is already clear, do not ask them to restate it; derive the contract
  narrowly from that request.
- **Scope checkpoint.** Before touching a new file, route, repository,
  worktree, device, account, worker, delegate, broad test suite, or live
  surface, ask: “Is this directly required by the current Goal and inside the
  allowlist?” If not, classify it `OUT_OF_SCOPE`, do not inspect/edit/run/
  delegate it, and report or ask for explicit expansion.
- **No implicit permission from a plan.** A plan is an implementation aid, not
  authorization to execute every phase. Adopt only the phases and files that
  the latest request explicitly covers; ignore stale plan sections.
- **Focused verification first.** Run only acceptance tests needed for the
  current scope. Do not expand to full-suite, adjacent-route, regression, or
  cleanup work unless the contract requires it or the user approves it.
- **Worker binding.** Every delegated worker receives the same contract,
  allowlist, non-goals, acceptance criteria, and stop condition. A worker that
  discovers scope drift must stop and hand off; it must not widen the scope.
- **Stop when done.** Once acceptance criteria pass, stop. Unrelated failures,
  adjacent improvements, and newly discovered routes are not follow-up work by
  default.

## 🔄 QUY TRÌNH CHỐT PHIÊN CHUẨN (User update 2026-08-23)
Khi user ra lệnh `chốt phiên`, `đóng phiên`, `kết thúc phiên`, hoặc `xong phiên`:
1. **Test live canary thực tế (BẮT BUỘC nếu có fix code/farm):** Chạy kiểm chứng trên máy thật/trạng thái lỗi để lấy bằng chứng runtime (PASS). Không được bỏ qua bước này.
2. **Model Review:** Đưa diff code + bằng chứng live test cho model review duyệt (APPROVED).
3. **Commit local exact-scope:** `git add <files>` đúng allowlist và `git commit -m "..."` local trước để đóng băng an toàn.
4. **Git pull --rebase:** `git pull --rebase <remote> <branch>` để kéo commit mới nhất từ PC khác về và xếp commit local lên đầu (chạy lại quick test nếu có commit mới).
5. **Git push & Verify SHA:** `git push <remote> <branch>` và đối chiếu `git ls-remote` khớp SHA local.
6. **Unlock & Báo cáo:** Giải phóng thiết bị/lock và báo cáo ngắn gọn (Mục đích -> Kết quả -> Blocker -> Remote SHA).

## 🛑 QUY TẮC AN TOÀN BẬT / TẮT CRON & REG COOLDOWN (User chốt 2026-08-26)
- **CẤM PAUSE CRON KHI CHẠY TAY / RECOVERY:** Mọi cron (nuôi acc, feed, reg đêm) đã có cơ chế tự lọc `device_lock` để skip các máy đang bận và chạy tiếp các máy rảnh còn lại. Tuyệt đối KHÔNG pause cron vì sẽ làm chết các watchdog giám sát an toàn và script tự động giải phóng lock quá hạn (TTL 2h).
- **MỖI MÁY REG TỐI ĐA 1 LẦN/NGÀY:** Máy đã reg `SUCCESS` hôm nay tự động nhận cooldown tới ngày hôm sau, detector tự động skip không bao giờ lập batch lại. Lỗi/PENDING không cooldown.
- **RECOVERY ĐÚNG DANH SÁCH LỖI:** Tuyệt đối không tự ý mở rộng phạm vi chạy lại toàn bộ batch pending khi được yêu cầu recovery.
