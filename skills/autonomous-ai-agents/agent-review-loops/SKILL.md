---
name: agent-review-loops
description: "Điều phối coding review đến APPROVED."
version: 1.2.6
metadata:
  hermes:
    tags: [orchestration, codex, claude, opencode, review-loop, preflight, live-validation]
    related_skills: [claude-code, codex, agent-model-routing, hermes-orchestration-dispatcher]
---
# Agent Review Loops

## 1. Nguyên Tắc Điều Phối & Phân Tầng
- **T1 Sửa nhỏ O(1) <= 15 dòng:** Coordinator tự sửa, verify focused test < 30s.
- **T2 Thi công lớn > 15 dòng:** Single Dispatch Gateway `dispatch_worker.py` (Haiku 5.5 CLI -> Agy CLI).
- **Thẩm định chốt phiên:** Bắt buộc chạy `closeout_gate.py`. Đạt >= 85 (hoặc Grace Band 80-84 diff <= 30) -> auto push qua `safe_push.py`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
