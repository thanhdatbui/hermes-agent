# Policy-refactor negative-probe matrix

Use this when reviewing changes that relax coordinator gates, add CLI allowlists, or replace universal planning with risk-based planning.

## Required negative probes

1. **Routine contract:** one ordinary file, absolute target, unique OLD_STRING, NEW_STRING, focused offline test → allow without a Sol plan.
2. **High-risk fail-closed:** guard/hook/policy/config/auth/schema/lock/concurrency or multi-file target without a valid review plan → block. Sol offline, remediation markers, `SOL_AUTOCALL_ATTEMPTED`, and textual fallback markers must not turn this into allow.
3. **CLI chaining:** `claude`, `opencode`, and `antigravity` are allowed only as complete, bounded commands. Probe `&&`, `;`, `||`, `|`, newline, redirects, `$()`, and backticks.
4. **Dangerous payloads:** probe chained `python -c`, `adb shell input tap/swipe/keyevent`, `git reset --hard`, `checkout .`, `restore .`, `clean -f`, and unauthorized push. Every case must block.
5. **Protected targets:** a maintenance CLI may inspect a protected path only through the approved bounded path; direct `write_file`/`patch`, or a chained command that reaches the path, must block.
6. **Closeout parser:** command-substitution and backtick nesting must be rejected even when the outer command begins with an allowlisted binary.
7. **Runtime parity:** run probes against the runtime-loaded module and separately verify deploy-template parity. Never accept a test that imports an untracked or different copy as production proof.
8. **Timeout state:** worker timeout must enter `INSPECT_REQUIRED`; artifact+focused-test evidence may recover to DONE, while missing artifact, failed verification, scope breach, or safety violation becomes BLOCKED.

## Reviewer output contract

Require exact changed absolute paths, actual test output, probe results, runtime/deploy path identity, and a first-line `VERDICT: APPROVED` or `VERDICT: REJECTED`. “All tests pass” alone is not an approval.