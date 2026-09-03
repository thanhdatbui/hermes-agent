---

name: automation-core-consumer

description: "Build and fix consumers of automation-core for Android/TikTok workflows. Covers startup contract, ADB config, workbook mapping, Excel pitfalls, device lock policy, and the Codex↔Claude approval loop."

version: 1.7.1

author: Hermes Agent

metadata:

  hermes:

    tags: [automation-core, android, tiktok, adb, consumer, workbook, openpyxl]

    related_skills: [consumer-scheduler-orchestration, github-code-review, automation-core-development, gemphonefarm-decrypt]

---



# automation-core-consumer

> Reference mới: `references/protocol-v2-reservation-and-datetime-marker-pitfalls.md` (Pitfall `DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE` do thiếu `lock_protocol_version=2`/`queued_v2` trong PowerShell launcher & fix `TARGET_INVENTORY_CONFLICT` do chuỗi datetime trong cột Device ID).


## Benign Popups: Standalone vs Chained Dispatch Invariant (2026-08-29)

- **Anti-Pattern (Predecessor/Chain Token Gating):** Never gate benign popup dismissals (e.g. `detect_facebook_contacts_email_permission_dialog`, `detect_contacts_settings_permission_dialog`, `detect_account_update_prompt`) behind ephemeral predecessor chain tokens (e.g. `add_phone_chain_token`).
- **Root Cause & Behavior:** TikTok renders permission and sync popups both in chained sequences (immediately following Add Phone close) and standalone (spontaneously on Profile navigation, FYP swipes, or app switcher). Enforcing chain tokens causes standalone occurrences to be rejected with `manual-needed:popup` / `unexpected popup/dialog marker detected`, needlessly stopping feed/automation runners to hold the scene.
- **Consumer Dispatch Contract:**
  1. Rely strictly on verified UI XML structure (matching exact title/body strings and canonical buttons) from `automation_core.tiktok.benign_popup`.
  2. Route all recognized benign popups directly to core action mapping (e.g. `dismiss_deny_button` / "Không cho phép").
  3. Ensure `_is_expected_tiktok_focus` permits foreign package focus (such as `com.facebook.katana` / `com.facebook.orca`) whenever the verified benign popup XML is present, without checking `action_label == "Add phone close"`.

## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

Build a consumer of `automation-core` for Android/TikTok automation.  

Repo root is typically `D:\Taadaa\<project-name>\`.



> **Core-side work?** If the task edits `src/automation_core/**` itself

> (recovery / device-lock / scheduler / runner changes, plan-phase builds in

> `.hermes/plans/`), load `automation-core-development` — it covers

> core-repo worktree + branch rules, worktree-src PYTHONPATH testing, and

> recovery-contract invariants. This skill covers the consumer side.



## Tooling pitfall: `search_files` fails on Taadaa repo paths



The `tiktok-luot nuoi acc` repo name contains spaces. `search_files`

(ripgrep-backed) mangles the path through MSYS (`/d/Taadaa/tiktok-luot nuoi

acc/...` does not resolve) and fails with `IO error ... The system cannot find

the path specified`. **Do not retry `search_files` repeatedly on a

space-containing repo path** — switch immediately to:

- `terminal` + `grep -n` with a leading `cd "/d/Taadaa/tiktok-luot nuoi acc" &&`

  (quotes required), or

- `read_file` with the native Windows path (`D:\\Taadaa\\...`).



**Broader than spaces (proven 2026-08-07):** `search_files` also fails with the

same `IO error ... The system cannot find the path specified (os error 3)` on

PLAIN `D:/Taadaa/<repo>/<file>` absolute paths that `terminal` + `grep -n`

handles fine. The ripgrep path conversion for this drive layout is unreliable

in general — when `search_files` errors on any Taadaa path, switch to

`terminal` + `grep -n` (with `cd "D:/Taadaa/<repo>" &&`) or `read_file`

immediately; do not retry the search tool. `git diff`/`read_file`/`patch` are

unaffected; only the ripgrep search tool path-mangles.



Also note: repos with `core.autocrlf=true` + LF source show "LF will be

replaced by CRLF" warnings on `git diff` — harmless; use `git diff --numstat`

for the real insertion/deletion counts and re-check `git diff` after each

`patch` tool edit to confirm no line-ending churn crept in.



**CRLF files: always detect before editing and preserve on append.** Some

tracked files are CRLF end-to-end (e.g. `automation-core/tests/test_ui_dump.py`

— 330 CRLF, 0 bare LF). The `patch` tool matches on LF-normalized text, but an

append via `write_file`/shell `>>` writes bare LF and mixes line endings.

Safe append recipe (keeps CRLF):

```python

path = r'D:/Taadaa/...'; data = open(path, 'rb').read()

assert b'\r\n' in data  # detect CRLF first

payload = NEW_TEXT.replace('\n', '\r\n').replace('\r\r\n', '\r\n')

open(path, 'ab').write(payload.encode('utf-8'))

```

For in-place edits on CRLF files, read bytes → decode → `replace('\r\n','\n')`

→ edit on LF → re-encode with `replace('\n','\r\n')` → write. Verify after:

`python -c "d=open(p,'rb').read(); print(d.count(b'\r\n'), d.count(b'\n')-d.count(b'\r\n'))"`

(second number must stay 0). Strongest one-line proof: all three counts equal

(`crlf==lf and cr==crlf`) → `pure_CRLF: True`.



**Multi-part edit via one python replace-script (validator + tests, proven

2026-08-09):** when the user mandates "python binary, KHÔNG patch tool/sed"

(byte-exact CRLF preservation), write ONE script with write_file (not heredoc —

braces/quotes/unicode get mangled), read bytes → normalize `\r\n`→`\n` in

memory → apply each hunk as `text.count(old) == 1` + `text.replace(old, new)`

(count-assert EVERY anchor!) → re-encode `\n`→`\r\n` → write. Pitfalls hit in

the wild:

- **Unterminated last line**: an anchor built with a trailing `\n` never

  matches a file whose final line has no EOL (`old_tail` count-assert fails).

  Inspect first: `tail -c 200 <file> | od -c`; drop the trailing newline from

  the EOF anchor (this session: file ended `findings)` + nothing).

- **MSYS path mangling when running the script from a D: cwd**: bare

  `/c/Users/...` and `$HOME/...` forms mangle to `D:\c\Users\...` /

  `C:\c\Users\...` (uv python can't open). The form that always resolves:

  `python "$(cygpath -w /c/Users/Kibe/script.py)"` — confirmed working from

  `/d/Taadaa/Tiktok-video` cwd.

- **`$?` after a pipe is the LAST command's exit** — `cmd | tail; echo $?`

  reports tail's status (exit 0 despite findings). Capture the real code:

  `cmd > /tmp/out.txt 2>&1; echo "REAL_EXIT=$?"`.



**Spec-driven multi-file .md rule edits (docs-only, proven 2026-08-08):** editing

AGENTS.md / PROJECT_RULES.md / ui-compatibility*.md rule docs across several

Taadaa repos (e.g. adding one canonical rule ID to 8 files per a PLAN/SPEC) is a

different beast from code edits — the spec mandates exact line endings, exact

anchors, and proof that nothing else changed. Working recipe:

1. **Baseline first**: snapshot each repo (`git status --short` + `git diff

   --stat`) and `file <path>` per target file into

   `D:\Taadaa\coordfallback-baseline-<ts>.txt`. The `file` output is the ground

   truth for CRLF/LF. **A file can be MIXED** ("with CRLF, LF line terminators")

   — `automation-core/docs/ui-compatibility-contract.md` has 290 CRLF + 315 LF

   (25 LF-only lines). Do NOT assume pure CRLF/LF and never "normalize".

2. **Backup outside repos**: copy the target files to

   `D:\Taadaa\coordfallback-backup-<ts>\` (NOT inside any repo — untracked files

   in repos pollute diff verification). Note `D:\Taadaa\.git` exists but is an

   EMPTY directory (not a real repo) — root-level baseline/backup artifacts are

   safe there.

3. **Edit via one Python binary-replace script** (write_file, NOT heredoc —

   heredocs mangle quotes/unicode in git-bash; also `python /c/Users/...` gets

   mangled to `D:\c\Users\...`, so run %TEMP% scripts as

   `python "C:/Users/.../script.py"`): read bytes, for each anchor assert

   `data.count(anchor_bytes) == 1`, replace once, write back. Build the anchor/

   replacement with the file's OWN EOL (`s.replace('\n','\r\n')` for CRLF files,

   plain for LF). Never decode/re-encode the whole file (reflows mixed EOLs).

   - **Anchor-count trap**: summing "CRLF-variant count + LF-variant count"

     double-counts single-line anchors (both variants are identical bytes when

     the anchor has no newline) → occ=2 means 1 real occurrence. Count the

     anchor with the file's actual EOL only.

   - Anchor by unique content, never line numbers; lengthen the anchor until

     unique if it appears twice.

4. **Verify byte-level (strongest)**: script asserts

   `backup_bytes + expected_replacements == current_bytes` for every file —

   proves exactly the intended edits happened, EOL preserved, nothing else

   drifted. Also re-grep the canonical ID across ALL target files (the spec

   usually requires it in every one).

5. **Validator + git diff vs baseline**: run the repo's canonical validator

   (`automation-core/tools/check_ui_compatibility.py --workspace-root D:\Taadaa`

   — checks each consumer AGENTS.md contains `ui-compatibility-contract.md` +

   its registry filename, and each registry record has the 9 concepts).

   **Since 2026-08-09 the per-record completeness check is age-split

   (fail-closed):** records NEW (heading date >= 2026-08-09, or ID/owner

   containing `20260809`/`2026-08-09`) missing concepts are hard findings

   (exit 1); OLD records missing concepts become `registry_record_incomplete_legacy:`

   lines on **stderr** and do NOT fail. Expected healthy state NOW: stdout

   `OK: 9/9 consumers`, exit 0, plus ~66 legacy warnings on stderr — that is

   NOT a regression, it is the rule (no retroactive enforcement of pre-existing

   debt). Binding/AGENTS/registry-missing findings still always fail. Detail,

   `_is_new_record` logic, tests: `references/ui-compat-validator-fail-closed-2026-08-09.md`.

   **Prove findings pre-existing**: if the validator flags files you did NOT

   touch, or the same finding exists in the pre-edit backup, it is pre-existing

   — do not fix out-of-scope files. Small `git diff --numstat` numbers = no

   line-ending churn (a whole-file EOL churn shows hundreds of changed lines).

6. **Concurrent dirty files**: other sessions may edit the same repos. Baseline

   `git diff --stat` numbers for files you must NOT touch must be IDENTICAL

   before/after your work — that is the proof you did not disturb them. Report

   pre-existing validator findings honestly instead of editing out-of-scope files.



Full recipe + reusable byte-verify script skeleton:

`references/docs-rule-edit-workflow-2026-08-08.md`.



Second full pass of the same recipe (2026-08-09 — added the canonical+registry

binding, 2 lines, to Tiktok_Reg + tiktok-log-in AGENTS.md → validator

`OK: 9/9 consumers`): `references/docs-edit-binding-2026-08-09.md`. Two

refinements from that pass:

- **Strict-N-line mandate**: when the task says "THÊM 2 dòng" (exactly N lines,

  no new section header), insert the bullets immediately AFTER the anchor's

  first line (the `##` heading) — deterministic, bare +2 diff. When placement

  is free, mirror the established sections (`## Shared UI Compatibility

  Binding` in `tiktok-luot nuoi acc`, `## UI Compatibility Contract` in

  Tiktok-video); keep the bullet format with backticks around both paths.

- **Pitfall**: verifying backslash paths with regex `grep -c` under bash

  returns 0 for strings that ARE present — use `grep -F`/`grep -Fc`. And for a

  **pre-dirty target file**, snapshot `git diff <file>` into the backup dir at

  baseline, then after editing run

  `diff <(grep '^+' baseline.diff) <(grep '^+' after.diff)` — output must be

  ONLY your new lines; together with `--numstat` that proves the pre-existing

  dirty content is untouched.



**Editing GIANT single-file consumer scripts (social_reg_v1.py ~430KB/10k lines,

proven 2026-08-07):** the `patch` tool's fuzzy matching is DANGEROUS here. On

multi-part edits touching Vietnamese-accented CRLF content it repeatedly

mis-matched and re-indented whole blocks (IndentationError cascades), and one

edit TRUNCATED THE FILE TO 0 BYTES (recoverable via `git checkout -- <file>`).

Rules:

- Keep `patch` edits to small, uniquely-anchored single hunks; after EVERY edit

  re-verify with `python -c "import ast; ast.parse(open(p,encoding='utf-8').read())"`.

- If a patch diff shows unexpected re-indentation of lines you did not touch,

  STOP — the match went wrong. Restore (`git checkout -- <file>`) and switch

  strategy rather than "fixing" the cascade with more patches.

- The reliable workflow for multi-part edits: write ONE standalone Python

  script (repo-local, delete after) that reads the file as UTF-8 with CRLF

  preserved, applies each edit as exact `content.replace(old, new, 1)` with

  `assert content.count(old) == 1` before each replace, `ast.parse()` the

  result, writes to a `_fixed.py` sibling, then `mv -f` over the original.

  Count-assertions catch stale/anchor drift immediately instead of fuzzy-silently.

- Backslashes in Windows paths inside heredocs get mangled by bash — put the

  script in the repo dir and run it with a relative filename, and use forward

  slashes (`D:/Taadaa/...`) inside the Python strings.

- After any edit: `file <target>` must still report CRLF; `git diff --check`

  must be clean; then run the real pytest targets (do not skip verification

  just because the edit was scripted).



**Safe multi-file CODE edits inside automation-core (proven 2026-08-08, jitter

0.4.38):** same baseline+backup+byte-replace discipline as the docs-rule

workflow applies to code edits. Extra pitfalls learned the hard way:

- **NEVER open a real repo file with mode `'wb'` from a debug/throwaway probe

  script — it TRUNCATES.** A "does wb work here?" probe opened

  `src/automation_core/tiktok_popup.py` with `'wb'` and wrote `b'TEST'` → the

  file was destroyed (246 lines → 4 bytes, grep/wc suddenly report 0 lines).

  Test-writes only on temp files. On this host direct `'wb'` is also

  intermittently `PermissionError`-ed while `'ab'`/`'rb+'` succeed — the

  RELIABLE write pattern is write `path+'.tmp'` then `os.replace(tmp, path)`

  (atomic rename; worked even when `'wb'` was denied).

- **Restore must verify sha256, not just "file looks back"**: after

  `cp $BACKUP/a.py $BACKUP/b.py .` the files landed flat at the REPO ROOT (cp

  multi-file to `.` ignores each file's intended subdirectory) while the real

  `src/...` paths still held edited content — only the sha256-vs-baseline

  compare caught it. Copy per-file to its explicit destination, then

  sha256-compare ALL of them against the baseline snapshot.

- **Write long python edit scripts via write_file, run with Windows path**:

  long heredocs with braces break bash ("unexpected end of file from `{'"),

  and `python /d/Taadaa/x.py` mangles to `D:\d\Taadaa\x.py` — use

  `python "D:/Taadaa/x.py"`.

- **Inline python with `&` (bitwise ops) in terminal gets rejected** as

  backgrounding ("uses '&' backgrounding") — put such probes in a script file.

- **FakeAdb tap-call assertions**: `adb.shell(["input","tap",str(x),str(y)])`

  records 4 elements — assert `call[:2] == ["input","tap"]` (NOT `call[:3]`,

  which already includes x) and read the coords at indices `[2]`,`[3]` (not

  `[3]`,`[4]`). Run new tests immediately after writing; pytest catches these

  index mistakes in seconds.

- **Proving a failing test is pre-existing**: grep the failing test file for

  imports of your modified modules (`tap_element|dismiss_popup|from

  automation_core.input`); if no import path touches your code and the file

  was already dirty in the baseline `git status`, it is pre-existing — report,

  do not fix out-of-scope.

- Full session detail (jitter design, evidence-bound jitter=0, verify matrix,

  incident timeline): `references/jitter-core-tap-2026-08-08.md`.



**Nested-function definition-order pitfall (proven 2026-08-07):** inside a big

function, a helper called at line N but `def`-ed at line M>N raises `NameError`

at runtime — and if the call site is wrapped in `try/except Exception`, the

error is SILENTLY swallowed and the helper simply never runs. Found:

`_gmail_pull_refresh(1)` at ~7143 was a no-op because its `def` sat at ~7236.

When moving logic earlier in a function (e.g. pulling a refresh call before a

fast-path), you must move the nested `def`s (and their transitive helper deps)

above the first call site — a "move the defs up" edit, not just a call-site edit.

Symptom to grep for: a call line number < its `def` line number in the same

function body.



otp-gmail pull-refresh-before-fast-path ordering fix (audit F1, 2026-08-07) is

in `references/otp-gmail-refresh-before-fastpath.md`.



**Stale installed `automation_core` shadowing `src/` in pytest (proven

2026-08-07):** the Hermes venv site-packages holds an OLD installed copy

(0.4.40) while the repo `src/` is newer (0.4.43). `python -m pytest

tests/test_ui_dump.py` without `PYTHONPATH` imports the STALE installed

package → tests for recently-added behavior fail (pkill tests failed with

`assert ['pkill','-9','-f','atx-agent'] in ...shell_calls`). Always run

automation-core tests with `PYTHONPATH=src python -m pytest ...` and confirm

the import first: `PYTHONPATH=src python -c "import automation_core.ui as u;

print(u.__file__)"` (must point at `D:\Taadaa\automation-core\src\...`). Same

trap hits the Tiktok_Reg runner tests: `PYTHONPATH="D:/Taadaa/automation-core/src;."

python -m pytest tests/...`.



## New consumer repo scaffold (proven 2026-08-11, tiktok-follow)



Creating a brand-new consumer under `D:\Taadaa\<name>`: copy `AGENTS.md` /

`PROJECT_RULES.md` / `CLAUDE.md` / `.gitignore` from the closest-purpose

sibling, adapt repo-specific strings (title, dev-guide path,

`nurture→<purpose>`, `python_runner→<purpose>_runner`) via ONE CRLF-preserving

python replace-script with count-asserts, then write fresh

HANDOFF/PROJECT_STRUCTURE/CHANGELOG/README, `docs/ui-compatibility.md` registry

skeleton, `docs/ai/<name>-development-guide.md`, and

`requirements-automation-core.txt` pinned to the newest wheel in

`D:\Taadaa\automation-core\dist\`. Runner dir is `<purpose>_runner/` (login_runner

pattern), not `python_runner`.



> **Porting a GemPhoneFarm workflow into the new consumer?** Load

> `gemphonefarm-decrypt` first — it reverses the Protected `.gemphonefarm`

> format (CryptoJS AES-256-CBC, password `!#gemlogin$#&^%*`) and extracts the

> selector/popup/param set that drives the runner design.



- **.gitignore pitfall**: unanchored `runs/` matches a `runs` dir at ANY depth,

  and a directory-level exclude can't be re-included via `!path/.gitkeep` —

  anchor as `/runs/*` + `!/runs/.gitkeep`; verify with `git check-ignore -v`

  (exit 1 = not ignored). `runtime/` stays fully ignored (no .gitkeep).

- **UI-compat validator (`check_ui_compatibility.py`) iterates a HARDCODED

  CONSUMERS list** — a new repo neither breaks the 9/9 check nor is

  auto-discovered; add it to CONSUMERS only once it has real UI records.

- Init with `git init -b master` (siblings use master); push via

  `gh repo create <owner>/<name> --private --source=. --push` (siblings are

  private).



Full recipe + verification: `references/consumer-repo-scaffold-2026-08-11.md`.



**`pip install` wheel bằng path MSYS `/d/...` FAIL âm thầm + wheel trong `dist` stale so với source (proven 2026-08-11, live consumer run):** `/d/Taadaa/automation-core/dist/x.whl` bị Windows-python mangle thành `C:\d\Taadaa\...` → `OSError: No such file or directory`, và nếu lệnh pipe `| tail -1` thì ERROR bị nuốt → tưởng "đã cài core mới" nhưng venv vẫn core cũ → consumer gọi API mới thì `TypeError: _dump_current_ui_unlocked() got an unexpected keyword argument 'expected_marker'`. Luôn dùng driver-Windows path `D:/Taadaa/...` (hoặc `$(cygpath -w ...)`) cho pip install. Và **wheel trong `dist` có thể built trước source hiện tại dù cùng version string** (dist-info còn ghi version cũ hơn; `automation_core.__version__` thậm chí có thể không tồn tại) — khi consumer code gọi API không có trong core đã cài: rebuild `pip wheel --no-deps -w dist .` từ source rồi cài lại, verify bằng `inspect.signature(<hàm thật>)` chứ không bằng `__version__`. Cuối cùng: **check `echo $PYTHONPATH` trước khi chẩn đoán "import sai bản"** — biến toàn cục của session có thể còn trỏ Hermes venv site-packages khiến import automation_core lấy bản cũ từ Hermes thay vì venv consumer; dùng `env -u PYTHONPATH` cho mọi verify import thuần.



## Startup Contract (must follow exactly)



```

ACQUIRE_LOCKS

→ CONNECT_DEVICE / prepare_device (wake, swipe_unlock, lock_rotation)

→ OPEN_TIKTOK

→ DISMISS_POPUPS

→ ACCOUNT_SWITCHER

→ DISMISS_POPUPS_AFTER_SWITCH

→ ACCOUNT_READY

```



- `prepare_device()` is called ONCE from `automation_core.device`. Consumed parameters: `rotation`, `wake=True`, `swipe_unlock=True`, `lock_rotation=True`.

- No TikTok-specific actions before `prepare_device`.

- TikTok-specific upload logic begins only after `ACCOUNT_READY`.



## OPEN_TIKTOK Implementation (must verify feed loaded)



> **Canonical update (2026-08-14):** The force-stop-every-attempt pattern below is retained only as legacy context and MUST NOT be copied into consumers using the current public `automation-core` startup/capture contracts. Current consumers call shared Android/TikTok preparation, then give Splash/loading and transient capture failures a monotonic non-destructive observation window of at least 60 seconds (overall Feed readiness normally 90 seconds). Do not force-stop, relaunch, kill ATX, or reboot during that initial window. After the deadline, recovery is bounded and ordered: one core persistent-backend recovery plus verified recapture, one canonical TikTok relaunch plus a fresh observation window, then optional callback-aware `reboot_and_restore` only when explicitly enabled and all cleanup/recovery/proxy/readiness/verifier callbacks exist. Raw `adb reboot`, raw ATX/uiautomator process killing, and custom boot loops are forbidden. Feed success requires exact foreground package plus semantic Feed markers. Treat the code block below as obsolete for migrated consumers.



The handler **must** do more than just call `adapter.launch_app()`. On some devices (e.g. SM-G930S) the app starts but sticks at SplashActivity — the ADB command succeeds but the UI never reaches the feed. This cascades into `PROFILE_ROOT_NOT_CONFIRMED` during account switching because there is no profile root.



**Legacy pattern — do not use in migrated consumers:**



```python

def _handle_open_tiktok(self) -> bool:

    package = self.context.config["tiktok_package"]

    adapter = self.context.adapter

    feed_indicators = ["for you", "following", "đề xuất", "home_tab",

                       "com.ss.android.ugc.trill:id/home"]



    for attempt in range(1, self.ui_retry_limit + 1):

        # 1. Force-stop guarantees a cold start (resets stuck SplashActivity)

        adapter._adb.shell(["am", "force-stop", package], timeout=10, check=False)

        time.sleep(2)



        # 2. Launch via monkey → am start fallback

        if not adapter.launch_app(package):

            if attempt < self.ui_retry_limit: time.sleep(3); continue

            break  # exhausted → MANUAL_REVIEW



        # 3. Poll UI dump for feed indicators (30s timeout, 2s interval)

        if _wait_for_feed(adapter, feed_indicators, timeout=30):

            return True

        if attempt < self.ui_retry_limit: time.sleep(2)



    # All retries exhausted → MANUAL_REVIEW

    self.context.is_ui_unavailable = True

    self.context.error = (

        f"[OPEN_TIKTOK_FAILED] TikTok không load feed/home sau "

        f"{self.ui_retry_limit} lần force-stop+launch. "

        f"Cần MANUAL_REVIEW: mở TikTok thủ công, kiểm tra login/onboarding."

    )

    return False

```



**Legacy-only notes (superseded by the canonical update above):**

- The force-stop-every-attempt and substring-marker rules below describe unmigrated historical consumers only. **Do not apply them to a consumer using current public startup/capture contracts.**

- A migrated consumer must use one absolute monotonic Feed deadline: the 60-second non-destructive Splash guard is inside the normal 90-second deadline, and B1/B2/B3 may not silently start after that deadline or mint a fresh 60/90-second window.

- Feed proof is exact foreground package + nonempty activity + fresh structured hierarchy + parsed exact semantic markers. Do not reject solely because the activity class contains `SplashActivity`: TikTok 46.x can host a fully rendered Feed in `com.ss.android.ugc.aweme.splash.SplashActivity`; classify loading from fresh semantic XML, not the class name. Never use broad substring checks such as `"following" in xml`, which also matches unrelated confirmation text.

- Freshness must be capture-generation/provenance evidence. A screenshot pixel digest is not a safe generic freshness token because a legitimate static Feed can remain pixel-identical across fresh captures.

- Compatibility probes must be read-only. Never call `acquire_device_lock` with a synthetic target merely to discover its signature; inspect the exact pinned artifact and, if acquisition must be tested, use a temporary `lock_root` plus public release/readback verification.



Detailed deadline composition, pinned-wheel compatibility, freshness, reboot-callback roles, and startup-only gates:

`references/canonical-startup-deadline-and-safe-probes-2026-08-14.md`.



### Soft reboot recovery (optional escalation before MANUAL_REVIEW)



When all `ui_retry_limit` launch attempts fail, the consumer can attempt a **device soft reboot** before escalating to MANUAL_REVIEW. This is gated by a config opt-in (`allow_device_reboot_recovery`, defaults `False` — fail-closed).



**When to add this:** Devices that occasionally enter a deep hang state where even force-stop + cold launch cannot reach the feed, but a full Android boot cycle clears the condition. Samsung S7-era farm devices are the typical case.



**Required pattern — reboot sequence, then retry launch once:**



```python

def _soft_reboot_recovery(self, adapter, package, feed_indicators) -> bool:

    # 1. adb shell reboot

    # 2. adb wait-for-device (120s timeout)

    # 3. Poll sys.boot_completed=1 via getprop (60s timeout)

    # 4. am force-stop TikTok

    # 5. adapter.launch_app(package)

    # 6. _wait_for_feed(adapter, indicators, timeout=30)

    # Return True only if feed confirmed after reboot

```



**Integration point in `_handle_open_tiktok`:** Between the retry loop and the MANUAL_REVIEW block:



```python

# After the for-loop exhausts all attempts

allow_reboot = self.context.config.get("allow_device_reboot_recovery", False)

if allow_reboot:

    reboot_ok = self._soft_reboot_recovery(adapter, package, feed_indicators)

    if reboot_ok:

        return True  # recovery succeeded, workflow continues

    # fall through to MANUAL_REVIEW

```



**Key rules:**

- **Config opt-in, fail-closed** — `allow_device_reboot_recovery` defaults `False`. Must be explicitly set to `True` in the YAML/JSON config file.

- **Log every step** — use `[REBOOT_N/6]` prefix so the log is grep-able during debugging.

- **wait-for-device needs 120s** — some Samsung farm devices take 60-90s to reappear after reboot. The default ADB connection timeout (20s in AdbClient) is too short for this path; pass `timeout=120` explicitly via `adb.run(["wait-for-device"], timeout=120, check=False)`.

- **sys.boot_completed polling** — after `wait-for-device` returns, the device is in `device` state but Android may still be booting. Add a secondary 60s polling loop checking `getprop sys.boot_completed` → `"1"` before assuming readiness.

- **Settle time** — insert `time.sleep(5)` after boot completes before force-stopping or launching. Some devices need a moment after `sys.boot_completed=1` for the UI layer to stabilize.

- **On failure → MANUAL_REVIEW** — if any reboot step fails or the post-reboot launch still can't reach the feed, the handler must fall through to the existing MANUAL_REVIEW path (with `is_ui_unavailable=True`). Never loop back into the retry cycle — reboot is the last resort.

- **Reuses existing infrastructure** — force-stop, `launch_app`, and `_wait_for_feed` are the same methods used in the normal retry loop. No new automation-core changes needed.

- **Error messages include reboot context** — when reboot was attempted and also failed, append "Soft reboot recovery cũng thất bại." to the MANUAL_REVIEW error so the operator knows reboot didn't help.



**Reference implementation:** See `references/device-reboot-recovery.md` for full code, logging format, and the session that introduced this pattern.



### _wait_for_feed helper



```python

def _wait_for_feed(self, adapter, indicators: list[str], timeout=30) -> bool:

    deadline = time.time() + timeout

    while time.time() < deadline:

        try:

            xml = adapter.dump_ui().lower()

            if any(ind in xml for ind in indicators):

                return True

        except Exception:

            pass

        time.sleep(2)

    return False

```



## Device Lock Policy

- **Protocol v2 Reservation Contract**: Xem chi tiết tại `references/device-lock-protocol-v2-reservation-and-datetime-marker-pitfalls.md` khi consumer launcher tạo reservation lock trước khi spawn worker con. Bắt buộc có `"status": "queued_v2"`, `"lock_protocol_version": 2`, và export `$env:CODEX_DEVICE_LOCK_RUN_ID = $runId` để worker claim thành công không bị `DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE`.



> **⚠️ POLICY REVERSED 2026-08-15 (user decision — read first):** User bỏ HẾT

> auto device-lock khỏi consumer repos (tiktok-luot nuoi acc và các repo farm):

> > "T ra lệnh lock máy nào ms đc lock còn k xoá hết auto lock"

> — lock CHỈ khi user ra lệnh cụ thể; KHÔNG auto acquire/release/check/

> FAILED_LOCKED. Lý do: 7000+ lỗi lock/tuần trong log; mỗi lần chạy script phải

> dọn lock cũ 30-60 phút. Các mục lock-retention/takeover bên dưới là tài liệu

> CŨ (policy trước 15/08) — giữ để hiểu lịch sử, KHÔNG áp dụng cho consumer

> đã migrate. **Vẫn GIỮ NGUYÊN**: journal/file lock (bảo vệ đọc-ghi dữ liệu)

> và **lock gan-proxy** (user: "riêng lock của ganproxy là k đc xoá" — gan-proxy

> fleet watcher giữ lock máy, đừng đụng).

> Khi user nói "bỏ lock" — hỏi scope đúng 1 lần (live-entry chỉ / cả flows /

> toàn bộ) rồi làm, đừng hỏi lại nhiều lần (user bực vì hỏi lặp).

> **Lock CÓ THỂ được bật lại theo lệnh user** (16/08: "Lock lại khi chạy"):

> runner `run_tiktok_upload_batch.ps1` pass `--lock-root` khi `$LockRoot` set —

> set `CODEX_DEVICE_LOCK_DIR` (default `C:\Users\Kibe\.codex\device-locks`)

> hoặc param `-LockRoot`. Đây KHÔNG phải đảo ngược policy — user vẫn là

> người quyết định từng lúc.

>

> **⚠️ POLICY CHỐT 2026-08-16 (user — áp dụng ALL repo trong D:\Taadaa):**

> > "T ra lệnh ms đc lock hoặc unlock. Còn cấm auto lock, chỉ đc auto unlock khi success"

>

> Ba mệnh đề bắt buộc:

> 1. **Lock/unlock CHỈ khi user ra lệnh** — không bao giờ tự động.

> 2. **CẤM auto lock** — mọi `acquire_device_lock` mặc định `user_authorized=False`

>    (core trả no-op lease, KHÔNG tạo lock file; lock tồn tại → chạy không lock).

> 3. **Auto-unlock CHỈ khi success** — fail/manual-review/abnormal exit GIỮ lock

>    (status `handoff`), chặn re-run; chỉ success (DONE) mới release.

>    Cơ chế này có sẵn trong state_machine: success → `_release_leases()`;

>    không DONE → `_hold_leases_for_recovery()` (set_status("handoff")).

>

> **Audit "all repo đã nhận rule chưa" (recipe đã chạy 2026-08-16, user: "Quét thêm

> các repo nằm trong taadaa đi"):**

> - Liệt kê repo: `find D:/Taadaa -maxdepth 2 -name .git -type d` (bỏ backup/worktree dirs).

> - Grep từng repo: `grep -rn 'acquire_device_lock\|user_authorized' <repo> --include='*.py'`

>   (loại test/build/dist/venv/.ai-runs/runs — .ai-runs/runs là artifacts, không phải source).

> - **Phân loại từng chỗ gọi theo 3 nhóm**:

>   a. Wrapper re-export từ core (`"""Compatibility import; implementation lives in

>      automation-core."""` — tiktok-log-in, register gmail, tiktok-follow) → kế thừa

>      default False của core, AN TOÀN.

>   b. Gọi `user_authorized=False` tường minh (gan-proxy, Tiktok-video, Tiktok_Reg

>      calibrate/gmail_machine_audit/login flows) → AN TOÀN.

>   c. Gọi theo env `DEVICE_LOCK_ENABLED in {1,true,yes}` (Tiktok_Reg

>      social_reg_v1.py:6738, run_social_batch_deferred.py) → user chủ động bật,

>      ĐÚNG rule.

> - **VI PHẠM THẬT ĐÃ TÌM THẤY + SỬA**: `Tiktok_Reg/device_lock.py:117` là bản

>   device_lock RIÊNG (KHÔNG phải wrapper core) với default

>   `user_authorized: bool = True` → mọi acquire không truyền tường minh sẽ auto-lock

>   khi env bật. Đã đổi default → `False` (commit `5891817`, branch reg-stable-0722).

>   Khi audit: phân biệt wrapper vs bản triển khai RIÊNG — chỉ bản riêng mới cần

>   check default.

> - **tiktok-add-bao-mat-f2a**: wrapper core nhưng 4 chỗ gọi acquire KHÔNG truyền

>   `user_authorized` → thêm tường minh `user_authorized=False` vào

>   run_capture_phase_a.py / run_capture_phase_b.py / run_phase_b_pilot.py /

>   run_batch_live_2fa.py (commit `6fa3d13`). Nguyên tắc: dù default core đã False,

>   ghi tường minh ở mọi chỗ gọi để phòng core đổi default về sau.

> - Sau khi sửa default: chỗ gọi không truyền (`_run_all_targets.py:149`) tự về

>   False; chỗ truyền True tường minh vẫn giữ (chủ đích user).

>

> **Nguồn log chẩn đoán lỗi lock (proof TRƯỚC khi sửa):** log chạy THẬT nằm

> trong **main repo**, không phải worktree:

> - `python_runner/runs/scheduler.jsonl` — lịch sử batch: `"skipped locked

>   machine(s)"` (lock cũ skip hàng loạt → manual-needed), `ImportError:

>   cannot import name 'DeviceLockNeedsUserDecision' from

>   automation_core.device_lock` (mọi batch fail 3.9s từ 14/08)

> - `python_runner/runs/device-lock-release-audit.jsonl` — audit của

>   release-device-lock.py (chính là "dọn cứt lock")

> - `python_runner/runs/schedule-recovery-ledger.jsonl` — ledger 950+ lock refs

> - `~/.codex/device-locks/` — lock thật: `machine_<n>.lock.json` +

>   `serial_<serial>.lock.json`; gan-proxy fleet watcher giữ lock máy 65

> - **PITFALL ImportError pattern:** automation_core installed đã BỎ symbol

>   (vd `DeviceLockNeedsUserDecision`) nhưng consumer vẫn import → mọi batch

>   fail ngay. Verify export thật bằng `dir()` trước khi kết luận "lock lỗi":

>   `python -c "import automation_core.device_lock as d; print([n for n in dir(d) if not n.startswith('_')])"`

> - **Batch chạy MAIN repo, không phải worktree:** worktree phase9-authority là

>   nhánh tách (code mới chưa merge). Hỏi user sửa ở đâu — đừng sửa worktree

>   rồi tưởng đã fix batch thật.

>

> Chi tiết session: `references/device-lock-removal-2026-08-15.md`.



> **⚠️ IMPLEMENTATION 2026-08-16 (commit `bdf5a5b`, `multi_machine_feed_session.py`):**

> "Xoá hết lock" khi user ra lệnh = xoá CẢ cơ chế **prior-evidence skip**

> (`_prior_target_evidence`, `_classify_prior_handoff`, `_write_recovery_handoff_evidence`,

> `_target_lock_aliases`, `_lock_release_proof`, `_verifier_success_proof`,

> `DEFERRED_LOCKED`/`skipped-device-locked` branch + constants) — máy fail lần trước

> TỰ chạy lại mỗi cron (không skip). Cũng xoá `finally` block ghi

> `recovery_lock_handoff.json`. Sau xoá: `NameError: device_lock_paths is not defined`

> có thể xuất hiện = **bug pre-existing** (file dùng hàm không import) — thêm import

> `from core.device_lock import device_lock_paths` (hoặc xoá call), KHÔNG phải lý do

> khôi phục lock. Tests cũ import `_PriorTargetEvidence`/`_write_recovery_handoff_evidence`

> phải xoá kèm (test handoff evidence records terminal state). 273 tests pass sau xoá.



- **Legacy process-conflict scans must match an exact machine argument on the same command line.** Never aggregate-search WMIC stdout: `--machine 1` prefix-matches machines 11/12 and the workflow marker can come from another record. Required TDD matrix and live reconciliation: `references/windows-process-conflict-exact-machine.md`.

- Device lock via `automation_core.device_lock.acquire_device_lock()`.

- Workbook lock via `automation_core.workbook.acquire_workbook_lock()`.

- Locks released in `finally` (via `_release_leases()`).

- **Consumer-side unlock recovery**: After `prepare_device()` returns, if `unlock_state == "locked_or_secure"`, the consumer MUST retry swipe-unlock with more aggressive parameters before proceeding. Do NOT blindly proceed (TikTok won't render on a genuinely locked screen) and do NOT immediately escalate to MANUAL_REVIEW (the core swipe may have been close but slightly mis-timed for this device).

  - Retry swipe from 95% height → 25% height (steeper than core's 85%→35%), with 500ms duration (longer than core's 280ms)

  - Verify unlock via `dumpsys window policy` — check that `mShowingLockscreen=false`, no `keyguardShowing=true`, etc.

  - Up to 3 retry attempts (match `ui_retry_limit` pattern)

  - If retries succeed → continue normally

  - If retries exhausted → `is_ui_unavailable=True` → MANUAL_REVIEW (ask user to unlock manually)

- **Keyguard detection patterns** (reusable module-level constants matching `automation_core.device._window_state()`):



  ```python

  _LOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (

      re.compile(r"mShowingLockscreen\s*=\s*true", re.IGNORECASE),

      re.compile(r"isStatusBarKeyguard\s*=\s*true", re.IGNORECASE),

      re.compile(r"keyguard(?:Showing|Locked)?\s*=\s*true", re.IGNORECASE),

      re.compile(r"showing\s+keyguard", re.IGNORECASE),

  )



  def _is_locked_in_dumpsys(text: str) -> bool:

      return any(pattern.search(text) for pattern in _LOCKED_PATTERNS)

  ```



### Consumer device_lock test migration khi core đổi behavior (catalog 2026-08-15, 5 repos)



Khi merge feature core đổi device_lock semantics (vd `user_authorized`/`DeviceLockNeedsUserDecision`/FULL_SCOPE_TAKEOVER gate), consumer `tests/test_device_lock*.py` vỡ theo ~6 pattern LẶP LẠI y hệt ở mọi repo. Chạy full suite từng repo, phân loại từng fail, sửa test (KHÔNG sửa core). Checklist:



1. **`reservation.release()` sau worker promote** → `DEVICE_LOCK_RELEASE_OWNERSHIP_MISMATCH` (strict release, lease không còn ownership). Fix: `reservation.release_with_audit(reason="queued lease was promoted")` (strict=False).

2. **`old.release()` trong `finally` sau takeover** → cùng lỗi. Fix: `old.release_with_audit(reason="superseded by takeover")`.

3. **`test_release_only_removes_current_owner`** (mutate lock_id rồi `lease.release()`) → strict raise. Fix: `audit = lease.release_with_audit(reason="foreign owner"); assert audit.released_paths == []`.

4. **Lock JSON viết TAY thiếu `lock_protocol_version`** → core coi là LEGACY → `FULL_SCOPE_TAKEOVER` cross-project bị chặn (legacy chỉ takeover qua `SAME_PROJECT_RECOVERY` cùng project — `_takeover_payload` dòng 917-925). Fix: thêm `"lock_protocol_version": 2` (+ `started_at`/`process_started_at` cũ hợp lệ để alive=False proof).

5. **Queued promotion (`_queued_promotion_payload`) đòi 3 điều kiện**: owner `status == "queued_v2"` (wire — KHÔNG phải `"queued"`), `owner_active is not False` (phải True — owner còn reservation), `_owner_process_alive is True`. Test viết tay `status: "queued"` / `owner_active: False` → `DeviceLockUnavailable` dòng 492. Fix: `"status": "queued_v2"` + `"owner_active": True`.

6. **KHÔNG ghi `process_started_at` = "now" trong test** — `_owner_process_alive` thấy process bắt đầu SAU mốc ghi → alive=False → queued promotion từ chối. Bỏ field (rơi về so sánh `started_at` → trả True).

7. **Jitter core trong tap** (`automation_core.input._jitter`, default 6px anti-detect) làm test assert tọa độ chính xác fail (`(20,30)` vs `(26,34)`). Fix trong test: `mock.patch("automation_core.input._jitter", side_effect=lambda coord, _max: coord)` quanh lời gọi tap.

8. **Summary startup thêm step** (vd `battery_level_simulated` giữa wake_unlock và ensure_portrait_rotation) → test assert `summary[2]` cố định lệch index. Fix: tìm row theo action `next(row for row in summary if row["action"] == "...")` thay vì hardcode index.

9. **Dismiss gọi 2 lần** (primary + fallback khi không allowlisted) → `assert_called_once` fail. Fix: `assert dismiss_mock.call_count == 2`.



Pitfall riêng: **2 class `ArtifactManager` KHÁC NHAU attr-set** — `automation_core.artifacts.ArtifactManager` có `root/run_id/run_root` (KHÔNG `run_dir`), còn `automation_core.tiktok.artifacts.ArtifactManager` có `run_dir` (KHÔNG `run_root`, KHÔNG `ensure_dir`). WIP consumer gọi `artifacts.ensure_dir()` + `artifacts.run_dir` → AttributeError. Check import trỏ class nào rồi dùng đúng attr (`run_dir.mkdir(parents=True, exist_ok=True)`).



### Lock retention semantics (MANUAL_REQUIRED / FINAL_BLOCKED)



Classification chia 3 nhánh trong recovery supervisor:

- **DEFERRED_LOCKED** (`lock_safe=False`): lock đang ACTIVE/FOREIGN/BUSY/UNVERIFIABLE → idempotent, không đụng, chờ.

- **MANUAL_REQUIRED** (`lock_safe=True`): sensitive (OTP/2FA/account/mailbox) HOẶC final (cap exhausted/crash) → cần người.

- **AUTO_RECOVERY_PENDING** (`lock_safe=True`): lỗi thường (CAPTURE_INVALID, ADB, network) → tự sửa.



`lock_safe=True` ≠ "giữ lock" — nó nghĩa là **không có lock đang giữ máy**, an toàn để người khác đụng. Lock chỉ giữ khi **đang recovery thật** (owner_active=true).



**Lỗ hổng thiết kế đã sửa (2026-08-06)**: trước đây máy fail (vd CAPTURE_INVALID) → release lock → shift hôm sau nhặt lại y hệt → cày lại 7-slot ladder mỗi lần, tốn quota, không bao giờ tự sửa. `incident_key` = `schedule_day + shift + machine + account_row + failure_signature + artifact_dir` → "terminal" chỉ tồn tại trong cùng shift.



**Fix (consumer-scoped, không đụng core)**: flow `finally` đổi `lease.finish(succeeded=goal_completed)` → `lease.set_status("blocked")` khi fail (giữ lock file, owner_active=false); success giữ `finish(succeeded=True)` (release như cũ). Lock `blocked` không thuộc `_ACTIVE_DEVICE_LOCK_STATUSES` → `acquire_device_lock` từ chối khi shift mới gặp (không takeover nếu không authorize) → máy bị skip, không cày lại.



### Session lock orchestration: device → workbook, release proof (2026-08-12, tiktok-follow P5)



For an engine/runner session that acquires BOTH locks, the proven order and

fail-closed rules (shared-core only — never create consumer-side lock files):



- Acquire device FIRST (`acquire_device_lock(machine=…, serial=…,

  project=<consumer>, run_id=<per-session>, status="running")`), then workbook

  (`acquire_workbook_lock(state_workbook if configured else safe mapping

  workbook, metadata={project, run_id})`). **Workbook acquire fail → release the

  device lease you already own**; if that rollback release itself fails, the

  outcome must escalate to MANUAL_REVIEW, never a "clean skip" with an

  unreleased lease.

- `finally` releases **workbook first, then device**. Use

  `lease.release_with_audit(reason=…)` — the audit (`released_paths`) IS the

  release proof. A release counts as failed when: it raises, OR it returns

  empty `released_paths` while `lease._released` is still False (core only sets

  `_released` when paths were actually deleted — FileNotFound/foreign-owner

  returns empty silently). Record all release errors in result `details` and

  flip a not-yet-failed result to MANUAL_REVIEW — never report success without

  release proof.

- Acquire-error classification (fail closed, never proceed to device ops):

  `DeviceLockUnavailable`, `DeviceLockReadinessError`, workbook `BLOCKED_*`

  → `SKIPPED_LOCKED` (no startup/tap/follow-state write); `DeviceLockTransactionError`

  or any unknown exception → `CONFIG_ERROR`. Keep locked vs config distinct.

- Injectable factory + explicit disable flag: engine takes `lock_factory=None`

  (production default = real shared-core factory with **lazy imports** so the

  consumer module still imports without automation-core on the path) and

  `locks_enabled=True`. Offline tests inject a fake factory OR pass

  `locks_enabled=False` explicitly — never make the production default

  fail-open.

- Not-yet-built mode/flow modules: gate with

  `importlib.util.find_spec("<pkg>.<mod>")` instead of eager-importing —

  missing module → fail-closed CONFIG_ERROR (or a NOT_IMPLEMENTED detail when a

  previous mode already produced results), never an ImportError crash at

  runtime.



Lock-test authoring traps (all hit in the wild):

- **Empty list is falsy**: `device_released_paths or [defaults]` silently

  replaces `[]` — the "unverified release" test never exercises its branch.

  Use explicit `if x is None` checks for list params.

- Fake leases must mirror core's `_released` semantics: `release_with_audit`

  marks `_released=True` ONLY when released paths are non-empty; otherwise the

  engine's release-unverified → MANUAL_REVIEW branch never fires in tests.

- Test-engine helper kwargs: keep engine injectables (`switcher_fn`,

  `identity_fn`, `busy_check`) as EXPLICIT keyword params of the helper; if they

  fall into a `**over` dict that feeds `config_from_dict`, unknown keys are

  silently ignored → the engine silently runs with the real (slow / device-

  touching) default and tests fail confusingly downstream.



Full pattern + code sketch + verification: `references/lock-orchestration-consumer-2026-08-12.md`.



### Guarded stale-lock takeover + startup-only verify (proven 2026-08-14, tiktok-follow máy 1)



User nói "gỡ/mở lock máy X rồi chạy lại" = explicit authorization cho guarded

`FULL_SCOPE_TAKEOVER` trên đúng target. Recipe đã chạy chuẩn end-to-end:



1. **Recheck trước khi đụng** (khớp proof parent): đọc CẢ 2 aliases

   (`machine_<n>.lock.json` + `serial_<serial>.lock.json`), khớp host/pid/run_id/lock_id.

   Verify PID chết bằng **core detector**, không tự parse tasklist:

   `automation_core.device_lock._pid_alive_windows(pid)` (generic: `_pid_alive`) → False = stale.

   Scan process exact-machine: follow_runner VÀ `tiktok_workflow` (consumer đăng video không ghi

   lock store). ADB `get-state` + `ro.product.model`.

2. **Verify signature từ wheel PINNED, không cần install** — PYTHONPATH trỏ thẳng vào file

   `.whl` (zipimport hoạt động):

   `PYTHONPATH='D:/Taadaa/automation-core/dist/automation_core-<ver>-py3-none-any.whl' python -B -c "import inspect, automation_core.device_lock as dl; print(inspect.signature(dl.acquire_device_lock))"`

   → `automation_core.__file__` hiện `...whl\automation_core\__init__.py`.

   **`DeviceLockLease`/`DeviceLockReleaseAudit` nằm trong `automation_core.device_lock` —

   KHÔNG có module `automation_core.lease`** (ModuleNotFoundError khi import thử).

   Audit fields: host, run_id, machine, serial, reason, released_paths, timestamp.

3. **Takeover bằng core API, KHÔNG xóa file tay**:

   `acquire_device_lock(machine=…, serial=…, project=…, command=…, status='running',

   run_id=<mới>, allow_takeover=True, takeover_scope='FULL_SCOPE_TAKEOVER',

   takeover_authorized=True, takeover_reason=…, bypass_proxy_readiness=True)`.

   Sau acquire đọc lại 2 aliases: mỗi file PHẢI có `takeover_from` = {pid, run_id, lock_id} CŨ

   + `takeover_authorization` = {scope, reason} + pid mới = lease.pid — đó là provenance proof.

4. **Release proof**: `lease.release_with_audit(reason=…)` → `audit.released_paths` phải đủ

   2 paths (serial + machine); sau release cả 2 aliases **absent** (không file sót).

5. **Chạy ĐÚNG 1 lần production startup-only** (tiktok-follow):

   `PYTHONPATH=<wheel> python -B -m follow_runner.run_follow --machine 1 --serial <serial>

   --config follow_runner/config.example.yaml --startup-only`

   — `--startup-only` BẮT BUỘC `--serial` (không đọc workbook; `details.lock.workbook=false`),

   zero follow. Verify artifacts `runs/startup-only/<run_id>/`: evidence.json

   `final_feed_verification.passed=true` + PNG decode + ui.xml parse + semantic marker

   (`đề xuất` là feed marker VN hợp lệ; "for you" vắng mặt không phải fail).

6. Post-run: cả 2 aliases absent, không process máy, ADB device, git status không đổi so baseline.



Script mẫu + output shape + lessons: `references/stale-lock-takeover-startup-only-2026-08-14.md`.



### Manual release script (gỡ lock tay)



User cần chạy lại máy bị retained → script `python_runner/scripts/release-device-lock.py`:

```

PYTHONPATH=python_runner:. python python_runner/scripts/release-device-lock.py --machine 60 [--serial ...] [--lock-root ...] [--dry-run]

```

- Từ chối active lock (`owner_active=true`) → exit 3 (fail-closed, không đụng worker đang chạy).

- Release blocked/handoff/temporarily_skipped/queued + stale running (PID chết) → exit 0, xóa file, audit JSONL.

- Dùng core `_release_lease_paths(lease_stub, strict=False)` — không xóa tay; stub cần `host/pid/lock_id/lock_paths`.

- Chỉ release lock cùng host (không reclaim remote host).

- **Windows PID check**: `os.kill(pid,0)` KHÔNG đáng tin trên Windows (PermissionError với PID không tồn tại → coi alive sai). Dùng `tasklist /FI "PID eq X" /NH` (check PID string trong stdout).



Chi tiết đầy đủ + test: `references/lock-retention-manual-release-2026-08-06.md`.



## Runtime reconciliation and focused verification



For Windows watcher/runtime drift, stale `automation_core` imports, scheduled-task wrappers, controlled watcher restart, single-machine reboot proof, and system-requested temporary verification, follow `references/runtime-reconciliation-and-ad-hoc-verification.md`. The key rule is to prove the exact executable's distribution version, imported module path, and function signature; requirements pins and task state alone are insufficient. When a wrapper inherits a global Hermes `PYTHONPATH`, clear it before assigning the consumer scripts path. Treat a temporary `hermes-verify-` probe as **ad-hoc verification**, not suite green, and clean it up after execution.



## ADB



- ADB is NOT in PATH. Must use explicit path:

  `C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe`

- Configurable via `adb_path` config key.

- `DeviceTransport.__init__` and `AdbClient` both consume `adb_path`.

- **Discovery pattern**: Before live run, check actual ADB availability:

  1. Try `adb_path` config key

  2. Fall back to sibling project config: `python_runner/config.example.yaml` has `adb_path: C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe`

  3. Run `adb -s <serial> get-state` AND `getprop ro.product.model` before any live action.

- **Preflight required after code APPROVED**: Fixture approval is NOT sufficient for live readiness. After Claude APPROVED but before first live run, must:

  1. Read the **real** workbook and check header aliases (e.g. `ID` vs `ID TikTok`, `Máy` vs `May`)

  2. Resolve numeric column types (e.g. `Folder Video = 489.0` → folder `489`)

  3. Check machine-first-row selection and serial/device ID extraction

  4. Verify next-video path exists on disk

  5. Run `adb devices -l` with the exact configured ADB path

  6. Verify no machine or serial lock for the target

  7. **Only then** start the live workflow

- **Lock check**: Must check BOTH `machine_<n>.lock.json` AND `serial_<serial>.lock.json`. A stale serial lock (PID dead) does not block but must be noted.

- **`AdbClient.shell()` prepends `"shell"` itself — never pass it as the first arg (proven 2026-08-15).** `src/automation_core/adb.py:206-207` is `def shell(self, args): return self.run(["shell", *args], ...)`. Consumer code calling `self._adb.shell(["shell", "content", ...])` silently executes `adb shell shell content ...` (double-shell → command fails or no-ops). All correct call sites pass the command argv only (`["content", "query", ...]`, `["rm", "-f", x]`, `["input", "tap", x, y]`, `["wm", "size"]`). When auditing consumer diffs, grep for `_adb\.shell\(\s*\[?\s*"shell"` — a match is a bug. Verify against the INSTALLED package (what runtime imports), not just repo source:

  `python -c "import automation_core, inspect; from automation_core.adb import AdbClient; print(automation_core.__file__); print(inspect.getsource(AdbClient.shell))"`.

  Note `device_transport.py`'s `"shell"` entries are raw subprocess argv (direct `adb ... shell ...`) and are CORRECT — only `AdbClient.shell()` args are affected.



## Workbook Mapping Pattern



- `Tik1.xlsx` (D:\\OneDrive\\Tiktok\\Tik1.xlsx) is the canonical workbook.

- Columns: `Máy | device ID (= ADB serial) | ID (= TikTok ID) | Folder Video | video gốc | Keyword Video | Hashtag Pool | Video Đã Đăng | Kiểm Tra Dữ Liệu`.

- **No `account_profile` YAML.** All mapping comes directly from the workbook.

- Each workbook (Tik1, Tik2, Tik3, ...) is an independent workflow.

- Consumer supports `--workflow-workbook` CLI arg to point to any TikN workbook.

- Machine-first-row selection: first row per machine number in the workbook.

- Serial/device ID from the workbook is the ADB serial directly.

- **Workbook lock workaround**: When pandas/permission fails on OneDrive-synced workbooks, use `openpyxl.load_workbook(path, read_only=True, data_only=True)` instead. This avoids file-lock conflicts with OneDrive sync.



### Inventory/Reconcile: Separate Mapping from Credential Tracking



For account reconciliation, do **not** force one workbook to serve two incompatible schemas:



- **Safe mapping workbook** is the source for inventory: machine number, ADB serial/device ID, and expected TikTok IDs. Pass it as `--workbook`.

- **Tracking workbook** (for example `taikhoan_dat_v2_updated .xlsx`) is the source for account/login fields. Pass it separately as `--tracking-workbook`; it is read only when an expected account is missing on-device and needs a login attempt.



Required flow:



```

safe mapping: machine + device ID + expected IDs

→ inspect account switcher

→ reboot/refresh only for an evidenced stale-navigation signature

→ select only expected IDs still missing on device

→ tracking workbook: retrieve the matching account data for those IDs

→ login and verify switcher again

```



Rules:

- Never pass the credential-tracking workbook as the inventory mapping merely because it contains account IDs; it may not have a usable serial header.

- Never derive credentials from the safe mapping workbook; it intentionally omits them.

- The reconciliation CLI should require distinct explicit arguments (`--workbook`, `--tracking-workbook`) and thread the tracking path only into the login-provider selection function.

- Before a live run, run a read-only parser check against the exact safe workbook: selected machine resolves to exactly one serial and the expected account count is nonzero. Treat a schema error as a pre-lock/config failure, not a device failure.

- Add regression tests proving the two paths are distinct and that only `device_missing` IDs are requested from the tracking provider.



### Canonical Header Normalization



Headers have many variants. Always normalize with:

- Unicode NFKC

- NBSP (\\u00a0, \\u200b) → space

- Collapse whitespace

- lowercase

- Strip diacritics (đ→d, ê→e, etc.)

- Known aliases per field (e.g. "ID" / "username" → "ID TikTok")



**"Missing required fields: ID TikTok" — check the CELL, not the header:**

Header `ID` map đúng qua alias → `ID TikTok`, nhưng nếu **giá trị ô trống

(None)** cho máy đó thì `validate_row()` vẫn throw

`AccountSourceError("Missing required fields: ID TikTok")`. Đừng mất thời gian

vào code path/alias — debug theo thứ tự:

1. Chạy `AccountSource(...).read_row()` trực tiếp cho máy đó → xem row keys

   và giá trị `ID TikTok`.

2. Đọc workbook bằng openpyxl in ra header canonical + giá trị các máy fail:

   ```python

   import openpyxl

   from tiktok_workflow.account_source import canonical_header

   wb = openpyxl.load_workbook(path, read_only=True, data_only=True)

   sheet = wb["TaiKhoan"]

   headers = {i+1: canonical_header(c.value) for i, c in

              enumerate(next(sheet.iter_rows(min_row=1, max_row=1)))}

   # ... in row theo máy, check headers[c] == "ID TikTok" và giá trị

   ```

3. Header map ổn mà giá trị None → **dữ liệu workbook thiếu**, báo user điền

   hoặc loại máy đó khỏi danh sách chạy (không phải bug code).



**Serial column aliases** (all known variants — missing one causes `CONFIG_ERROR: account workbook is missing serial column`):

- `"so seri"`, `"series model may"`, `"phoneid"`, `"phone id"`, `"serial"`

- `"device id"`, `"deviceid"` ← real-world workbooks often use "device ID" as the column header

- When adding a consumer, always check the actual workbook column headers with `openpyxl` before hardcoding `SERIAL_HEADERS`.



### `taikhoan_dat_v2_updated .xlsx` column layout (verified 2026-08-10)



Source tracking workbook `D:\OneDrive\Tiktok_Reg\taikhoan_dat_v2_updated .xlsx`, sheet `Tài Khoản`:



| idx | Header | Ghi chú |

|---|---|---|

| 0 | Máy | |

| 1 | Tik | |

| 2 | ID | TikTok ID |

| 3-6 | PASS / 2FA / GMAIL / PASS MAIL | credentials — không in/log |

| 7 | NGÀY THÁNG NĂM SINH | DOB |

| 8 | NGÀY TẠO | |

| **9** | **device ID** | **= serial/ADB serial — cột serial ĐÚNG** |

| 10 | (không header) | rác — không đọc |



**Pitfall shifted columns:** có lịch sử 23 dòng bị lệch 1 cột — DOB/NGÀY TẠO đẩy sang phải,

serial rơi xuống cột 10 (K). Script cũ `tiktok-log-in/scripts/sync_taikhoan_run_safe.mjs` đọc

`row?.[10]` (SAI) → `SOURCE_SERIAL_CONFLICT:<máy>:0` khi source gần như không còn serial ở cột đó.

**Luôn đọc serial ở idx 9, và xác nhận bằng regex serial** (`^[0-9a-fA-F]{14,20}$`) thay vì tin vị trí

cố định — nếu cột 9 toàn ngày tháng (dạng `dd/mm/yyyy`) thì đang lệch cột, cần shift

(c10→c9, c9→c8, c8→c7) trước khi đồng bộ.



**Canonical sync script:** farm tự động rebuild `taikhoan_run_safe.xlsx` qua

`tiktok-luot nuoi acc/scripts/sync-safe-workbook.py` (đọc header linh hoạt, EXTRA_MACHINES 75-80,

6 slots/máy, atomic publish qua `single_writer_workbook_update` + reopen-verify). Đừng viết script

sync mới — tái sử dụng script này; wrapper cron chỉ cần gọi nó (xem

`consumer-scheduler-orchestration/references/hermes-cron-watchdog-sync-example.md`).



### Excel Data Type Pitfalls



- `Folder Video` can be an int/float (489 or 489.0). Must convert safely:

  `int(x) → str(x)` for int, `str(int(x)) if x == int(x) else str(x)` for float.

- `Video Đã Đăng` can be int/float/None. Must int-cast with zero default.

- `EmptyCell` (openpyxl read-only mode) has no `column_letter`. Iterate by index.

- `video_number` override must propagate to `context.video_number` and workbook write.



## ACCOUNT_SWITCHER Error Handling — Simplified (v2)



`_handle_account_switcher()` calls `open_profile_root()` then `open_switcher()` from `automation_core.tiktok.account_switcher`. The consumer must **NOT** add fallback tiers, coordinate hacks, subpage-clearing helpers, or recovery pipelines. Core is the single source of truth for navigation.



> **Canonical update (2026-08-14, tiktok-follow):** core ≥ 0.4.44 provides a

> 3-API switch+verify flow. Consumers on current core must call

> `open_account_switcher(adapter)` → `select_exact_account(adapter, expected)`

> → `verify_selected_account(adapter, expected, xml_text=post_xml)` instead of

> the 2-call pattern below, and must NOT add a separate identity tap after

> selection (the post-select XML returned by `select_exact_account` IS the

> verification input). The v2 pattern remains only for consumers pinned to

> older core lacking those entrypoints. Full API facts + test design:

> `references/account-ready-only-canonical-switcher-2026-08-14.md`.



### Required pattern



```

_handle_account_switcher():

  1. if not dismiss_popups_core(): return False  ← check is_ui_unavailable after dismiss

  2. open_profile_root(adapter)                  ← core call, no consumer fallback

  3. if not dismiss_popups_core(): return False  ← popups may appear after profile loads

  4. open_switcher(adapter)                      ← core call, no recovery tiers

  5. if not dismiss_popups_core(): return False  ← popups after switcher opens

  6. return True

```



**CRITICAL — check is_ui_unavailable after every _dismiss_popups_core() call.**

`_handle_dismiss_popups()` can fail silently (UI dump exception sets `is_ui_unavailable=True` and returns `False`). If the caller ignores the return value, the state machine proceeds into core navigation with a broken UI, producing confusing downstream errors. Always gate: `if not self._dismiss_popups_core(): return False`.



On ANY core failure (AccountSwitcherError or other exception):

- Set `context.is_ui_unavailable = True`

- Populate `context.error` with `[ACCOUNT_SWITCHER_FAILED]` + core error + MANUAL_REVIEW instructions

- Save checkpoint

- Call `_detect_account_switcher_edge_cases()` for CAPTCHA/login detection

- Return False → state machine routes to MANUAL_REVIEW



### Helper methods



```python

def _dismiss_popups_core(self) -> bool:

    """Dismiss popups best-effort using core module.



    Returns:

        True nếu dismiss OK (hoặc không có popup), False nếu is_ui_unavailable bị set.

    """

    try:

        self._handle_dismiss_popups()

    except Exception:

        pass  # Best-effort

    return not self.context.is_ui_unavailable



def _fail_account_switcher(self, err_msg: str) -> None:

    """Centralized error logging → MANUAL_REVIEW."""

    self.context.is_ui_unavailable = True

    full_msg = (

        f"[ACCOUNT_SWITCHER_FAILED] {err_msg}. "

        f"Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa, "

        f"dismiss popup/onboarding thủ công rồi retry."

    )

    self.context.error = full_msg

    self.context.checkpoint.update({

        "last_state": WorkflowState.ACCOUNT_SWITCHER.value,

        "error": full_msg,

    })

    logger.error(full_msg)

    self._detect_account_switcher_edge_cases()

```



### Rules



- **No consumer-side recovery.** Do NOT add `_fallback_tap_profile_tab`, `_reset_to_home_feed`, `_reopen_tiktok_clean`, `_clear_profile_subpage_before_navigation`, or `_verify_clean_profile_root`. These have been removed from all consumers.

- **Only core: `open_profile_root` and `open_switcher`.** Do NOT import `leave_profile_subpage`, `is_switcher_open`, `is_profile_subpage`, or `find_switcher_anchor` from the consumer. Core handles all internal retries and subpage clearing.

- **All failures → MANUAL_REVIEW.** A device that can't navigate to profile/switcher after core's internal retries needs human intervention, not a job-level retry.

- **Dismiss popups before and after** every core navigation call. Use the existing `_handle_dismiss_popups()` which delegates to `automation_core.popup.detect_popup`.



### Core `coordinate_fallback` adapter hook (2026-08-07)



Core's `open_switcher` (and via delegation `open_account_switcher`) now honours

an optional adapter hook `coordinate_fallback(action: str) -> tuple[int, int] | None`.

Call order when no semantic anchor resolves: `switcher_image_point` → hook

(`action="switcher"`) → else raise `SWITCHER_ANCHOR_AMBIGUOUS`. Hook absent or

returning `None` = exactly the old behaviour (no crash, no TypeError) — fully

backward compatible. A consumer with a legit coordinate need (stale/frozen dump

on a specific device) should implement THIS hook, not any consumer-side

coordinate hack. Contract wording, call-site order, and pytest recipes for the

hook (with/without hook, XML fixtures that reliably yield no-anchor):

`references/account-switcher-coordinate-fallback-2026-08-07.md`.



### Consumer adapter hook seam — durable fix for SWITCHER_ANCHOR_AMBIGUOUS (proven 2026-08-15, tiktok-follow máy 1)



The bounded ladder (above, 2026-08-14) is a BAND-AID. Root-cause audit of a

fresh run (`follow-1-dcc073efdd4a`, log `/tmp/tiktok-follow-m1-accountready-*.log`)

proved the durable failure is a MISSING CONSUMER SEAM, not the transport blip:



- Core ≥ 0.4.44 `open_switcher`/`open_account_switcher` honour backward-

  compatible adapter hooks: `profile_identity(xml) -> dict`,

  `coordinate_fallback(action) -> (x,y)|None`, `recover_ui_dump()`,

  `restart_profile_navigation()`, `tap_profile()`, `switcher_image_point()`,

  `prepare_switcher_anchor()`. An adapter with NONE of them raises

  `SWITCHER_ANCHOR_AMBIGUOUS` whenever the capture returns a profile-root XML

  missing header identity nodes (ATX/transport-degraded tree).

- **Artifact forensics (no success artifact → read `%TEMP%`):** the run's UI

  timeline is reconstructible from

  `%TEMP%/automation-core-ui-capture/ui_capture_*.json` (outcome

  VERIFIED_SUCCESS, `xml_bytes`+`node_count` per capture) and

  `ui_dump_error_*.json` (outcome FINAL_BLOCKED, `failure_signature`,

  `transport_failure`). Sort by mtime: fresh run was Feed (20 nodes / 8835 B)

  → Profile (11 nodes / 4794 B) → `ADB_TRANSPORT_LOST_AFTER_VERIFIED_PERSISTENT_CAPTURE`

  → shell-fallback HTTP 502 + timeout. Post-failure recapture stayed TikTok

  Feed, switcher closed, `followed=[]` — clean fail-closed, no login/OTP surface.

- **Offline replay against the PINNED wheel (decisive, no device):** unzip the

  exact wheel (`unzip -o -q <whl> -d /tmp/acNNN`), then

  `sys.path.insert(0, '/tmp/acNNN')` and call

  `find_switcher_anchor(xml, identity, allow_generic_header=True)` on real

  probe XML. Canonical profile root (máy 1, TikTok 46.x): resolves `sf5`

  (username `@…`, clickable) with identity=None, `sd0` (display name) with

  `profile_identity` → tap target proven. Degraded 11-node XML (no header

  name/username): returns `None` regardless of identity → the exact raise path.

- **Stable máy-1 locators:** profile header `com.ss.android.ugc.trill:id/sd0`

  (display name, clickable) / `:id/sf5` (username, clickable) are the switch

  anchors; `_is_profile_root` is true via selected bottom tab + `sửa hồ sơ`

  fallback. `sf5` single-match is also mode2's own identity gate idiom.

- **Minimal canonical fix = TDD RED→GREEN at the public hook seam:** add

  `FollowAdapter.profile_identity(xml_text=None)` and delegate parsing to

  `automation_core.tiktok.profile.profile_identity_from_xml`. Return only

  `{"display_name", "username", "allow_generic_header": True}`; strip known

  Profile control labels from `display_name`, clear any non-`@` username, and

  return empty values on exception/missing identity. Core alone then applies

  `find_switcher_anchor` and owns the semantic tap. Add three proofs: parser

  output resolves a fake header, a header-less tree stays anchor-less, and

  `open_switcher(pre_confirmed_xml=...)` opens through the hook without any

  consumer navigation/coordinate fallback. Do not add

  `coordinate_fallback`/`restart_profile_navigation`/`recover_ui_dump` without

  a later artifact proving that specific seam is required.

- **Gate the materially-different live run:** exact-byte independent audit must

  approve the final hashes after tests/compile/diff-check. For a retained

  failed lease, verify both aliases contain one exact lease and the old PID is

  dead, then use guarded `FULL_SCOPE_TAKEOVER` and

  `release_with_audit`; require both released paths and both aliases absent.

  Run exactly once. If it fails, retain the new dual lock and do not blind

  retry.

- **Do not equate anchor progress with checkpoint success.** A hook can remove

  `SWITCHER_ANCHOR_AMBIGUOUS` yet the same run can correctly end

  `UI_DUMP_FAILED` when fresh artifacts show real

  `ADB_TRANSPORT_TIMEOUT`, HTTP 502, shell null-root, or shell timeout under

  the full caller deadline. Classify this as transport/capture failure, not as

  proof the hook failed. Verify `followed=[]`, no success artifact, no target

  process, final screen classification, and retained lock; stop there pending

  explicit operator review.

- Verdict rule: when the pinned core already exposes the hook and the consumer

  just doesn't implement it, that is a consumer code fix, not a live blocker.

  A subsequent fresh transport/capture failure is a separate fail-closed live

  outcome and must not trigger another automatic code change or rerun.



Full artifact timeline, implemented hook/TDD/audit evidence, and post-hook

`UI_DUMP_FAILED` boundary:

`references/account-ready-anchor-hook-seam-2026-08-15.md`.



## Tiktok_Reg relaunch: gate tự block chính nó + repo scoping (2026-08-11)



Chạy lại `social_reg_v1.py <stt> --resume` có thể bị `MACHINE_IN_USE` dù không có worker thật:

gate quét cmdline process chứa `social_reg_v1.py <stt>` rồi loại trừ chain ppid của chính mình —

nhưng chạy qua `env -u PYTHONPATH` trong git-bash chèn process `env.exe` trung gian làm đứt chain

→ bash wrapper của CHÍNH lệnh đang chạy bị tính là external → self-block (log `BLOCK pid=<wrapper>`).

Cách chạy an toàn: (1) dọn mọi process cmdline khớp script bằng PowerShell Stop-Process, (2) xoá

lock `handoff` PID chết ở `~/.codex/device-locks/{machine_<stt>,serial_<serial>}.lock.json`,

(3) chạy bằng `PYTHONPATH= python ...` (bash assignment, KHÔNG `env`) để python là con trực tiếp

của wrapper. OTP reader Hotmail dùng `_outlook_newest_tiktok_row` (mail mới nhất theo time_evidence,

fail-closed nếu không có code 6 số); `--resume` chỉ dùng khi màn target còn focus — flow đã thoát

về feed account cũ thì restart từ đầu là lựa chọn duy nhất.



**Repo scope:** chat TG gắn 1 repo — chỉ báo/xử lý máy thuộc repo đó (m30 reg = Tiktok_Reg,

m74 upload = Tiktok-video), không lôi trạng thái repo khác vào status report.



Chi tiết + lệnh cleanup đầy đủ: `references/reg-relaunch-gate-self-block-2026-08-11.md`.



## Recovery-adapter migration — P2+ consumer runtime integration pattern



Use this class-level pattern whenever a consumer must adopt the shared `automation-core` recovery control plane after discovery has proved a real offline-testable seam (login, reconcile, mail, proxy, or similar). The consumer adapter maps runtime outcomes; it must not create a second retry/orchestration system.



### Mandatory phase gates



1. **Isolate and baseline.** Create a dedicated worktree from the exact base SHA; leave the dirty source checkout untouched. Read the consumer rules and discovery report. Run the exact combined focused suite named by the plan *before writing*. Record the interpreter, installed `automation-core` distribution version, and imported module path; a requirements pin or worker self-report is not proof of the runtime package.

2. **RED first.** Add the smallest focused adapter test in the allowlist and run it against HEAD. The failure must identify the missing runtime contract, not a typo or a collection/import accident. Do not create an unplanned intermediate adapter module.

3. **GREEN at the proven seams.** Patch only the production choke points and the core pin. Preserve the consumer's existing local retry behavior; map it into core instead of adding another loop. Use fixture/fake adapters and temp artifact roots only—never live device, credential, workbook, or provider actions.

4. **Audit before integration.** Independently inspect the full diff (including removed lines and export lists), run focused tests, compile/import checks, and `git diff --check`. Use the explicit approved audit model required by the project. No commit, rebase, merge, or push follows a worker completion label alone.



### Outcome mapping contract



- Intentional terminal consumer outcomes (`FAILED_SAFE`, terminal account states, invalid/credential/identity failures) map to core `NON_RETRYABLE`; they do **not** consult AI escalation.

- Retryable inventory/UI/network outcomes call the shared `RecoveryHandlerRegistry`/`EscalationRegistry` at the proven seam. Keep normal recovery budget (`RecoveryPolicy.max_meaningful_attempts`, normally 8) separate from the AI escalation budget (normally 3); a consumer may tighten a cap but never silently substitute one for the other.

- A repeated/final local failure such as `FINAL_BLOCKED` after its bounded restart/reboot allowance is exhausted must finalize the durable core queue as `FAILED_LOCKED` and retain the device lock. Assert the persisted queue state and restart behavior—not merely the returned result status.

- Missing handler, hook exception, timeout, invalid proof, or proof-free hook success is fail-closed: `FAILED_LOCKED`, no release, no watchdog/scheduler re-fire. A hook success is release-relevant only when it is backed by a valid recapture artifact and passed verifier proof; the core's `proof_backed` contract is the authority.

- If discovery finds no runtime call-site for a proposed feature (for example guided recovery), record it as disproved/needs-proof and do not invent a new feature just to satisfy the plan.



### Evidence and async-worker pitfalls



- A notification such as `ASYNC DELEGATION BATCH COMPLETE` without the consolidated result, changed-file list, test output, and verifiable artifact is **not** implementation evidence. Reconcile the exact worktree (`status`, branch/HEAD, diff, mtimes) and run the verifier yourself; if source is still at base, keep the phase pending.

- Classify baseline failures against the pre-write combined run. Preserve unrelated sibling/environment failures; never edit an out-of-scope repository merely to make the migration suite green.

- For core upgrades, verify the actual target wheel and `automation_core.__file__`; clear inherited `PYTHONPATH` (`env -u PYTHONPATH`) on every Python/pytest command. Build or install the validated wheel outside the core repository when needed.



Detailed login/reconcile seam matrices, queue assertions, and RED/GREEN command templates are in `references/recovery-adapter-p2-consumer-pattern.md`.



## Recovery-adapter migration — P1 Discovery + baseline-only workflow (proven 2026-08-12, `tiktok-luot nuoi acc` pilot)



When a consumer must be wired to the shared-core recovery machinery (registry +

EscalationHook, core pin bump), the FIRST phase is read-only discovery in an

isolated worktree — never patch production/test/pin in the same step. Exact

workflow (mandatory order):



1. **Isolate**: create a dedicated worktree from the EXACT base SHA the brief

   pins (`git worktree add -b <branch> <wt-path> <sha>`), never touching the

   dirty original repo (no reset/clean/stage; keep every git call on it

   read-only). Preflight record: repo identity, base SHA, worktree status,

   branch, and a status-only snapshot of the original repo's dirty state.

2. **Baseline BEFORE any write**: run the exact focused offline suite named by

   the plan/rules as ONE command (`python -B -m pytest -q -p no:cacheprovider

   <exact files>`), save output outside the repo, record collected/error/pass

   counts + pre-existing classification. Per-file runs are diagnostics only

   (collection differs standalone vs multi-file). Record ambient interpreter

   + installed `automation_core` dist version — the pin file is not what

   pytest imports.

3. **Trace the runtime call-site with FACT path:line only** — the plan's

   discovery candidates are read-only; other files may be read to trace

   callers. For the feed-session pilot the proven chain was:

   `run_tiktok.py:959-968` (mode dispatch) → `flows/feed_swipe_smoke.py:17701`

   `feed_session_smoke` → `:14360` `_feed_session_flow` → `:990`

   `_capture_xml_text` → `core/ui_capture.py:94` `capture_required_ui_result`

   → `:217` `recover_capture_stack` / `:257` `recover_capture_deadline`

   (`core/capture_recovery.py:7263/7724`) → UIDumpError

   `CAPTURE_RECOVERY_ATTEMPT_BUDGET_EXHAUSTED` / `FINAL_BLOCKED` →

   `feed_swipe_smoke.py:1020-1043` terminal branch.

4. **Answer the gate question explicitly**: `build_recovery_handler_registry()`

   (`scheduler/recovery_handlers.py:689-713`) was built ONLY at

   `scheduler/recovery_runtime.py:2928` (scheduler/supervisor main) and

   consumed only via `validate_required_handlers` (:1032) and

   `validate_handler_gate` (:1700/:2101) — i.e. scheduler-gate-only, NOT in

   the in-process feed path. The feed path has its own flow handlers

   (`flows/recovery_handlers.py` uses `classify_tiktok_screen` at :211) and

   capture ladder. Conclusion for P1: registry wiring must be ADDED at the

   proven runtime seam, not assumed present.

5. **Prove the seam is offline-testable**: the seam (`feed_swipe_smoke.py:

   1020-1043`) already has hundreds of offline tests patching

   `_capture_xml_text` / `capture_ui_xml`; `ui_capture.py:110-112` already

   accepts a `capture_recovery_callbacks` opt-in that the feed flow does not

   pass. Mark ASSUMPTION/NEEDS_PROOF explicitly (multi-machine path, wheel

   0.4.45 binary compat, watcher scope); never invent symbols.

6. **Pin contract check by reading only**: pin file

   (`requirements-automation-core.txt`) vs core `pyproject.toml` version vs

   source names in `src/automation_core/{__init__,recovery,escalation}.py`

   (register/require/validate_required, EscalationHook budget). No installs,

   no live runs.

7. **Conclusion rule**: `READY_FOR_P1_IMPLEMENTATION` ONLY if a concrete

   offline-testable runtime seam is proven; otherwise `NEEDS_PROOF` and stop

   the pilot. Never claim live-connected.

8. **Post-write verification**: re-read/hash/stat the report, markdown/diff

   check, confirm no source/test/config/requirements changes (tracked-file

   digest manifest before/after), confirm original repo status — and

   reflog-check for foreign commits that moved the original HEAD mid-session.



Key facts from the 2026-08-12 pilot: `_SENSITIVE_MARKERS` already contains

`MANUAL_NEEDED_POPUP` (`recovery_supervisor.py:1151`); `pm clear` = 0

occurrences in non-test `python_runner/**/*.py`; `REQUIRED_FAILURE_CLASSES =

(CAPTURE_INVALID, MANUAL_NEEDED_POPUP)`.



Full call-chain trace, baseline evidence, and report anatomy:

`references/recovery-adapter-p1-discovery-2026-08-12.md`.



## Recovery-adapter migration — P1 RED/GREEN implementation (proven 2026-08-12, feed pilot)



After discovery proves the seam, the RED→GREEN phase has its own traps (all

hit in the wild this session):



1. **Venv pinning trap: `python -m venv` on this host silently creates a

   BROKEN venv.** In git-bash, `python` resolves to the Hermes-agent venv

   python, so the new venv's `Scripts/python.exe` still imports site-packages

   from the HERMES venv, not its own. Diagnostic: `pip install` prints

   "Not uninstalling <pkg> at ...hermes-agent\venv\lib\site-packages, outside

   environment <new-venv>" and `import automation_core` resolves to the hermes

   copy. Create the venv with the REAL interpreter's absolute path

   (`C:/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe -m venv

   <path>` — this host runs Python 3.12.4; `py -3.11` has NO runtime and MSYS

   `python` resolves to the hermes venv), then VERIFY before installing:

   `python -c "import sys, automation_core; print(sys.executable, automation_core.__file__)"`

   must show the new venv's python + its own site-packages, `sys.path` must

   contain no hermes-agent path, and `pip show automation-core` must list the

   target version. Recreate rather than "repair" a poisoned venv. Also prefix

   EVERY python/pytest command with `env -u PYTHONPATH` — the session's global

   PYTHONPATH points at hermes site-packages and silently re-poisons even a

   clean venv (the actual root cause of "venv cũ hỏng").

2. **Strict per-phase file allowlist: the wiring goes INTO the allowlisted

   files, never into a new intermediate module.** Creating

   `flows/<name>_adapter.py` when the plan says "CREATE only

   tests/test_<x>_pilot.py" violates the allowlist even if the module is

   clean. Put the runtime helper(s) directly in the proven seam file

   (`flows/feed_swipe_smoke.py` SEAM A terminal branch) and the registry/hook

   exposure in the registry file (`scheduler/recovery_handlers.py`); the RED

   test imports those symbols. Re-check `git status --porcelain` after every

   write — a stray `??` file is an allowlist violation.

3. **RED must run in the PINNED venv (0.4.45), not the ambient hermes venv

   (0.4.43).** New core modules appear between versions (`escalation` is

   absent in 0.4.43, present in 0.4.45): running the new test in the old env

   yields a misleading collection error (`ModuleNotFoundError: No module named

   'automation_core.escalation'`).

4. **Make RED test collection survive the missing feature**: import future

   wiring symbols behind try/except and `pytest.fail("FEATURE_MISSING: ...")`

   inside each wiring test. One collection ImportError blocks ALL tests

   (including the core-contract tests that must be shown passing); guarded

   imports give per-test RED failures with a clear reason.

5. **Build the target wheel from core source, output OUTSIDE the core repo**:

   `python -m pip wheel --no-deps -w <out-dir-not-in-repo> D:/Taadaa/automation-core`

   (setuptools backend; `dist/` is inside the repo — building there dirties

   it). Record `sha256sum <wheel>` for evidence; a locally rebuilt wheel's SHA

   differs from a previously cached one — document provenance, both valid.

6. **Guard new core module imports for old-pin compatibility**: follow the

   existing idiom (`recovery_supervisor.py:26-33`):

   `try: from automation_core.escalation import EscalationRegistry except ImportError: EscalationRegistry = None`

   and fail closed at the live boundary. Same for any new recovery_runner

   symbols — the scheduler files already use this so baseline suites keep

   collecting on the old wheel.

7. **Prove RED against the HEAD production files, not the seam you already

   wrote.** When the wiring is written before the RED run (common in one

   session), the honest sequence is: `git diff <allowlist files> > seam.patch`

   → `git checkout -- <those files>` (revert to HEAD; safe in the worktree,

   never in the original repo) → run pytest → expect a collection error like

   `cannot import name 'CAPTURE_INVALID' from 'flows.feed_swipe_smoke'` (=

   "adapter chưa wire", the correct RED reason) → `git apply seam.patch` →

   run GREEN. Both runs in the pinned venv; record both counts.

8. **MSYS `/tmp` is invisible to native Windows git**: `git diff ... >

   /tmp/seam.patch` writes to `C:\Users\Kibe\AppData\Local\Temp\seam.patch`

   (MSYS maps `/tmp` there), but `git apply /tmp/seam.patch` fails with

   `can't open patch '/tmp/seam.patch'` — pass the Windows path

   (`C:/Users/Kibe/AppData/Local/Temp/seam.patch` or `$(cygpath -w /tmp/...)`).

   Same class as the pip-install MSYS-path mangling, but for the native git

   binary.

9. **A `patch`/`write_file` call can land in the WRONG file and destroy it**

   (this session: a big SEAM-A block meant for `flows/feed_swipe_smoke.py`

   overwrote `core/ui_capture.py`). Recovery is instant for tracked files:

   `git checkout -- <file>` in the worktree, then `git status --porcelain` to

   confirm it's clean. Double-check the `path` argument before applying large

   blocks, and heed the tool's "last read with offset/limit pagination —

   re-read the whole file before overwriting" warning.

10. **Replacing an import block in a CRLF file with blank-line-separated

    imports silently DROPS adjacent import lines** (this session:

    `ensure_run_plan_deadline`, `find_by_gem_xpath`, `iter_elements`,

    `parse_xml` vanished across several hunks in `feed_swipe_smoke.py`;

    lint `IndentationError`/missing names surfaced it). After ANY patch to an

    import block, grep the full block back (`sed -n` the range) and confirm

    every previously-imported name is still present before continuing; a

    missing import only fails at collection/runtime, not at patch time.

11. **A worker adding new public names can silently DROP existing `__all__`

    exports** (this session: `ADAPTER_CAPABILITIES` vanished from

    `scheduler/recovery_handlers.py` `__all__` while the worker added

    `register_escalation_hook`/`expose_recovery_registry`; the constant still

    existed at module level, so nothing imported it and no test caught it —

    only the coordinator's diff review did). Post-worker diff review must

    compare `__all__` against HEAD: existing entries preserved in original

    order, ONLY additions allowed. Same check applies to `__all__` additions —

    new public names should be appended to `__all__` (audit finding B pattern),

    and if a module has no `__all__`, do not invent one without saying so.

12. **A self-corrected allowlist deviation leaves a dangling import in the

    test file.** The worker created then deleted an out-of-allowlist module

    (`flows/feed_recovery_adapter.py`) but the RED test still did

    `from flows.feed_recovery_adapter import ...` — collection failed until

    the test was rewritten to import from the allowlisted seam file. After ANY

    cleanup/deviation report, re-read the test imports and confirm every

    symbol resolves from surviving files before re-running.

13. **Worker self-reports of the installed core version can be WRONG even

    after a verified setup** (this session: worker reported `automation-core

    0.4.43` in its handoff while `pip show automation-core` + `__file__`

    independently proved 0.4.45 in the pinned venv). Never propagate a

    worker's version claim into a report or decision — re-verify with

    `pip show <pkg>` (Name/Version/Location) and

    `python -c "import automation_core; print(automation_core.__file__)"`

    yourself, and note the discrepancy rather than repeating it.



Core 0.4.45 API facts verified by reading source (not docs) this session:

`RecoveryQueue.finalize_failed_locked` accepts only pre-RETRYING failure

states (CLASSIFIED/RECOVERY_RESERVED/RECOVERING/RECAPTURED/GUIDED_RECOVERY_REQUIRED)

and never fabricates artifacts; strict queue rejects artifact_root inside a

repo or OneDrive (`RUNTIME_ROOT_MUST_BE_OUTSIDE_REPOSITORY`) — use tmp_path /

%TEMP% in tests; `EscalationRegistry.call` redacts evidence, consults ONLY the

first registered hook, budget default 3, hook exception → FAILED outcome

(fail-closed); `BatchRecoveryOrchestrator._run_one` routes cap exhaustion

(`MEANINGFUL_ATTEMPT_BUDGET_EXHAUSTED`) to FAILED_LOCKED with the device lock

retained, and a restart over the same durable queue skips FAILED_LOCKED

targets (no re-detect/retry). **CAVEAT — cap exhaustion is only durable at

meaningful cap ≥ 2 (proven by a real test failure this session):** with

`RecoveryPolicy(max_meaningful_attempts=1)`, `reserve_handler` raises

`RecoveryBudgetExhaustedError` BEFORE minting the reservation token, so the

except-branch's `finalize_failed_locked` fails with

`RECOVERY_RESERVATION_OWNERSHIP_REQUIRED`, which propagates out of `_run_one`

and lands in `run()`'s catch → result-level `FAILED_LOCKED` (reason

`ORCHESTRATOR_ERROR`) but the DURABLE queue state stays `CLASSIFIED` — the

restart guard then does NOT skip the target and it would be re-detected.

Write cap tests with `max_meaningful_attempts >= 2` (or the plan's meaningful

8) so the cap exhausts through the normal retry path and FAILED_LOCKED is

really persisted; assert `queue.get(id).state == FAILED_LOCKED`, not just the

returned result status.



Full session detail (exact commands, diagnostics, wiring sketch, remaining

blocker): `references/feed-p1-red-green-2026-08-12.md`.



## Audit routing (updated 2026-08-12 — user preference)



- **Routine consumer audits:** Claude AG Opus

  `ag/claude-opus-4-6-thinking/high` → GPT-5.6 Sol/high when AG is

  unavailable, blocked, or returns no usable verdict. Stop at the first usable

  verdict; do not run cumulative reviews in one slot.

- **Claude CLI is escalation-only:** use it through

  `C:\\Users\\Kibe\\.codex\\skills\\claude-final-audit\\scripts\\invoke-claude-final-audit.ps1`

  only for a difficult/high-risk audit, a hard security/lock/shared-core issue,

  or when Claude AG and GPT-5.6 Sol cannot reach a reliable conclusion. Pass

  `-Effort high`; never call `claude -p` directly. Keep the selected auditor

  and model stable through a REJECT → fix → re-audit cycle.

- Audit the exact committed diff (or an explicitly bounded plan), not a dirty

  working tree. Before audit, run the relevant tests, compile/import checks,

  and `git diff --check`; after a worker reports completion, independently

  inspect the exact diff and rerun the verifier. A worker report or exit code is

  not completion proof.

- **`D:\\Taadaa\\tools\\invoke-ag-audit.ps1` is deprecated.** For a diff audit

  use `bash D:/Taadaa/reports/ag-audit/run-ag-audit.sh <repo> <commit>

  [model] [timeout]`. For plan/prompt audit without a diff use

  `python D:/Taadaa/reports/ag-audit/ag_audit_direct.py <prompt-file> <model>

  <resp-file> <timeout>`; pass Windows-style `D:/...` paths, not MSYS `/d/...`

  paths that can be mangled.

- Claude CLI wrapper may classify Markdown verdicts as

  `PARTIAL_NO_VERDICT/PROCESS_FAILED`; read the stdout artifact under

  `D:\\CodexRuntime\\<repo>\\audit\\claude\\` before classifying the audit.

- Full plan-audit loop and findings taxonomy:

  `references/plan-audit-loop-2026-08-11.md`.

- Offline TDD with FakeAdapter queue-XML:

  `references/fake-adapter-queue-testing.md`.

- Follow-specific safety/phase-gate lessons from the P3 build — including

  fresh-capture/stale-XML rejection, guarded one-shot navigation canaries and

  live search-result identity collisions:

  `references/tiktok-follow-p3-safety-gates-2026-08-12.md`.

- ACCOUNT_READY-only failure root-cause (máy 1): `SWITCHER_ANCHOR_AMBIGUOUS`

  masked a transient `ADB_TRANSPORT_TIMEOUT`; consumer `dump_ui()` is codeless,

  so read `ui_dump_error_*.json` for the real signature. Bounded-ladder fix in

  `_canonical_switch_verify` + TDD pitfalls (fail-once fake, first-open call

  recorded, ladder-fail call trace):

  `references/account-ready-anchor-recovery-2026-08-14.md`. **The ladder is a

  band-aid — the durable fix is the consumer `profile_identity()` adapter hook

  (see `references/account-ready-anchor-hook-seam-2026-08-15.md`); the RED

  tests already exist in untracked `follow_runner/tests/test_adapter.py`.**

- Shared-core lock orchestration for session engines (acquire order, workbook-

  fail rollback, release proof, locked-vs-config classification, fake-factory

  test traps): `references/lock-orchestration-consumer-2026-08-12.md`.



### Doc-contract drift audit — catching a silently-reversed UI contract (proven 2026-08-15, Tiktok-video avatar picker)



When a diff changes UI-selection behavior, check it against the repo's own

`docs/ui-compatibility*.md` contract — not just against tests. The avatar

first-tile-tap diff (state_machine.py `_select_avatar_from_download`) passed

its focused tests but silently reversed the documented fail-closed contract.

The audit steps that caught it (read-only, reusable):



1. **Grep the doc for the contract ID the code cites.** Code comment cited

   `COMPAT-AVATAR-007`; `git grep -n "AVATAR-007" HEAD -- docs/` returned

   nothing → the code referenced a contract that was never documented. Also

   check the newest doc section covering the same code path (COMPAT-AVATAR-003/004

   forbade exactly the new behavior: "Không được làm: ... chọn mù Recent đầu tiên",

   "tin tile đầu tiên là avatar").

2. **Check deleted enforcement tests via git history, not just HEAD.** The two

   tests that enforced the old contract were removed in an earlier commit

   (`git show <commit> -- tests/test_tiktok_workflow.py`); the diff added only

   a label-ordering test, so the new core behavior (tap first image tile, no

   source-similarity gate) had **zero** regression coverage. A changed behavior

   with no test for the new path + no test for the old fail-closed path is a

   REJECT-level gap even when the added test passes.

3. **Check the code's own docstrings for contradiction.** The gate function's

   docstring said "Recent-picker ordering is advisory only; source-tile

   similarity is the authoritative selector proof" while the caller removed the

   similarity check — internal contradiction = contract reversal.

4. **Verify library-API assumptions against the installed package.** The shell

   fix was validated against `inspect.getsource(AdbClient.shell)` of the

   installed automation_core, not just repo source.

5. **Run focused tests under a clean interpreter.** The hermes venv's broken

   Pillow (`cannot import name '_imaging'`) produced 2 false failures; with

   `PYTHONPATH=` + the system `Python312\python.exe` all 47 avatar tests passed.

   A broken-venv failure must be separated from code failure before judging.

6. **Canary blast-radius check:** confirm standalone scripts require explicit

   `-AssignmentManifest`/`-WorkerId`/allow-lists and that force-paths are

   gated by config allow-lists, so a REJECT can't silently go live.



This pattern generalizes: whenever a diff "simplifies" a safety gate (removes

a similarity/identity check, replaces verify-then-act with act-then-verify),

check the governing doc, the deleted tests, and the code's own docstrings in

parallel — one of the three will show the reversal.



**Two doc-contract gates, not one (proven 2026-08-15, follow-up review of the

same avatar picker):** doc-contract checking yields two DISTINCT verdicts —

do not conflate them:

- **Reversal (REJECT-level):** the diff removes a gate the doc EXPLICITLY

  forbids removing AND the enforcement tests were deleted → REJECT (case

  above).

- **Coverage gap (non-blocking):** code comments cite a contract ID absent

  from the doc (`COMPAT-AVATAR-007`: `git grep -n "AVATAR-007" HEAD -- docs/`

  returns nothing) but no doc section forbids the new behavior and the change

  is a genuine bug fix → APPROVED with a doc follow-up note. A missing doc

  entry for a code-comment ID is documentation debt, not a contract violation.



Independent-review verdict checklist for consumer diffs (APPROVED case,

all steps read-only, no device/credentials/workbook):

1. `git diff --stat HEAD` + `git diff HEAD -- <named files>` only; confirm the

   working tree is otherwise clean.

2. Verify library-API assumptions against the INSTALLED package

   (`inspect.getsource(AdbClient.shell)` → prepends `"shell"`), then confirm

   the diff removes the duplicate and grep repo-wide for leftover

   `shell(\s*\[\s*"shell"` stragglers (device_transport.py raw argv is correct).

3. Cross-check push-target path vs album-order labels: avatar pushed to

   `/sdcard/Pictures/` ⇒ `photo_album_labels` must lead with `"Pictures"`

   (state_machine.py:5514-5517 vs :6684). Docs silence is fine; contradiction

   is not.

4. Test coherence: the rewritten test must actually exercise the NEW ordering

   (fake adapter returns True only for the new-first label; assert

   `attempts[0]`), and the REMOVED test's old assertions must match the old

   semantics. Run the changed tests — they must pass.

5. Fail-closed path preserved: no-tile case still raises

   (`AVATAR_PICKER_NO_MATCH`), cleanup/purge/touch/refresh chain intact

   (state_machine.py:5524-5575).

6. Separate environment failures from code failures and report them

   separately per review instructions (this session: broken Pillow in the

   hermes venv — `ImportError: cannot import name '_imaging'` — failed

   unrelated `test_media_push_*`/visual-match tests; prove they fail on the

   PIL import, not on diff content).



Session evidence trail (diff summary, exact line refs, test output):

`references/independent-diff-review-avatar-2026-08-15.md`.



## Consumer live-readiness gate (before claiming a phase is complete)



Offline tests prove only the injected adapter path. Before approving a phase

that will later run on devices, inspect the real execution path as well:



1. Import every module reached by the CLI/session entrypoint; do not leave an

   eager import of a not-yet-built mode or optional flow.

2. Confirm production uses `automation_core` device/workbook locks, not only a

   test `busy_check`; the device lease and workbook lease must be acquired in

   the shared namespace and released/retained in `finally` according to the

   terminal status.

3. Distinguish `MANUAL_REVIEW`, `SKIPPED_LOCKED`, `FOLLOW_BLOCKED`, and

   `CONFIG_ERROR`; never collapse manual-needed or blocked outcomes into a

   successful/ordinary skip record.

4. Confirm the CLI live path actually constructs the adapter/engine and runs the

   requested mode. `LIVE_NOT_IMPLEMENTED` is a blocker, even when dry-run and

   unit tests are green.

5. Verify shared-core signatures from the checked-out source or pinned wheel

   before writing consumer adapters: `acquire_device_lock`,

   `acquire_workbook_lock`, `detect_popup`, and account-switcher APIs are

   version-sensitive.

6. For UI changes, add a local compatibility record and a regression test in

   the same phase. Never claim a new tab/selector is calibrated from a synthetic

   fixture; mode-specific UI fixtures must come from a real dump when the plan

   requires probe evidence.



## Các section chi tiết (trim 2026-08-09)



> adb-install-and-topology-notes.md



