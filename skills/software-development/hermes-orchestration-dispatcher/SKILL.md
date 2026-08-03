---
name: hermes-orchestration-dispatcher
description: "Điều phối: task đơn giản Hermes tự sửa → Claude/OpenCode audit review → lặp fail mới Codex implement."
version: 1.4.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [orchestration, dispatch, codex, claude, opencode, workflow, audit, review]
---

# Hermes Orchestration Dispatcher

## Quy tắc cứng (theo D:\Taadaa\AGENTS.md)

**KHI SKILL NÀY ĐƯỢC LOAD:** Hermes phân loại task rồi điều phối theo ladder dưới đây. Hermes KHÔNG bao giờ tự ý implement thẳng khi chưa qua audit review, trừ task đơn giản trong phạm vi dưới.

### Phân loại task

- **SIMPLE** (Hermes tự sửa được): task 1-2 file, mechanical edit, bug rõ ràng, có test hiện có, không đụng shared core (`automation-core`), không sensitive (account/OTP/lock/workbook policy), không multi-machine. → **Hermes tự sửa trực tiếp**.
- **COMPLEX** (dispatch Codex implement): đụng `automation-core` hoặc shared recovery/lock/verifier/scheduler, cross-consumer, account/OTP/2FA safety, sensitive workbook policy, multi-machine/incident, architecture refactor. → **Codex implement** (Sol/high, ladder escalation).
- **BOUNDED_RESEARCH/AUDIT** (delegate review): read-only exploration, log/artifact analysis, test chạy, independent review. → **Claude/OpenCode audit**.

## Vòng lặp điều phối chuẩn

```
1. Phân loại task (SIMPLE / COMPLEX / AUDIT).
2. SIMPLE  → Hermes tự sửa code + test + chạy verify.
   COMPLEX → viết spec tasks/<date>-<slug>.md → dispatch Codex implement.
3. Dispatch AUDIT REVIEW (Claude ưu tiên, fallback OpenCode free, cuối Codex reviewer độc lập).
   Claude/OpenCode CHỈ review/audit — KHÔNG bao giờ implement.
4. Reviewer trả APPROVED / MINOR_FIXES / REJECT.
   - APPROVED → xong (verify cuối: test + diff).
   - MINOR_FIXES/REJECT → Hermes tự sửa theo findings (SIMPLE scope) HOẶC Codex sửa (COMPLEX scope).
5. Re-review (vòng 2+).
6. Vẫn fail CÓ DẤU HIỆU LẶP (cùng findings, cùng chỗ treo/fail, 2+ vòng không tiến triển)
   → Chuyển hẳn cho Codex implement: phiên MỚI, kèm what-was-tried/why-failed + materially different plan (theo AGENTS.md), không lặp y hệt prompt.
7. Codex xong → review lại → APPROVED → verify cuối.
```

## Nguyên tắc vai trò

- **Hermes**: tự sửa task SIMPLE; viết spec; dispatch; sửa theo findings; verify cuối (test + diff + git diff --check). KHÔNG implement task COMPLEX thẳng tay.
- **Claude**: reviewer/auditor CHỈ ĐỌC. Không bao giờ implement. Quota gate theo `D:\Taadaa\AGENTS.md` (preflight `claude-quota-preflight.ps1`, `<85%` mới dùng).
- **OpenCode**: reviewer/auditor fallback (free model), CHỈ ĐỌC. Không bao giờ implement.
- **Codex**: implementer cho task COMPLEX + sửa findings khi Hermes lặp fail. Reviewer độc lập chỉ khi Claude+OpenCode đều unavailable.

## Model Fallback Khi Claude Review Hết Quota

Khi `claude -p` trả quota/session limit, rate limit, billing error:
- **KHÔNG bỏ review gate, KHÔNG chờ reset.**
- Fallback chỉ thay **audit/review**, không thay Codex implementer.
- Thứ tự: `freemodel/claude-opus-4-8` → `opencode-go/grok-4.5` → `opencode-go/glm-5.2`, `--variant max`.
- `opencode run --agent plan --auto --model <m> --variant max '<prompt>'` (read-only, quyền đọc external dir).
- Prompt phải có verdict `APPROVED | MINOR_FIXES | REJECT` dòng đầu.
- Smoke-test: `opencode run --model <m> 'Respond with exactly: OPENCODE_FALLBACK_READY'`.
- Shell vỡ quote → viết `.txt`, `PROMPT=$(cat file); opencode run ... "${PROMPT}"`.
- `APPROVED` từ fallback thay thế gate Claude cho run hiện tại.
- Nếu toàn bộ Claude/OpenCode reviewer hết quota hoặc unavailable, dùng **Codex reviewer độc lập** làm fallback cuối: phiên mới, `--ephemeral`, `--sandbox read-only`, dùng model Codex mặc định đã route được tới Sol (hiện là `gpt-5.6-sol`) và override reasoning `high`; không ép `-m sol` nếu alias đó route sang provider thiếu credential; prompt verdict `APPROVED | MINOR_FIXES | REJECT`. Không reuse/resume session implementer và không để implementer tự spawn subagent để tự duyệt thay đổi của chính nó.
- Nếu Codex reviewer trả finding, Hermes sửa (SIMPLE scope) hoặc dispatch Codex implementer mới (COMPLEX scope), rồi review lại.

## Codex Model Ladder (theo D:\Taadaa\AGENTS.md)

Khi dispatch Codex implement, chọn model theo độ khó (không phải mặc định):

- **Luna / medium**: task bounded rõ output (scan, log/XML extraction, structured summary, test fixture, mechanical edit có spec).
- **Luna / high**: bounded work cần tracing/verification thêm.
- **Terra / high**: scoped implementation/recovery patch, code-path tracing, non-mechanical patch, targeted retry, review Luna evidence. **Terra là recovery patch owner.**
- **Sol / high**: trước khi đổi `automation-core`, shared recovery/lock/verifier/scheduler, account/OTP/2FA sensitive, multi-consumer. Không phải mặc định chỉ vì task liên quan automation.
- **Sol / ultra**: chỉ khi ULTRA_GATE=YES (independent shards/deepest investigation).
- Luna không được là final decision-maker cho live automation outcomes, SUCCESS/FINAL_BLOCKED, root-cause, recovery choices, account/device/workbook actions — Terra/Sol phải review evidence/diff/verifier trước.
- Model choice không authorize live actions ngoài scope user; live/recovery luôn theo recovery state machine + verifier proof.

## Codex Implementer Escalation (Sol high → extra high → ultra)

Khi Codex implementer fail/treo ở model mặc định: nâng dần `-c model_reasoning_effort="high"` → `"extra_high"` → `"ultra"`. **Mỗi nấc là phiên Codex MỚI hoàn toàn (không resume session cũ)** và **phải làm khác đi nấc trước** (theo `D:\Taadaa\AGENTS.md`: kèm what-was-tried/why-failed + materially different plan, không lặp y hệt prompt). Sol/ultra chỉ khi có independent shards (Automatic Ultra Gate). Smoke-test trước mỗi nấc (`Respond with exactly: READY`). Codex hay treo ở cuối sau khi đã ghi xong file — kiểm tra file/test trước khi kill.

## Fallback OpenCode Free Khi Codex + Claude Đều Fail

Theo `D:\Taadaa\AGENTS.md`: audit order **Claude → OpenCode → Codex fallback**. Khi Claude hết quota/fail và Codex cũng fail/treo → dùng **model free của OpenCode** làm audit/review read-only: ưu tiên `opencode/deepseek-v4-flash-free`, fallback free model khác khi quota/rate-limit. Dùng wrapper `taadaa-review`/`invoke-opencode-audit.ps1` nếu có; smoke-test trước; verdict `APPROVED | MINOR_FIXES | REJECT`; label `OPENCODE_AUDIT` (không gọi là Claude approval). OpenCode unavailable → `OPENCODE_RUNTIME_UNAVAILABLE` → Codex reviewer độc lập (`CODEX_FALLBACK_AUDIT`).

## Audit/Read-Only Dispatch

1. Viết audit spec (hoặc dùng diff thực tế).
2. Codex đọc file + phân tích (nếu COMPLEX) HOẶC bỏ qua (SIMPLE).
3. Hermes cross-verify CRITICAL/HIGH findings (`read_file()` ok).
4. Claude review → CONFIRMED/REJECTED.

## Trigger

"dùng rule điều phối", "dispatch codex claude", "gọi audit review", "gọi model ra review"

## Enforcement từ D:\Taadaa\AGENTS.md (bắt buộc khi làm việc trong Taadaa)

File cha `D:\Taadaa\AGENTS.md` là nguồn quyền lực. Skill này tóm tắt các điểm Hermes phải tuân thủ (không thay thế file cha — đọc file cha khi cần chi tiết):

### Automatic Ultra Gate (bắt buộc in khi cần Sol/Ultra)

Khi task có thể cần Sol/Ultra, trước khi chọn model phải phân loại ngầm:
```
ULTRA_GATE: YES | NO
REASONS: <matching signals>
SHARDS: <number and short names>
```
`ULTRA_GATE=YES` chỉ khi ≥1 tín hiệu: đụng `automation-core` + 2+ consumer; 2+ repo/máy/target/execution path song song; versioned contract migration/rollout (core + consumer + regression); multi-machine incident có cluster riêng; security/account-safety/scheduler/lock/production review cần tách implementation + audit. `NO` mặc định cho 1 path/1 module/1 consumer/1 target — dùng Sol/high, không in gate. "Task khó" mơ hồ KHÔNG phải Ultra signal.

### Claude quota hard gate (5h + weekly)

TRƯỚC MỖI lần gọi Claude (kể cả retry):
- Chạy `D:\Taadaa\tools\claude-quota-preflight.ps1 <ledger-path>` — exit 0 = cho phép, 20 = 5h đạt 85% (block), **22 = weekly đạt 90% (block)**, 21 = quota unavailable (block). Chi tiết exit code + pitfall PS 5.1 `ToHexString`: `references/claude-quota-preflight.md`.
- Điều kiện chạy: `used_5h_percent < 85%` **VÀ `used_weekly_percent < 90%`** (khi weekly có trong /usage). Đạt 90% weekly → **dừng hẳn, không dùng Claude nữa** (không chỉ chờ reset 5h).
- Reading >60s cũ = stale → block.
- Ghi decision vào `D:\CodexRuntime\<project-id>\audit\claude-quota-ledger.jsonl` (event, decision, used/remaining 5h + weekly, observed_at, source_id, reason).
- Long-running audit (>60s) cần quota monitor poll ≤30s; đạt 85% 5h hoặc 90% weekly → cancel process tree, treat as no verdict, fallback OpenCode → Codex.
- CLI/auth availability KHÔNG phải quota proof.

### Scheduler Maintenance Authority

User ủy quyền Codex stop/restart scheduler/watcher/batch runner khi runtime cần sửa: chỉ stop process tree đã xác định, verify đã exit, offline validation xong, restart cùng service, báo trạng thái verified. Không đụng live account/ADB/mailbox/workbook ngoài phạm vi scheduler.

### Shared Parallel Runner Policy

- Live runner mặc định dispatch TOÀN BỘ target đã chọn song song theo `max worker`; không ép `MaxParallel=1`/vòng lặp từng máy trừ khi user yêu cầu.
- Mỗi target giữ lock riêng, handler riêng, retry bound riêng, verifier riêng; lỗi target này không làm target khác báo success.
- Bắt buộc random thứ tự máy mỗi run + stagger random bounded (`automation_core.scheduler.machine_launch`); ghi seed/order/delay evidence redacted.
- Worker exit không phải completion proof; chỉ VERIFIED_SUCCESS/FINAL_BLOCKED.

### Recovery Contract (tóm tắt — consumer AGENTS.md + core contract là nguồn)

- Mọi live action đổi UI/device state phải qua handler/primitive có contract; KHÔNG ADB/tọa độ thủ công ngoài script.
- Chưa có handler → `NO_HANDLER_IMPLEMENTED`: dừng target, evidence, thêm handler + regression test + verifier trước retry.
- Max 2 meaningful attempts/failure signature; attempt 2 phải materially different + evidence-backed; không attempt 3 cùng signature.
- Trước `FINAL_BLOCKED` phải same-target Sol/high handoff + verify `sol_handoff_completed=true` trong `D:\CodexRuntime\<project-id>\recovery\handoff-ledger.jsonl`.
- Chỉ `VERIFIED_SUCCESS` mới cho cleanup/workbook/release.

### Target Serial Provenance

Serial máy phải resolve từ workbook `D:\OneDrive\codex_gmail_debug\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx` (May + Device ID). Không dùng adb devices thô/hardcode/artifact cũ/proxy workbook làm nguồn serial.

### Live Run Scope & Device-Lock Policy

- `FULL_SCOPE_TAKEOVER`: "chạy full/all máy" → mọi máy trong range vào scope accounting.
- `EXCLUDE_LOCKED`: "all máy trừ máy lock" → inspect lock trước, exclude, giữ lock, kết quả `SKIPPED_LOCKED`/`EXCLUDED_LOCKED` (không success, không FINAL_BLOCKED).
- Không takeover lease `owner_active=true`/unverifiable; không xóa lock file bằng tay; lock host khác không reclaim cục bộ.
- Ghi scope mode + target list + lock decision + owner PID vào batch audit artifact redacted; lock skip exit 0 KHÔNG được map thành Verified=True.

### Configuration Policy Audit Gate

Thay đổi `D:\Taadaa\AGENTS.md`/custom-agent TOML/global Codex config/OneDrive bundle/2+ consumer AGENTS.md = policy change → cần independent read-only review (prefer subagent + `claude-final-audit` khi có Claude). Gate này không authorize live actions.

## Sync rule (git auto-sync — thay OneDrive 2026-08-03)

- 2 skill điều phối (`agent-review-loops`, `hermes-orchestration-dispatcher`) **junction tới `D:\Taadaa\Hermes\skills\`** (git repo `thanhdatbui/hermes-agent.git`) — sửa local = git thấy ngay, không copy tay.
- **Cron `sync-hermes-skills-to-git`** (mỗi 30 phút, no_agent, silent khi không đổi) tự commit+push lên GitHub.
- Sửa skill xong: đợi cron (≤30 phút) HOẶC chạy ngay `python C:\Users\Kibe\AppData\Local\hermes\scripts\sync-hermes-skills.py`.
- Máy mới: đọc `D:\Taadaa\Hermes\deploy\SKILL_SYNC_WORKFLOW.md` (junction + cron setup) hoặc copy skill từ git repo vào `AppData\Local\hermes\skills\` + `/reset`.
- KHÔNG dùng OneDrive cho skill nữa. Codex dùng `D:\OneDrive\CodexConfig\setup-codex.ps1`; `D:\Taadaa\AGENTS.md` sửa xong copy sang `workspace-AGENTS.md`.
- Pitfall: `FETCH_HEAD` bị lỗi "Permission denied" nếu bị ghi đè tay (echo >) — xóa file `.git/FETCH_HEAD` là git tự tạo lại. Cron job có thể dừng sau 1 lần chạy dù repeat=forever — kiểm tra `cronjob list` state, re-enable nếu completed.

## Pipeline Fallback

- **Codex sandbox not found** → `--sandbox danger-full-access`
- **Codex BLOCKED hoàn toàn** → Claude implementer (`claude -p --dangerously-skip-permissions`) CHỈ khi task COMPLEX và không có lựa chọn khác.
- **Claude permission mode** → luôn `--dangerously-skip-permissions` khi non-interactive.

## Pitfall

- Session 2026-07-27: Hermes tự ý implement thẳng code khi user nói "dùng rule điều phối" — KHÔNG LẶP LẠI với task COMPLEX.
- Session 2026-08-03: Hermes dispatch Codex cho task SIMPLE (avatar verify, usb popup) thay vì tự sửa — lãng phí. Task SIMPLE → Hermes tự sửa, chỉ audit review gọi ra.
- Claude/OpenCode KHÔNG BAO GIỜ implement — chỉ review/audit.
- Vòng lặp fail 2+ vòng cùng findings → chuyển Codex, không tự cày tiếp.
