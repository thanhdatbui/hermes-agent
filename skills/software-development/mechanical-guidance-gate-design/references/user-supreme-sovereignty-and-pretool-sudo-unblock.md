# User Supreme Sovereignty & Pre-Tool Sudo Unblock Protocol (Hướng B)

## 1. Context & The Hierarchy Inversion Anti-Pattern
When designing mechanical enforcement gates (pre-tool hooks, runtime fences, and self-protection guards), system designers often fall into the **Hierarchy Inversion Anti-Pattern**:
- Natural & Lawful Authority: `Root Owner (User) > Coordinator > Autonomous Worker Subagents`.
- Anti-Pattern Failure: Pre-tool guards enforce unconditional blocks (e.g. `⛔ GUARD SELF-PROTECTION / GUARD SOURCE BLACKLISTED` or hardcoded `FORBIDDEN_PATTERNS = ('hooks/', 'guard_')`).
- Result: When the Root Owner explicitly issues an emergency command (e.g. `"tao cho phép"`, `"làm luôn"`, `"force"`, `"bypass"`), the agent is paralyzed and replies "I cannot touch this directory, you must run it yourself in host terminal".
- User Verdict: "Đáng lẽ quyền của user phải bypass mọi hệ thống, tự nhiên chính user bị chặn là phản mẫu kiến trúc vô lý."

---

## 2. Unix Sudo Philosophy Applied to AI Agents
1. **Root Owner Exemption via Cryptographic Proof**:
   - Safety gates exist exclusively to prevent **Autonomous AI Runaway** (AI tự tung tự tác sửa rào chắn của chính nó khi không có lệnh).
   - Safety gates MUST NOT disarm or deadlock the Root Owner.
   - When explicit user trigger keywords are matched (`ALLOWED_KEYWORDS = ("tao cho phép", "làm luôn", "force", "bypass", ...)`), `user_sudo.py` mints a cryptographically signed HMAC-SHA256 grant.
2. **Pre-Tool Decision Gate Verification**:
   - Pre-tool inspection hooks MUST consult `user_sudo.verify_and_consume_grant(session_id, target_path, diff_lines)` before rejecting protected paths.
   - If a valid, non-expired, single-use grant exists:
     - The guard yields (`action: allow`), burns the nonce immediately (preventing AI reuse), and logs `USER_SUDO_OVERRIDE_EXECUTED`.
   - If no grant exists (autonomous AI attempt):
     - The guard enforces 100% fail-closed block.

---

## 3. Hard Safeguards under Sudo (Bounded O(1) Ceilings)
Even with User Sudo enabled, mechanical boundaries are maintained to prevent catastrophic corruption:
1. **O(1) Diff Cap**: Modifications must remain $\le 30$ lines of diff (`diff_lines <= 30`).
2. **Single-Use Nonce**: A grant is burned the instant it is verified; an agent cannot reuse the grant for subsequent unprompted edits.
3. **Canary Test & Auto-Rollback**: Every sudo modification must be verified by a focused test (< 30s). If the test fails, the agent MUST immediately execute `git checkout -- <target_file>` to restore clean state.
4. **Absolute Exclusion Zone**: Secrets, credentials, `.env`, and live SQLite account databases remain permanently barred from agent writes even under sudo.

---

## 4. Churn Metric Discipline (Số Lượt Loay Hoay)
When evaluating guard effectiveness in Watchdogs:
1. **0-Turn Auto-Rewire**:
   - The hook intercepts and silently rewrites invalid parameters (e.g. budget auto-clamp, foreground timeout auto-clamp).
   - Classified as `REWIRED` / `PASS`, NEVER as a Gate FAIL.
2. **1-Turn Guided Recovery**:
   - The hook blocks and provides actionable copy-paste command (`required_action.command`). The agent succeeds on turn 2.
   - Classified as `GUIDED_PASS`.
3. **Churn Friction ($\ge 2$ turns)**:
   - The agent struggles 2–5 turns on the same rule.
   - Classified as `CHURN_FRICTION`. Every rule averaging $> 2$ turns of churn is a mandatory candidate for mechanical Auto-Rewire (eliminating passive whining text blocks).
