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

## 3. Anti-paralysis và tính xác thực của closeout

- Không được coi `exit code 0`, điểm reviewer, receipt, hoặc self-report là bằng chứng độc lập. Chỉ claim `APPROVED`, `PUSHED`, hoặc `DONE` khi artifact hiện tại khớp đúng HEAD/scope và các focused test, canary, evidence gate bắt buộc đều đã được kiểm tra.
- Không tạo nhánh "giữ local rồi kết thúc" sau khi mechanical gate đã xanh. Quy trình phải có kết thúc hữu hạn: remediation có giới hạn, chạy lại mechanical gate, rồi commit/push qua wrapper đã kiểm soát. Nếu gate đỏ, báo đúng lỗi tái hiện được và đường dẫn bằng chứng; không bịa Grace, không tự hạ ngưỡng, không biến nhận xét reviewer thành lỗi.
- Grace Band chỉ được dùng khi policy hiện hành và audit artifact trực tiếp cho phép; không suy ra từ biên bản cũ hoặc lời kể trong phiên. Grace không thay thế test, canary, evidence, scope binding, hay P0/P1 gate.
- Khi user yêu cầu Claude CLI review, gọi đúng wrapper/role, yêu cầu verdict cuối rõ ràng, và đối chiếu verdict với diff hiện tại. Claude trả exit 0 nhưng thiếu verdict hoặc review nhầm scope vẫn là chưa duyệt.
- Giới hạn review/remediation phải hữu hạn. Sau mỗi lần rớt, phân loại transient/structural/business; chỉ sửa finding có bằng chứng cụ thể, không score-chasing vô hạn. Reviewer chỉ được chặn khi chỉ ra repro/test đỏ/crash hoặc vi phạm gate có artifact, không phải chỉ bằng câu "nên bổ sung".
- Với UI/farm, receipt phải gắn run hiện tại và ảnh phải được soi/OCR trước claim thành công. Popup hoặc từ khóa âm phải đi qua handler tự phục hồi có giới hạn; không gửi ảnh mù và không chạy vòng lặp UI vô hạn.

## 4. Tài Liệu Tham Khảo (References)
- Adversarial Gate Hardening & In-Process PEB Isolation: [`references/adversarial-gate-hardening-and-peb-isolation.md`](references/adversarial-gate-hardening-and-peb-isolation.md)
- Anti-Paralysis Mechanical Override & Zero-Local-Deferred: [`references/anti-paralysis-mechanical-override-and-zero-local-deferred-20261018.md`](references/anti-paralysis-mechanical-override-and-zero-local-deferred-20261018.md)
- Sol Closeout Gate Lifecycle: [`references/sol-closeout-gate-lifecycle.md`](references/sol-closeout-gate-lifecycle.md)
- Anti-Premature Block: [`references/anti-premature-block-in-closeout.md`](references/anti-premature-block-in-closeout.md)
- Session Close Remediation Discipline: [`references/session-close-remediation-discipline.md`](references/session-close-remediation-discipline.md)
- Evidence-first anti-paralysis closeout: [`references/evidence-first-anti-paralysis-closeout.md`](references/evidence-first-anti-paralysis-closeout.md)
- Multi-Round Adversarial Gate Hardening & Fail-Closed Review: [`references/multi-round-adversarial-gate-hardening-lessons-20261022.md`](references/multi-round-adversarial-gate-hardening-lessons-20261022.md)
- Claude Quota Silent Fallback & Safe Push Invariants: [`references/claude-quota-silent-fallback-and-safe-push-invariants.md`](references/claude-quota-silent-fallback-and-safe-push-invariants.md)
- GPM CDP Login-Only Closeout Recipe: [`references/gpm-cdp-login-only-closeout-recipe-20261022.md`](references/gpm-cdp-login-only-closeout-recipe-20261022.md)
- Claude Quota Cache Invalidation & Sonnet Review Timeout: [`references/claude-quota-cache-invalidation-and-sonnet-review-timeout.md`](references/claude-quota-cache-invalidation-and-sonnet-review-timeout.md)
