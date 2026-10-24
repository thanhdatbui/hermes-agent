# Action Mandate & Zero-Deadlock Governance (Session Learnings 2026-10-24)

## 1. Foreground Timeout Clamp vs Worker Timeout (The 60s Illusion)
- **Root Cause:** Host terminal hook (`hooks/guard_broad_grep.py`) clamped all foreground commands to 60s (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`).
- **Consequence:** Subprocesses like `dispatch_worker.py` (which run Sol/Agy with internal 300s timeouts) were killed by the parent harness at 60s with Exit 124. The agent misattributed this as "worker timeout" and whined, while in reality the parent harness pulled the plug.
- **Fix:** Add a dedicated `LONG_RUNNING_ALLOWLIST` in `guard_broad_grep.py` allowing up to 360s for legitimate coordination runners (`dispatch_worker.py`, `closeout_gate.py`, `pytest`, `sol_worker.py`, `ag_cli.py`, `sol_repair.py`, `claude_worker.py`), matched with word boundaries `(?<![\w.-]){tool}(?![\w.-])`.

## 2. Windows cp1252 Stdout Crash Prevention
- **Root Cause:** On Windows, subprocess pipes default to system encoding (`cp1252`). When hooks print Vietnamese error messages or JSON payloads with diacritics to stdout, Python crashes silently with `UnicodeEncodeError`.
- **Fix:** In every Python hook, explicitly call `sys.stdout.reconfigure(encoding="utf-8")` before printing any output.

## 3. Bare-Word Trigger Collision & Self-Inflicted Advisor Spam
- **Root Cause:** `consult_advisor.py` had a bare-word regex `r"\b(advisor|sol review)\b"`. Any user message containing `"advisor"` (e.g. "cấm gọi advisor", "R t fix vụ spam advisor r sao session này vẫn cứ lải nhải v") returned `True`, triggering post-response auto-append hook (`ensure_dual_answer`) to query Sol and append `--- Advisor (Sol / review) ---` right under the complaint!
- **Fix:**
  1. `SUMMON_PATTERNS`: Require multi-word explicit action verbs: `r"\b(?:gọi|hỏi|nhờ|kêu)\s+(?:sol|advisor)\b"`, `r"\b(?:sol|advisor)\s+(?:thấy\s+sao|nghĩ\s+sao|review|lên\s+plan|cho\s+ý\s+kiến)\b"`. Bare word `advisor` alone is strictly forbidden.
  2. `EXCLUDE_PATTERNS`: Must evaluate first. Any message containing negation/complaint words (`tắt`, `dừng`, `cấm`, `đừng`, `không`, `spam`, `lải nhải`, `đéo`) combined with `advisor/sol` immediately returns `False`.

## 4. GuardEngine Multi-Rule Matching
- **Root Cause:** `GuardEngine._match_rule()` stopped at the first rule matching `(tool_class, op)`. In `rules.json`, both `case_162` and `case_161` matched `(code_edit, commit)`, so `case_161` was never evaluated.
- **Fix:** Switch to `_match_rules()` evaluating all matching rules in declaration order. Return `DENY` on the first failing predicate; return `ALLOW` only when 100% of matching rules pass.

## 5. Closeout Gate Target Pruning
- **Root Cause:** In `closeout_gate.py`, `targeted_candidate()` raised `ValueError: targets without working-tree changes` if any file in `--files` had no uncommitted diff, crashing the pipeline.
- **Fix:** Prune unchanged targets with `print("· Pruned unchanged targets: ...")` and continue evaluating the remaining changed targets. Only raise `ValueError` if zero targets have any changes.
