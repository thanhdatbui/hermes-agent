# Claude CLI Advisor/Reviewer vs Coordinator Builder Workflow (2026-10-18)

## Context & Operator Mandate
In Taadaa Farm operations, locking rules via soft prompts (System Prompt, AGENTS.md, or Hermes Memory) is strictly forbidden. Prompts suffer from model drift, hallucination, and probabilistic violation. Every operational safety rule must be mechanically enforced as a **PreToolUse Guard Hook / Gate**.

Furthermore, Operator explicitly clarified the division of labor between AI models:
- **Claude Sonnet 5.5 CLI is the Architect / Senior Reviewer**: Consulted for high-level security design, adversarial edge-case analysis, and code review verdicts (`VERDICT: APPROVED` or `REJECTED`). Claude Sonnet CLI does NOT write large codebases or test suites, preserving its valuable 5-hour quota.
- **Hermes Coordinator / Worker (Haiku 5.5 / Coordinator) is the Builder**: Directly writes the Python implementation code and unit test suites, iterating based on Reviewer feedback.

---

## 4-Step Adversarial Implementation Loop

```
1. Design Consultation (Claude Sonnet 5.5 --role planner)
   └─> Get fail-closed architecture, allowlist regex patterns, edge-case checklist.

2. Builder Implementation (Coordinator / Haiku Worker)
   └─> Write hook code in D:/Taadaa/tools/guard_<name>.py.
   └─> Write comprehensive unit test suite in D:/Taadaa/tools/tests/test_guard_<name>.py.
   └─> Run pytest locally to ensure 100% test pass.

3. Independent Review (Claude Sonnet 5.5 --role reviewer)
   └─> Call: python D:/Taadaa/tools/claude_worker.py --role reviewer --max-turns 4 "<prompt>"
   └─> Strict requirement: "Answer directly without running bash commands" (prevents hang).
   └─> Reviewer traces logic and returns VERDICT: APPROVED or REJECTED with specific P1/P2/P3 findings.

4. Remediation & Repeat
   └─> If REJECTED: Worker remediates all P1/P2 findings and adds regression tests.
   └─> Repeat Steps 2-3 until VERDICT: APPROVED is achieved.
```

---

## Case Study: `guard_android_proxy.py` (5-Round Evolution)

The `guard_android_proxy.py` hook mechanically blocks setting domain names/hostnames or public WAN IPs as the Android `http_proxy`, enforcing LAN RFC1918 IPs (`192.168.110.2`) to prevent Hairpin NAT drops.

Through 5 adversarial review rounds with Claude Sonnet 5.5 Reviewer, the test suite expanded from 6 tests to 48 tests, uncovering critical real-world bypasses:

1. **Round 1 (REJECTED):**
   - *Bypass:* Chained commands via `&` evaluated only the first match.
   - *False Positive:* Legitimate `settings get` and `settings delete` were blocked because no proxy value followed.
   - *False Positive:* Device serial variables (`adb -s $SERIAL ...`) were rejected because dynamic variable regex checked the whole line.
   - *Test Flaw:* Test helper defaulted to `allow` on empty stdout without checking `returncode == 0`.

2. **Round 2 (REJECTED):**
   - *Bypass:* Splitting commands by `;&|\n` stripped the `adb shell` context from later sub-commands, allowing `adb shell "echo hi; export http_proxy=evil.com"`.
   - *Bypass:* Quote concatenation (`"192.168.110.2".evil.com`) fooled regex into seeing a valid IP while shell concatenated it into a domain.
   - *Bypass:* Fail-open shortcut on `get`/`delete` allowed subshells like `settings get ... $(settings put ... http_proxy evil.com)`.
   - *Windows Encoding:* `json.load(sys.stdin)` used locale cp1252, failing on non-ASCII bytes and exiting 0 (fail-open). Fixed with `sys.stdin.buffer.read().decode('utf-8-sig', errors='replace')`.

3. **Round 3 (REJECTED):**
   - *Bypass:* `WRAPPER_CLOSE_QUOTE_RE = ([^"']*)["']` matched lone quote tokens (`"`) as empty string `""`, treating `" evil.com:1"` as an allowed proxy clear. Fixed by changing `*` to `+`.

4. **Round 4 (REJECTED):**
   - *False Positive:* Nested quotes like `adb shell "settings put global http_proxy '192.168.110.2:20033'"` were flagged as malformed.
   - *False Positive:* Read-only commands (`adb shell dumpsys settings | grep http_proxy`) were blocked.
   - *Scope Lock:* Documented deliberate key-splitting obfuscation (`http_"proxy"`) as out of scope for agent error prevention.

5. **Round 5 (APPROVED):**
   - Verified 48/48 unit tests passing across all edge cases.

---

## Closeout Gate & Pre-Push Hook Scope Alignment

When closing out a session with `closeout_gate.py --push`:
1. The pre-push hook (`.git/hooks/pre-push`) inspects `git diff-tree --no-commit-id --name-only -r HEAD` (the single HEAD commit).
2. If intermediate commits were created during the review rounds touching different files, `HEAD` only sees the files in the last commit, causing an `audit_binding.scope != current_scope` mismatch rejection.
3. **Mandatory Invariant**: Always squash intermediate review commits into a **single commit** spanning the complete file scope before calling `closeout_gate.py`:
   ```bash
   git reset --soft origin/main
   git commit -m "feat(guard): add guard_android_proxy hook with 48 unit tests"
   python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/tools" --base origin/main --files guard_android_proxy.py tests/test_guard_android_proxy.py --push
   ```
This guarantees 100% scope alignment between the commit and `gate_audit.jsonl`, enabling clean auto-push.
