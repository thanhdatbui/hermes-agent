# In-Loop Advisor Hardening and Clean Target Scope in Closeout

This reference documents two recurring findings and failure modes encountered during Closeout Gate review loops involving dynamic advisors and scoped diff extraction.

## 1. Clean Target Scope Trap (`targets without working-tree changes`)

### Failure Signature
```text
STEP 2: EXTRACT CANDIDATE DIFF
✘ Failed to extract diff: targets without working-tree changes: ['toolsets.py']
```

### Cause
When running `closeout_gate.py --repo <repo> --files <file1> <file2> ...`, every file listed in `--files` must have a non-empty candidate diff against the base ref (or working tree). If a file's edits were reverted or clean in the working tree, the gate fails immediately at candidate diff extraction.

### Prevention & Verification
Before invoking `closeout_gate.py`, verify that all candidate paths actually appear with non-empty diff in:
```bash
git status --short -- <target_files>
```
Exclude any file that has zero diff or whose hash matches HEAD.

---

## 2. Dynamic / In-Loop Advisor Safety & Reviewer Rubric Requirements

When adding an advisor model or secondary in-loop consultation seam (e.g. consulting a planning/review model like Sol Web via a local proxy), independent reviewers (Sol Auditor / Codex Terra) inspect five strict safety criteria:

### A. Egress Hardening (Fail-Closed Loopback Only & Redirect-Safe)
- Never allow unvalidated HTTP endpoints from environment variables (`HERMES_ADVISOR_ENDPOINT`).
- Validate that the target endpoint is strictly loopback (`localhost`, `127.0.0.1`, `::1`). If non-loopback, fail closed with `status="unavailable"` and `error="Endpoint not loopback"`.
- **Redirect SSRF Protection**: `urllib.request.urlopen` by default automatically follows HTTP 301/302 redirects. A local service could redirect to an external host, leaking payloads. Always install a custom `HTTPRedirectHandler` (e.g. `_LoopbackRedirectHandler`) that inspects `newurl` on every hop and raises `HTTPError` if the target is not loopback.
- **Hard Final Serialized Payload Limit**: Do not just trim selected fields. Verify the total serialized request payload (`len(json.dumps(payload).encode('utf-8')) <= 16000`). If still oversized after iterative shrinking, abort fail-closed with `unavailable` before calling the network.

### B. Tool Discovery & Registry Isolation
- If the advisor tool is registered in `tools.registry`, it must have `check_fn = lambda: False`.
- This ensures LLMs never discover it in their standard tool list, preventing bypass of the one-call turn cap or unintended invocation during ordinary tool loops.
- Remove the tool name from core toolsets (`_HERMES_CORE_TOOLS`).
- Add focused offline tests proving: `entry.check_fn() is False`, but calling `entry.handler(args)` directly remains fully functional.

### C. Output Policy Filter & Fail-Open Guarantee
- Never append raw advisor text directly to the user response.
- Pass advisor output through a strict policy filter:
  - Reject malformed or non-`ok` status.
  - Enforce a structured allowlist schema: advice must be a dictionary with strictly allowed safe keys (`recommendation`, `reasoning`, `confidence`, `next_steps`, `plan`).
  - Normalize Unicode and strip zero-width/control characters before safety scanning to prevent obfuscation bypasses.
  - Reject command-like operational content (e.g. `adb`, `curl`, `powershell`, `rm -rf`, `delete`, `tap`, `swipe`).
  - If dangerous instructions or schema violations are detected, reject with `(None, "policy_blocked")`.
- **Fail-Open Invariant:** On any advisor failure (timeout, network error, policy block, malformed JSON), always return the primary model's answer untouched with a clean fallback notice (`Advisor: unavailable (primary answer shown)`).

### D. Bounded Turn Deadline
- Reduce advisor consultation timeout (e.g. `DEFAULT_TIMEOUT = 15s`) so turn completion is never delayed excessively.
- Track real `elapsed_ms`, `reason` (`ok`, `policy_blocked`, `malformed`, `unavailable`), and `request_id` in structured telemetry.

### E. Redaction & Regex Hygiene
- **Quoted JSON Secret Redaction**: Cover both standard `key: value` and quoted JSON strings `{"apiKey": "secret"}` with patterns like `(?i)(["']?)(?:apikey|...)\1\s*:\s*(["'])(.*?)\2`.
- In Vietnamese advice classifiers, beware of over-escaping word boundaries in Python raw f-strings:
  - Correct: `rf"(?<!\w){re.escape(phrase)}(?!\w)"`
  - Wrong: `rf"(?<!\\w){re.escape(phrase)}(?!\\w)"` (matches embedded words like `tư vấnđi` or `nênđi` because `\w` is treated as literal backslash followed by 'w').
