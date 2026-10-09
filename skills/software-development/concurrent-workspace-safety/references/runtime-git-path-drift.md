# Runtime path vs Git path drift

## Incident pattern
A live Hermes plugin was edited under the user runtime directory while the user expected the change to appear in a Taadaa Git repository. The runtime file compiled and its focused tests passed, but Git inspection of the assumed repository did not show the change. The missing link was not a test failure; it was an unverified source-of-truth relationship.

## Required evidence matrix

| Evidence | Question | Minimum proof |
|---|---|---|
| implemented_path | Which bytes changed? | Exact absolute path, diff/hash, timestamp |
| tracked_path | Which Git path should carry them? | `git rev-parse --show-toplevel`, `git ls-files`, scoped status/diff |
| runtime_loading_path | Which path does Hermes load? | Loader/config/import path or runtime manifest, plus source/hash comparison |
| deployment_path | Is there a copy/sync step? | Exact script/config and a dry, read-only inspection of its direction |

Never collapse these into one claim such as “the tool is on Git”.

## Single-controller simplification

If one Windows host is the only controller, a multi-host deployment template may be unnecessary, but this does not automatically justify a junction. First choose the desired canonical path:

1. Git-managed path loaded directly by Hermes, or
2. Runtime path that is itself Git-managed, or
3. A deliberately maintained generated/deployment copy with a verified one-way sync.

Avoid two writable copies. If AppData must remain the loader path, a junction can be considered only after verifying the target exists, the destination is not already a junction, no process owns the plugin, and a rollback copy/hash is available. A junction changes filesystem topology and requires explicit user-authorized migration scope.

## Verification and reporting

Before any write: snapshot scoped status, hashes, and current loader path. After any write: verify the exact changed path, Git tracking state, runtime import/load path, EOL preservation, compile/import, and focused tests. Report separate fields:

- `implemented_path`
- `tracked_path`
- `runtime_loading_path`
- `source_of_truth`
- `verification`
- `rollback`

If the runtime and repository diverge, classify it as `SOURCE_OF_TRUTH_DRIFT`; do not claim migration completion from a passing test alone.
