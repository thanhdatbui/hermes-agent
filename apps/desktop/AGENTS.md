# Desktop Engineering Guide

How to build Hermes Desktop well. This is a judgment guide, not an inventory —
it teaches the invariants and the reasoning behind them so a change fits the app
even as files move. Read it with the repository `AGENTS.md` (root rules still
apply) and [`DESIGN.md`](./DESIGN.md) for the visual and interaction contract.

When a rule here and the code disagree, trust the code and fix whichever is
wrong — but never break an invariant to make a change easier.

## Delegation Policy

<!-- CODEX-DIRECT-WORKER-POLICY:START -->
## Coordinator -> direct worker boundary (canonical)

- The desktop/main session is coordinator/report surface only: it may perform read-only triage/research, route handoffs, inspect artifacts/diffs, run deterministic read-only verification, and report.
- For every write, edit, build, package, deployment, or other side effect, the coordinator must dispatch exactly one fresh, non-resumed, non-forked in-process direct worker pinned to the session's own model (`deepseek-v4-flash` for Hermes, `gpt-5.6-luna` for Codex), `reasoning_effort=high`, and `role=worker`, with an exclusive exact file/component/worktree scope. `gpt-5.6-luna/high` and `deepseek-v4-flash/high` are equivalent worker roles.
- The direct worker is already the sole executor: it patches, builds, and tests its assigned scope directly. It must not inherit, spawn, resume, fork, or delegate to another worker/agent/session, and must not invoke an external agent or CLI route. If the tool surface exposes any delegation capability, the worker must fail closed with `NESTED_DELEGATION_FORBIDDEN` and must not call it.
- A created/bound direct worker treats its current session as the final executor; it must not probe for, request, or create another worker/runtime, and it must never self-report SUBAGENT_RUNTIME_UNAVAILABLE. Tool absence inside an existing worker is not pre-create transport failure; use WORKER_RUNTIME_NOT_VERIFIED or NESTED_DELEGATION_FORBIDDEN as applicable and stop.
- Terra/high, Terra/xhigh, Sol/high, and Sol/max are read-only planners/advisors/auditors; they never patch, build, or run live/side-effecting work.
- An external CLI transport is not the normal route. The coordinator may use it only as the separately gated fallback in the parent `D:\Taadaa\AGENTS.md`, after authenticated pre-create in-process `transport-unavailable`, machine-readable `capability-unavailable`, or in-process dispatch `429`, plus proof that no worker/session/process/lease/action exists for the exact scope. The same model/profile, reservation, binding, checkpoint, reconciliation, and post-verifier gates still apply.
- Failure labels are lifecycle-hard: `SUBAGENT_RUNTIME_UNAVAILABLE` is reserved exclusively for a pre-create transport failure, and only with machine-readable evidence plus exact-scope reconciliation proving that no child/worker, session, process, lease, tool event, or action exists. A worker that exists or is bound must never self-report or assign this code.
- Use `WORKER_PROFILE_MISMATCH` for a created worker with the wrong pin and `WORKER_RUNTIME_NOT_VERIFIED` when provider/profile binding cannot be verified. Use `WAIT_WINDOW_EXPIRED` when a bounded wait has no final while the worker remains active. A timeout never changes a label or becomes `SUBAGENT_RUNTIME_UNAVAILABLE`.
- A replacement is permitted only after the current worker has shut down and exact-scope lease/process/tool-event/action reconciliation proves no overlap; replacements never run in parallel, and a worker must not self-replace or initiate replacement.
- If no valid direct worker exists, stop all write/live/side-effecting work. Coordinator direct fallback is allowed only when the current user request explicitly authorizes it, both worker routes have failed and been reconciled, and the parent contract permits exact-scope offline repository files; it never authorizes live work.
- Worker self-report, process status, scheduler status, or exit code is not completion proof; the coordinator must independently inspect the exact diff and run the deterministic verifier.
<!-- CODEX-DIRECT-WORKER-POLICY:END -->

## What this app is

Desktop is its own native chat surface. It is not the browser dashboard and it
does not embed the TUI. Three parties, each authoritative for one thing:

- **Electron** owns the machine: process lifecycle, native filesystem/git/
  windows, install/update, and a narrow, typed capability bridge.
- **The renderer** owns the experience: navigation, presentation, and ephemeral
  interaction state.
- **The agent backend** owns the work: sessions, tools, model calls, streaming.

Keep the seams clean. The renderer never reaches for Node or Electron directly;
native power arrives through a deliberate capability, not a general escape hatch.
Agent behavior lives behind the gateway, never reimplemented in React. When a
change blurs a seam, that is the smell — fix the seam, don't widen it.

## Decide state by authority

The first question for any piece of state is *who is allowed to be right about
it*, not where it is convenient to store it. Put state with its authority:

- The **backend** is authoritative for anything another Hermes surface can also
  change. Treat the renderer's copy as a cache of that truth.
- **Electron** is authoritative for machine and runtime facts.
- The **renderer** owns only what is purely about this window's presentation.

From that, everything else follows: shared renderer state lives in small stores
owned by the feature that owns the concern; request-shaped server data that wants
invalidation lives in the query layer; short-lived interaction detail stays in
the component; hot coordination that must not paint stays in a ref. Reach for the
narrowest home that still lets the state be correct. A new global store is a
claim that many distant surfaces need it — earn that claim.

Persisted state must declare its scope in its own key: is this global, or does it
belong to a connection, a profile, a stored session, a project, or a window?
Getting the scope wrong is how one profile's setting bleeds into another.

## Identity is not incidental

Sessions have more than one identity, and conflating them is a recurring source
of "session not found" and vanishing history. Reason about which identity a
surface needs: durable navigation and anything the user pins or persists key off
the stable/durable identity; live streaming keys off the runtime identity; state
that must outlive compression keys off the lineage root. Keep the mapping between
them explicit and translate at the boundary rather than passing the wrong id
inward.

## Server truth is cached, not owned

The renderer paints from a cache of backend truth, so it must reconcile, not
assume:

- **Merge, don't clobber.** A refresh is new information layered over what you
  already know, not a replacement that can drop live or pinned rows.
- **Be optimistic, then honest.** Direct manipulation should paint immediately
  from a snapshot; a failed write rolls back visibly and an authoritative
  refresh gets the last word.
- **Guard against the past.** Async results can arrive out of order; a stale
  response must never overwrite newer intent. Generation counters and request
  tokens exist for this.
- **Isolate the foreground.** Only the surface the user is looking at may publish
  into the shared view; background work updates its own cache quietly.
- **Coalesce noise, flush signal.** Batch high-frequency cosmetic updates, but
  let terminal transitions (a turn finishing, needing input, failing) reach the
  user immediately.
- **Preserve reference identity on no-ops.** Handing React a fresh array that
  contains the same data re-renders expensive trees for nothing.

## Switching context is a re-home, not a reboot

Changing profile, connection, or mode is a workspace switch, not a cold start.
The shell and whatever the user was doing stay put; only the gateway-bound view
is cleared and repopulated, and the previous context must not leak into the next
one. Reserve the full-screen boot/connecting experience for a genuinely unusable
backend.

There are three distinct switch shapes, and conflating them is the classic bug:

- A **connection/mode apply** (local ↔ remote ↔ cloud) is the soft re-home:
  shell mounted, gateway-bound stores explicitly wiped, then reconnect. Query
  invalidation alone cannot evict live session stores — wipe them.
- A **runtime home change** (switching the underlying `HERMES_HOME` profile) is
  a hard re-home: the window legitimately reloads and state resets by remount.
- A **live profile swap** in the same window activates another profile's socket
  while background profiles keep streaming; lists merge rather than wipe, and
  only an explicit user selection starts a fresh foreground draft.

Treating a soft switch as hard flickers the app; treating a hard one as soft
strands stale rows. After any swap, the active socket, active profile, and
connection atoms must agree, or REST and filesystem calls route to the wrong
backend.

## Cross everything as an observable ladder

Desktop lives at the seams: versions, profiles, local vs remote vs cloud,
partially installed runtimes, stale caches, older backends. The durable technique
for all of it is the same — an ordered ladder of candidates:

1. Precedence is written down, in one place, as data or a pure function.
2. A candidate is trusted only after it is validated at the right boundary.
   Existence is not proof; probe what you're about to rely on.
3. A failed *read* falls to the next rung; a failed *authoritative write*
   surfaces or rolls back rather than silently retargeting.
4. A missing capability and a transient failure are different: the first may
   enable a compatibility path or a disabled state; the second should retry.
5. Retries are bounded and end in a real recovery affordance — never an infinite
   spinner or a hot loop.
6. One resolver owns each policy so every caller gets the same answer. Scatter is
   how two call sites drift apart.

This is the shape of backend discovery, command/version fallbacks, connection and
auth resolution, workspace-cwd selection, capability detection, and preview
normalization alike. Learn the shape, not a snapshot of the current rungs.

Two auth-flavored corollaries worth naming because they are easy to get wrong:

- **One-time credentials are never reused.** An OAuth gateway connection mints a
  fresh WebSocket ticket on every dial; a mint failure means reauthentication,
  not "fall back to the cached URL." Only long-lived token/local auth may reuse
  a cached URL as a lower rung.
- **A connection test must exercise the leg you'll actually use.** An HTTP
  status probe passing while the WebSocket/auth leg fails is a false positive
  that ships as "it said connected but nothing works."

## Compatibility without carrying the past forever

Desktop and its runtime update on separate clocks, so a change can meet an older
backend. Keep those users working: preserve the current feature, keep the
fallback narrow and tied to an identified older runtime, and cover it with a
test. A fallback that quietly degrades the feature it's meant to protect is worse
than the crash it replaced.

## Keep the waist narrow, grow at the edges

The root contribution rubric governs here too. New capability should arrive at
the smallest surface that solves it: extend what exists, add a feature locally,
lean on an existing seam — before you invent a framework. The shell's internal
registries are composition seams, not a public plugin ABI; do not build a
universal extension system, a manifest, or a plugin adapter for a single
consumer. Design a shared contract only once more than one real consumer proves
its shape. "Plugin" means several unrelated things across Hermes — do not assume
one surface's extension model runs in another.

## Respect the person using it

Design and engineering meet at intent. The user's attention and context are
sacred:

- Never navigate, move focus, or open a surface because something *happened* in
  the background. Offer; don't hijack.
- The states around loading are distinct experiences — empty, loading,
  reconnecting, degraded/stale, and exhausted-recovery each deserve their own
  honest copy and their own way out.
- Keyboard ownership follows focus. The focused surface wins its keys; one
  cancel gesture does exactly one thing.
- Expensive, stateful surfaces (terminals, live tools) stay alive when hidden.
  Visibility is not lifecycle.

## Make it feel instant

Performance is a feature the user feels, especially in drag, resize, scroll,
typing, streaming, and terminals. The principles are timeless even as the code
changes: keep hot-path state local or narrowly derived; don't subscribe heavy
trees to per-frame updates; coalesce pointer work; avoid reading layout right
after writing style; and don't mount expensive content mid-gesture. Prove speed
against realistic content — a fast empty demo proves nothing about a long
transcript. If motion is masking latency, remove the motion, don't tune it.

## Testing as a habit of proof

Test the behavior that would actually break a user, not a snapshot of today's
data. Favor invariants over frozen values. Exercise the real path for anything
at a seam — resolver precedence and its failure rungs, identity and scope
boundaries, optimistic rollback and stale-response ordering, and both sides of a
local/remote adapter with its profile routing intact. Match how the suite is
actually run rather than inventing a command; when in doubt, read the scripts.

## The taste test before you hand off

- Does every piece of state live with its authority, at the narrowest scope?
- Would a background event ever steal the foreground or the user's focus?
- Does each resolver have one home, a validated ladder, and a bounded, recoverable
  end?
- Do local, remote, and profile routing still agree?
- Does async failure leave a usable UI and a way forward?
- Do hot interactions stay cheap under realistic load?
- Does the change pass the [`DESIGN.md`](./DESIGN.md) checklist and update all
  locales?

If any answer is "not sure," that's the part to go verify.

<!-- SESSION-START-CONTEXT:START -->
## Session-start context (bắt buộc mỗi session mới — CHỐNG PHÌNH CONTEXT)
- Khi session mới bắt đầu (vừa `/new`, resume, hoặc đổi máy): trước khi hỏi user hoặc tự làm gì, chạy đúng 4 bước có chọn lọc:
  1. Đọc file `AGENTS.md` này. Nếu có `HANDOFF.md`, CHỈ đọc phần `Current State / Blockers / Next Task` (nếu file >20KB thì không nạp toàn bộ lịch sử).
  2. Tìm trong `.hermes/plans/` (nếu có): CHỈ đọc **đúng 1 file `.md` mới nhất theo timestamp**. KHÔNG đọc toàn bộ thư mục plans.
  3. Kiểm tra git: `git status --short` + `git log --oneline -5`.
  4. Tổng hợp thành 1 báo cáo ngắn ("Task đang dở / bước kế tiếp / trạng thái git") rồi hỏi xác nhận TRƯỚC khi tiếp tục — CẤM tự đoán task và tự làm tiếp.
- Mục đích: chống phình context (không nạp hàng trăm KB startup), giữ mạch làm việc qua các lần /new và đổi máy.
<!-- SESSION-START-CONTEXT:END -->

## 13. PREFLIGHT SCHEDULE CHECK (Bắt buộc trước mọi batch chạy tay/live — user chốt 2026-08-18)
Trước khi chạy bất kỳ batch tác vụ nào trên farm (Reg TikTok, Hotmail login, Add mail khôi phục, Register Gmail, Upload video, Reconcile...):
1. **TỰ ĐỘNG KIỂM TRA LỊCH CRON NUÔI ACC:** Agent BẮT BUỘC tự động kiểm tra manifest nuôi acc (`D:\Taadaa\runtime\kibe\cron-state\manifests\<ngày>\active_manifest.json` qua skill `farm-schedule-preflight-check`) TRƯỚC KHI KHỞI CHẠY.
2. **KHOẢNG ĐỆM AN TOÀN ≥ 1 TIẾNG:** Chỉ được chọn và chạy trên các máy hoàn toàn rảnh trong suốt thời gian chạy batch và **cách ca nuôi acc kế tiếp tối thiểu 60 phút**.
3. **CẤM CHẠY TRÙNG MÁY:** Tuyệt đối không khởi chạy batch trên các máy đang trong ca nuôi hoặc sắp vào ca < 60 phút.
4. **USER CHỈ CẦN BẢO "CHẠY SCRIPT XXX" → AGENT TỰ CHECK LỊCH RỒI CHẠY:** User không cần phải nhắc "kiểm tra lịch", agent tự động check máy rảnh -> lọc danh sách máy an toàn -> chạy. Khi gặp lỗi máy nào -> dừng máy đó, chụp ảnh gửi user, chỉ lock khi user yêu cầu để debug sau.

## CLOSE-SESSION HARD TRIGGER
Các câu “chốt phiên”, “chốt phiên đi”, “đóng phiên”, “kết thúc phiên”, “xong phiên” là **lệnh thực thi closeout**. Các câu hỏi tiến độ chung như “xong chưa” hoặc “đã xong chưa” chỉ được trả lời trạng thái, không tự kích hoạt closeout. Bắt buộc load `session-close-protocol` và chạy: review độc lập `APPROVED` → kiểm tra branch/worktree/conflict → dọn đúng file tạm do session tạo → commit đúng scope → fetch/pull --rebase → push + xác minh remote SHA. Closeout không được tự động merge hoặc xoá mọi branch/worktree chỉ vì phát hiện trong `git worktree list`; chỉ merge/remove khi có evidence ownership session hiện tại, exact allowlist, clean/committed state, independent review `APPROVED`, và absorbed/superseded. Unknown, dirty, hoặc concurrent-owned phải preserve và báo `BLOCKED`. Thiếu bất kỳ gate nào chỉ được báo `BLOCKED_AT_<STEP>`; cấm nói “đã chốt/xong” bằng miệng.
