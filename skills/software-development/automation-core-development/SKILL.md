---

name: automation-core-development

description: "Develop the shared automation-core control plane (D:\\Taadaa\\automation-core) itself — plan-phase builds touching recovery/device_lock/batch_aggregator/scheduler. Covers worktree rules, PYTHONPATH=src testing (see references/batch-aggregator-post-verification-exclusion.md, references/batch-aggregator-session-lost-vs-challenge.md & references/stale-site-packages-shadowing-reconciliation.md), full-suite collection blocker, CRLF-safe editing (patch-tool fuzzy matcher mangling), recovery-contract invariants incl. FAILED_LOCKED, the Phase 3 user-explicit lock open (cli.py lock list/inspect/open), and RED/GREEN verification evidence."

version: 1.0.0

author: Hermes Agent

platforms: [windows]

metadata:

  hermes:

    tags: [automation-core, recovery, device-lock, scheduler, worktree, tdd, crlf, verification]

    related_skills: [automation-core-consumer, test-driven-development, concurrent-workspace-safety, git-worktree-merge-reconciliation]

---
# automation-core-development

> References quan trọng:
> - `references/startup-monkey-launch-resilience.md`: Cơ chế launch app monkey an toàn (pre-check foreground, timeout/exception recovery, retry guard) & cạm bẫy mock `focus_reader` trong unit test.
> - `references/device-lock-finish-ambient-exception-capture.md` — Bẫy `sys.exc_info()[1] is None` dead code trong khối `except` của `finish()`, nuốt lỗi release; giải pháp chụp `ambient_exc` trước `try` block (Claude Opus High approved 07/09/2026).
> - `references/stale-site-packages-shadowing-reconciliation.md` — Thư mục tĩnh site-packages đè src khi dùng pip editable.
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

Develop the SHARED CORE repo `D:\Taadaa\automation-core` itself (app-neutral

control plane). Complement of `automation-core-consumer` (consumer adapters):

core owns mechanisms/state machines; consumers own provider/account/workbook

policy. Load this skill when the task edits `src/automation_core/**`,

implements a phase from `.hermes/plans/*.md` in this repo, or runs the

recovery/device-lock/scheduler contract tests.

**Quy tắc phân định Scope (User Rule 2026-08-29)**:
- `automation-core` CHUYÊN xử lý TikTok và các cơ chế/hạ tầng dùng chung (device lock, VPN, startup, scheduler, UI parser).
- Tuyệt đối KHÔNG đẩy các xử lý UI/flow đặc thù của app bên ngoài (như quy trình đăng nhập Google Account, Gmail add mail, Hotmail) vào `automation-core`. Các flow đó thuộc về các repo chuyên trách riêng biệt (`add mail khoi phuc`, `Hotmail`, `Tiktok_Reg`).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
