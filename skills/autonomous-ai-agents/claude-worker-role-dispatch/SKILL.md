---
name: claude-worker-role-dispatch
description: "Dispatch Claude CLI with role, turns cap and gate."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [claude, worker, dispatcher, role-based, quota-gate, turns-cap, farm-safety]
    related_skills: [claude-limit-protection, hermes-orchestration-dispatcher, monolith-modularization-and-architecture-gates]
---
# Claude Worker Role-Based Dispatch

- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

Use this skill when calling Claude Code CLI for any task on the Taadaa Farm. All Claude CLI invocations MUST go through `D:/Taadaa/tools/claude_worker.py`, never via raw `claude -p` in terminal.

## Architecture Gate: Bắt Buộc Claude Sonnet Plan Khi Can Thiệp Kiến Trúc / Auth
- **Quy tắc Gate bất biến:** Khi phát hiện thay đổi cơ chế xác thực hoặc kiến trúc hệ thống cốt lõi (như thay đổi cơ chế lưu/đọc token, can thiệp Windows Credential Manager `wincred`, đổi protocol hoặc luồng dữ liệu tiến trình), Coordinator **BẮT BUỘC PHẢI GỌI CLAUDE SONNET LÊN PLAN TRƯỚC** (`--role planner` hoặc Sonnet CLI).
- **CẤM NHẢY CÓC:** Tuyệt đối cấm Coordinator tự ý chốt giải pháp kiến trúc rồi gọi thẳng Haiku Worker thi công code mà bỏ qua bước lập plan của Claude Sonnet.

## CRITICAL: Correct Model Aliases

| Intent | Alias đúng | WRONG (exit 1) |
|--------|-----------|----------------|
| Sonnet | `sonnet` | `claude-sonnet`, `claude-sonnet-5-5` |
| Haiku | `haiku` | `claude-haiku` |
| Opus | `opus` | `claude-opus` |

Alias sai → error "isn't described by this version's model catalog" → exit 1.

### Bẫy Disabling Tools `--tools ""` trong Python Subprocess (2026-10-23)
Khi cần tắt hoàn toàn công cụ khi gọi `claude -p` (ví dụ chạy review chỉ đọc code), bắt buộc truyền `cmd = [..., "--tools", ""]` (chuỗi rỗng).
CẤM truyền `"--tools", "\"\""` vì Python `subprocess.run(shell=False)` sẽ gửi nguyên vẹn 2 ký tự nháy kép `""` sang binary, khiến Claude CLI phân tích thành tên công cụ rác và báo lỗi cú pháp.

### Bẫy Quota Reset-Hint & Cache 2 Giờ (2026-10-23)
Khi qua giờ reset quota 5h của Claude (ví dụ 3:49am), cache `plan-usage-history.json` vẫn chưa đủ 2 giờ để xem là stale (`MAX_QUOTA_STALE_HOURS = 2.0`), khiến `claude_worker.py` tiếp tục chặn `QUOTA_GATE` với mẫu cũ 100%.
Khắc phục: Ép làm mới ngay qua lệnh:
`python -c "import sys; sys.path.insert(0, 'D:/Taadaa/tools'); from claude_worker import try_refresh_claude_quota; try_refresh_claude_quota()"`
để lấy mẫu quota mới (0%) từ `claude -p /usage` cập nhật vào cache.

**Gate ABC Incident (2026-10-22):** Coordinator bỏ qua Gate A+B sau T0, tự viết >100 dòng và deploy. Post-mortem: `references/gate-abc-enforcement-gap-incident-20261022.md`.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
