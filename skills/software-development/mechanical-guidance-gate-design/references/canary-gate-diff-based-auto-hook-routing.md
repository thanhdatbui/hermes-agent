# Canary Gate: Diff-Based Auto Hook Routing vs. LLM Memory Trap

## 1. Problem Statement: The Fallacy of LLM Memory for Process Routing
- When an agent completes a code fix on a complex workflow or monolith (e.g., adding auto-login recovery to `_run_upload_hook` in `multi_machine_feed_session.py`), testing the change requires specific runner flags (e.g., `--allow-upload-hook`).
- **The Failure Mode:** Relying on LLM Memory or prompt directives to remember to pass the flag fails consistently. The agent runs the default generic canary (e.g. 2 swipes of feed), sees exit code 0, and reports a false-positive success without ever executing the modified hook code.
- **The Anti-Pattern:** Adding a directive to persistent memory (`MEMORY`) creates false reassurance. The user explicitly stated: *"đéo dùng memory nhé, dùng memory mày đéo bh tuân thủ. k thiết kế trong script ddc à, có gate canary k?"*.

## 2. Mechanical Gate Architecture
Instead of relying on prompt compliance, enforce hook routing mechanically inside the test runner (`canary_runner.py`):

1. **Git Diff Inspection (`canary_plan.py`):**
   The runner evaluates the git diff (`git diff HEAD~1` or uncommitted changes) against a declarative matrix (`canary_matrix.json`).
2. **Matrix Rules (`canary_matrix.json`):**
   Path globs directly map changed files to required canary hooks:
   ```json
   {
     "id": "upload-hook",
     "path_globs": ["*upload*", "**/flows/*upload*", "**/flows/multi_machine_feed_session*"],
     "hook": "upload",
     "scope": "single"
   }
   ```
3. **Deterministic Flag Injection (`canary_runner.py`):**
   If `--hook` is omitted by the operator/agent, `canary_runner.py` queries `canary_plan.build_canary_plan()`:
   - Detects the required hook from the diff requirements.
   - Automatically injects the matching flags (e.g. `--allow-upload-hook`) into the execution command.
   - Logs `[CANARY_GATE] Auto-detected hook 'upload' from git diff requirements`.

## 3. Core Rule of Mechanical Guidance
Never leave workflow compliance to LLM memory when a mechanical parser can inspect git state and enforce the exact parameters deterministically.
