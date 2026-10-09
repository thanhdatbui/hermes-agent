# GPT Family Behavior Profiles (Terra vs Luna) & Gateway Concurrency Tuning

## 1. Gateway & Delegation Concurrency Controls in Hermes
When multiple Telegram chats/sessions run simultaneously, request bursts can overwhelm upstream pools:
- **`delegation.max_concurrent_children`** (currently `6` in `config.yaml`): Governs parallel subagents spawned within a single coordinator session via `delegate_task`.
- **`gateway.max_workers`** (in `config.yaml`): Governs the total concurrent worker threads in the Hermes messaging gateway processing incoming platform messages.
  - Default: `50` (permits massive session concurrency spikes of 12–17 sessions, generating up to 1.4M TPM into upstream pools).
  - Recommended tuning: Reduce gently from `50` to `40`. This smooths incoming peak load while maintaining ample headroom for 5–6 simultaneous group chats without causing queuing delays.

## 2. ChatGPT Web Pool (`chatgpt-web/gpt-5.6-sol-high` on :20129)
- **Role Boundary:**
  - **CANNOT be Worker or Coordinator:** ChatGPT Web pool accounts use browser session tokens without native OpenAI/Codex Function Calling (tool use). If assigned as an execution worker, the model will output explanatory text rather than executing `terminal`, `read_file`, or `patch` tools.
  - **IDEAL for Text-In -> Text-Out Tasks (Zero Quota Cost):**
    1. **Plan Auditor & T2 Planner:** Configured in `D:/Taadaa/tools/sol_planner.py` targeting `chatgpt-web/gpt-5.6-sol-high` across 94 web pool accounts.
    2. **Closeout Gatekeeper:** Configured in `D:/Taadaa/tools/closeout_gate.py` using combo `review` (Tier 0: `chatgpt-web-pool`).
- **Tiered Workflow 2.0 Invariant:** Routine $O(1)$ contracts are drafted directly by Gemini Coordinator in 3–5s. Sol Web Planner is trigger-gated (only called for sensitive guard/hook edits, >3 files, or 2 consecutive dispatch failures).

## 3. GPT Family Behavioral Profiles & Pitfalls (Codex Terra vs Luna)

| Dimension | **Codex Luna** (`gpt-5.6-luna-high`) | **Codex Terra** (`gpt-5.6-terra-high`) |
|---|---|---|
| **Core Strength** | Top-1 syntax and implementation accuracy. Senior code patterns (atomic file ops via `tempfile + os.replace`, monotonic watchdogs, SHA256 byte verification). | High architectural discipline, stronger system reasoning than Luna, no helpful-aggression scope creep. |
| **Pathology / Flaw** | **Helpful-Aggression:** Misinterprets advisory prose/reviewer remarks as mandatory TODOs. Expands scope to 5–7 files, causing `DIFF_TOO_LARGE` (>30KB). | **Senior Refactoring Itch & Latency:** Tendency to refactor surrounding code for elegance rather than minimal 1-line surgical fix (e.g. rewriting dict comprehensions). Prone to 90s hard timeouts on lock/concurrency reasoning. |
| **Quota Impact** | Codex Developer quota (moderate burn). | Codex Developer quota (expensive burn; heavy thinking token count). |
| **Strict Operational Invariant** | **NEVER allow Luna as Coordinator or Session Closer:** Will derail entire sessions during closeout. **ONLY use as T2 Worker in Sterile Cage** (`cage_gate.py`, budget $\le 30$ lines, 1 file, 1 focused test). | **NEVER use Terra as routine bulk worker:** High quota burn and 90s timeouts stall pipeline. Use as secondary reviewer/auditor or tie-breaker when Sol Web is unavailable. |
