"""verify_append_outside_d.py — byte-exact verification of an EOL-preserving block append.

Reusable, deterministic verifier for the rule-file-append class of task. Run it AFTER
applying appends (do NOT hand-type the expectations). It proves:
  - marker appears exactly once per target,
  - every byte before the appended block is unchanged vs the pre-change backup,
  - the appended suffix is byte-identical to (EOL+EOL+block_eol+EOL) where block_eol
    is the canonical block rebuilt from the current source file under the SAME EOL,
  - the file's EOL class is preserved,
  - (root only) a corruption-repair is limited to the intended region and introduced no
    control characters.

Edit TARGETS / SOURCE / MARKER / BACKUP_DIR at the top. Runs read-only; never commits.

Lessons baked in (2026-08-22):
  * Extract the canonical block by marker->next '## ' boundary, NEVER by hardcoded line
    numbers (rlines[67:99] over-shot into the next '### ' subsection).
  * Rebuild the expected suffix per file EOL; comparing a CRLF target against a hardcoded
    LF literal gives a false FAIL.
  * Repair must be idempotent (guard with count==1) and provable: reversing the edit
    reconstructs the exact pre-change baseline.
"""
import os

ROOT = 'D:/Taadaa'
BACKUP_DIR = 'C:/Users/Kibe/scope-lock-op/backup'   # backups mirror relpath '/' -> '__'
SOURCE = os.path.join(ROOT, 'AGENTS.md')            # file that holds the canonical block
MARKER = b'## Task Contract and Scope Lock (MANDATORY)'

TARGETS = [
 'AGENTS.md','add mail khoi phuc/AGENTS.md','add mail khoi phuc/PROJECT_RULES.md',
 'AI-Tools/AGENTS.md','AI-Tools/PROJECT_RULES.md','automation-core/AGENTS.md',
 'automation-core-implementation/AGENTS.md','gan-proxy/AGENTS.md','gan-proxy/PROJECT_RULES.md',
 'Hermes/AGENTS.md','Hermes/PROJECT_RULES.md','Hotmail/AGENTS.md','Hotmail/PROJECT_RULES.md',
 'open claw/AGENTS.md','open claw/PROJECT_RULES.md','register gmail/AGENTS.md','register gmail/PROJECT_RULES.md',
 'site ban hang clone/AGENTS.md','site ban hang clone/PROJECT_RULES.md','tiktok-add-bao-mat-f2a/AGENTS.md',
 'tiktok-add-bao-mat-f2a/PROJECT_RULES.md','tiktok-follow/AGENTS.md','tiktok-follow/PROJECT_RULES.md',
 'tiktok-log-in/AGENTS.md','tiktok-log-in/PROJECT_RULES.md','tiktok-luot nuoi acc/AGENTS.md',
 'tiktok-luot nuoi acc/PROJECT_RULES.md','tiktok-luot nuoi acc-implementation/AGENTS.md',
 'tiktok-luot nuoi acc-implementation/PROJECT_RULES.md','Tiktok-video/AGENTS.md','Tiktok-video/PROJECT_RULES.md',
 'Tiktok_Reg/AGENTS.md','Tiktok_Reg/PROJECT_RULES.md',
]

# root corruption repair tokens (set to None if not applicable)
OLD_TOK = b'manifest nu\xc3\xb4i acc (`D:\\Taadaa\nuntime\\kibe\\cron-state\\manifests\\<ng\xc3\xa0y>\x07ctive_manifest.json`'
NEW_TOK = b'manifest nu\xc3\xb4i acc (`D:\\Taadaa\\runtime\\kibe\\cron-state\\manifests\\<ng\xc3\xa0y>\\active_manifest.json`'

def eol_bytes(b):
    return b'\r\n' if b'\r\n' in b else (b'\n' if b'\n' in b else b'')
def eol_class(b):
    e = eol_bytes(b); return 'CRLF' if e==b'\r\n' else ('LF' if e==b'\n' else 'NONE')
def ctrl(b): return [c for c in b if c <= 31 and c not in (9, 10, 13)]

# canonical block from current SOURCE, by boundary
slines = open(SOURCE, 'rb').read().split(b'\n')
s = next(i for i, l in enumerate(slines) if l == MARKER)
e = next(i for i in range(s + 1, len(slines)) if slines[i].startswith(b'### '))
blk = slines[s:e]
while blk and blk[-1] == b'': blk.pop()
block_lf = b'\n'.join(blk)
assert block_lf.startswith(MARKER) and block_lf.endswith(b'  default.')

def backup_of(rel): return os.path.join(BACKUP_DIR, rel.replace('/', '__'))

results = []; all_ok = True
for t in TARGETS:
    cur = open(os.path.join(ROOT, t), 'rb').read()
    base = open(backup_of(t), 'rb').read()
    eol = eol_bytes(cur)
    block_eol = block_lf.replace(b'\n', eol)
    expected = eol + eol + block_eol + eol
    prefix_ok = cur[:len(base)] == base
    suffix_ok = cur[len(base):] == expected
    eol_pres = eol_class(cur) == eol_class(base)
    marker_ok = cur.count(MARKER) == 1
    ok = marker_ok and prefix_ok and suffix_ok and eol_pres
    extra = ''
    if t == 'AGENTS.md' and OLD_TOK is not None:
        rev = cur.replace(NEW_TOK, OLD_TOK)
        repair_ok = (rev == base) and (b'\x07' not in cur) and (len(ctrl(cur)) == 0)
        ok = ok and repair_ok
        extra = ' repair_only_corruption=%s no_bel=%s ctrl=%d' % (rev == base, b'\x07' not in cur, len(ctrl(cur)))
    all_ok = all_ok and ok
    results.append((t, marker_ok, eol_class(cur), eol_class(base), len(cur) - len(base), ok, extra))

for (t, mk, ec, ebc, d, ok, ex) in results:
    print('[%s] %-46s mk=%d %s(was %s) +%dB%s' %
          ('OK' if ok else 'FAIL', t, mk, ec, ebc, d, ex))

# target-only scan
anomalies = []; seen = set()
for dp, _, fns in os.walk(ROOT):
    for fn in fns:
        if fn.lower().endswith('.md'):
            rel = os.path.relpath(os.path.join(dp, fn), ROOT).replace('\\', '/')
            c = open(os.path.join(dp, fn), 'rb').read().count(MARKER)
            if rel in TARGETS:
                seen.add(rel);  (c != 1) and anomalies.append((rel, c, 'target marker!=1'))
            elif c > 0:
                anomalies.append((rel, c, 'NON-TARGET has marker'))
target_only_ok = (not anomalies) and (len(seen) == len(TARGETS))
all_ok = all_ok and target_only_ok
print('\nALL_OK:', all_ok, '| target_only:', target_only_ok,
      '| anomalies:', len(anomalies), '| all targets pass:', all(r[5] for r in results))
