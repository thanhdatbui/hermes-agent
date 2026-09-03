# Classifier marker-list consistency audit (token-routing fixes)

## When to use
A dirty/window diff touches a classifier that routes by substring markers
(e.g. `_classify_post_signup_submit_mode`, `_classify_post_email_submit_xml`,
`_classify_after_continue_flat`, `detect_after_continue` in the TikTok-reg
codebase). Hybrid fixes typically add a *secondary* marker list (an "OTP
present" / "magic-link present" sub-list) used only inside a combined-branch
decision.

## Why it matters
If a marker lives in the secondary list but NOT in the primary detection
tuple, it can never be seen on the path that gates entry into the branch to
reach the intended return value → dead entry that silently misclassifies a
real screen. Conversely, a secondary list broader than the primary can pull
the wrong screen into the branch. This is the single most common MINOR_FIXES
finding in classifier diffs and is invisible to a green regression suite (the
tests use whatever markers the author thought of).

## Probe 1 — diff the marker lists
Pull the outer primary detection tuple (e.g. `numeric = any(marker in flat
for marker in (...))`) and the inner hybrid OTP-marker list (e.g. `if any(m
in flat for m in (...))`) as raw string literals, then compare:

```python
outer = {"ma gom 6 chu so","nhap ma xac minh","verification code",
         "enter the code","sent a code","gui lai ma","resend code"}
inner = {"gui lai ma","nhap ma","ma gom 6 chu so","ma pin",
         "enter the code","verification code","sent a code","resend code"}
dead = inner - outer          # {'nhap ma','ma pin'} -> never reaches hybrid branch
assert not dead, f"secondary-only markers unreachable from primary: {dead}"
```

Real finding (STT39/54 audit 2026-08-13): hybrid screen whose *only* OTP
signal was `nhap ma` / `ma pin` (no `gui lai ma`) could never enter the
hybrid->numeric branch -> misclassified `magic-link`. The two markers were
dead because absent from the outer `numeric` tuple. Repair: widen the primary
tuple (or fold the two lists together) so every test-relevant marker is
reachable. Does NOT affect the 2 required regression tests (which use `gui
lai ma`) nor the live XML (which literally contains "Gửi lại mã" -> `gui lai
ma`).

## Probe 2 — confirm fail-closed by AST transitive reachability
When a fix removes/avoids a fallback path (e.g. numeric Hotmail OTP must no
longer call `_try_get_otp_outlook_cdp` / `_try_get_otp_browser`), `git diff`
absence does NOT prove unreachable — a legacy wrapper may still call it. Build
a name->def map, walk the transitive call-closure from each production root
caller, and report the intersection with the suspect set.

```python
import ast
from pathlib import Path
t = ast.parse(Path('social_reg_v1.py').read_text(encoding='utf-8'))
funcs = {n.name:n for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
def callee(n): return n.id if isinstance(n,ast.Name) else n.attr if isinstance(n,ast.Attribute) else None
suspect = {'_try_get_otp_outlook_cdp','_try_get_otp_browser'}
seen = {'handle_tiktok_email_otp','_request_and_read_fresh_tiktok_email_otp'}
q = list(seen)
while q:
    name = q.pop(0); node = funcs.get(name)
    if not node: continue
    for x in ast.walk(node):
        if isinstance(x, ast.Call):
            tg = callee(x.func)
            if tg in funcs and tg not in seen:
                seen.add(tg); q.append(tg)
print('suspect_reachable=', sorted(seen & suspect))   # [] => fail-closed proven
```

Also enumerate production callers of the changed entry point to confirm the
`signup_mode` / `entry_surface` contract is propagated everywhere: grep all
`*.py` for `handle_tiktok_email_otp(...)` and assert each signup caller passes
`signup_mode=` while legacy login callers intentionally omit it (-> legacy
branch).

## Isolation for the offline suite
Run scoped tests with the installed package shadow disabled so a stale
site-packages copy cannot fake-green the worktree:

```bash
env -u PYTHONPATH python -m pytest tests/test_signup_email_transition.py -q
# read-only compile that leaves no bytecode in the repo:
tmp=$(mktemp -d); env -u PYTHONPATH PYTHONPYCACHEPREFIX="$tmp" python -m py_compile social_reg_v1.py; git status --short social_reg_v1.py
```

## Verdict discipline
A green focused suite + confirmed fail-closed reachability still does not make
APPROVED if Probe 1 shows a dead secondary marker that the live screen can
hit. That is MINOR_FIXES (non-blocking) unless the dead marker is the one the
live bug depends on (then P0/REJECT).
