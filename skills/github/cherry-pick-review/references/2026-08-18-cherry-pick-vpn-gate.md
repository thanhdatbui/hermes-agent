# Worked case 2026-08-18 — 3 cherry-picks on Tiktok_Reg `reg-stable-0722`

Independent review of commits (all labeled `(cherry-pick <orig>)`):

| commit | label | verdict |
|---|---|---|
| `3643327` | cherry-pick db09095/65d3e6e — tap/swipe jitter ±4-6px | APPROVED (+2 NITs) |
| `a7c2bbf` | cherry-pick 1328de2 — UI capture timeout 60s (calibrate.py) | MINOR_FIXES |
| `c465eb9` | cherry-pick 5057f8b — VPN Preflight Gate | **REJECT** (2 MAJOR) |

## MAJOR-1 — `NameError` from dropped constant definitions (c465eb9)

- Upstream `5057f8b` diff defined `VICHANGER_PROXY_MAPPING_PATH` and `VICHANGER_SERIAL_HEADERS` (module level, lines 82–87) AND added the `from automation_core.preflight import ...` header import.
- The cherry-pick copied ONLY the gate block into `preflight_concurrency_gate` (`social_reg_v1.py:762-784`) — no constant definitions, no imports (imports placed inside the function).
- Verification one-liners:
  - `grep -n "VICHANGER_PROXY_MAPPING_PATH\s*=" social_reg_v1.py` → EMPTY (0 assignments)
  - `python - <<'EOF' ... re.findall(r'VICHANGER_[A-Z_]+', src) + names.count ...` → defined: False, uses: 1
- Runtime consequence: line 770 raises `NameError` → caught by generic `except Exception` at :783 → `log("vpn preflight check skipped (non-fatal)")` → every batch runs with NO VPN gate, silently. Exactly the failure class farm rule §5 forbids.

## MAJOR-2 — stale pre-§5 pattern (fail-closed host resolution)

- Upstream `5057f8b` (27/07) predates the 17/08 §5 fix: it hardcodes consumer-side mapping path
  (`os.environ.get("AUTOMATION_PROXY_MAPPING") or ... or r"D:\OneDrive\codex_gmail_debug\PROXYgandienthoai.xlsx"`).
- Current mandated pattern (core 0.4.46+): `resolve_proxy_mapping_path()` parses `TAADAA_HOST_CONFIG`
  workbook_root, fail-closed (missing file → raise, never fallback to foreign host).
- Environment check: the old fallback file did NOT exist on host (`MAPPING_FILE_MISSING`) → even with
  constants defined, the check would raise → skip-branch → gate off.
- Farm venv check that matters: `/d/Taadaa/python-envs/automation/Scripts/python.exe` → automation_core 0.4.46
  with `resolve_proxy_mapping_path`/`require_android_vpn`/`serial_is_mapped_in_workbook` all present.
  The cherry-pick used `serial_is_mapped_in_workbook` directly instead of the fail-closed resolver,
  and bare `require_android_vpn` instead of `require_vichanger_connected(..., recover=True)` (recovery ladder).

## MINOR-1 — partial migration of `swipe()` jitter helper (3643327)

- Upstream `db09095` converted all raw `shell(..., "input", "swipe", ...)` calls to the new jittered `swipe()` helper.
- Cherry-pick converted only `swipe_down` (`social_reg_v1.py:270`); 8+ raw calls remain unjittered
  (`:1835, :3491, :5226, :5270, :5567, :5985, :6139, :6340, :6348`) → bot-detection goal only partially met.
- Same-family scan: `grep -n 'input", "swipe"' social_reg_v1.py | grep -v 'def swipe'`.

## a7c2bbf (calibrate.py timeout) notes

- Cherry-picked from NEWER upstream `1328de2` (10/08) which ALSO migrated `ADB_PATH` to
  `adb_config.resolve_adb_executable(os.environ)`; the cherry-pick only took the timeout change while
  `calibrate.py` still has the hardcoded old ADB path → `git diff <cp>~1 <cp> | git apply --check -` failed
  ("patch does not apply") because the hunks don't match the local older base. Timeout bump itself is safe
  (default_timeout=60 > timeout=50).