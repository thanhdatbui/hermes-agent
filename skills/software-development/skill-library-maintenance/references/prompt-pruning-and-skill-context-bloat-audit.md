# Prompt Pruning via Mechanical Gates & Skill Context-Bloat Audit

## 1. Context & Incident (17/10/2026)
In this session, background janitor/sync tasks popped up visible `cmd.exe` windows on Windows during interactive gaming, tabbing the user out.
The user demanded:
1. Design a mechanical AST gate (`guard_cronjob_safety.py`) to block any unsuppressed console windows at tool invocation rather than relying on prompt warnings.
2. Audit all rules that already have mechanical gates in place and prune the prompt prose to eliminate token waste.
3. Audit Hermes skills for prompt/content bloat (skills with inlined logs, rules, and prose exceeding 100KB).

---

## 2. Mechanical Gate vs Prompt Prose Pruning Matrix
When a mechanical gate enforces an invariant fail-closed at runtime, prose warnings in system prompts (`PROJECT_RULES.md`, `AGENTS.md`) become redundant dead weight. Pruning them reduces prompt tokens by 30-40% without compromising safety:

| Domain | Mechanical Hook / Gate | Enforced Behavior | Prompt Pruning Action |
|---|---|---|---|
| **Console Window Suppression** | `guard_cronjob_safety.py` | Quét AST script: bắt buộc `0x08000000` (`CREATE_NO_WINDOW`), cấm `os.system`/`os.popen`, bắt buộc `pythonw`/`Hidden`. | Xóa toàn bộ văn bản răn đe "cấm bật cmd cướp focus"; hook tự động chặn khi tạo cron/terminal. |
| **Broad Directory Search** | `guard_broad_grep.py` | Chặn đứng `os.walk`, `rg`, `find`, `grep -r`, `Get-ChildItem -recurse` trên `D:\`. | Xóa các đoạn cấm quét đĩa dài dòng; chỉ giữ 1 dòng định tuyến: `inspect_machine.py <N>`. |
| **Subagent Code Edits** | `guard_dispatch_contract.py` | Chặn `delegate_task` khi có intent sửa code nếu chưa có Patch Contract O(1). | Xóa các đoạn giải thích lý do cấm subagent sửa code lan man. |
| **Large File Dumps** | `guard_read_file_size.py` | Chặn `read_file` trên file lớn nếu không truyền `offset`/`limit`. | Xóa khỏi prompt; hook tự ép budget ký tự. |
| **Pytest Scope** | `guard_pytest_scope.py` | Chặn lệnh `pytest` trần không có target file cụ thể. | Thu gọn thành 1 cụm ngắn: `focused test < 30s`. |
| **Closeout Review Loop** | `closeout_gate.py` & `pre-push.sh` | Hook pre-push từ chối `git push` nếu Sol Reviewer chấm < 80 điểm hoặc có test fail. | Cắt bỏ 40 dòng mô tả thủ tục 5 bước; chỉ giữ 1 dòng trigger CLI. |

---

## 3. Skill Library Context-Bloat Audit Findings
An audit across 182 skills revealed widespread inlining of operational logs, duplicated rules, and historical case studies directly into `SKILL.md` (many exceeding 100KB / 700 lines):
- `automation/taadaa-farm-ops-rules` (116.2 KB)
- `automation/farm-anti-overengineering` (112.0 KB)
- `software-development/tiktok-registration-ops` (110.1 KB)
- `devops/gpm-account-pool-automation` (109.9 KB)
- `software-development/tiktok-upload-ui-recovery` (109.8 KB)
- `automation/taadaa-farm-batch-ops` (109.1 KB)
- `software-development/tiktok-login-automation` (109.1 KB)

### The Anti-Pattern & Impact:
1. **Severe Session Context Pollution:** Loading a single 110KB skill injects ~30,000 tokens into the session context, triggering early compaction loops, latency spikes, and reasoning degradation.
2. **Duplication of System Invariants:** Rules already present in `PROJECT_RULES.md` were copied verbatim into multiple individual skills.

### Architectural Standard for Thin Skills:
- **`SKILL.md` (Core Anchor):** Strictly keep ≤ 100–150 lines (≤ 10–15 KB). Contains only the trigger condition, the single canonical entrypoint/tool command, and high-level pitfalls.
- **`references/<topic>.md` (On-Demand Deep Dives):** Historical cases, detailed error logs, JSON schemas, and platform quirks belong exclusively in `references/`.
- **Atomic Surgery:** When trimming a >100KB skill, extract section blocks verbatim into `references/<subtopic>.md` before replacing with a 1-line reference in `SKILL.md`, ensuring `kept_chars + moved_chars ≈ original_chars`.
