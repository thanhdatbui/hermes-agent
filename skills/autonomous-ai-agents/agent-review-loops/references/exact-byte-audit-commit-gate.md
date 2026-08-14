# Exact-byte pre-commit audit → commit gate (Phase 9B pattern, 2026-08-14)

Proven 4× liên tiếp (9B.1, 9B.2, 9B.2b, 9B.3) trên authority worktree
`tiktok-luot-nuoi-acc-phase9-authority-910a8add`. Đây là cách audit candidate
**chưa commit** (worktree dirty, chờ gate) bằng AG Opus exact-byte + commit
đúng allowlist.

## Pipeline

1. TDD RED → GREEN → full suite → static gates: `py_compile` (module thật),
   PowerShell parser cho `.ps1` (KHÔNG bao giờ `py_compile` .ps1),
   `git diff --check`, EOL/BOM (LF, no BOM).
2. Ghi evidence JSON vào `C:\Users\Kibe\AppData\Local\hermes\cache\terminal\`
   — per-file: bytes/lines/sha256/lf/crlf/bom + status_short + test counts.
3. Viết **bundle builder** (`build_phase9_9bN_reaudit.py`): chạy `git
   rev-parse HEAD` + `git branch --show-current` + `git status --short
   --untracked-files=all` (chặn nếu HEAD ≠ expected), đọc evidence, rồi dựng
   prompt file chứa: EXACT STATUS, per-file binding
   `rel\tsha256=...\tbytes=...\tlines=...\tlf=...\tcrlf=...\tbom=...`, plan
   section (numbered lines), evidence, FULL numbered content (`i|line`) của
   từng file allowlist + diff của file bị edit, 10-11 mandatory questions,
   verdict rule. Writes prompt txt (không in qua argv).
4. Chạy builder foreground (nhanh). Rồi AG audit **background**:
   ```bash
   python "D:/Taadaa/reports/ag-audit/ag_audit_direct.py" \
     "<prompt>.txt" ag/claude-opus-4-6-thinking "<response>.md" 600
   ```
   PHẢI `background=true` (audit 2-8 phút) — foreground timeout tối đa 600s.
   `run-ag-audit.sh` chỉ audit `git show <commit>` — KHÔNG dùng cho candidate
   chưa commit.
5. APPROVED → **commit helper** (`commit_phase9_9bN.py`): verify dòng đầu
   response == `APPROVED`; HEAD == expected parent; branch đúng; dirty paths
   (`porcelain -z`) == EXACT allowlist (set + count); `git diff --check`;
   re-hash file hiện tại == audited binding (reject nếu bytes đổi sau audit);
   EOL/BOM; `git add -- <paths>`; staged `--name-only` == allowlist; staged
   blob sha (`git show :<path>`) == current; `git commit -m <msg> -- <paths>`;
   post-commit `HEAD^` == parent, committed files == allowlist, worktree
   clean. KHÔNG push/amend.
6. Post-commit verify: `git log -1 --oneline`, `git rev-parse HEAD HEAD^`,
   `git status --short`.

## Pitfalls (đều hit thật 2026-08-14)

- **Post-audit edit invalidates verdict.** AG APPROVED kèm minor note về
  dead-path env trong PS1 → fix → PHẢI rebuild bundle + re-audit exact bytes
  mới. Không bao giờ commit bytes khác bytes đã audit.
- **Evidence SHA ≠ binding SHA**: khi AG note "evidence SHA không khớp
  binding" (evidence cũ sau khi fix) → binding là authority; refresh evidence
  file khớp binding trước khi commit.
- **Human-text parser: block split** dùng `(?m)^(?=  [0-9a-fA-F]{4,}\s*\[)` —
  lookahead kiểu `\n(?=...)` bỏ SÓT block đầu tiên (không có `\n` trước).
- **Regex id class phải khớp format id thật**: Hermes cron id là hex 12+
  chars (`7e576815788f`); fake `j0001` fail `[0-9a-fA-F]`. Khi fake store,
  dùng hex (`0001abcd`, `a1b2c3d4`) — chính fake sai, không phải parser sai.
- **`str(timedelta(hours=7))` == `"7:00:00"`**, KHÔNG phải `"+07:00"` — assert
  flag `hcm_equivalent`, đừng assert chuỗi offset.
- **Missing top-level `import json`** tái diễn khi code viết bằng
  `__import__("json")` inline — dùng MỘT import ở module level (staging.py +
  test module đều dính).
- **Helper gọi sai số arg** (`_assert_edited_paused(edited, spec, txn_id,
  pre)` vs signature 3 param) — kiểm signature helper trước khi gọi.
- **Time-of-day dependent test**: wrapper test dùng real-now fail lúc
  02:00-05:59 HCM (silent window). Luôn inject clock cố định
  (`HERMES_CRON_NOW` / `now_fn`) cho test wrapper behavior, không dùng
  real-now.
- **Sau machine reset**: process nền cũ có thể báo
  `Orphan recovery ... effect UNKNOWN` — chỉ cần chạy lại lệnh, không phải
  lỗi code.
