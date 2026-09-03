# File surgery one-shots (verified 2026-08-09, `tiktok-upload-ui-recovery`)

## Restore a destroyed SKILL.md from the tool-output cache

When a file was truncated to 0 bytes (open('wb') + exception), the full original
is in the persisted tool result. Extract + write, single write:

```python
import json, os
cache = r'C:\Users\Kibe\AppData\Local\hermes\cache\terminal\hermes-results\<call_id>.txt'
data = json.load(open(cache, encoding='utf-8'))
content = data['content']                      # full original SKILL.md text
# detect EOL from the ORIGINAL file's recorded file_size if known; farm skills = CRLF
payload = content.replace('\n', '\r\n').encode('utf-8')
open(p, 'wb').write(payload)                    # single write, nothing else after
# verify: len(payload) == file_size recorded in the first read_file of the session
import hashlib
print(hashlib.sha256(payload).hexdigest())      # keep this for the audit
```

## Trim: move sections to references, keep EOL, build-then-write

```python
import os
base = r'...\skills\<cat>\<skill>'
p = os.path.join(base, 'SKILL.md')
raw = open(p, 'rb').read()
nl_s = '\r\n' if b'\r\n' in raw else '\n'       # detect EOL FIRST
lines = raw.decode('utf-8').split(nl_s)

def find_idx(prefix):
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    if not hits: raise SystemExit('anchor not found: ' + prefix)
    return hits[0]

s = find_idx('## SectionToMove')
e = find_idx('## NextSectionAfter')
moved = [lines[s]] + lines[(s+1):e]             # verbatim, heading included

new_lines = lines[:s] + ['## Brief pointer line', '', '> Full content: `references/moved.md`.', ''] + lines[e:]
new_txt = nl_s.join(new_lines)

# BUILD BOTH payloads first, then single writes (never open('wb') mid-computation)
open(p, 'wb').write(nl_s.encode().join(l.encode() for l in new_lines) + nl_s.encode())
ref_payload = ('\n'.join(moved)).replace('\n', nl_s).encode('utf-8') + nl_s.encode()
open(os.path.join(base, 'references', 'moved.md'), 'wb').write(ref_payload)
print('SKILL.md chars:', len(new_txt), '(limit 100000)')
```

Key rules baked in:
- Anchor by heading PREFIX (`startswith`), not line numbers — headers move.
- Build the entire output in memory; the ONLY `open('wb')` calls are the final single writes.
- `find_idx` raises with the missing anchor name instead of writing garbage.