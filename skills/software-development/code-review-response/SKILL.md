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

## Stateful Cooldown/Retry Review Pattern

For batch supervisors that retry a failed login or external workflow, review the state machine as a fail-closed contract rather than only checking the happy path:

1. Derive cooldown eligibility only from a semantically authoritative failure record (matching stage, terminal failure status, and parseable timestamp). Never fall back to a generic `updated_at` field, and never treat missing/malformed time as immediately eligible.
2. Test exact boundary behavior on both sides of the cooldown threshold, plus missing/malformed timestamps and every supported failure status.
3. Persist a retry counter at the state boundary where an automatic retry is authorized. Increment it exactly when unblocking, enforce a hard maximum, and transition to a terminal quarantine state before another retry can be selected.
4. Emit structured telemetry from the production failure/unblock paths, including identity, machine/proxy context, retry count, and actionable detail. Tests should patch/assert the real telemetry seam rather than writing synthetic log records.
5. Verify integration: the selected/unblocked state must reach the real executor/script invocation, and executor failure must feed back into the same failure state and telemetry contract.

See `references/stateful-cooldown-retry-review.md` for the reusable fixture matrix and reviewer checklist.

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

### Dispatch Guard & Hook Lifecycle Classification (Recoverable Remediation vs Hard Stop)
**Problem**: Review audits (e.g. Sol review gate) reject pre-tool hooks / dispatch contract validators when fixable contract defects are classified as `HARD_STOP`. Treating fixable coordinator errors (missing investigation budget, budget exceeding threshold, missing `OLD_STRING`, missing `FILE` label, missing target file) as terminal stops breaks automated remediation loops.
**Fix**:
1. Classify prompt/contract syntax and parameter errors as `REMEDIATION_REQUIRED` with concrete `blocker` and `next_action` guidance so the caller/coordinator can correct arguments and redispatch.
2. Reserve `HARD_STOP` strictly for non-recoverable security, ethics, safety, or unauthorized bypass attempts (such as unstructured or unauthorized `SOL_FALLBACK` lacking valid authorization tokens).
3. In regression tests, add explicit assertions proving:
   - Recoverable parameter defects emit `REMEDIATION_REQUIRED`.
   - Unauthorized safety/policy bypasses remain `HARD_STOP`.

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

### Playwright Locator Count Anti-Pattern (`.first.count()`)
**Problem**: Calling `.first.count()` on a Playwright locator:
```python
# Before (BUG / Anti-pattern):
save_pw = page.locator('button:has-text("Lưu"), ...').first
if save_pw.count() > 0 and save_pw.is_visible():
    ...
```
In Playwright, `locator.first` creates a locator pinned to the first element matching the selector. Calling `.count()` on `.first` always evaluates to either `0` or `1`, but chaining `.first.count()` is error-prone, confuses element cardinality checks, and violates Playwright idiom. If multiple matching buttons exist, `.count()` on the base locator checks the actual pool size before selecting `.first`.

**Fix**: Always check `.count()` on the base locator collection, then interact via `.first`:
```python
# After (Correct):
save_btns = page.locator('button:has-text("Lưu"), ...')
if save_btns.count() > 0 and save_btns.first.is_visible():
    save_btns.first.click()
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

### UI Detector Extraction and Mock-Page Contract

When a review asks to extract repeated Playwright/browser challenge detection into
`detect_*_options`, preserve the existing selector behavior and make the seam
unit-testable:

1. Keep selector strings and priority order stable unless behavior change is
   explicitly requested.
2. Return a deterministic pair: an ordered availability tuple for the existing
   classifier plus a named locator map for the actionable elements.
3. Add a focused fake-page test whose locator implements only `locator`, `.first`,
   `count()`, and `is_visible()`. Assert all availability flags, stable option
   names, and actionable locator values. This tests the real helper without a
   browser session.
4. Leave orchestration responsible for priority selection, telemetry, click, and
   retry/continue; the detector owns only selector discovery and visibility checks.
5. Re-run the focused test after fixture or source edits, then the affected module,
   import/compile checks, and `git diff --check`. A passing test before the last
   edit is stale evidence.

This is a reusable pattern for challenge methods, consent dialogs, login-route
selection, and other DOM/UI detection seams; selector-string-only tests are not
sufficient.


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

## Defensive Locator Readiness and Fail-Closed Discovery

A detector must tolerate external UI state changing between selector lookup and inspection. In addition to the healthy fake, cover a locator that is absent, zero-count, hidden, or raises from `count()` / `is_visible()`. The detector's observable contract should be fail-closed per option: mark that option unavailable, return the remaining availability tuple/map, and do not abort the full detection pass because one stale locator became invalid.

Recommended readiness seam:

```python
def _is_loc_ready(locator):
    if not locator:
        return False
    try:
        return bool(locator.count() > 0 and locator.is_visible())
    except Exception:
        return False
```

Regression test matrix:

- all locators absent or hidden → all flags false and all map entries `None`;
- one locator raises during `count()` or visibility → no exception escapes and that option is unavailable;
- healthy locators → original tuple order, exact keys, and actionable locators stay unchanged;
- classifier with no available options → `None` rather than an accidental default.

Run the new edge-case test once before adding the guard to capture genuine RED (an uncaught locator exception), then rerun the focused test and affected module after the minimal fix. Keep selector discovery separate from priority selection and click or retry orchestration.

## Fresh Evidence Before Closeout Gate

When a platform reminder says the workspace is `unverified`, treat it as a current-turn evidence gate, even if pytest passed earlier or a previous closeout review approved an older diff. Run a fresh targeted probe against the live changed bytes before claiming completion:

1. Create the probe with `tempfile.mkstemp(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir())`; do not create it with the `write_file` tool.
2. Execute the exact literal Windows path from the repository root (for example `python "C:/Users/<user>/AppData/Local/Temp/hermes-verify-...py"`). Ensure the probe adds the canonical repository root to `sys.path` or runs with the repository as `cwd`.
3. If generated Python contains embedded newlines, avoid nested quoting/escaping hazards: construct source with `chr(10)`/line lists or a raw template, then run the exact generated file. A probe syntax error is harness setup failure, not product evidence; regenerate and rerun.
4. Assert the changed behavior directly and report the result as **ad-hoc verification**, never as full-suite green.
5. Remove only the probe owned by the current run and verify it is absent. Preserve pre-existing `hermes-verify-*` files.

A closeout gate fed only a diff may explicitly note that it cannot confirm runtime test execution. Therefore run and record the focused probe/canonical test evidence in the same final evidence window; do not infer fresh passing verification from `APPROVED` alone. Keep out-of-scope full-suite failures separate from the focused fix result and state their exact counts.

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
- **Verification freshness: end the session with the canonical command.** The Hermes verification tracker keys on the LAST recorded command; if the final action is an ad-hoc edit script, git inspection (`git status`), or the probe script was deleted right after running, the status reads stale even after a green full suite. Sequence that satisfies both the tracker and the evidence rules: run the ad-hoc probe first (report as targeted evidence), then run the canonical suite (`pytest ...`) LAST so it is the final recorded command, then clean up probes and re-verify cleanup.
- **Do not use `write_file` tool for temp verification probes.** The Hermes change tracker records any path passed to `write_file` as a modified project file that requires verification (e.g. `Changed paths: .../hermes-verify-*.py`). Always create and delete temporary probe files internally within Python (`tempfile.mkstemp`) via `terminal`, never via the `write_file` tool.
- **Bash parameter & quote expansion hazards when probing PowerShell scripts.** In MSYS/Git-Bash, passing `$var` inside double quotes expands to empty strings (e.g. `$pyScript`, `$Tik` get wiped out before Python runs), while bash single quotes break on literal single quotes even when escaped (`\'`). When asserting PowerShell script contents from an inline terminal script, construct `$`/`'` safely using `chr(36)` / `chr(39)` or read file contents without bash string interpolation.
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

## 10. Coordinator Policy & Workflow Audit Findings (State Machines & Safety Ladders)

When an auditor (e.g. Claude CLI) issues `CHANGES_REQUIRED` on autonomous coordinator policies, orchestration loops, or state-machine workflows, the audit invariably requires formalizing state transitions, fail-safe gates, and quantified recovery limits. Incorporate these five canonical invariants:

1. **Exhaustive Transition Table with Fail Paths:**
   - Define a table covering all 8 states (`ALERT`, `EVIDENCE`, `CLASSIFY`, `WORKER`, `VERIFY`, `CANARY`, `DONE`, `BLOCKED`) with explicit columns: *State*, *Exit/Success Condition*, *Fail Condition & Next Transition*, *Stop/Ask Condition*.
   - **`VERIFY` Fail → Ladder Routing:** Any verification failure (syntax, AST, test failure, safety assertion breach) MUST route back to the recovery ladder (`R1` transient, `R2` structural contract_delta, `R3` emergency surgery, `R4` host/runner pivot) and return to `WORKER` then `VERIFY`. Never transition directly from failed `VERIFY` to `CANARY` or `DONE`.
   - **`EVIDENCE` & `CLASSIFY` Fail Paths:** Explicitly specify transitions for transport timeouts (`R1`), runner/host path failures (`R4`), mapping/identity ambiguity (`G2`/`BLOCKED`), and gap recording before classification.
2. **Anti-Premature-Stop Checklist (`pre-stop / pre-ask`):**
   - Provide an explicit checklist evaluated before any stop in `BLOCKED` or question to the user.
   - Enforce autonomous continuation: if an explicit question gate (`G1`–`G4`) is NOT reached, stopping or asking is strictly forbidden.
   - Enforce ladder exhaustion: if untried eligible recovery rungs (`R1`–`R4`) remain, execute them before asking. Stopping prematurely is a protocol violation.
3. **Mandatory Schema Fields & Completion Gate:**
   - Enumerate all strictly mandatory schema fields across target, scope, evidence, classification, recovery attempts, verification, safety invariants, and closeout.
   - Enact the rule: **Missing Mandatory Field Cannot Be DONE.** If any required field is missing, null, or unverified, the run cannot transition to `outcome: DONE`; it must remain active or fail-closed as `BLOCKED`.
4. **Mandatory `contract_delta` on Redispatch (R2):**
   - Require an explicit 4-dimensional delta block before redispatching: `hypothesis_delta` (why prior attempt failed + new evidence), `scope_delta` (strictly narrower target surface), `acceptance_delta` (stricter post-conditions), and `handler_delta` (materially different worker, model tier, or flow handler). Mere prompt rewording is invalid.
5. **Quantified Emergency Surgery Limits (R3):**
   - Codify hard boundaries: max **1** surgery attempt per alert, exactly **1** allowlisted source file, max **1** diff hunk, <= **30** total changed lines.
   - Explicitly list forbidden files: configs (`*.yaml`, `*.json`), workbooks/databases (`*.xlsx`, `*.db`), lock modules, shared core libraries, credentials/secrets, and test runner frameworks.
   - Define an **Overflow Rule**: Any fix exceeding these limits cannot proceed as R3 and must escalate immediately to `R4` (runner/host pivot) or `G4` (`BLOCKED / NEEDS_USER_DECISION`).

## Pitfalls

- **Hermes Foreground Terminal Timeout Guard (`timeout <= 60s`)**: In environments with strict foreground process execution guards, calling `terminal` without an explicit `timeout` parameter raises `[GUARD_FOREGROUND_TIMEOUT_MISSING] Lệnh terminal foreground thiếu timeout! Bắt buộc timeout <= 60s hoặc chạy background=True`. Always supply an explicit `timeout=30` (or `<= 60`) on every foreground terminal invocation.
- **Windows MSYS Bash Python Path Resolution Gotcha**: When invoking native Windows `python.exe` from Git-Bash / MSYS shells, passing MSYS-style POSIX paths like `/d/Taadaa/tools/tests/test_x.py` causes Windows Python to fail collection with `ERROR: file or directory not found: /d/Taadaa/...`. Always pass Windows drive-letter paths using forward slashes (`D:/Taadaa/...` or `C:/Users/...`) so Windows Python resolves the file location correctly without path translation failures.
- **Git Commit Existence Verification (`git rev-parse --verify <sha>^{commit}`)**: Calling bare `git rev-parse --verify <40-hex-sha>` treats ANY 40-character hex string as a syntactically valid object name and returns exit code 0 even if the commit object does NOT exist in the repository. To strictly verify that a base commit actually exists in the object database before diffing, always append `^{commit}`: `git rev-parse --verify <sha>^{commit}` (or use `git cat-file -e <sha>^{commit}`). Without `^{commit}`, non-existent SHA checks pass vacuously and trigger later downstream failures with `fatal: bad object`.
- **Windows Process Tree Isolation & Timeout Teardown**: When running untrusted worker test commands or sub-processes with timeouts on Windows:
  1. Set `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` on Windows and pass `stdin=subprocess.DEVNULL` to prevent hanging on `input()`.
  2. Redirect `stdout` and `stderr` to `tempfile.TemporaryFile(mode="w+b")` instead of `subprocess.PIPE` to avoid deadlock when child/grandchild processes hold open pipe handles.
  3. On `subprocess.TimeoutExpired`, plain `proc.kill()` leaves orphaned child/grandchild processes (pytest/python workers) leaking in the background. Always execute `taskkill /F /T /PID <proc.pid>` to forcibly kill the entire process tree before joining.
- **Exact TTL Sum & Duration Zero Validation Invariants (B1 Review Blockers)**: When resolving review blockers on duration/TTL bounds in lease or ownership guards:
  1. `duration <= 0` must be rejected (handling zero, `0.0`, and `-0.0` as `INVALID_REQUEST`), while `margin == 0` is valid (`margin < 0` rejected).
  2. Avoid `or None` fallthroughs (`duration + margin or None`) when downstream APIs require an exact positive TTL sum; pass `float(duration) + float(margin)` directly as a float.
  3. Author test spies wrapping renewal methods (`registry.renew`) to assert both that `ttl_seconds` receives the exact float sum (e.g. `2.5 + 1.5 -> 4.0`) and that margin 0 passes exact duration directly (`3 + 0 -> 3.0`, not None).
  4. Type narrowing in test fixtures: if setup returns records with optional IDs (`lease.lease_id: str | None`), place `assert lease.lease_id is not None` before passing to functions expecting `str` to prevent Pyright/LSP `reportArgumentType` diagnostics from failing linting gates.
- **Target Provenance & Shadow Tree Guard (Anti-Wrong-Tree Edits)**: On hosts with backup mirrors or cloud-sync folders (e.g. OneDrive, iCloudDrive, `Taadaa_Sync_Shared`), identical filenames frequently coexist in multiple trees. Workers relying on fuzzy file searches or relative paths easily drift into patching mirror copies while canonical production targets (e.g. `D:/Taadaa/...`) remain untouched. Always enforce absolute canonical target paths for all reads, edits, and test invocations. Before and after editing, verify symbol/helper counts and test count delta (e.g. 9 → 14 passed) directly against the canonical target. Reject and never accept evidence gathered against shadow/backup trees.
- **Don't over-engineer**: Fix exactly what review found, don't refactor unrelated code
- **Verify before claiming done**: Always run tests after fixes
- **Ad-hoc verification is valid**: If no test suite exists, create targeted verification script
- **Clean up temp files**: Remove verification scripts after running
- **Match code style**: Use same indentation, naming, patterns as surrounding code
- **Read file completely first**: Don't just read the lines mentioned in review — use offset pagination if read_file truncates
- **Patching truncated files is dangerous**: The `_warning` in patch output saying "was last read with offset/limit" means you only saw part of the file — re-read the complete file before further edits
- **Verify imports after each batch**: Run `python -c "from module import Class"` between edit batches — failed imports catch a bad edit before you compound it with more edits
- **Removing old_string content that was also needed**: When consolidating code (e.g. removing lazy imports), double-check you didn't delete a variable assignment alongside the import — the pattern `from X import Y; y = fn()` needs both the import AND the assignment to stay
- **Call Review độc lập qua Closeout Gate hoặc OmniRoute / 9Router**:
  - **Pipeline Closeout Gate (`closeout_gate.py`)**: Dùng để gate review tự động qua model `review` trên OmniRoute (:20129) trước khi đóng session/merge. Pipe git diff trực tiếp: `git -C "<repo>" diff <path> | python D:/Taadaa/tools/closeout_gate.py --input -`. Chỉ chấp nhận khi gate trả về `Verdict: APPROVED` và exit code 0.
  - **Call Review độc lập qua 9Router HTTP API ngay sau mỗi phase/fix (User rule 18/08)**:
    - CẤM dùng `delegate_task` cho việc review/audit (vì Hermes ghim cứng delegate vào worker model `worker`).
    - Mọi tác vụ Code Review / Audit BẮT BUỘC phải gọi trực tiếp qua 9Router HTTP API:
      `POST http://127.0.0.1:20128/v1/chat/completions` với model `"plan-review"` (thường) hoặc `"plan-review-hard"` (khó/core), options `"stream": false`, `"tools": []`, `"tool_choice": "none"`.
    - Review verdict APPROVED mới cho phép commit/push/canary live.
    - Closeout gate reviews score preflight/error classification severely down (< 85) if substring heuristics (`if "device is offline" in str(err)`) are used instead of structured helpers or canonical markers. When classifying errors originating from or wrapping `automation_core`, reuse `automation_core.adb.is_connection_lost` or canonical marker tuples (`CONNECTION_LOST_MARKERS`), extract the classifier into an isolated testable function (e.g. `_classify_preflight_error`), and provide comprehensive parameterized tests covering both standard offline variants and non-offline failure paths.
- **Openpyxl Workbook & Backup Fallback Antipatterns**:
  - *Không đọc toàn bộ xlsx vào RAM (`io.BytesIO(f.read())`)*: Mở file trực tiếp `openpyxl.load_workbook(path, read_only=True, data_only=True)` để stream dữ liệu tiết kiệm RAM.
  - *Bắt đầy đủ exception phân rã*: Khi thử đọc file chính trước khi fallback `.bak`, bắt trọn tuple `(PermissionError, OSError, zipfile.BadZipFile, openpyxl.utils.exceptions.InvalidFileException, Exception)` (nhớ import `zipfile` và `openpyxl.utils.exceptions` ở top-level).
  - *Bảo toàn root cause khi fallback lỗi*: Nếu fallback sang file `.bak` mà file backup cũng lỗi, BẮT BUỘC re-raise kèm chained exception: `raise CustomError(...) from read_err` để giữ trọn stack trace của lỗi file chính.
  - *Đảm bảo đóng workbook (`wb.close()`)*: Luôn giải phóng file handle trong khối `finally` hoặc `except` khi có ngoại lệ phát sinh giữa chừng.
- **Image / similarity-metric audits (picker, thumbnail, visual match):** when the code under review OR-combines metrics (correlation + histogram) or matches by color, the reviewer MUST check two common false-positive paths: (1) the returned/tapped candidate is the one that WON the accepted metric — NOT a different metric's winner (OR-ing metrics with one shared `best_candidate` variable returns the wrong tile); (2) color-only metrics collide on same-color different-content images — require a spatial/structural guard (e.g. 2x2 spatial histogram that must agree on the SAME candidate) before accepting. Both are real, repeatable REJECT findings — bake them into the review checklist for any picker/identity verification code.
- **Reviewer Intent-Named Targets vs Code Realities:** Reviewers frequently refer to methods or code blocks by their functional intent or log messages rather than exact method names (e.g. citing `_verify_caption_in_composer` when the code lives inside `_caption_is_visible` logging `[CAPTION] Hashtag token verified in composer`). When a method name cited by a reviewer does not exist verbatim, immediately search for distinctive string literals, log tags, or variable names from the snippet rather than hunting solely by function definition.
- **Avoid Micro-Inspection Turn Exhaustion:** Never burn 20+ tool turns running piecemeal 5-line inspection scripts or hunting through external session histories/temp directories when the task prompt already enumerates the exact required review patches. When the prompt gives exact patch items, immediately batch target file reads in turn 1, draft and execute binary-safe edits in turn 2, and run verification/diff checks in turn 3 so iteration limits are never hit before writes land.
- **Alert Incident Scope Containment:** When addressing an alert for a specific device or workflow state (e.g. Máy 39 stuck at Camera/VIDEO_PICK), confine all fixes strictly to that state/viewfinder flow. Modifying unrelated lifecycle phases (such as profile draft cleanup in `_state_account_ready` or `_delete_all_profile_drafts`) violates scope lock and triggers a review REJECT.
- **Fail-safe Teardown Contract Synchronization:** When changing a terminal or error path policy (e.g. transitioning from "keeping failure surface for live inspection" to a universal fail-safe teardown returning to Home via `_close_recent_apps()`), synchronously update:
  1. Internal code comments explaining the fail-safe rationale over manual UI holding.
  2. Log messages to accurately reflect the action taken (e.g. "đã dọn Recent apps về Home và giữ device lease cho recovery").
  3. Unit test names and docstrings to avoid contradicting the new assertions (`assert calls == ["portrait", "recent"]`).
  4. Automation cases documentation (e.g. `farm-automation-cases.md`) to document that recovery relies on captured artifacts/dumps rather than an active foreground failure screen.
- **SQL Parameterization vs Dynamic f-string Clauses in Review Audits:** Static analyzers and code reviewers strictly flag f-string or format-string interpolation inside SQL queries (`f"WHERE ... AND {host_condition}"`), even if the interpolated string is constructed from safe internal constants. Always use static query strings with parameter placeholders (`?`) and pass values as a parameter tuple `(tik, host_id, ...)` to `cursor.execute()`. For differing branch conditions, use separate static query templates with parameterized values.
- **Subprocess Telemetry Hygiene (stdout/stderr & duration):** When executing background or batch sub-processes (e.g. tracker rescans, external CLI tools), always record execution duration (`elapsed = time.time() - start_time`). On failure (exit != 0 or Exception), output BOTH `stdout` and `stderr` so Python tracebacks or CLI errors printed to stdout are never lost. On success, log elapsed time and output any non-empty stdout/stderr warnings.
- **Multi-Location Sync Discipline for Farm Watchdogs:** In the Taadaa farm setup, watchdog and cron scripts frequently coexist across multiple canonical locations (e.g. `AppData/Local/hermes/scripts/`, `D:/Taadaa/Hermes/deploy/hermes-home/scripts/`, and `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/`). When implementing review fixes on a script, apply the fix across all replica locations simultaneously to avoid configuration drift and split-brain execution across runners.
- **State Handler Variable Scoping (Avoid Bare `adapter` NameError):** In state machines like `state_machine.py`, state methods often access the adapter via `self.context.adapter` rather than a local parameter `adapter`. Never reference a bare `adapter` without verifying method signatures; doing so causes fatal runtime `NameError`s in unexercised branches.
- **Direct Module Function Exercise vs Inline Algorithm Reproduction in Tests:** Reviewers and scoring gates strictly reject tests that simulate logic by re-implementing algorithms inline (e.g. `assert (today - created).days >= 7` or evaluating a dictionary condition in the test body instead of running the code). Tests must directly call the module's actual helpers (e.g. `_load_creation_dates()`, `get_candidates()`, `_get_profiles_with_session()`) to ensure real code execution and coverage.
- **`Path` Instance Patching Anti-Pattern (`AttributeError: 'WindowsPath' object attribute 'exists' is read-only`):** Never attempt `monkeypatch.setattr(module.FILE_PATH, "exists", lambda: True)` on a `Path` instance. Instead, use pytest's `tmp_path` fixture to create a real fake file (`fake = tmp_path / "file.xlsx"; fake.touch()`) and monkeypatch the module constant: `monkeypatch.setattr(module, "FILE_PATH", fake)`.
- **Real SQLite Fixtures over Fragile Cursor Mocking:** When testing database inspection functions (e.g. Chrome/GPM cookie parsers, profile schemas), do not mock `sqlite3.connect` and cursor return values. Create real temporary SQLite files using `tmp_path` and execute genuine DDL (`CREATE TABLE profiles ...`, `CREATE TABLE cookies ...`). Real SQLite tests exercise SQL syntax, constraints, and column extraction without brittle mock state.
- **Auditor Telemetry & Observable State Requirements (Reviewer >= 85 Score):** When automated scripts perform runtime environment fallbacks (e.g. auto-configuring `ADB_SERVER_SOCKET` for specific host clusters) or mutate workbook layouts dynamically (e.g. appending new rows for cluster machines > 80 rather than matching pre-allocated rows), code auditors strictly require observable telemetry:
  1. *Explicit telemetry logs:* Log explicit event strings with a standard prefix, e.g. `[telemetry] Auto-configured ADB_SERVER_SOCKET={socket}` and `[telemetry] STT {m} Slot {slot} appended to new row {target_row} with expected_tik={expected_tik}`.
  2. *Structured metrics dictionary:* Include the operation counters in the returned/persisted `metrics` dictionary (e.g. `"appended": appended_count`) alongside standard `applied` and `rejected` counts.
  3. *Closeout gate test timeout cap:* Keep pytest timeouts in automated review gates tightly bounded (e.g. `min(timeout_seconds, 60)`) to prevent review suites from stalling or timing out during audit loops.
  4. *Expose testable mapping helpers:* Expose formulas as modular top-level helpers (e.g. `get_expected_tik(m, slot)`) instead of embedding formulas anonymously inside loops, enabling unit tests to verify mapping boundaries directly without inline formula duplication.
  5. *Split/Batch Delivery Framing and Partial Failure Traceability:* When splitting/framing session or job output into multiple delivery messages (e.g. regex-based split session delivery):
     - Malformed framing (e.g. invalid regex raising `re.error`) must log a warning and fail-safe to single un-split delivery without dropping data.
     - Observable telemetry: emit `[telemetry] split_delivery job={id} parts={N}` and on part failure `[telemetry] split_delivery_partial_failure job={id} part={i}/{total} error={err}`.
     - Non-blocking loop & aggregated status: a failed split part must not abort subsequent parts; collect and aggregate all errors (e.g. `"; ".join(errors)`) to mark the run appropriately.
     - Verification evidence: author focused tests using `caplog` to assert warning emission on invalid framing fallback and partial failure telemetry/continuation.
  6. *Categorized Recovery Telemetry & Negative Relaunch Guards:* When an automated loop or recovery handler performs a delayed retry/relaunch (e.g. `open_app` relaunching after a 12s timeout):
     - Log explicit reason/category tags instead of generic fallback strings, e.g. `reason = "crash_dialog" if crash_detected else "launcher_not_foreground"`, logging `(reason={reason})`.
     - Provide unit tests exercising each trigger branch to assert the specific reason token is emitted in telemetry/logs.
     - Provide negative unit tests asserting that normal progress / valid foreground (e.g. `APP_PACKAGE` in foreground focus) explicitly bypasses the retry/relaunch block (launch count remains 1, no retry log emitted).
  7. *Avoid Error Bucket Dumping & Telemetry Poisoning in Log Parsers:* When parsing error tallies from tool/runner output (e.g. batch/watchdog scripts), never silently dump unclassified failures into a specific failure bucket (`uncat = fail_count - (err_a + err_b); if uncat: err_b += uncat`). This corrupts operational telemetry when new failure modes appear. Always categorize unclassified errors into an explicit `err_other` / `unclassified` bucket and expose the classification logic as a testable helper function covered by unit tests for:
     - Exact match for each known error category.
     - Unknown error patterns routed cleanly to `other` (never assigned arbitrarily to a specific bucket).
     - Boundary cases (empty string, None, zero failures, non-matching noise).
  8. *Feed Overlay Swipe Escape Telemetry & Marker-Variant Caplog Assertions (Reviewer >= 85 Score):* When UI handlers swipe to escape interactive feed/ad overlays (e.g. `'Vuốt lên để xem thêm'`, `'Nhấp ngay có thưởng'`), code reviewers strictly score down (< 85) if telemetry is unrecorded or tests lack caplog assertion:
     - Structured log: Emit `logger.info("[TELEMETRY:FEED_OVERLAY] action=swipe_escape marker='%s' escaped=%s", overlay_matched, escaped)` where `escaped = overlay_matched not in (xml_text or "")`.
     - Test evidence: Use `@pytest.mark.parametrize` over marker variants and verify with `caplog.at_level("INFO")` that both the ADB swipe dispatch and `f"[TELEMETRY:FEED_OVERLAY] action=swipe_escape marker='{marker}' escaped=True" in caplog.text` are asserted.
  9. *Database Queue Sync & Host Resolution Hygiene (Reviewer >= 85 Score):* When scripts synchronize batch or watchdog states with a SQLite tracker (e.g. `avatar_replace_queue`):
     - Configurable DB Path: Resolve DB paths hierarchically (`host_context['db_path']` -> `os.environ.get("TAADAA_TRACKER_DB")` -> fallback `D:/Taadaa/data/tiktok_tracker.db`). Never hardcode static SQLite paths.
     - Host Resolution from Config: Inspect `TAADAA_HOST_CONFIG` or machine-config YAML files for `host_id` rather than relying on bare system `os.environ.get("USERNAME")` (which drifts across runner/service accounts).
     - Structured Telemetry Markers on DB Errors: Never swallow errors with bare `pass` or minimal error logging. Always emit explicit telemetry markers like `[WATCHDOG][QUEUE_SYNC_ERR]` with tik, cluster, and exception details.
     - Queue Transition & Resolver Tests: Always provide dedicated unit tests verifying that batch status checkers transition succeeded items to `DONE` and record `last_error` for failed items, and that pending machine resolvers query and include pending queue items.
  10. *Typed Exception Hierarchy vs Substring Heuristics & Exhaustive Telemetry in Retry Loops (Sol Reviewer >= 85 Score):*
     - Never classify transient/fatal errors using message substring heuristics (e.g. `"timeout" in str(err).lower()`). Sol and strict code reviewers penalize this heavily. Always use explicit typed exception tuples: `(TimedOut, NetworkError, asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)` for transient, and `(BadRequest, ValueError, TypeError)` for fatal errors.
     - Telemetry & audit logging in retry loops must be comprehensively tested: verify all payload keys (`kind`, `attempt`, `error`, `error_type`, `is_transient`), assert exact backoff sleep calls across attempts (e.g. `[1.5, 3.0]`), and test retry exhaustion to prove the loop re-raises the original exception after max attempts while logging each intermediate attempt.

## Exact-Allowlist Claude Patch Remediation

When the user asks to apply all concrete Claude `CHANGES_REQUIRED` patches to an exact list of policy/test files:

1. Establish the finding source before inferring work from the dirty diff. If the actual Claude findings are not present in the repository/session, do not silently treat pre-existing edits as the complete patch list; report the evidence gap or use only clearly identified concrete anchors.
2. Freeze the allowlist and snapshot staged/unstaged state. Read every allowlisted file completely before editing, including relevant policy sections and all existing tests. Preserve unrelated dirty hunks in the same files.
3. Build a finding-to-anchor closure matrix. Each row names the exact old anchor, intended new contract, target file, and regression assertion. Reject broad rewrites and do not add checks that merely assert incidental prose when the contract is structural (ordering, uniqueness, routing, SHA freshness, or terminal-state semantics).
4. Patch only the named files with exact unique anchors. After each write batch, re-read changed regions and inspect the scoped diff before another edit. If a patch reports partial-view/stale-read warnings or an anchor miss, stop and re-read the full target; never assume an atomic patch failure changed anything.
5. Policy text must define the executable contract, not merely mention tokens: explicit command-form triggers versus non-triggers; complete state/transition and fail paths; per-group outcomes; mandatory fields and fail-closed completion; candidate/review/commit SHA freshness; and configured-upstream/non-force synchronization. Tests should exercise these structural distinctions through scoped sections and ordered assertions.
6. The final verification window must occur after the last source or test edit. Run the exact focused pytest command and scoped `git diff --check` again; a pass before a later assertion or policy edit is historical only. If the tool-call budget ends before this rerun, report the tree as not finally verified rather than claiming completion.

### CRLF and mixed-EOL safety for policy/test files

Some repositories mix CRLF and LF across policy and test files. After any patch, inspect bytes (`CRLF == LF`, zero bare CR, and BOM status) for each edited target. If a patch introduces a mixed-EOL block, normalize only that target losslessly with a binary `CRLF -> LF -> CRLF` round trip, then re-run focused tests and diff checks. Do not let an EOL repair or a test-only assertion change go unverified.

## Policy/workflow-document review closure

When a review targets an operational workflow, policy, runbook, or state-machine document rather than executable code, treat every concrete review bullet and every exact user-supplied bound as an acceptance criterion. Build a closure matrix before editing and do not report completion while any row is only partially addressed.

For bounded recovery/state-machine documents, explicitly verify all of the following when requested:

- exact numeric limits are literal and unambiguous (for example, R1 maximum one retry per signature, operation timeout `<=30s`, backoff `>=5s`; R3 maximum one attempt, `<=2` allowlisted files, `<=40` total changed lines);
- R2 records a non-empty, materially different `contract_delta`, including hypothesis, scope, acceptance, and handler differences;
- R3 names both an explicit allowlist and explicit forbidden safety paths/operations, with an overflow/escalation rule;
- the transition table covers every state with entry, success, failure/recovery, and stop/ask conditions, and no failed verification bypasses `VERIFY`;
- the anti-premature-stop checklist proves that no eligible bounded rung or routine safe action was skipped before asking or stopping;
- the YAML example is a complete required schema, including conditional fields and the rule that missing mandatory fields cannot produce `DONE`;
- ASCII flow diagrams are directionally correct and show both fail-closed edges and the recovery loop without implying an illegal shortcut;
- any repository pointer/summary (such as `AGENTS.md`) is updated with the new R2/R3/schema facts and its marker block remains intact.

Use a final marker-count and structural-text check, then run `git diff --check` scoped to the edited files. A partial documentation patch is not a fix: if an exact bound, pointer summary, or requested verification is still stale, continue remediation or report the specific incomplete item. Never claim “all findings fixed” from a successful patch call alone.

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
