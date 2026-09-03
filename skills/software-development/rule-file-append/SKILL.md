---
name: rule-file-append
description: >-
  Append an approved text section (policy/rule block) to the END of rule files
  (AGENTS.md / PROJECT_RULES.md) across many repos while preserving each file's
  EOL byte-for-byte, with baseline+backup+verify discipline and NO commit.
  Trigger: user says "thêm section ... vào CUỐI tất cả AGENTS.md + PROJECT_RULES.md",
  "append rule to all repos", "chèn text duyệt vào cuối file", or any multi-file
  append where EOL preservation, verification, and worker-scope boundaries matter.
---

# Rule File Append (EOL-preserving, baseline+backup+verify, no commit)

Class of task: user approves a fixed text block and wants it appended verbatim to
the END of many rule files (often AGENTS.md + PROJECT_RULES.md in a fleet of repos),
where the same task may be split across multiple worker sessions. Success criteria:
byte-exact appended block, per-file EOL unchanged, verifiable delta, files backed
up, **nothing committed**, and no file outside the assigned list touched.

## User-intent and policy-scope gate

- Treat the user's explicit requested behavior as the source of truth for the rule being edited. Do not invent stronger permission gates, mandatory metadata, alias requirements, attempt caps, or extra stop conditions merely because they sound safer.
- **Anti-Overengineering & Pragmatic Rules Invariant:** Rules added to repos must be directly actionable, concise, and focused on operational safety (timeouts, zero silent failures, safe resume, fail-closed evidence capture). A rule MUST NOT be phrased academically (e.g. theoretical contract proofs, multi-page planning requirements) in a way that AI coding agents/workers use it as an excuse to debate theory, refuse tasks, or delay fixing bugs. Always append a clear operational note: *"Quy tắc này phục vụ code an toàn, KHÔNG dùng để từ chối hoặc trì hoãn việc sửa lỗi khi được yêu cầu."*
- A rule update must reduce the reported failure mode without making ordinary authorized work impossible. In particular, if the user says to fix/recover a target, the rule must not turn normal preflight evidence into a reason to refuse the requested work; reserve hard stops for concrete safety blockers already in the contract.
- Keep historical evidence, current-state observation, and execution authorization distinct. A live state that drifted from an old incident does not erase the incident target; it informs handler selection. A cooperative lock coordinates compliant runners but is not an OS/ADB input barrier.
- When correcting an over-strict block, replace the marked block rather than layering another exception block on top. Verify that the new block is unique, that text outside it is unchanged, and that the resulting rule is materially simpler and operationally executable.
- After a user correction, report the correction plainly and patch the class-level skill that governs the rule-edit workflow. Detailed incident text belongs in `references/`, not in a new one-session skill.

## Workflow

### Exact-contract propagation gate

When the user provides an exact absolute allowlist, treat it as the complete
write set—not as a representative sample. Count and deduplicate it, confirm
every target exists, and assert all targets stay below the permitted root and
outside explicitly forbidden trees before the first write. Keep all generated
scripts, stdout captures, baselines, and backups outside the repository fleet
when the contract requires it. Use a mirrored backup tree keyed by the
repo-relative path; never flatten repeated `AGENTS.md` or `PROJECT_RULES.md`
names. Persist the exact write set in the report and compare it to the
allowlist during final verification. A ready-to-run checklist and report field
set is in `references/external-artifacts-and-exact-contract.md`.

Capture a baseline first, then perform a pre-write ownership checkpoint by
rehashing every target. If any target changed during the ownership window,
stop with `SCOPE_CONFLICT`; do not replay, restore, normalize, or overwrite the
file. Construct expected post-edit bytes from the untouched mirrored backup and
compare live bytes to that expectation so preservation is proved, rather than
inferred from marker counts or line deltas alone.

1. **Inventory first.** List the exact files. Watch for:
   - Nested `AGENTS.md` inside repos (e.g. `Hermes/apps/desktop/AGENTS.md`,
     `node_modules/.../AGENTS.md`) — these are usually NOT in the assigned list.
     Only touch the explicit paths the user listed (typically repo-root files).
   - Backups from previous runs (`*.bak`, `*.bak-*`) — never touch.
   - Worker-scope: if user says "các repo chưa được worker khác xử lý", verify
     with `rg "section marker"` that your targets do NOT already contain the
     section (repos already containing it belong to another worker — skip them).
2. **Baseline before touching.** Write `<prefix>-baseline<N>-<ts>.txt` with, per file:
   `sha256  EOL-class  crlf=N lone_lf=N lone_cr=N lines=N  <abs path>`.
   Write `<prefix>-backup<N>-<ts>/` dir with a copy of every target file first.
   (Prefix often `rule-merge`, N increments per worker: baseline1, baseline2...)
3. **EOL detection (byte-level, not `file` cmd):** count `b'\r\n'` (crlf),
   `b'\n'` total (lf), derive lone_lf = lf - crlf, lone_cr = `b'\r'` - crlf.
   Classify: CRLF if crlf>0 and lone_lf==0 and lone_cr==0; LF if lone_lf>0 and
   crlf==0 and lone_cr==0; else MIXED. (Real fleets have MIXED files — handle them.)
4. **Append EOL choice:** CRLF for pure-CRLF files; LF for pure-LF; for MIXED
   files use the **dominant** EOL (count `b'\r'` vs `b'\n'`: more CR → CRLF else
   LF). Dominant-EOL keeps the file's pre-existing minority-EOL count
   byte-identical — the strongest reading of "giữ nguyên EOL / không mixed mới".
   Real example: `register gmail/PROJECT_RULES.md` = 2 CRLF among 248 LF lines
   with a CRLF tail; dominant-LF append → CR stays 2, LF +8, clean delta story.
   Tail-EOL is the defensible alternative (uniform boundary, but the minority
   count balloons: 2→10 CRLF). Pick one, SAY which in the report, and make the
   verify block-rebuild + delta expectations use the SAME policy.
5. **Blank separator:** files usually end with exactly one trailing newline (no
   blank line). If so, append `EOL` once as a blank separator line, then the
   section lines each terminated with EOL, ending with a final EOL. If the file
   already ends with a blank line (`EOL+EOL`), skip the separator.
6. **Append in Python** with `open(p,'ab')` — raw bytes, never text mode (no
   newline translation). Build `block = EOL + EOL.join(s.encode('utf-8') for s in SECTION) + EOL`.
7. **Verify (mandatory, not optional):**
   - `rg -n "<marker>" <file>` count == exactly 1 per file; marker line exists.
   - Byte-exact: `b.endswith(expected_block)` — rebuild expected block with the
     same EOL logic; this catches any silent conversion.
   - EOL deltas vs baseline, per class: LF file → lone_lf +N (crlf stays 0);
     CRLF file → crlf +N (lone_lf stays 0); MIXED → depends on dominant EOL:
     LF-dominant → lone_lf +N with crlf/lone_cr byte-identical; CRLF-dominant →
     crlf +N with lone counts unchanged. `delta lines == N added` (blank
     separator + section lines). Strongest proof: `cur_bytes.startswith(backup_bytes)`
     — nothing before the appended block changed at all.
   - Spot-read tails of 3 files (one LF, one CRLF, one MIXED) to eyeball the
     section renders cleanly.
8. **Report** the table (file, EOL before→after, delta lines, PASS), artifacts
   (baseline + backup paths), and what was NOT touched. **Never git commit/push**
   unless explicitly told.
9. **Verbatim block từ repo chuẩn (chép nguyên khối):** khi khối đã duyệt đang
   tồn tại trong 1 repo (vd `Tiktok-video/PROJECT_RULES.md`), slice bytes
   `b[b.index(MARKER):b.index(next_heading)]`, decode + `repr()` để xác nhận nội
   dung, rồi dùng chính các dòng đó làm SECTION — KHÔNG gõ lại tay (tránh lệch ký
   tự em-dash/mũi tên "—"/"→" và lệch số dòng). Repo chuẩn đó bị SKIP ("đã có
   marker, không đụng lại") và không tính vào danh sách append.

## Pitfalls (all hit in real runs)

- **MSYS path mangling:** after `cd /d/Taadaa`, running `python3 /c/Users/Kibe/x.py`
  resolves to `D:\c\Users\...` and fails. Use Windows-style `"C:/Users/Kibe/x.py"`
  or absolute `C:\` paths when invoking python scripts.
- **Baseline file parsing:** keys are the FULL paths; each line is
  `sha  EOL  kv-pairs  path` where path is the LAST token after `"  "` split.
  Parse with `line.split("  ")` and take `fields[-1]` as the path key — otherwise
  you get `KeyError` on lookup.
- **EOL-delta check bug (both mirrors):** a naive "crlf grew by N" check fails
  LF files (growth is in lone_lf), AND a naive "CR count unchanged" check fails
  CRLF files (every appended CRLF line adds one CR — this session's 6th/7th file
  "FAIL" was exactly this, a verify-condition bug, not a bad append). Per class:
  LF → CR stays 0, LF grows; CRLF → CR==LF invariant, both grow by N; MIXED
  LF-dominant → CR byte-identical, LF grows. Check per original EOL class + the
  chosen append policy.
- **Never classify with `cr > lf`:** pure CRLF files have cr == lf, so a
  `"CRLF" if cr > lf else "LF"` heuristic mislabels them LF (baseline-report
  display bug, hit in the wild). Classify via crlf-pairs/lone counts only.
- **Native git.exe + MSYS paths:** `git -C /d/Taadaa ...` fails ("cannot change
  to '/d/Taadaa'") because Windows git doesn't parse `/d/` paths — `cd` into the
  dir first, then run git. An empty `.git` stub dir (no HEAD/objects) makes
  `git status/log` report "not a git repository" — that state IS your no-commit
  proof; report it as such instead of treating it as an error. Same for
  search_files / rg-style tools: pass Windows paths (`D:\...`); `/d/...` gives an
  rg IO error.
- **`rm` triggers approval prompts** on watched roots — split destructive cleanup
  from read-only verification, or leave the temp script and say so.
- **Temp scripts:** keep the append script in the user home (`C:\Users\<user>\`)
  or a scratch dir, not inside the repo fleet; the repo fleet may itself be the
  deployment root. Note in the report if you left it behind.
- **Do not "fix" MIXED files** — preserve their existing mixing exactly; only the
  appended block follows the tail EOL.
- **Count lines honestly:** the user may estimate delta ("10-11 dòng") — report
  the ACTUAL added line count (blank separator + section lines) from the approved
  text, not the estimate. Delta must equal the true number of lines added.
  (Real example: approved text of heading+blank+intro+4 items = 7 lines, +1 blank
  separator = +8 lines/file, NOT the user's guessed +10.)
- **Python 3.11 f-string backslash SyntaxError:** `f"...{d.endswith(b'\n')}..."`
  raises `SyntaxError: f-string expression part cannot include a backslash`.
  Precompute the boolean into a variable, or build report lines with `%`/string
  concatenation, whenever the expression needs a byte literal.
- **MSYS `sha256sum` backslash mangling:** paths from `os.path.relpath` on Windows
  carry `\` separators; feeding them to `sha256sum "$rel"` in a bash loop yields
  mangled hashes (`\74b7...`) and false MISMATCH. Normalize with
  `tr '\\' '/'` before hashing in verification loops.
- **Backup basename collisions:** fleets contain many `AGENTS.md` and
  `PROJECT_RULES.md` — a flat backup copy silently overwrites. Mirror the
  repo-relative path (`backup/<repo>/AGENTS.md`) or prefix with the parent dir
  name. Verify backups afterwards: each backup's sha256 must equal the baseline
  sha for that file.
- **Unterminated last line:** if a target file has no trailing EOL (last line
  unterminated), append the file's EOL once before the separator, and flag it
  (`FIXED-UNTERMINATED-LAST-LINE`) so the delta stays honest — don't let the
  section merge into the last content line.
- **Verifier-expectation false-FAIL (2026-08-10, sweep 15 file AGENTS.md):** lần verify đầu tiên báo FAIL TOÀN BỘ 15 target (`block_eol_proof`/`eol_delta_proof`) vì expected-delta trong script đếm sai (kỳ vọng 10 EOL nhưng block thực tế 9 dòng — marker start + 7 dòng nội dung + marker end). Append ĐÚNG, verifier sai. Đừng tin mass-FAIL đầu tiên về EOL-delta: đếm lại số dòng thực của block đã duyệt từ chính approved text (mỗi dòng = 1 EOL), sửa kỳ vọng, chạy lại verify — report thứ hai khớp actual (`VERIFIED_FACTS_ALL_TRUE` 15/15).
- **Cross-workstream pollution (2026-08-10):** append AGENTS.md cho repo đang bị một independent audit workstream khác chạy (vd P1 harness audit cùng repo) → auditor thấy `M AGENTS.md` và REJECT oan "scope escape" dù đó là thay đổi chủ đích của propagation. Khi propagation chạy song song audit: báo auditor rõ dirty path đó là intentional từ workstream khác, hoặc sequence để policy workstream xong/commit trước khi audit. Đừng để propagation làm hỏng release gate của repo khác.
- **Dispatch qua codex worker + prompt file (2026-08-10, 15-file AGENTS sweep):** thay vì append trực tiếp, viết prompt file (15 path allowlist + block verbatim + EOL rule + baseline/backup ở external dir + checkpoint JSON 3 phase + report path), chạy nền `codex exec --ephemeral --sandbox danger-full-access --model gpt-5.6-luna -c model_reasoning_effort="high" "$(cat '<prompt>.txt')" > transcript 2>&1`; worker cập nhật checkpoint sau baseline/append/verify (phase `baseline_captured` → ... → `verified`) và report per-target. Verify lại độc lập bằng python: marker START/END đếm 1:1, prefix_proof, EOL class giữ nguyên, delta = số dòng block. File target MIXED (vd `Hermes\AGENTS.md` = 97 CRLF + 3 lone-LF) → dominant-EOL, count ngoài block byte-identical.

## Pitfalls Unicode tiếng Việt + chèn block giữa file (hit 2026-08-17, propagate STOP GATE 19 file)

- **Lệch dấu tiếng Việt khi gõ lại block (hit 2 lần liên tiếp → 19/19 OLD-NOT-FOUND)**: block tiếng Việt gõ tay lệch dấu so với file thật — `"Dừng"` (U+1EAB huyền) vs `"Đừng"` (U+1EAA hỏi); `"ĐỐI"` (U+1ED1) vs `"ĐỐI"` (U+1ED0). Quy tắc: khi cần match/replace block ĐÃ TỒN TẠI trong file, LUÔN slice bytes block từ chính file thật (mục "Verbatim block" ở trên) — KHÔNG gõ lại tay dù chỉ 1 từ. Verify sớm: `block.encode("utf-8") in data` trên 1 file đại diện TRƯỚC khi chạy toàn bộ.
- **Bytes literal KHÔNG decode `\uXXXX`**: `b"6. C\u1ea4M..."` là bytes thô chứ không phải Unicode — Python bytes literal không decode escape Unicode → SyntaxWarning + không bao giờ match. Pattern Unicode phải build từ str rồi `.encode("utf-8")`, hoặc dùng bytes hex thô (`b"g\xe1\xbb\xadi \xc4\x91\xc6\xb0\xe1\xbb\x9dng d\xe1\xba\xabn"`).
- **Chèn block giữa file (insert-at-marker) phải join đúng EOL file đích**: block LF chèn vào file CRLF → `eol.join()` ra hybrid `crlf != lf` → verify EOL-class fail. Sau join nếu file CRLF: `out.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")`; verify class EOL trước/sau.
- **Blank separator bắt buộc khi chèn giữa**: block chèn sau anchor line PHẢI kèm blank line trước + sau. Thiếu → block dính vào dòng cuối, và chạy lại lần 2 NHÂN ĐÔI dòng (hit: dòng `5. Ảnh...`/`6. CẤM...` xuất hiện 2 lần trong file). Verify cuối: marker count == 1 **và** đếm dòng đầu block == 1.
- **Restore-from-backup khi chèn sai**: giữ backup của bản SẠCH (ngay sau append đầu) tách riêng khỏi backup sau-chèn-sai. Hỏng → restore bản sạch → chèn lại đúng thứ tự. KHÔNG hàn vá trên file đã hỏng (file hỏng MIXED EOL + dòng lặp — vá tiếp chỉ tệ hơn).
- **Inject-verify có thể timeout nếu session không bind cwd**: `hermes chat -q` chạy từ repo root đôi khi vẫn quét toàn `/d/Taadaa` (`grep -rl` 60s+ → exit 124). Prompt ngắn gọn, cwd đúng repo; nếu timeout, read-file trực tiếp (marker 1:1 + đọc block) là bằng chứng đủ về nội dung.

## Inject-verify: prove the rule reached a FRESH session (live 2026-08-16)

The strongest proof that an AGENTS.md rule is effective is NOT a file diff — it is a
fresh agent session quoting the rule back. Technique:

```bash
cd <repo-root> && timeout 180 hermes chat -q "Bạn có thấy quy tắc <rule-name> trong file AGENTS.md hiện tại không? Nếu có, nêu 2 việc đầu tiên bạn phải làm khi session mới bắt đầu." 2>&1 | tail -30
```

A fresh session answering with the correct block content + line numbers (verified live:
session `20260816_002655_5a384f` returned the SESSION-START-CONTEXT block at dòng 14-25)
proves the file is injected into the system prompt. Answer "không thấy" = wrong cwd or
wrong file — the `cwd-only` AGENTS.md discovery contract bites: Hermes loads `.hermes.md` →
`AGENTS.md` → `CLAUDE.md` → `.cursorrules` (first match wins), and **AGENTS.md is read at
the exact cwd only** (no parent/child walk), so the session must start inside the repo
(`cd D:\Taadaa\automation-core`) for the rule to load. Also check precedence: if the file
starts with a role-gate block (WORKER-ROLE-GATE), insert the new block AFTER it so the
role-gate's "highest precedence" claim stays true.

## Non-append variants (insert-at-top / insert-after-marker)

The append-only title under-sells the skill. When the user wants the rule near the TOP
(e.g. after a role-gate, before `# Shared ... Rules` heading) instead of at the END:
- Use `patch` (mode=replace) with the anchor as old_string and `new_block + anchor` as
  new_string — NOT byte-append, which only reaches the file tail.
- Backup first even for one-file edits: `cp AGENTS.md AGENTS.md.bak-$(date +%Y%m%d-%H%M%S)`.
- Verify after insert: re-read the region, confirm the block sits after the intended
  anchor, `rg -c "<marker>"` == 1, and run the inject-verify probe above.
- `D:\Taadaa\AGENTS.md` is NOT a git repo (`git rev-parse` fails) → the manual backup is
  the ONLY restore evidence; repos like `automation-core/AGENTS.md` are git-tracked
  (commit after user review).

## Commit+push propagation loop (khi user yêu cầu push, vd "Ghi hết")

The user's "xong" convention = commit+push từng repo với commit message tiếng Việt. Loop: cd vào từng repo → `git add` file policy → commit → push → report per-repo. Pitfalls (tất cả hit thật 2026-08-09 trên 17 repo):
- **git add pathspec abort:** `git add AGENTS.md PROJECT_RULES.md` FAILS TOÀN BỘ (`fatal: pathspec ... did not match any files`) khi một path không tồn tại (repo thường chỉ có AGENTS.md, không có PROJECT_RULES.md) → KHÔNG file nào được stage, loop báo "no-change" sai lệch. Check `[ -f "$f" ]` từng path (hoặc add từng file), verify bằng `git diff --cached --quiet` TRƯỚC khi kết luận no-change.
- **Branch ≠ upstream:** repo ở `master` với upstream `origin/main` → `git push` fail "upstream branch does not match". Xem `git log origin/main..master --oneline` xác nhận các commit chưa push là của mình, rồi push `git push origin HEAD:main`.
- **Push pre-flight = `@{u}` + `git remote -v` (hit 2026-08-10, 12-repo COMMIT GATE sweep):** chạy `git rev-parse --abbrev-ref --symbolic-full-name @{u}` trên TỪNG repo trước khi bấm push, vì: (1) `@{u}` có thể trỏ `origin/main` trong khi local branch tên `master` → `push.default=simple` vẫn fail dù upstream nhìn "đúng" (open claw: fix `git push origin HEAD:main`); (2) `@{u}` có thể trỏ FORK — Hermes local `main` track `fork/main` (fork user thanhdatbui), `origin` là upstream NousResearch → plain `git push` đi vào fork, ĐÚNG ý user; đừng mặc định `origin` là đích push, và báo trong report remote nào nhận push.
- **Scope `git status` về đúng file target** (`git status --short --untracked-files=no -- <file>`): repo automation chứa `.runtime/`/`artifacts/` untracked hàng trăm MB (Hermes, Tiktok_Reg phun 700KB+ output với `--untracked-files=all`) → nghẹt context. Inventory một-shot bằng Python: branch + upstream + remote_head + target-file status + EOL bytes + marker count gom trong 1 vòng lặp, không chạy full `git status`.
- **Chứng minh commit chỉ chứa file rule:** trước commit `git diff --cached --name-only` == [đúng 1 tên file]; sau commit `git show --name-only --pretty=format: HEAD` — nhiều repo vốn dirty sẵn (AI-Tools, gan-proxy, tiktok-log-in...) nhưng commit push lên phải chứa DUY NHẤT file policy, không cuốn file lạ vào; report kèm `files=[...]` để chứng minh.
- **Bỏ qua non-git dirs** (`[ -d "$d/.git" ]`) và **context-worktrees** (`D:\Taadaa\context-worktrees\*` là scratch checkout tạm — KHÔNG commit ở đó; rule sẽ vào qua main checkout của repo cha).
- **Rule file hidden+readonly:** nhiều `PROJECT_RULES.md` là hidden+readonly → `PermissionError` cả khi đã `chmod`; fix = `attrib -R -H "<file>"` rồi mới ghi lại. Riêng `attrib -R` in "Not resetting hidden file" và vẫn fail.
- **Policy file gitignored/untracked:** `git add` stage được 0 file ("no-change") nhưng Hermes đọc AGENTS.md từ DISK — rule vẫn có hiệu lực; báo "covered-on-disk", đừng coi là thiếu.

## Pitfalls: terminal/docstring execution + exact-block extraction (hit 2026-08-22, 33-file Taadaa scope-lock propagation)

- **Terminal heredoc mangles byte-literal escapes.** `python3 - <<'PY'` with a bytes
  literal like `b'...`D:\\Taadaa\nuntime...'` triggers `SyntaxWarning: invalid escape
  sequence '\T'` and — worse — the `\T`/backslashes get reinterpreted so your `old`/`new`
  tokens never match the real file bytes (silent no-op or wrong match). Fix: write the
  script to a file (e.g. via the `write_file` tool) and run `python3 C:/Users/Kibe/.../x.py`.
  Memory: file-based scripts also dodge the **`&&` backgrounding guard** — `cd /d/Taadaa && python3 ...`
  is rejected as "uses '&' backgrounding"; set the `workdir` param instead of `cd &&`.
- **Do NOT hardcode block line numbers.** `rlines[67:99]` over-shot into the next
  `### Taadaa Scope Override` subsection (captured `  default.\n\n### Taadaa Scope
  Override`) because the last bullet wrapped past line 99. Extract the block by
  **boundary**, not index: find `start = index of marker line`; `end = next i where
  lines[i].startswith(b'### ')`; take `lines[start:end]`, strip one trailing blank.
  Reuse the same extraction for the verify block-rebuild so append and verify agree.
- **Suffix verify false-FAIL when comparing cross-EOL.** A CRLF target's appended block,
  checked against a hardcoded **LF** literal (`b'...default.'`), mismatches on the
  embedded `0x0A`. Rebuild the expected suffix per file: `block_eol = block_lf.replace(b'\n', eol)`
  where `eol = b'\r\n' if b'\r\n' in file else b'\n'`; assert
  `cur[len(base):] == eol + eol + block_eol + eol`. This is the definitive byte-exact
  proof and replaces the brittle "EOL-delta class" heuristic for the append case.
- **`search_files` (rg) cannot resolve `/d/` MSYS paths** — returns `IO error os 2/3`
  even though the file exists. Use `read_file` with `D:/...` (forward slash) or run
  `grep`/`python` from the terminal with Windows paths. The `cd /d/Taadaa` form works
  for terminal commands; only the rg-backed tool chokes on `/d/`.
- **Repair-or-append must be idempotent.** When fixing corruption AND appending a block
  in one pass, guard the repair with `if data.count(old_tok)==1:` so re-running the
  script doesn't fail (the corruption is already gone). Prove a repair is limited to the
  intended region by asserting `data.replace(new_tok, old_tok) == backup_bytes`
  (reversing the edit reconstructs the exact pre-change baseline).
- **Backup basename collisions (resolved):** this run used `backup/<relpath with '/'→'__'>`
  (e.g. `backup/add mail khoi phuc__AGENTS.md`) so the many same-named `AGENTS.md`/
  `PROJECT_RULES.md` copies don't overwrite. Keep that scheme; also persist
  `baseline_sha256.json` (per-file pre-change sha) so verification is content-based, not
  just size.

## Script

`scripts/append_rule_section.py` — parameterized version of the proven script:
edit `TARGETS` + `SECTION` + `PREFIX` + `WORKER_N` at the top, run, it does
baseline + backup + append + full verification (per-file EOL class, byte-exact
tail, expected-delta check) and prints a PASS/FAIL table. Handles MIXED files
via dominant-EOL (minority-EOL count stays byte-identical), files already
ending with a blank line (skips the extra separator), and unterminated last
lines (terminates + flags them). Reuse rather than retyping.

`scripts/verify_append_outside_d.py` — read-only, byte-exact verifier for the
append case: proves marker==1, prefix unchanged vs backup, appended suffix ==
`eol+eol+block_eol+eol` (block rebuilt per file EOL), EOL class preserved, and a
target-only `os.walk` finds 0 non-target markers. Handles idempotent root-repair
scope proof. Pair with `references/scope-lock-propagation-recipe.md` (end-to-end
33-file skeleton: backup outside fleet, boundary-extracted block, per-EOL suffix).
