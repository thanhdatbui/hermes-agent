# Model Effort Sweep Playbook (max→high / high→max)

Khi user đổi reasoning effort của 1 model worker (tiền lệ: `flash/max`→`flash/high` 2026-08-06,
`luna/max`→`luna/high` 2026-08-07), sweep phải phủ TOÀN BỘ cây, giữ CRLF, và verify độc lập.
Bài học từ 2 lần sweep: lần 2 bỏ sót 5 file + hỏng CRLF 4 file — verify bắt được cả hai.

## 1. Pattern cần sweep (theo model bị đổi)

| Model | Pattern chính | Kèm theo |
|---|---|---|
| luna | `gpt-5.6-luna/max`, `Luna/max`, `luna/max` (case), `` `gpt-5.6-luna`/`max` `` (backtick) | `reasoning_effort=max`, `reasoning.effort=max`, `reasoning_effort: max` (yaml), `reasoning.effort=max` |
| flash | `flash/max` | `agent.reasoning_effort: max` (config Hermes), 9router `providerThinking.<provider>.mode` (THINK:auto) |

**LUÔN giữ nguyên model khác**: sol/max, terra/high, flash/high (khi sweep luna) — guard chống over-sweep.

## 2. Inventory — phạm vi file bắt buộc

`find` với `-prune` (KHÔNG os.walk — treo timeout trên cây D:\Taadaa do .ai-runs/runtime khổng lồ):

```bash
find . \( -name ".ai-runs" -o -name ".git" -o -name "node_modules" -o -name ".worktrees" \
  -o -name ".codex-worktrees" -o -name "automation-core-artifacts" -o -name "reports" \
  -o -name "*.bak" -o -name "*.bak-*" -o -name "CHANGELOG.md" -o -name "AGENTS_SIMPLIFY_AUDIT*" \
  -o -name "AGENTS_POLICY_AUDIT.md" -o -name "__pycache__" -o -name ".pytest_cache" \
  -o -name "build" -o -name "site-packages" -o -name "merge-backups" \) -prune \
  -o -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" -o -name "*.ps1" \
  -o -name "*.toml" -o -name "*.py" -o -name "*.json" -o -name "*.txt" \) -print \
  | xargs grep -liE "luna/max|Luna/max" | sort
```

**Pitfall ext filter**: lần đầu chỉ `*.md/*.yaml/*.yml/*.ps1` → bỏ sót `.py` (recovery_runtime.py,
recovery_supervisor.py), `.txt`… **Phải đủ `.py/.json/.txt`.** Và đừng prune nhầm thư mục LIVE:
`python_runner/` thật (không phải merge-backups), `docs/ai/`, `tasks/` đều có file policy.

## 3. Edit giữ CRLF (quy trình đúng)

```python
# 1. backup + sha256
cp "$f" "$f.bak-lunahigh-$(date +%Y%m%d%H%M%S)"

# 2. binary replace thuần — KHÔNG đụng newline
d = open(p,'rb').read()
open(p,'wb').write(d.replace(b'Luna/max', b'Luna/high').replace(b'luna/max', b'luna/high'))
```

**Pitfall PermissionError**: python `open(f,'wb')` fail Errno 13 trên path có space/ký tự đặc biệt
(`tiktok-luot nuoi acc/PROJECT_RULES.md`) dù file writable → bash sed fallback, NHƯNG:

**Pitfall CRLF (CHÍ MẠNG)**: MSYS `sed -i` phá CRLF toàn file (172→0, 2708→0, 2153→0).
- **Cách restore SAI**: `d.replace(b'\n', b'\r\n')` trên file mixed → tạo `\r\r\n` double CR, count phồng (484 vs 455). CẤM.
- **Cách đúng**: restore nguyên bản TỪ backup `.bak-lunahigh-<ts>` rồi binary replace thuần (bước 2) — CRLF count = backup 100%.

## 4. Verify (script mẫu — `hermes-verify-<topic>.py` dưới Temp)

```python
import os, sys, glob
BASE = 'D:/Taadaa'
SKIP_DIRS = {'.git','node_modules','.ai-runs','.worktrees','.codex-worktrees',
             'automation-core-artifacts','reports','__pycache__','.pytest_cache','.hermes',
             'build','site-packages','merge-backups','_luna-max-to-high-backup-20260807-060924'}
SKIP_NAME = ('CHANGELOG.md','AGENTS_SIMPLIFY_AUDIT_gemini.md','AGENTS_SIMPLIFY_AUDIT_file_v8.md','AGENTS_POLICY_AUDIT.md')
EXTS = ('.md','.yaml','.yml','.ps1','.toml','.py','.json','.txt')

def scan(needle_lower):
    hits = []
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('_luna-')]
        for fn in files:
            if fn.endswith('.bak') or '.bak-' in fn or fn in SKIP_NAME: continue
            if not fn.lower().endswith(EXTS): continue
            p = os.path.join(root, fn)
            try: data = open(p,'rb').read()
            except OSError: continue
            if needle_lower in data.lower(): hits.append(p)
    return hits

left = scan(b'luna/max')
# filter intentional doc line: skill lesson "Sweep luna/max→luna/high 2026-08-07" describes the pattern
filtered = [p for p in left if not ('hermes-orchestration-dispatcher' in p and p.endswith('SKILL.md'))]
print('leftover:', filtered)   # MUST be []

# CRLF vs backup (backup cạnh file .bak-lunahigh-*, fallback backup dir)
for rel in ['AGENTS.md','HERMES_SUBAGENT_RULES.md',
            'tiktok-luot nuoi acc/python_runner/scheduler/recovery_runtime.py']:
    cur = os.path.join(BASE, rel)
    cands = sorted(glob.glob(cur + '.bak-lunahigh-*'))
    bak = cands[-1] if cands else os.path.join(BASE,'_luna-max-to-high-backup-20260807-060924', rel)
    cc = open(cur,'rb').read().count(b'\r\n'); bc = open(bak,'rb').read().count(b'\r\n')
    print(f'CRLF {rel}: {cc}=={bc} {"OK" if cc==bc else "FAIL"}')
```

**Pitfall verify**:
- Dòng bài học mô tả chính pattern (`- **Sweep luna/max→luna/high...`) là FALSE POSITIVE — giữ chủ ý, filter khỏi leftover check.
- SKILL.md CRLF-strict check phải loại khi `skill_manage patch` chủ ý thêm dòng (369 vs 368) — diff lines, không count cứng.
- Verify vòng 2 bắt thêm file sót (`tasks/2026-08-04-autonomous-schedule-recovery.md`) → sau sweep CHẠY verify, không tự tin bằng mắt.

## 5. Sau sweep — rà skill bị đụng

Sweep đổi cả ghi chú LỊCH SỬ trong skill (line mô tả sweep flash cũ thành
`reasoning_effort=high`→`=high` vô nghĩa). Sau khi sweep: grep skill tìm pattern bị vỡ nghĩa,
sửa lại + thêm bài học mới. Không để skill tự mâu thuẫn.

## 6. Sync

- `Hermes/skills/**` junction tới git repo → sửa local = git thấy ngay; cron `sync-hermes-skills-to-git` tự push (≤30 phút) hoặc chạy `python C:\Users\Kibe\AppData\Local\hermes\scripts\sync-hermes-skills.py`.
- Backup giữ nguyên (`_luna-max-to-high-backup-<ts>/` + `.bak-lunahigh-*`) cho rollback; chỉ dọn khi user yêu cầu.

## 7. Variant: targeted policy-file sweep với release-gate greps (2026-08-08, v5-high)

Khác sweep toàn cây (§1-6), variant này sửa ĐÚNG 2 file policy (AGENTS.md + SKILL.md) với
release-gate là bộ greps khớp-như-contract. Quy trình đã chạy thành công:

**Bước 0 — GREP-FIRST enumerate, đừng tin danh sách line từ task/plan.** Task báo "5 dòng sót"
(L24/700/719/1079/1094) nhưng grep `sonnet-5` lộ thêm **L1123** `(claude-sonnet-5, effort high,
or claude-opus-5, effort medium)` — chứa CẢ 2 pattern cấm; sửa thiếu = gate fail. Grep gate là
contract, line list chỉ là gợi ý. Luôn chạy ĐỦ bộ gates TRƯỚC khi viết edit script:
```bash
grep -n "sonnet-5" AGENTS.md; grep -n "opus-5" AGENTS.md   # enumerate
grep -c "sonnet-5" AGENTS.md                                # gate cấm: phải = 0 sau khi sửa
grep -c "opus-5.*medium\|opus-5./medium" AGENTS.md          # gate cấm: = 0
grep -c "claude-opus-5.*high\|opus-5.*high" AGENTS.md       # gate dương: >= N
```

**Gate semantics (thiết kế regex đúng ngữ nghĩa):**
- `grep sonnet-5` match SUBSTRING → `claude-sonnet-5` (model AG hợp lệ, GIỮ NGUYÊN) cũng trúng;
  `claude-sonnet-4-6` thì không. Gate cấm phải nhắm đúng token bị bỏ (`sonnet-5`), không nhắm family.
- `opus-5.*medium` match NGANG DÒNG → `(`claude-opus-5`, effort `medium`)` trúng. Gate dương
  (`.*high` ≥ N) bắt buộc kèm để chứng minh pattern MỚI đã vào, không chỉ pattern cũ biến mất.
- Các `medium` ngoài phạm vi phải liệt kê chủ ý: nhãn độ khó task (`(medium-hard)`,
  `medium/hard classification`) và executor ladder deepseek-pro (`Pro/low, medium, high, max`,
  `model_reasoning_effort` valid-values) — KHÔNG đụng, note vào báo cáo.

**Edit script — sentinel pairs + expected count (mẫu):**
```python
edits = [  # (old, new, count_kỳ_vọng) — count TRƯỚC replace, fail nếu lệch
  (b"...(`sonnet-5`/high or `opus-5`/medium,", b"..(`claude-opus-5`/high,", 1),
  (b"  `ag/claude-sonnet-4-6`/high -> Claude CLI (`sonnet-5`/high for medium tasks,\n"
   b"  `opus-5`/medium for hard tasks, quota-gated) -> OpenCode free (dynamic",
   b"  `ag/claude-sonnet-4-6`/high -> Claude CLI (`claude-opus-5`/high for hard tasks,\n"
   b"  quota-gated) -> OpenCode free (dynamic", 2),  # block trùng ×2 (L1079 + L1094)
]
for old, new, cnt in edits:
    assert data.count(old) == cnt, f"count {data.count(old)} != {cnt}"
    data = data.replace(old, new)
```
Chuỗi có tiếng Việt/unichar (em-dash, TRƯỚC) → `.encode('utf-8')` trong script, đừng gõ hex tay.
Backup `.bak-v5-high-<ts>` cạnh file + sha256 before/after.

**Byte-identical proof — SIMULATION replace (không diff, không reverse-patch tay):**
```python
sim = orig                       # bytes ĐỌC ĐẦU TIÊN, trước mọi replace
for old, new, cnt in edits: sim = sim.replace(old, new)
assert sim == final, "KHÔNG byte-identical ngoài vùng sửa"
```
Apply lại ĐÚNG pairs lên bytes gốc rồi so == bytes cuối = chứng minh chặt chẽ nhất; diff/reverse
patch tay là nguồn typo.

**EOL probe từng file, không giả định:** AGENTS.md LF-only (CRLF=0), SKILL.md toàn CRLF —
insert dòng bài học mới phải mang đúng `\r\n` (anchor `...one-slot).` rồi chèn `\r\n- **...`),
count CRLF sau = trước + 1.

**Lịch sử có ngày = ngoại lệ chủ ý:** dòng bài học ghi ngày còn nhắc pattern cũ (SKILL.md L288
`claude-opus-5` medium) GIỮ NGUYÊN; sau khi sửa, grep còn sót phải == đúng số dòng lịch sử đó
(SKILL.md `opus-5.*medium` == 1 = L288) — assert số này, không phải 0. Verify độc lập bằng shell
grep lại (không chỉ tin self-report script) + sha256sum backup vs "before".
