---
name: php-verification-without-runtime
description: "Verify PHP edits (CMSNT/SHOPCLONE7, legacy PHP) when php CLI is unavailable: brace balance, node --check on rendered embedded JS, content invariants, diff hygiene, ad-hoc verify scripts."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [php, verification, lint, cmsnt, shopclone7, legacy-php, no-runtime, embedded-js]
    related_skills: [systematic-debugging, test-driven-development, code-audit]
---

# PHP Verification Without a PHP Runtime

## Overview

You edited PHP files but there is no `php` CLI on the machine (common on Windows sandboxes/git-bash hosts). You must still produce **honest, mechanical evidence** — and you must NEVER claim `php -l` passed or invent a lint result.

**Rule:** `php -l` BLOCKED must be stated explicitly in every report. Everything below is *ad-hoc verification*, not a canonical suite green.

## When to Use

- Any edit to PHP files (CMSNT/SHOPCLONE7 supplier/API adapters, views, crons, legacy apps) when `command -v php` / `where php` comes up empty.
- The system (or user) asks for verification evidence but the repo has no canonical test/lint command.
- Before handing off PHP work for deploy — state clearly that `php -l` must be run on a PHP-enabled machine.

## Verification Stack (in order)

1. **Runtime probe**: `command -v php`, `where php`, check common dirs (`/c/xampp/php`, `/c/php`, repo-relative `php.exe`). If found → `php -l file1 file2 ...`. If not → mark BLOCKED, continue below.

2. **Brace/paren/bracket balance** — run `scripts/php_verify_no_runtime.py` (or inline): strip `/* */`, `//`, and quoted strings crudely, then count `{}` `()` `[]`. Unbalanced = definite syntax break. This is the strongest mechanical signal available without a runtime.

3. **Embedded JS really parses** — PHP views carry `<script>` blocks that `php -l` wouldn't even check; a stray brace there is a silent page-break. Extract and parse the **relevant changed inline block** (for example, the block containing the supplier field-toggle function), not every `<script>` tag blindly. Templates often contain third-party snippets, external-loader fragments, or literal template content that is not standalone JavaScript. Substitute PHP template tags before `node --check`:
   ```python
   b = re.sub(r'"<\?=.*?\?>"', '"TEMPLATE"', b, flags=re.S)  # url: "<?=...?>" -> url: "TEMPLATE"
   b = re.sub(r"<\?=.*?\?>", "TEMPLATE", b, flags=re.S)
   b = re.sub(r"<\?php.*?\?>", "", b, flags=re.S)
   # node --check on the relevant rendered JS block
   ```
   `node --check` is a REAL parse of what the browser would execute. Naive `<?=...?>` → `"TEMPLATE"` substitution creates `""TEMPLATE""` — do the two-step substitution above. If a broad extractor reports a syntax error, identify whether it is in the changed block before treating it as a regression.

   Optional: when PHP CLI is unavailable, a PHP AST parser can provide supplementary syntax evidence for all scoped files. Report it as `php-parser`/AST parsing, never as `php -l`.

4. **Content invariants on the REAL files** — for acceptance criteria, assert presence/absence of markers in the actual file text (e.g. `"body['coupon']" not in buy_fn_text`, `"array_key_exists('ok', $json)" in sup`). Test the file, not a copy. When a check needs the function body only, slice it with `re.search(r"function NAME\(.*?\r?\n\}\r?\n", src, re.S)` — the `\r?\n` is REQUIRED on CRLF PHP files (CMSNT live files are often CRLF; `\n}\n` matches nothing there and every body-based check silently FAILs, looking like a code bug). NOT `.count()` on a Match object (no such method).

5. **Diff hygiene**:
   - `git diff --check` — filter lines starting `warning:` (autocrlf noise is not an error); any other output is a real trailing-whitespace/conflict-marker error.
   - Scope: `git diff --name-only` must contain only the intended files (plus pre-existing dirty files you did NOT touch).
   - Near-identical blocks (cloned templates): use `git diff --patience` so hunks don't misalign and look like the template changed.
   - Secret scan: grep added lines for key-shaped values; only parameter NAMES like `$api_key` should appear, never values.

6. **EOL byte-check with Python, not grep**:
   ```python
   data = open(f, 'rb').read(); data.count(b'\r\n'), data.count(b'\n')
   ```
   `grep -c $'\r'` in MSYS git-bash returns bogus counts (matches everything). `file` output can also lie about line endings. Python byte counts are ground truth.

## Fresh-Evidence Temp Script Pattern

When asked for verification evidence after edits (system prompt or user), create a temp script:
1. Path via OS-safe `tempfile`: `python -c "import tempfile,os; fd,p=tempfile.mkstemp(prefix='hermes-verify-',suffix='.py'); os.close(fd); print(p)"` → write_file the script there (or use `write_file` to a `%TEMP%\hermes-verify-*.py` path).
2. Run it, capture exit code, then `rm -f` it.
3. Summarize explicitly: "ad-hoc verification, not suite green; php -l BLOCKED (no PHP runtime)".
4. **Tracker re-run rule**: deleting the temp script after a pass can make the workspace verification tracker flag the turn "unverified" even though it passed — it keys off edited paths, not past output. When that happens, don't just cite prior results: recreate the script, run it again in the SAME turn with full output shown, then clean up. Evidence must be fresh in the turn that edited the files (proven 2026-08-11, source-price alert deploy).

## CMSNT/SHOPCLONE7 cron-function harness (fake DB + fake Telegram)

For `*AlertCheck($CMSNT)`-style cron alert functions (settings-row state, dedup, Telegram send), verify behavior with a disposable PHP harness on a PHP host (e.g. the production VPS `php7.4`) instead of touching live DB/Telegram:

- `FakeDB` class stubbing `site() / get_row_safe() / insert() / update() / get_list_safe()` over in-memory `$stateStore` + `$productsTable`; global fake `sendMessTelegram()` appending to `$sentMessages` and pulling from a `$telegramResponses` queue (empty queue = default `ok:true`).
- Cover: silent first baseline, increase AND decrease, HTML escaping, new-row silent, send-fail → state NOT advanced → retry next run, chunking (every message ≤4096), one-chunk-fail → nothing advances, telegram-off → return false + no state mutation, no product-table mutation.
- Starter with scenario skeleton: `templates/cmsnt-cron-function-harness.php`.
- Lint the harness with `php -l` on the PHP host; the harness itself is the deterministic behavioral probe — report it as harness evidence, never as suite green.

## Pitfalls (all hit in real sessions)

- **patch tool fuzzy-match shifts indentation of whole blocks**: replacing a large block can re-indent every line (+N spaces) while staying semantically identical, inflating the diff and hiding real changes. After any large patch replacement, read the region back; for pure re-indentation use a small Python script (`lines[i] = lines[i][12:]` for a 0-indexed range), never the patch tool.
- **Stray closing brace when splitting if/else-if chains**: restructuring `else if (A || B || C)` into separate branches leaves the ORIGINAL branch's closing `}` behind → the next `else if` chain binds to the wrong `if` or the function closes early. Delete the leftover brace and re-indent the orphaned inner block; verify with `node --check` afterwards.
- **Heredocs mangle content**: `python - <<'EOF'` strips trailing spaces and alters backslashes/quotes — fatal when the script itself contains trailing-whitespace strings or `\\`. Write scripts with write_file instead.
- **search_files (ripgrep) fails on MSYS paths** (`/d/...` → "system cannot find the path specified"), and can also fail on `D:\...`; `read_file` accepts MSYS paths fine. For content greps use `terminal` + `grep -rn` (or search from a relative cwd). This is a tool-path quirk, not a code bug — don't conclude "no matches" from an error.
- **Python on Windows**: needs Windows paths (`D:/...`), not MSYS (`/d/...`); `python` may be the WindowsApps stub — verify `python --version` actually prints a version before relying on it (stub prints nothing/errors when run).
- **PHP test harness: array copy-on-write**: `foreach ($arr as &$p) { $p['x'] = ...; }` mutates `$arr` only — an earlier `$copy = $arr;` keeps the old values, so asserting against `$copy` (or a pre-loop snapshot taken before an intentional mutation) gives false FAILs that look like code bugs. Snapshot the fixture immediately before each `run()` and assert against the array you actually mutated (both hit 2026-08-11 in the source-price-alert harness).
- **First-run baseline silent (the `$isFirstRun` trap)**: a state-dedup alert function that must baseline silently on first run CANNOT use the naive `$previous = []` empty map — every row then looks "new" and the baseline fires alerts. Two proven fixes: require the old value to EXIST before diffing (`$oldCost !== null`, sourcePriceAlertCheck), or set `$isFirstRun = !$stateRow` and gate the alert with `!$isFirstRun && <new-row test>` (newApiProductAlertCheck). The harness caught this exact bug on first GREEN run (2026-08-11). Pick per spec: the balance watcher deliberately INVERTED it — first run alerts immediately for already-below suppliers, then dedups on the not-below→below transition. Assert the chosen direction in the harness.
- **Harness scenario seeding**: transition/chunking scenarios on a fresh `$stateStore = []` false-FAIL with "0 messages" because the first run IS the silent baseline by design. Seed first: run the function once with the baseline fixture (or empty product set), THEN mutate the fixture and re-run to test transitions/chunking. Construct the fixture for the run you're actually testing, same class as the snapshot rule (hit 2026-08-11, api-product/balance alert harness).

## Support Files

- `scripts/php_verify_no_runtime.py` — parameterized balance + EOL + embedded-JS `node --check` verifier. Run: `python scripts/php_verify_no_runtime.py file1.php file2.php ...`
- `references/cmsnt-supplier-integration.md` — condensed CMSNT/SHOPCLONE7 supplier-type integration pattern (XSCR template, 5 touch points, SHOPMAIL hardening list) for extending supplier APIs.
- `templates/cmsnt-cron-function-harness.php` — FakeDB + fake `sendMessTelegram` harness starter for verifying `*AlertCheck($CMSNT)` cron functions (baseline/dedup/retry/chunking) without live DB/Telegram.
