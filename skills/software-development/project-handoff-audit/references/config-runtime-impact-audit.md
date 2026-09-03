# Configuration / Runtime Impact Audit Reference

## Purpose

Use this reference for a read-only audit of an agent's configuration changes and their possible effect on sibling automation repositories.

## Evidence checklist

1. Identify the reported artifact and classify it as recommendation, applied configuration, runtime output, or historical log.
2. Inspect persistent configuration stores directly:
   - Windows user/machine environment via `winreg` or an equivalent read-only query.
   - Do not rely only on `env` from the current shell; it may be stale or omit registry values.
3. Inspect the live daemon/process:
   - executable path;
   - command line and flags;
   - PID and owner only as needed;
   - current read-only health/version/list command when safe.
4. Inspect repository state:
   - tracked diff and status;
   - untracked files and recent files;
   - local configuration helpers and test files;
   - generated logs/artifacts without editing them.
5. Trace propagation:
   - `os.environ.update(...)` or equivalent;
   - child `env=` passed to `Popen`/`subprocess`;
   - explicit executable resolver/path pinning;
   - imports from shared core versus consumer-local helpers.
6. Search each named consumer and shared core for the exact variables, helper names, executable path, and environment propagation.
7. Run only focused, non-live verification: unit/config tests, executable version, daemon status, or device listing if the user authorized read-only inspection. Do not run workflows or mutate device/workbook state.

## Classification table

| Layer | Proof | Report as |
|---|---|---|
| Persistent OS config | registry/user-machine store value | Global impact |
| Current daemon | live PID, executable, command line | Runtime status |
| Consumer-local helper | file path plus import/call and dirty/untracked status | Repo-local impact |
| Shared package/core | exact reference or diff in core | Shared-core impact |
| Report/log only | file contents without applied-state evidence | Recommendation/intent only |

## Common pitfalls

- A report saying "compatible" is not a compatibility proof.
- A value in the current shell is not proof of a persistent Windows user variable, and an unset current shell is not enough to prove the registry is unset.
- A local helper that sets `os.environ` can affect all child processes of one runner without affecting sibling repositories.
- A daemon using a standard port does not prove that a proposed environment variable was applied; inspect the actual command line and persistent store.
- Search paths must be verified before concluding that a repository has no references. On Windows Git Bash, `D:\Taadaa` may be represented as `/d/Taadaa`, but tool path adapters can differ; use a native absolute path or a shell probe when a search tool reports an I/O path error.
- Preserve unrelated dirty state. Do not revert or clean untracked configuration files during an audit.
- Keep device serials, account identifiers, workbook fields, credentials, and tokens redacted in the final report.

## Minimal redacted result shape

```text
global impact: <none / confirmed / unknown> + persistent-store evidence
repo-local impact: <repo and exact helper/entrypoints>
shared-core impact: <none / confirmed / unknown>
live runtime status: <daemon executable, flags, health result>
verification: <focused checks and results>
mutations: none (read-only audit)
```
