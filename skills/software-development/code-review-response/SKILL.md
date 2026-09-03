---
name: code-review-response
description: Respond to code review findings (especially critical/P0 issues). Implement fixes, verify with tests, and ensure no regressions.
triggers:
  - code review feedback
  - P0 critical issues
  - review findings
  - Claude review
  - fixing review comments
  - fix re-review
  - verify fixes applied
  - re-review findings
  - verify criteria
  - verification review
  - check requirements
  - compliance review
---

# Code Review Response

Systematic approach to fixing critical issues identified in code review.

## When to Use

- Received code review with P0/critical issues
- Need to implement reviewer-suggested fixes
- Must verify fixes don't introduce regressions

## Severity-Based Triage

Review findings come in severity tiers. Handle in strict priority order:

| Tier | Label | Action |
|------|-------|--------|
| 🔴 Critical | Blocking, security, data loss, TODO stubs | Implement immediately |
| 🟠 High | Correctness, major API misuse, private API access | Fix after critical, before medium |
| 🟡 Medium | Style, dead code, minor patterns, doc/import hygiene | Auto-fix in batch after everything else |

For each tier, read all findings first, then batch independent fixes across files.

## Workflow

### 1. Read All Findings First
Before touching code, read ALL review findings completely. Understand:
- What files are affected
- What the issues are (type mismatches, race conditions, missing logic, TODO stubs, private API access, styling)
- Severity and dependencies between fixes
- Whether any findings affect the same file (plan conflicts)

### 1b. Read Each Affected File Completely
- Use `read_file` to get full file contents (not just error-line snippets)
- If `read_file` truncates (shows offset/limit pagination), continue with `offset=` until you have the complete file
- **Only then** start editing — patching a partial view risks corrupting surrounding lines
- Understand the full method/class/module before making targeted changes
- Pay attention to the project's language convention (code may mix Vietnamese, English, Chinese — match existing style)

### 2. Batch Independent Changes Across Files
- Group fixes by file — all fixes to the same file can be done in sequence
- **Independent fixes across different files** can be patched in parallel (one turn)
- Dependent fixes (where fix A changes a signature that fix B must match) MUST be serialized
- After each batch, verify: `python -c "from project.module import Symbol"` (or `python -c "import package"`)

### 3. Fix Issues Systematically
For each issue:
- Read the affected file completely
- Understand the context and surrounding code
- Implement the minimal fix that addresses the specific issue
- Match existing code style and conventions
- Do NOT refactor unrelated code

### 4. Verify Each Fix
After fixing each issue (or group of related issues):
- Re-read the changed files if another agent/external writer may have touched them since your last read. Never patch from stale/partial content.
- Run the repository's canonical suite, using the project's import path explicitly when needed (for example `PYTHONPATH=scripts python -m pytest tests/`).
- If the suite is unavailable, stale, or does not cover the finding, create focused ad-hoc verification with an OS-safe temporary path. On Windows, use `tempfile`/`TemporaryDirectory` and a `hermes-verify-` prefix under the user's Temp directory; do not hand-build `/tmp` paths. Run it, assert the exact behavior, and remove it when possible.
- Distinguish evidence labels precisely: `pytest: N passed` is suite evidence; `ad-hoc verification passed` is targeted evidence only. Never call a stale or unrelated prior run "fresh passing verification".
- If the verifier repeats an `unverified` warning after a suite run, satisfy it with a new focused temp-script run and report that result explicitly as ad-hoc evidence; do not relabel the focused run as a fresh full-suite result.
- Verify both: (a) existing tests still pass, (b) each changed behavior works, without live device/upload actions when the user forbids them.

### 5. Report Results Clearly
Summarize:
- What was fixed (one line per issue)
- Files modified
- Verification evidence (test counts, specific behavioral tests)
- Any issues encountered

## Common P0 Issues and Fixes

### Type Mismatches
**Problem**: Function expects type A but receives type B
**Fix**: Update type annotations to accept the actual usage
```python
# Before: text: Optional[str]
# After: text: Union[str, List[str], None]
```

### Missing Retry Logic
**Problem**: Comments say "TODO: implement retry" but no retry exists
**Fix**: Implement retry wrapper with checkpoint/resume
```python
def execute(self, context):
    for attempt in range(self.retry_limit):
        if attempt > 0:
            self._load_checkpoint()  # Resume from last state
        result = self._run_states()
        if result:
            return True
        # Reset for next attempt
    return False
```

### Race Conditions
**Problem**: Check-then-write pattern allows race
**Fix**: Use atomic file operations
```python
# Non-atomic (BAD):
if not file.exists():
    write_file()

# Atomic (GOOD):
fd = os.open(file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
with os.fdopen(fd, 'w') as f:
    f.write(data)
```

### TODO Stubs in Critical Path
**Problem**: Critical workflow handlers are empty TODO stubs (`return True` with no real logic)
**Fix**: Implement real automation matching the surrounding pattern:
```python
# Before:
def handle_video_pick(self) -> bool:
    logger.info("Will implement later")
    return True

# After:
def handle_video_pick(self) -> bool:
    """Pick video from gallery — multi-strategy fallback."""
    # 1. Try resource-id selectors first
    # 2. Fall back to text-based matching
    # 3. Fall back to coordinate tap
    # Each step dumps UI and searches for expected element
    for strategy in [selector_tap, text_tap, coordinate_tap]:
        if strategy():
            return True
    return False
```

### Multi-Strategy Fallback Chains (Brittle Systems)
**Problem**: A single approach (e.g. `adb pull -`) will fail on some device/OS versions
**Fix**: Implement a fallback chain — try each strategy, collect errors, raise with all messages:
```python
errors = []
# Strategy 1: primary approach
result = method_a()
if result.ok:
    return result
errors.append(f"method_a failed: {result.stderr}")

# Strategy 2: fallback
result = method_b()
if result.ok:
    return result
errors.append(f"method_b failed: {result.stderr}")

raise AllFailedError(f"All strategies failed: {'; '.join(errors)}")
```

### Negative Exclusions on Multi-Locale Surfaces (FYP vs Profile)
**Problem**: Global negative exclusion on terms like `"following"` / `"follower"` rejects valid FYP overlays on English UI (where top header tabs are "Following" and "For You").
**Fix**: Scope negative exclusions to composite profile/login signals (`"edit profile"`, `"profile views"`, `"add bio"`, `"xác minh"`, `"login"`), never bare words that appear on normal feed surfaces.

### Fail-Closed OCR Fallback and Bounded Polling Dismissers
**Problem**: OCR fallback triggers on arbitrary non-app screens (e.g. GMS dialogs/system UI); dismissers assume swipe/click succeeded without verifying disappearance.
**Fix**:
1. Require verified package context before accepting OCR text.
2. In gesture/popup dismissers, scale coordinates dynamically (`wm size` / `window_size()`) and perform bounded polling via `dump_hierarchy()` to verify that the overlay actually closed; if recapture fails or the overlay lingers, return `dismissed=False`.

### Uniform Result Type Contract in Flow Handlers
**Problem**: Inconsistent return types across error branches (e.g. returning `CalibrationResult` in an exception branch while caller/normal path expects `NavigationResult`).
**Fix**: Enforce uniform dataclass/contract return types across all success, error, and exception branches.

### Method-Body Imports (Code Smell)
**Problem**: `import X` inside a method body (lazy-import that doesn't save meaningful startup time)
**Fix**: Move to top-level imports:
```python
# Before:
class Foo:
    def bar(self):
        import openpyxl  # ← lazy import, no justification
        wb = openpyxl.load_workbook(...)

# After:
import openpyxl  # top-level

class Foo:
    def bar(self):
        wb = openpyxl.load_workbook(...)
```
**Exceptions**: Keep lazy imports for heavyweight GUI/ML libraries (torch, tkinter) or circular-dependency breakers — comment the reason.

### Dead Code
**Problem**: Defined dict/list/constant that is never referenced anywhere
**Fix**: Remove it. If it documents a schema, move to a docstring or a `references/` file.
```python
# Before (never used):
COLUMN_MAP = {"A": "Name", "B": "Age", ...}

# After: removed. The xlsx reader parses headers dynamically.
```

### Private Attribute Access
**Problem**: External code reads `obj._private_attr` (e.g. `config._data.get(...)`)
**Fix**: Add a public property to the class, update all call sites:
```python
# In config.py:
@property
def video_source_root(self) -> Path:
    raw = self._data.get("video_source_root")
    return Path(raw) if raw else self.media_source_root

# In consumer (before):
path = config._data.get("video_source_root", fallback)
# After:
path = config.video_source_root
```

### Silent Error Swallowing
**Problem**: `except Exception: ... return True` — handler claims success even when it crashed
**Fix**: Log the error, detect known edge cases from state, and return False to trigger retry:
```python
try:
    risky_operation()
except Exception as e:
    logger.warning(f"Operation failed: {e}")
    # Check UI for known edge cases
    xml = dump_ui()
    if "captcha" in xml.lower():
        context.is_captcha = True
    return False  # Let state machine handle retry/escalation
```

### Computed-But-Never-Used Variables (Dead Code Variant)
**Problem**: A variable is assigned (e.g. `escaped = caption.replace(...)`) but the next line uses the original value (`caption`) instead of the computed one. The variable is dead.

**Fix**: Remove the unused assignment, or if the intent was to use the escaped version, fix the call site to reference the computed variable:
```python
# Before (dead code):
escaped = caption.replace(" ", "\\ ").replace("'", "\\'")
result = adapter._adb.shell(["input", "text", caption], ...)  # ← uses raw caption

# Fix option 1 (remove dead code):
result = adapter._adb.shell(["input", "text", caption], ...)

# Fix option 2 (use the computed value):
escaped = caption.replace(" ", "\\ ").replace("'", "\\'")
result = adapter._adb.shell(["input", "text", escaped], ...)
```
**Detection pattern**: Scan for `var = expr(...)` followed by a `var2 = ...` or method call that references the original source variable instead of `var`.

## 6. Criteria-Based Verification Review

When the user gives explicit behavioral/design criteria to verify — e.g. "check that A runs before B, if A fails then C, if C fails then D with message E" — produce a structured verification table. This differs from quality-focused review (checking for bugs, style, security) and from re-review (checking another agent's fixes). It is a **compliance review** against stated requirements.

### When to Use

- User specifies exact behavioral criteria: "verify X does Y, Z must not happen, if W then Q"
- User lists specific methods to inspect and specific flows to trace
- A design doc or issue describes expected behavior and you need to confirm the code matches
- Reviewing fallback chains, escalation paths, state machines — where behavior matters more than style
- User says "review code" but provides a verification checklist, not a diff

### User-Preference: "Không hỏi user" (Don't Ask)

When the user provides explicit, self-contained criteria and ends with an instruction like "Không hỏi user" (don't ask the user), **execute the entire review without asking any clarifying questions**. The criteria are the spec — interpret them literally, trace each one, deliver the verdict. If a criterion is ambiguous, make the most conservative interpretation (assume the worst case that the reviewer intended to catch). Do not seek clarification unless a criterion is truly impossible to evaluate without additional context (e.g. a referenced file doesn't exist, or a method name was misspelled and no match exists in the codebase).

### Workflow

1. **Parse the user's criteria first** — read all criteria before any file read. Build a mental map of what flows, states, and constraints must be verified. Note instructions like "Không hỏi user" (don't ask) — treat the criteria as self-contained; do not seek clarification.

2. **Read all referenced files in parallel** — use one turn with multiple `read_file` calls for every file the user named. If pagination is needed, continue with `offset=` until you have complete methods. Parallel reading is faster and lets you cross-reference methods between files in a single turn.

3. **Identify all implicit code** — imports, dependencies, ancillary functions called from the named methods. Read those too. A fallback that calls `adapter.tap_profile()` means you must also read `tap_profile()`.

4. **Create a tracking checklist** — use the `todo` tool to create an item per criterion. This prevents losing track mid-review and automatically resets for the next session. Mark items `completed` as you gather evidence for each one.

5. **Build a verification checklist** — one row per criterion. Map the user's words to specific code patterns:

   | # | Criterion | Expected Code Pattern | Status |
   |---|-----------|-----------------------|--------|
   | 1 | Core flow runs first | The primary function/method is called before any fallback clause | ⏳ |
   | 2 | Fallback doesn't replace core | Core call is not inside a conditional that skips it | ⏳ |
   | 3 | Fallback failure → escalation | Error path reaches MANUAL_REVIEW with actionable message | ⏳ |
   | 4 | No fabricated success | `return True` / `success=True` only when actually successful | ⏳ |

6. **Verify side-effect constraints** — "don't modify X"? Check `git diff HEAD -- path/to/X` to confirm. Run `git diff HEAD --` on any shared library the user explicitly specified must not change (e.g. automation-core).

7. **Run build-time verification** — run in this order:
   - **Import/compile check first** — `python -c "from package.module import Function"` — this catches broken imports and syntax errors before tests run. A failing import will be masked if the test file doesn't import the specific module.
   - **pytest second** — `python -m pytest tests/ -v` — the canonical test suite proves nothing is broken.
   - **Evidence labels** — label distinctly: `import: OK` vs `pytest: 92/92 passed`. A passing import doesn't mean tests pass, and passing tests don't mean the module can be imported.

8. **Produce structured verdict** — verification table + build evidence + decision.

### Verdict Format

```markdown
## Verification Review: [topic]

### Checklist

| # | Criterion | Expected | Actual | Status |
|---|-----------|----------|--------|--------|
| 1 | Core flow runs before fallback | `open_profile_root()` called first | Line 714: first action in retry loop | ✅ PASS |
| 2 | Fallback doesn't replace core | Core call unconditional | No conditional gate before line 714 | ✅ PASS |
| 3 | Fallback fail → escalation | MANUAL_REVIEW with instructions | Lines 740-757: `is_ui_unavailable=True`, detailed message | ✅ PASS |
| 4 | No fabricated success | success=True only on real success | Line 737: `profile_success=True` after verified fallback | ✅ PASS |
| 5 | No automation-core changes | No diffs in shared library | git diff shows 0 changes in automation-core/ | ✅ PASS |

### Build Verification

| Check | Result |
|-------|--------|
| pytest | 92/92 passed |
| Compile | OK (py_compile) |
| Import | OK |

### Minor Findings

- **Finding 1** — non-blocking, suggestion only
- **Finding 2** — minor issue, not blocking

### Decision

**✅ APPROVED** — All criteria met. Ready for merge.
```

### Common Criteria Categories

**Flow ordering:**
- Does step A execute before step B?
- Is the primary strategy attempted before any fallback?
- Are retries exhausted before escalation?

**Error handling:**
- Does each error path produce a unique, actionable message?
- Are transient errors (retryable) distinguished from permanent failures?
- Are edge-case flags (`is_ui_unavailable`, `is_captcha`, etc.) set appropriately?

**Side effects:**
- Are shared/global modules modified (if the constraint says no)?
- Are new dependencies introduced unnecessarily?

**Truthfulness:**
- Does `return True` / `success = True` only appear on actual success, not after swallowing an error?
- Does the log message match what actually happened?
- Is a checkpoint saved with correct data before returning a terminal state?

### Pitfalls

- **Don't trust docstrings alone** — verify by reading the actual code path, line by line
- **Don't skip reading fallback/ancillary methods** — a fallback that calls another public method means you must read that method too
- **Don't forget build verification** — "looks right" is not enough; run tests and imports
- **Criteria without evidence is speculation** — every PASS/FAIL must cite line numbers or diff output
- **Side-effect checks require git diff** — "X was not modified" is only proven by `git diff HEAD --path-to-X`
- **Name your source for each criterion** — when the criterion came from user words, quote them; when it came from a doc or issue, cite it. This prevents scope creep and makes the verdict auditable.
- **Domain-specific patterns** — ADB/Android automation code has unique patterns (force-stop + monkey launch, uiautomator dump fallback chains, feed-polling by UI indicators, bottom-nav resolution-aware taps, device reboot recovery). See `references/adb-automation-review-patterns.md` for the full review checklist for these patterns.
- **Don't skip the dry-run trace** — verify that `dry_run` short-circuits before device-dependent operations (feed polling, UI dump, tap). A mock XML that happens to contain a feed indicator can mask a missing early-return.
- **Import check before pytest** — run `python -c "from package.module import Symbol"` separately before `pytest`. A failing import may be invisible in test output if the test file doesn't import the specific module. Label evidence distinctly: `import: OK` vs `pytest: N/N passed`. These are separate guarantees.
---

## 7. Re-Review: Verifying Fixes Applied by Another Contributor

When you did an initial code review (finding issues) and another agent or contributor applied the fixes (Codex, Claude Code, OpenCode, a human), you need to **re-review** — not just re-test — to confirm the fixes actually landed correctly. This is distinct from both initial review and self-verification.

See `references/fix-re-review-format.md` for the structured verdict output template.

### When to Use

- User says "re-review", "verify the fixes", "check if Codex fixed it", "recheck the changes"
- Fixes were applied by a different agent or a human while you context-switched
- You have a known finding list and need to confirm each one was resolved
- A previous code review identified issues, and the implementation was delegated

### Workflow

#### 1. Read All Affected Files in Parallel

Use one turn with multiple `read_file` calls. Every file that was supposedly fixed should be loaded in the same batch. Do not read files one-by-one — use the parallelism.

```text
# One turn, six reads:
read_file(state_machine.py)
read_file(adapter.py)
read_file(config.py)
read_file(account_source.py)
read_file(report.py)
read_file(requirements.txt)
```

#### 2. Build a Finding Checklist

Map each finding from the original review to what you expect to see in the code. Tracking by ID makes the verdict report scannable:

| ID | Finding | Expected Fix | Status |
|----|---------|-------------|--------|
| C1 | VIDEO_PICK stub → real UI automation | Multi-strategy fallback with `_find_ui_element`, `_wait_for_element`, `_tap_if_found` | ⏳ |
| C2 | adb pull failure | Fallback chain (exec-out cat → temp pull → content provider) | ⏳ |
| H2 | Private `config._data` access | Public `video_source_root` property | ⏳ |

#### 3. Trace Each Finding Through the Code

For each finding, search the relevant file(s) for the expected change. Don't just check it exists — check it's correct:

- **Does the fix address the root cause?** — Not just the symptom
- **Is the fix robust?** — Multiple fallback strategies? Error handling? Timeouts?
- **Are there untouched copies of the old pattern?** — One call site fixed, another identical one left alone elsewhere in the same file
- **Does the fix introduce new issues?** — Dead code (assigned-but-unused variables), wrong API method names, stale comments, regression in style

#### 4. Run Verification

```bash
# 1. Verify all modules import cleanly
python -c "from project.module import ClassA, ClassB"
python -c "import project"

# 2. Run the test suite
python -m pytest tests/ -v

# 3. Static analysis if tooling is available
which ruff && ruff check .
```

Every import error or test failure must be traced back to a specific fix. If a fix introduced a regression, flag it — do not wave it away as "pre-existing".

#### 5. Report Per-Finding Verdict

Use `references/fix-re-review-format.md` for the structured template. Example:

| Finding | Verdict | Notes |
|---------|---------|-------|
| 🔴 C1 | ✅ **APPROVED** | Real UI automation with multi-strategy fallback, timeouts, and element verification |
| 🟠 H2 | ✅ **FIXED** | `video_source_root` property added with fallback to `media_source_root` |
| 🟡 M3 | ✅ **FIXED** | Returns `False` on failure, detects CAPTCHA/login, sets edge case flags |
| — | ⚠️ **MINOR** | Variable `escaped` assigned but never used (state_machine.py:986) |

### Re-Review Decision Table

| All APPROVED? | MINOR items? | Any REJECT? | Action |
|:---:|:---:|:---:|--------|
| ✅ Yes | No | No | **APPROVED** — all fixes good, merge ready |
| ✅ Yes | Yes | No | **APPROVED (MINOR_FIXES)** — fix minor items, then merge |
| No | — | No | **PARTIAL_APPROVAL** — approved items mergeable, rejected need a new fix cycle |
| No | — | Yes | **REJECT** — at least one fix is wrong; needs full redo |

### Pitfalls (Re-Review Specific)

- **Don't re-read the review findings as if they're new code** — the findings are your checklist. You're not reviewing from scratch; you're verifying specific points. Re-reading everything costs time and risks re-discovering what was already found
- **Batch reads, serialize writes** — read all files in one turn. Only write if the re-review demands additional fixes, and do that in a separate turn after the verdict
- **API method mismatch** — verify method names used in fixes actually exist on the target class. A fix that calls `adb.run()` when the API only has `adb.shell()` is silently broken
- **Dead code detection (assigned-but-unused)** — the fixer may have left scaffolding: a variable computed but never passed to the next call. Scan for this explicitly
- **Regressions** — a test that passed before the fix and fails after is the fixer's bug, not "pre-existing". Report it
- **Look for untouched copies of old pattern** — the fixer may have targeted one call site but missed an identical one two methods away in the same file. This is the most common re-review fail

## 8. Editing CRLF Repos and Validator Honesty

### Shared-worktree re-review handoff gate

If a sibling worker edits the reviewed file after your last read, the candidate bytes have changed and your prior reasoning is stale. Treat a patch-tool collision or mtime warning as a hard handoff: stop writing, bind any test result to the current bytes only, and report `BLOCKED_AT_CONCURRENT_WRITER_REVIEW` until ownership is reconciled. Never retry a patch merely because it is small or apparently non-overlapping. Before resuming, inspect both staged and unstaged diffs and re-read the full affected functions.

### Worker-call compatibility is part of correctness

A review fix that adds a keyword argument to a worker/helper invocation changes a testable interface. Search direct fakes and mocks before running the suite; old fakes may reject the new keyword and turn every worker into a fallback failure. A focused failure such as `unexpected keyword argument` must be classified as an interface regression and fixed or explicitly reconciled before evaluating watchdog/deadline semantics. Do not call the implementation verified while this seam is red.

Windows Taadaa/automation-core repos (and most consumer repos) store docs, tools, and tests with **CRLF line endings, no BOM**. When fixing review findings there:

- **Prefer the lossless LF↔CRLF round-trip for PURE-CRLF files** — when the target is 100% CRLF (assert `text.count('\r\n') > 0 and '\n' not in text.replace('\r\n', '')`), normalize once to LF, do every edit with plain `\n`-joined strings (they now match), assert `text.count(old) == 1` before each replace, then convert every `\n` back to `\r\n` on write. This is simpler and safer than `E.join([...])` surgery and is immune to escape-transport noise. Backup first (`cp file /tmp/x.bak`) and abort-on-mismatch so a failed run writes nothing. Full script template + verification commands: `references/crlf-safe-edit-recipe.md`.
- **`CẤM patch tool/sed` on a CRLF-pure file is a hard constraint** — e.g. the Tiktok-video convention: `scripts/tiktok_workflow/state_machine.py` is CRLF THUẦN and may ONLY be edited via a Python binary read/write script (the round-trip above). Do not argue; byte-identical EOLs are what keep future line-level merges clean. Same rule for CRLF-pure docs (`docs/tiktok-ui-compatibility.md`).
- **write_file transports backslash escapes as literal text — probe before authoring a big edit script** — a payload `\n` arrives in the file as literal backslash-n (Python evaluates it to a real newline at runtime), `\r\n` arrives as literal `\r\n` text (runtime value = real CRLF — which works for CRLF-building scripts), and a raw newline inside a single-quoted string literal breaks the script with SyntaxError. Verify with a 3-line probe file + `python -c "print(repr(open('p','rb').read()))"` before writing a 19-edit script, and let the script build CRLF at runtime instead of in the payload. The script itself may be LF; only the TARGET file's EOLs matter.
- **Patch Tool Atomic Validation Failures ("Found N matches for old_string")**: When `patch` fails validation (e.g. hunk not found or multiple matches), it is strictly atomic — **no files were modified**. Never claim or assume the patch landed. Re-read the region with `read_file`, expand context to include surrounding function/class headers or unique statement anchors, or use targeted Python binary surgery to ensure exactly one unique match. Verify on disk immediately with `git diff --stat` or `py_compile`.
- **Mock Calibration for Newly Activated Seams/Hooks**: When a feature or rate change activates a downstream flow hook (e.g. `_maybe_follow_video` or deep-like rate compensation), existing integration test mocks in unaffected test suites may fail with `UIDumpError` / unmocked capture calls if they simulate `_feed_session_flow` without providing doubles for the newly active hook. Update test fixtures to mock the newly active hook (`_maybe_follow_video = Mock(return_value=False)`) or assert the new rate expectation explicitly.
- **Patch Tool Atomic Validation Failures ("Found N matches for old_string")**: When `patch` fails validation (e.g. hunk not found or multiple matches), it is strictly atomic — **no files were modified**. Never claim or assume the patch landed. Re-read the region with `read_file`, expand context to include surrounding function/class headers or unique statement anchors, or use targeted Python binary surgery to ensure exactly one unique match. Verify on disk immediately with `git diff --stat` or `py_compile`.
- **Mock Calibration for Newly Activated Seams/Hooks**: When a feature or rate change activates a downstream flow hook (e.g. `_maybe_follow_video` or deep-like rate compensation), existing integration test mocks in unaffected test suites may fail with `UIDumpError` / unmocked capture calls if they simulate `_feed_session_flow` without providing doubles for the newly active hook. Update test fixtures to mock the newly active hook (`_maybe_follow_video = Mock(return_value=False)`) or assert the new rate expectation explicitly.
- **`patch` tool double-escapes files whose content carries literal backslash escapes** — patching a CRLF-edit script that stores `\\r\\n` as literal escape text inside Python string literals makes the fuzzy matcher escalate the escapes (`\\r\\n` → `\\\\r\\\\n` → `\\\\\\\\r\\\\\\\\n`), corrupting the script (hit this session; the mangled lines were only caught by lint step + rewriting the file). When the file's content IS backslash-escape text, rewrite the whole script with write_file instead of a targeted patch.
- **`patch` fuzzy matcher mis-aligns multi-line continuation indentation on CRLF files** — replacing the first line of a multi-line `if (...)` condition (keeping the continuation lines) left the continuation with wrong indentation AND re-indented a following comment; a second fuzzy patch then compounded it instead of fixing it. The matcher is safe for single-line / simple-block edits but NOT for multi-line re-indentation. Fix: byte-exact binary replace — `data = p.read_bytes(); assert data.count(old) == 1; p.write_bytes(data.replace(old, new))` with `old`/`new` joined by `\r\n` — then re-read the region and verify EOL purity (`out.count(b"\r\n") == out.count(b"\n")`).
- **Bash-heredoc-generated edit scripts mangle escape sequences** — a `"\\n"` inside a `<<'PY'` heredoc replacement string can land in the GENERATED file as a real newline inside a string literal (`+ "` + LF + `" + ...` → unterminated-string SyntaxError, caught only by pytest collection/ast.parse). When a patch script must emit escape text, author it with write_file (its escape transport is documented and predictable) instead of a heredoc, and ALWAYS verify the output file immediately — `python -c "import ast; ast.parse(...)"` or `pytest --collect-only` — before trusting the edit.
- **Assert EOL purity — never "CRLF count unchanged"** — a replacement that changes the line count (7-line rule → 28-line block) legitimately breaks `assert out.count(b"\r\n") == data.count(b"\r\n")` (this session: the assert fired, the edit was fine). The correct proof: `n_crlf = out.count(b"\r\n"); assert n_crlf == out.count(b"\n") and out.count(b"\r") == n_crlf` — every LF preceded by CR and no bare CR → byte-pure EOL regardless of line growth.
- **`write_file` emits LF** — after writing a file, convert bytes: `b.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')`, then verify by byte-counting `CRLF: N, lone LF: 0, BOM: False`. The `patch` tool preserves CRLF; plain python writes do not.
- **Python `str.replace` with `\n` never matches CRLF content** — a multi-line `old` string silently matches 0 times (`text.count(old) == 0`) and the replacement never happens. Build search strings with `E = '\r\n'; E.join([...])`, or do line-based surgery: `lines = text.split('\r\n')`, find line indices, splice `lines[k:k] = [...]`, rejoin. Always `assert text.count(old) == 1` before replacing.
- **Line-splice edits can drop adjacent clauses** — overwriting `lines[i+1]`/`lines[i+2]` can clobber a clause that belonged to the next logical line (this session dropped the "and target (wm size override), then" clause and only caught it by re-reading the diff). After surgery, re-read the final block and `git diff` it; restore dropped content.
- **Preserve pre-existing dirty files** — when the user says "không commit/push" and other files are already dirty (`git status --short`), leave them untouched and state in the report that they were pre-existing, not yours.
- **Line-splice with embedded `\n` inside replacement strings corrupts CRLF files — normalize→edit→re-encode, don't half-splice** (hit 2026-08-12 on the P1 pilot audit-fix): `lines = text.split('\r\n')` then `lines[j] = 'line1\nline2'` (LF inside ONE list element) followed by `'\r\n'.join(lines)` yields a mixed-EOL file — the element's inner `\n`s stay bare LF while everything else is CRLF, output shows "ghost lines" (no line-number prefix in dumps), and overlapping multi-line replaces can duplicate dict keys (`"state"` appearing twice in a `return {...}`). Recovery that worked: normalize the WHOLE file to LF once (`text.replace('\r\n','\n')`), apply every hunk with plain-`\n` strings (assert `text.count(old) == 1` per hunk), then re-encode `'\n'.join(...).replace('\n','\r\n')` on write — never mix the two strategies in one pass. Verify with `data.count(b'\r\n') == data.count(b'\n')` (byte-pure) + re-read the edited region for duplicates.
- **`Path.read_text()` hides CRLF (universal-newlines translation)** — `read_text()` converts CRLF→LF, so `repr()` line dumps show only `\n` even when `file` says CRLF; you cannot tell the true EOL layout from them, and exact-match `old` strings built from those dumps silently fail (`count == 0`). For byte-exact search/replace and EOL verification always `read_bytes().decode("utf-8")`; after ANY CRLF file read, explicitly re-add `\r\n` to search strings before counting.
Sanity-probe the load first when a script exports old/new strings: `print(text.count('\\r\\n'))` — if > 0 you are NOT normalized.
- **Multi-line call anchors — anchor on the line as it ACTUALLY appears** — inserting a gate before `end_result = adapter._adb.shell([` failed with count 0 because the call spans lines: `shell(` ends the line and `[` starts the next (`["input", "keyevent", ...]`), so `shell([` never exists in the file. Grep the exact statement line first, then anchor on the unique fragment that really exists (`end_result = adapter._adb.shell(`). A count-0 assert is an anchor bug, never relax it — the assert is the safety net that caught this.
- **EOF anchor on a no-trailing-newline file: the final line has no `\n` to match** — an `apply(old, new)` whose `old` ends with `\n` fails `assert count == 1` (count 0) when the target file ends WITHOUT a trailing newline (this session: `swipe_feed` was the last function in a CRLF-pure file, `return` at EOF). Anchor `old` WITHOUT the trailing `\n` (let `new` re-add it), and keep the explicit ensure-trailing-newline step after all edits so a "missing newline at EOF" finding closes in the same pass.
- **Edit-script helper closure: assigning the outer buffer needs `global text`** — a `def apply(old, new): text = text.replace(old, new, 1)` helper that assigns the outer buffer crashes with UnboundLocalError on the FIRST apply call (the assignment makes `text` local to the helper). Declare `global text` inside the helper, or hold the buffer in a mutable container. Abort-before-write is the safe outcome (file untouched), but expect this error so it does not read as a file problem — it is purely a Python scoping issue in the edit script.

Validator fixes (e.g. `tools/check_ui_compatibility.py` — also see `references/validator-contract-editing.md`):

- **A check that can't find its target file passes vacuously** — a wrong path segment (`core_repo / CANONICAL_NAME` instead of `core_repo / "docs" / CANONICAL_NAME`) makes `is_file()` False and the check returns `[]` with no error and no finding. Probe the check directly (call the internal function, print the parsed records/IDs) to prove it is live before trusting a clean run. The fail-closed form: when the target is genuinely missing, return a hard finding — `return [f"core_missing:{contract}"]` — never `[]`, so deleting the canonical file fails the run instead of silently passing. Your happy-path test workspace must then seed the file (and its test must `unlink()` it + assert `core_missing:`).
- **Date-formatted cutoffs need format normalization before `>=`** — lexicographic compare of a compact date against an ISO cutoff is wrong: `"20260808" >= "2026-08-09"` is True (byte `'8'` > `'-'`), so an 08-08 record would be misclassified as new. Normalize both forms to one ISO format first (`d if "-" in d else f"{d[:4]}-{d[4:6]}-{d[6:8]}"`), and parse both spellings from record headings AND IDs.
- **"Marker anywhere in prose" concept checks are fail-open** (audit complaint): a concept mentioned only in a paragraph, or inside another bullet's label (`- UI signature and evidence:` must NOT satisfy the standalone `evidence` concept — startswith-prefix only), passes when it shouldn't. For strict records (newer than the cutoff), require a DEDICATED bullet label (`- **Label:** value` / `- Label: value`) with a NON-EMPTY value; prose never counts. Preserve a looser marker-based legacy path for pre-cutoff records so old registries warn instead of fail — the cut-off must stay non-retroactive.
- **Capture the validator's expected real output BEFORE editing** — run it first, record the exact numbers (`OK: 9/9 consumers`, `total legacy warnings: 66`); after the change, diff output. Identical counts prove no retroactive break; a changed baseline must be explained. Round-2 example: strict bullet rules for new records kept the real run at 9/9, 0 findings, 66 warnings.
- **Acceptance criteria like "validator must output 0 findings" may be unattainable on real data** — consumer registries genuinely lack required fields. Per instruction, do NOT fix out-of-scope files and do NOT weaken markers just to force 0; report the honest finding list (grouped per repo, with counts) and state that registry fixes are a separate task. Extend markers only for legitimate alternative phrasings of the same concept (VN + EN label variants), never for labels so loose they mask real gaps (e.g. bare "action" or "ordered").
- **Baseline-parity = per-record set comparison, not just counts** — when you change concept-detection semantics (e.g. legacy path from substring → strict bullets), the warning COUNT can jump (66 → 173) even with zero regressions: strict parsing stops counting prose mentions. Reconstruct the OLD detector in a scratch Python script (re-implement the pre-change logic inline or from git) and compare the warning SETS per record: same records warned, 0 newly-warned, 0 dropped; every missing-set diff must be individually explainable as the intended strictness gain. Report the set comparison, not "counts match" — identical totals can hide swapped record sets.
- **Strict-bullet parsing inflating warnings → dump the label vocabulary first** — when strict bullets suddenly warn on ~100 records, run the bullet-label regex over EVERY registry and print the DISTINCT labels. Usually a single un-covered label variant explains the whole spike (this session: `thứ tự selector/fallback:` — the marker list had `selector/fallback` and `thứ tự xử lý` separately but not the combined form; adding exactly that one marker restored exact baseline parity). Never "fix" a spike with loose words (bare `recovery`, `fallback`, `luồng`) — those mask real gaps and get REJECTed on re-review.
- **Decorated labels: strip LEADING decoration before prefix-matching** — in markdown `- **ID/owner:**` the closing `**` sits AFTER the colon, so the bullet-label regex yields label `'**id/owner'` + value `'** x'` and wrapper-only `_strip_decoration` can't help. Loop-strip leading `**`/`*`/backtick before `startswith(marker)`; a record whose labels are all bold must be CHECKED, never silently skipped. Debug regex confusion by dumping group spans + per-index chars.
- **Bold labels must also parse correctly in the VALUE parser, not just the discriminator** — decoration-stripping the discriminator isn't enough: the shared `_BULLET_LABEL_RE` (`(label)\s*:\s*(value)`) still splits `- **ID/owner:** x` as label `**ID/owner` + value `** x` (closing `**` leaks into the value), so every bold-labeled record false-misses. Fix: a dedicated `_BOLD_BULLET_LABEL_RE = ^\*\*(?P<label>[^*:\n]+?):\*\*\s*(?P<value>.*)$` matched first (colon INSIDE the bold pair), plain regex as fallback; then `_strip_decoration` both sides, empty value → missing. Test both `- **Label:**` empty, `- **Label:** **` decoration-only, and a full 9-concept all-bold record passing.
- **"Is this finding mine?" — old-logic A/B attribution** — when the real workspace shows a finding not in the parent's baseline, monkey-patch the PRE-change function implementations back onto the freshly-loaded module and re-run the real check. Identical finding + identical warning count ⇒ pre-existing (usually uncommitted consumer WIP dated today, not your change). Report the proof; don't claim clean, don't take the blame, don't fix out-of-scope records to force 0. Full round-4 detail (V4-05/V4-06 + baseline-drift): `references/validator-contract-editing.md`.

## Audit-gated release decisions

For a formal independent audit that gates staging/commit/push/merge, load `references/audit-gate-finalization.md`. It covers exact-verdict handling, finding admission, invariant-batched remediation, fresh verification, and the final staged-scope gate. In particular, an auditor process `exit 0` is never an `APPROVED` verdict.

## 9. Audit-Fix Passes (findings lists → code → tests → full suite)

When a review/audit REJECT comes as a numbered findings list ("sửa 7 finding P1 + P2-01 … chạy full suite phải pass; không commit/push"), treat the pass as: findings → code → tests → full suite → stop. Rules:

### Critical distinction: remediation is not release approval

A reviewer verdict of **REJECT** means the candidate is not releasable; it does **not** mean remediation should stop. Immediately patch the findings, add regression tests, run the focused/full gates, and request a fresh re-review of the new bytes. A separate release gate (for example, a live canary or user authorization) may still block review approval, commit, pull/rebase, push, or rollout, but it must not be used as a reason to return a blocker instead of fixing code. Use this state model:

| State | Allowed next action |
|---|---|
| `REJECT` findings present | Fix findings and tests; do not release |
| focused/full tests red | Continue debugging/remediation; do not release |
| live canary/Gate 0 failed | Stop release actions only; preserve the failure evidence and continue offline remediation unless the user explicitly forbids it |
| fresh re-review `APPROVED` | Proceed to the remaining release gates |
| release gate not met | Report the exact gate blocker; never relabel the code as approved |

Do not conflate `BLOCKED_AT_GATE_0` with `BLOCKED_FROM_REMEDIATION`. The former forbids release actions; the latter is only appropriate when a prerequisite prevents even safe offline code/test work. If another agent supplies a `REJECT`, treat every finding as an actionable checklist and keep working until each is fixed or an actual implementation prerequisite is proven unavailable.

For delegated remediation, the coordinator owns the next cycle: re-read the worker's changed files, compare the exact diff against the finding list, run the finding-specific regression probes, and re-review the resulting bytes. Never report the worker's `REJECT` as the final outcome when the user's request was to fix the review. See `references/delegated-review-remediation-vs-release.md` for the state model and cohort/watchdog regression categories.

Rules:

- **Run the existing suite BEFORE writing new tests.** Failures then split into three triage buckets: (a) old tests assert the OLD lenient contract — their mocks need updating to the new API/precondition (findings often explicitly allow "cập nhật mock cho khớp API mới"; keep the test name and assertions, add mocks such as `machine.context.soft_reboot_recovery_outcome = "ATTEMPTED_FAILED"` + `_package_is_foreground = lambda *_: True`); (b) the new behavior only manifests when a new gate mock is present; (c) REAL BUGS the refactor introduced — e.g. this session's `_caption_chunk_landed` returned False whenever the dump had no `EditText`-class node, surfaced only by the failing typing-fallback test (it needed the same whole-dump visible-text fallback the ratio verifier uses). Never dismiss a failure as "expected" without triaging it into one of these buckets.
- **"Boolean return is ambiguous" findings → structured signal.** The complaint "coordinate fallback chạy vô điều kiện sau `_maybe_soft_reboot_recovery()` trả False" is fixed by a multi-state classifier (e.g. `VERIFIED / ATTEMPTED_FAILED / NOT_ELIGIBLE / EVIDENCE_MISSING / ALREADY_CONSUMED / NOT_RESERVED`); the caller proceeds only when `outcome ∈ {VERIFIED, ATTEMPTED_FAILED}`, everything else goes straight to MANUAL_REVIEW — no blind tap. Same shape: per-error-code classifier with a per-code budget (1×/signature/run) instead of one global flag.
- **Every stricter gate gets a fail-closed test + persistent evidence.** tap returns False → no recapture/no retry; foreground not True → visual gate rejected; all-black screenshot → coordinate rejected; each typed chunk verified in-field else the field is cleared (clear-fail sets a residue flag that forbids the next fallback from appending). Evidence previously thrown away (`attempts=[]`) goes persistent per signature into the context/checkpoint with timestamps + before/after screenshots.
- **Artifact freshness findings ("visual verdict uses a stale frame") → unique-path fresh capture per verdict.** The REJECT pattern: a helper returns a fixed fallback path (`run_dir / "feed-visual-fallback.png"`) whenever the file EXISTS — so a later `_wait_for_feed` in the same run/next run reuses a frame from an earlier call and false-accepts feed after the screen changed. Fix shape: (a) each verdict captures to a UNIQUE path (`feed-visual-{seq}-{ts}.png`, timestamp-ms or monotonic seq so consecutive calls never collide); (b) if the caller already captured a fresh artifact (e.g. coordinate-fallback `_capture_coordinate_fallback_artifact`), accept it via an explicit `screenshot_path` parameter and consume it for the FIRST verdict only, then fall back to fresh captures — never thread one stale frame through the whole poll loop; (c) unlink the legacy fixed-name file on capture so no two runs share a file. Regression test shape: mock `transport.screenshot` to record every path AND render a real feed/non-feed image per call; pre-seed the legacy fallback file with a feed-looking image; call `_wait_for_feed` twice — run 1 (screen non-feed) must be False based on the FRESH capture (not the seeded file), run 2 (screen feed) True with a path DIFFERENT from run 1; assert the legacy file was deleted. The old V4-04 test that asserted "artifact exists → reuse without recapture" was the bug itself — REPLACE it, do not keep it passing.
- **End gate**: full suite green (~320 tests in this file), EOL byte counts unchanged on the CRLF-pure file, no commit/push, pre-existing dirty files untouched, backup restore-verified.
- **Exact-file-scope fixes with OUT-OF-SCOPE shared fixtures (conftest.py)** — when the allowed scope excludes the fixtures but new code must stay compatible: (a) duck-type new optional adapter APIs (`getattr(adapter, "screen_size", None)`) with a fallback that works on the existing fake (e.g. parse the UI-dump ROOT node bounds); (b) early-return BEFORE any `dump_ui()` call when the loop count is 0, so the fake's XML queue never shifts and existing tests keep their exact dump budget; (c) when fixture helpers hardcode attributes (e.g. `xml_node` always emits `class="android.widget.TextView"`, `focused="false"`, no `editable`), author RAW XML strings inside the test file to exercise new parse fields — never touch the out-of-scope conftest. Same shape: assert tap coordinates prove two DISTINCT nodes were tapped (not the same content-desc twice). Full worked example (resolution-safe swipe, reload-budget counter, transport-finding locking test, probe skeleton): `references/in-scope-fix-fixture-compat.md`.
- **Audit finding suspects a transport dependency — verify, then comment, DON'T change behavior.** When the auditor claims `adapter.shell` routes through atx-agent so `pkill -9 -f atx-agent` would kill its own transport, read the implementation: if `shell` is a direct `subprocess.run([adb, -s, serial, "shell"] + args)`, the finding is a non-issue for that architecture. Do NOT rewrite behavior just to appease the audit (the user explicitly forbids it) — add a code comment with the evidence and a locking unit test that monkeypatches `subprocess.run` and asserts the EXACT cmd list (`["adb","-s",serial,"shell","pkill","-9","-f","atx-agent"]`). Report the verdict: verified non-issue, behavior unchanged.
- **Verification freshness: end the session with the canonical command.** The Hermes verification tracker keys on the LAST recorded command; if the final action is an ad-hoc edit script, or the probe script was deleted right after running, the status reads `stale` even after a green full suite (hit twice this session despite 70 passed). Sequence that satisfies both the tracker and the evidence rules: run the ad-hoc probe first (report as targeted evidence), then run the canonical suite (`pytest ...`) LAST so it is the final recorded command, then clean up probes and re-verify cleanup with `[ -e path ]`.
- **System says `unverified` after a prior green run → create fresh evidence, do not argue from history.** Use the v2 interpreter explicitly and create the focused probe with `tempfile.mkstemp(prefix="hermes-verify-", dir=r"C:/Users/<user>/AppData/Local/Temp")`; verify the exact changed behavior (AST/comment/export assertions plus relevant static invariants), run it, delete it, and assert the path is gone. Then run the exact canonical test command from the repository root as the FINAL command—never from a subdirectory where the relative test path changes—and report the probe as **ad-hoc verification**, not as suite coverage. Treat any temp probe path listed as a changed path as a cleanup failure that must be corrected before claiming a clean handoff.
- **Fragile `str(exc) == "LITERAL"` matching → dedicated exception subclass.** When a finding flags string-matching on error messages (e.g. `str(exc) == "MEANINGFUL_ATTEMPT_BUDGET_EXHAUSTED"`), fix by: add `class XBudgetExhaustedError(XContractError)` beside the base error; switch ALL raise sites to the subclass but KEEP THE MESSAGE STRING IDENTICAL (so `str(exc)` and every `except BaseError` / `pytest.raises(BaseError, match=...)` stay backward-compatible — grep for other string-matchers on the literal first); route the handler with `isinstance(exc, XBudgetExhaustedError)`, never `type(exc) == ...`. BEFORE declaring the branch dead code, trace each raise site through the state machine for reachable configs (this session: default `max_meaningful_attempts=8` made the loop check fire first, but `max=1` makes `reserve_handler` raise at CLASSIFIED → branch alive). Add two regression tests: (1) end-to-end reachable path → terminal status + durable queue state + lock held; (2) same exception type raised with a DIFFERENT message → still routed to the fail-closed path (this test FAILS on the old string-match code — it is the proof). Full recipe: `references/exception-type-routing.md`.
- **git-bash temp-script gotcha: native python.exe double-converts MSYS paths.** `python "$TMPDIR/hermes-verify-x.py"` with `$TMPDIR=/c/Users/...` reaches python as `C:\c\Users\...` (file not found), while the SAME var-expanded path works for `cat`/`rm` (MSYS-native tools) — so your own cleanup deletes the file python never saw. Use literal Windows-style paths (`C:/Users/...`) for both write and run (or author the script with write_file), and verify cleanup with `[ -e path ]`.

## Audit Completeness: Trace Primary, Retry, and Recovery Paths

A focused suite can pass while the implementation still violates the reviewed contract in a secondary retry/recovery path. For seam-classification or fail-closed OTP/mailbox changes, audit every route to the sensitive operation, not only the initial branch. See `references/secondary-fallback-audit.md` for the concrete pattern.

1. Enumerate every direct and indirect call site of protected readers/actions (for example, newest-message reader, stale CDP reader, browser preview reader, and shared resend handler).
2. Trace the normal path, timeout path, explicit rejection path, shared-recovery path, and post-recovery refresh path separately.
3. Treat comments and tests as claims, not proof. If a comment says "never fallback" but a later helper still calls the forbidden function, report the contradiction and reject until the code is corrected.
4. Add or inspect negative call-site tests that monkeypatch forbidden readers and assert they remain uncalled after the primary reader returns `None`, after a rejected code, and after a resend/refresh attempt.
5. Before approving, run a final static search for every forbidden symbol and inspect each occurrence in context; a green focused suite does not override a confirmed contract violation.

This is especially important when a new strict reader is added: verify that legacy fallback helpers cannot reintroduce the old unsafe reader after the strict reader fails.

## Delegated Patch Re-Audit and Scope-Control Gate

When another worker/agent edits a dirty repository after a review finding, re-audit the actual diff before trusting its report:

1. **Refresh from disk first** — re-read every changed target after the worker finishes; do not patch from a stale snapshot. Record the exact dirty baseline and preserve unrelated user/worker changes.
2. **Repair syntax/EOL before behavioral triage** — for CRLF-pure files, use a byte-exact Python edit with occurrence assertions, then verify `CRLF == LF`, zero bare LF, and `py_compile`. A green `git diff --check` does not prove syntax validity.
3. **Separate intended findings from collateral behavior changes** — compare the changed helper/function against `git show HEAD:<file>`. If a worker changed an unrelated fallback/health contract and focused tests regress, restore only that collateral block from HEAD while retaining the review fix; never broaden the refactor to make the new behavior fit.
4. **Run gates in layers** — focused finding/regression tests first, then compile and diff checks, then the full suite with `-x -vv` when it is large or slow. A focused pass is not a full-suite pass. If the full suite fails on a symbol/test outside the finding scope, prove it against HEAD and report it as a baseline/out-of-scope blocker; do not silently fix it.
5. **Use honest release language** — `focused PASS` and `full-suite BLOCKED` are distinct verdicts. Do not authorize live execution when the required audit verdict or full release gate is absent, even if the focused tests pass.

A concise session-specific repair/reverification recipe is in `references/delegated-patch-scope-and-crlf.md`.

## State-Machine Invariant Tightening

When a P1 fix strengthens an identity or ordering invariant, treat existing fixture helpers as part of the contract. A helper that reserves an invocation randomly and later emits `RECOVERING`/`FAILED` with a caller-supplied invocation is an invalid fixture after the guard is correct; update the fixture to pass the same invocation explicitly rather than weakening production validation. Verify in this order: (1) one append-path splice test fails with the expected exception, (2) one replay-path forged-record test fails, (3) update only stale fixture assumptions, (4) run the focused tests, then the full canonical suite. Keep append and replay assertions separate—passing append does not prove replay enforcement.

## Adversarial Tests for Fail-Closed Validators (anti gate-masking)

When closing findings on a multi-gate fail-closed validator (`validate_manifest`-style chains where each gate raises its own reason code), the classic `pytest.raises(ValueError)` blanket test is gate-masked: a day/slot/pair-gap gate can fire before the binding under test, so the test passes without ever exercising the intended gate. Design rules that held up: mutate ONE metadata field per parametrized case, keep day/slot/session topology canonical, re-hash dependent ids EXACTLY as production does, sync ALL bound metadata (e.g. entry `lock.serial` when `serial` mutates — a lock-binding gate fires MANIFEST_IDENTITY_MISMATCH before the source-mapping gate otherwise), and assert the EXACT reason code, not just ValueError. When a new unconditional canonical check rejects a legacy forge fixture, calibrate the FIXTURE to be canonical for its new shape (re-hash the derived fields the new check binds) — never loosen the gate, never delete the test — and flag any allowlist deviation explicitly. Full gate-ordering table + the R10 machine-999 calibration case: `references/fail-closed-validator-adversarial-tests.md`.

## Pitfalls

- **Don't over-engineer**: Fix exactly what review found, don't refactor unrelated code
- **Verify before claiming done**: Always run tests after fixes
- **Ad-hoc verification is valid**: If no test suite exists, create targeted verification script
- **Clean up temp files**: Remove verification scripts after running
- **Match code style**: Use same indentation, naming, patterns as surrounding code
- **Read file completely first**: Don't just read the lines mentioned in review — use offset pagination if read_file truncates
- **Patching truncated files is dangerous**: The `_warning` in patch output saying "was last read with offset/limit" means you only saw part of the file — re-read the complete file before further edits
- **Verify imports after each batch**: Run `python -c "from module import Class"` between edit batches — failed imports catch a bad edit before you compound it with more edits
- **Removing old_string content that was also needed**: When consolidating code (e.g. removing lazy imports), double-check you didn't delete a variable assignment alongside the import — the pattern `from X import Y; y = fn()` needs both the import AND the assignment to stay
- **Call Review độc lập qua 9Router HTTP API ngay sau mỗi phase/fix (User rule 18/08)**:
  - CẤM dùng `delegate_task` cho việc review/audit (vì Hermes ghim cứng delegate vào worker model `worker`).
  - Mọi tác vụ Code Review / Audit BẮT BUỘC phải gọi trực tiếp qua 9Router HTTP API:
    `POST http://127.0.0.1:20128/v1/chat/completions` với model `"plan-review"` (thường) hoặc `"plan-review-hard"` (khó/core), options `"stream": false`, `"tools": []`, `"tool_choice": "none"`.
  - Review verdict APPROVED mới cho phép commit/push/canary live.
- **Image / similarity-metric audits (picker, thumbnail, visual match):** when the code under review OR-combines metrics (correlation + histogram) or matches by color, the reviewer MUST check two common false-positive paths: (1) the returned/tapped candidate is the one that WON the accepted metric — NOT a different metric's winner (OR-ing metrics with one shared `best_candidate` variable returns the wrong tile); (2) color-only metrics collide on same-color different-content images — require a spatial/structural guard (e.g. 2x2 spatial histogram that must agree on the SAME candidate) before accepting. Both are real, repeatable REJECT findings — bake them into the review checklist for any picker/identity verification code.

## Verification Strategy

For dynamic popup selector regressions, use `references/dynamic-popup-selector-regression.md` for the fixture, fail-closed detector, negative-selector assertion, and exact verification pattern.

### Option 1: Existing Test Suite (preferred)
```bash
pytest tests/ -v
```

### Option 2: Ad-Hoc Verification (when needed)
```python
# Test specific behavior
from module import Class
obj = Class()
assert obj.method() == expected_value

# Test edge cases
try:
    obj.failing_case()
except ExpectedException:
    pass
```

### Report Format
```
✅ Fixed P0 #1: <description>
✅ Fixed P0 #2: <description>
...
✅ pytest: 11/11 passed
✅ Ad-hoc verification: All fixes verified
```

## Example Session

```
User: Fix 4 P0 critical issues that Claude review found. After fix, run pytest to verify.

Agent workflow:
1. Read all 4 P0 issues from review
2. Read affected files (ui_profile.py, state_machine.py, locks.py)
3. Fix each issue:
   - P0 #1: Type mismatch → update Union type
   - P0 #2: Missing retry → implement 2-tier retry with checkpoint
   - P0 #3: Race condition → use atomic file creation
   - P0 #4: Commented code → uncomment
4. Run pytest: 11/11 passed
5. Create ad-hoc verification for each specific fix
6. Report: All 4 P0s fixed, verified with pytest + ad-hoc tests
```
