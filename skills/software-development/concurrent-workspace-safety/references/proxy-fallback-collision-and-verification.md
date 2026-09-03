# Proxy fallback collision and verification

## Incident pattern

A router had three intended resilience layers:

```text
account-assigned proxy → provider proxy pool → direct egress
```

The live request failed on an account proxy with a Fast-Fail 502 and then returned `ALL_TARGETS_SKIPPED`. Source inspection showed two separate control paths:

- proxy resolution returned the first account assignment immediately;
- direct fallback lived inside the egress helper and did not select provider-pool candidates.

A successful unit test for proxy-pool rotation proved only that an alive pool member could be resolved. It did not prove that a request which failed after TCP connection (such as an HTTP 502) retried through the next pool member.

## Acceptance matrix

| Seam | Required evidence | What it does not prove |
|---|---|---|
| Registry/pool read | dead account proxy is replaced by an alive provider-pool member | request-level retry after an HTTP 502 |
| Egress fast-fail | unreachable proxy produces a tagged `proxy_unreachable` error | provider-pool selection unless a candidate list is passed |
| Request dispatch | account → pool member(s) → direct order is observed | unrelated provider/account health behavior |
| Negative classification | upstream 401/403/429 stays an upstream/account error | transport failures are correctly tagged |
| Runtime | process loaded the changed source after restart/reload and log shows pool/direct transition | unit tests alone |

## Safe workflow

1. Record baseline `git status`, exact scoped paths, mtimes, current commit, and focused test command.
2. Read the resolver and the actual dispatch caller. Trace whether a pool is only read or actually passed to the request executor.
3. Write a minimal request-level regression test before production code. It must inject deterministic candidates and assert call order.
4. Run RED and confirm the failure is the missing fallback, not a collection/import/setup error.
5. Implement one seam at a time. Preserve explicit connection-level proxy-off behavior and do not mutate DB assignments merely to make the test pass.
6. Add negative tests proving ordinary upstream 401/403/429 responses do not trigger proxy rotation.
7. Run focused tests, typecheck/lint applicable to changed files, and `git diff --check`.
8. Re-stat and re-read scoped files after tests. A concurrent writer can change the tree during a long test run; green output may describe superseded bytes.
9. If a patch reports the file changed since last read, stop edits. Do not restore/reset/replay the patch. Preserve the current diff and report `SCOPE_CONFLICT` or continue only after ownership reconciliation.
10. Do not claim 3-layer fallback from a resolver-only test. Report the exact verified seam and remaining runtime gap.

## Reporting template

- **Implemented:** exact source path and seam changed.
- **Verified:** exact test command and pass/fail count.
- **Not proved:** request-level fallback, runtime reload, or live canary if not exercised.
- **Conflict:** baseline/final mtimes and foreign dirty paths; distinguish foreign changes from agent-caused scope drift.
