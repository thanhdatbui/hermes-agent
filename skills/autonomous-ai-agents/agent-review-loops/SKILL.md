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

## 2. Quy Chuẩn Strike Khắc Phục (3-Strike Reviewer Hand-off & Mechanical Override)
- **Strike 1 & 2:** Sol Repair (:20129) tạo proposal O(1) AST.
- **Strike 3:** Trượt 3 lần -> Chuyển giao quyền can thiệp cho `claude_worker.py --role worker` (Haiku 5.5) hoặc `ag_cli.py fix`.
- **Mechanical Override & CẤM TUYỆT ĐỐI RAW GIT PUSH:**
  * Giới hạn tối đa 3 vòng sửa (`MAX_FIX_ATTEMPTS = 3`). Khi hết 3 lượt attempt mà Reviewer vẫn không approve, nhưng Mechanical Gate xanh 100% (pytest pass, diff <= 150 dòng, test count không giảm, không đụng protected paths).
  * **CẤM RAW GIT PUSH KHI BỊ CHẶN:** Mọi push bắt buộc phải đi qua `safe_push.py`. Khi `safe_push.py` chặn (`BLOCKED_GATE_NOT_APPROVED` hoặc `BLOCKED_AGENT_OVERRIDE`), CẤM TUYỆT ĐỐI Coordinator tự ý gõ `git push` trực tiếp để lách gate. Việc lách gate để push code chưa đạt điểm reviewer là vi phạm Hard Invariant cấp cao nhất.
  * Khi gặp bế tắc điểm review mà không thể pass gate: Báo cáo trung thực trạng thái (điểm số, finding của reviewer, log pytest, canary status) và chờ chỉ đạo của User, KHÔNG được tự tiện force push hoặc cowboy push.
- **Phân Biệt Reviewer Engine (Claude Sonnet CLI vs Sol System Prompt):**
  * Trong `closeout_gate.py`, Tier 0 Primary Reviewer là Claude Sonnet CLI (`claude --model sonnet --effort high`).
  * System prompt của gate bắt đầu bằng danh xưng "Bạn là Sol Auditor...", nhưng engine thực thi là Claude Sonnet CLI (`base_url: "claude_cli:sonnet"` trong `gate_audit.jsonl`).
  * CẤM nhầm lẫn persona trong prompt với engine thực thi. Chỉ khi Claude Sonnet CLI timeout/lỗi thì gate mới fallback sang Tier 1 OmniRoute (:20129).
- **Chỉ dừng khi có Bug thật (`BLOCKED_BY_REPRODUCED_BUG`):** Chỉ dừng khi có test đỏ hoặc crash thật; reviewer bắt bẻ cảm tính không có repro thì không được chặn push.
- **Kỷ Luật "Cấm Khóc Lóc Blocked Khi Làm Việc":** Không được lấy lý do "reviewer chưa approve" hoặc tranh cãi ranh giới kiến trúc cấp hệ điều hành (user-space permissions) để đóng băng phiên hay than phiền blocked. Khi Mechanical Gate và test suite xanh 100%, Coordinator chủ động đặc tả rõ Threat Model Scope, thực thi dứt điểm và đưa task về đích.
- Bỏ qua Sol cày điểm sau khi Claude CLI sửa xong và test pass 100%.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
