---
name: multi-agent-review-loop
description: "Điều phối worker-reviewer với phản biện hai chiều."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [multi-agent, coding, review, codex, claude, opencode, orchestration]
    category: software-development
---

# Multi-Agent Review Loop Skill

Skill này điều phối một agent làm code và một agent review/audit theo vòng phản biện hai chiều. Nó không gắn cứng vendor/model, không tự coi `APPROVED` là đủ nếu chưa có bằng chứng test, và chỉ dùng reviewer fallback khi reviewer chính hết quota hoặc provider lỗi.

## When to Use

- Khi cần một coding agent implement rồi reviewer độc lập audit.
- Khi muốn worker đọc finding, chấp nhận hoặc phản biện từng finding.
- Khi cần đổi Codex/Claude/OpenCode/model mà không đổi logic orchestration.

## Role Separation (Critical)

Khi user đã giao role rõ ràng (ví dụ: "Codex plan và code, Claude audit và review, Hermes chỉ điều phối"), **TUYỆT ĐỐI KHÔNG tự ý làm thay**:

- **Hermes = Orchestrator**: Chỉ điều phối, dispatch, tổng hợp kết quả. KHÔNG code, KHÔNG audit, KHÔNG review.
- **Codex = Plan + Code**: Dispatch cho planning, architecture, implementation.
- **Claude = Audit + Review**: Dispatch cho audit findings, code review.

### Pitfall: Không tự ý code khi đã giao role

**WRONG**: User giao "Codex code" → Hermes tự write_file/patch vì nghĩ "leaf không thể write file" → phải code trực tiếp.

**RIGHT**: User giao "Codex code" → Hermes dispatch Codex subagent. Nếu subagent role="leaf" không thể write file, đó là vấn đề của **routing**, không phải lý do để Hermes làm thay. Giải pháp: dispatch với role phù hợp hoặc hỏi user, không tự ý nhận việc.

### Workflow đúng

```text
1. Hermes nhận task
2. Dispatch Codex (role=orchestrator/leaf) → Plan + Code
3. Dispatch Claude (role=leaf, model=opus-5) → Audit/Review
4. Nếu NEEDS_CHANGES → Dispatch Codex fix
5. Re-review cho đến khi PASS
6. Hermes tổng hợp kết quả cuối
```

**Tuyệt đối không**: Hermes tự write_file/patch/edit code khi đã có thỏa thuận role separation.

## Model Routing for Reviewer

Khi user đã chỉ định model cho reviewer (ví dụ: "Claude audit/review dùng opus-5"), **luân phiên dispatch đúng model**:

```text
reviewer: model=claude-opus-5  # hoặc model user chỉ định
worker: model=codex-mini  # hoặc model mặc định cho coding
```

**Không hardcode model trong logic orchestration.** Model chỉ nằm trong RoleSpec/config khi dispatch. Nếu user thay đổi preference ("từ giờ dùng opus-5"), cập nhật memory và áp dụng ngay lần dispatch tiếp theo.

## Prerequisites

- Git repository và working directory rõ ràng.
- CLI của worker/reviewer đã được cài và xác thực.
- Không cho worker và reviewer cùng sửa working tree trong cùng thời điểm.
- Với Windows CMD, không dùng `\\` để nối dòng; viết một dòng hoặc dùng `^`.

## How to Run

1. Xác định role: `worker`, `reviewer`, `fallback_reviewer`.
2. Cấu hình backend/model theo role; không hardcode vendor trong protocol.
3. Worker implement và ghi report.
4. Reviewer đọc task, diff, test output trước khi đọc report của worker.
5. Worker trả lời từng finding bằng `ACCEPT` hoặc `REJECT`, kèm rationale/evidence.
6. Reviewer re-check phản hồi; lặp tối đa số vòng đã đặt.
7. Chỉ hoàn tất khi reviewer approve và final tests pass.

## Quick Reference

```text
implementation → audit → finding_response → consensus
```

Verdict chính:

```text
APPROVED
CHANGES_REQUESTED
FINAL_BLOCKED
MAX_ROUNDS
```

Fallback chỉ kích hoạt với lỗi được phân loại `quota` hoặc `provider`; không nuốt lỗi task/contract.

## Procedure

### 1. Role-based routing

Dùng interface chung kiểu:

```text
worker.run(task, context) -> implementation result
reviewer.review(task, diff, tests) -> structured verdict
```

Model/backend chỉ nằm trong `RoleSpec` hoặc config. Ví dụ routing có thể là:

```text
worker mặc định: model coding nhanh
worker khi plan/audit/code change: model reasoning cao
reviewer: model độc lập, read-only
fallback reviewer: backend khác khi quota/provider lỗi
```

Không đưa secret vào state/artifact; chỉ persist role name, backend và option keys.

### 2. Review độc lập

Reviewer phải:

- Đọc task/spec và diff thực tế.
- Kiểm tra code path, error path, sibling path và test coverage.
- Không tin self-report của worker trước khi kiểm tra evidence.
- Ghi finding có id, severity, file/location, evidence và required fix.
- Phân biệt blocking với non-blocking; chỉ blocking mới bắt worker sửa.

### 3. Hai chiều

Worker phải trả lời đủ từng finding:

```json
{
  "finding_id": "F1",
  "disposition": "ACCEPT",
  "rationale": "...",
  "evidence": ["tests/..." ]
}
```

Nếu `REJECT`, phải nêu bằng chứng hoặc reproduction; không chỉ nói “không đồng ý”. Reviewer phải phản hồi lại từng `REJECT`, giữ hoặc rút finding, rồi mới quyết định consensus.

### 4. State và recovery

Ghi state sau mỗi phase và artifact riêng theo round. Dùng atomic replace khi ghi JSON. Giới hạn số vòng; nếu cùng finding lặp lại mà không có thay đổi có ý nghĩa, chuyển `FINAL_BLOCKED` thay vì loop vô hạn. Khi resume, kiểm tra task và role configuration có khớp state.

### 5. Verification

Final success cần cả:

```text
reviewer: APPROVED
worker responses: complete
final tests: PASS
```

Nếu wrapper test chuẩn không chạy được do môi trường, chạy focused verification bằng command phù hợp và báo rõ đó là ad-hoc verification, không gọi là suite green.

## Pitfalls

- Không mặc định gọi ba agent; dùng worker + reviewer, fallback chỉ là escalation.
- Không cho reviewer sửa code trong flow chính.
- Không chạy blind retry cùng command; mỗi retry phải có recovery/evidence khác.
- Không dùng `\\` trong Windows CMD.
- Không nhầm app login với CLI auth/provider config; kiểm tra runtime provider/model bằng smoke test.
- Không đọc report worker trước diff nếu muốn tránh anchoring.
- Không kết luận `APPROVED` chỉ vì test cũ pass.

## Verification

Kiểm tra tối thiểu:

- State/artifact được tạo đúng thư mục.
- Worker trả lời đủ mọi finding.
- Reviewer fallback chỉ chạy khi quota/provider lỗi.
- Vòng lặp dừng ở `APPROVED`, `MAX_ROUNDS` hoặc `FINAL_BLOCKED`.
- Test focused và smoke test runtime đều có output thực tế.

## Support Files

- `references/session-routing.md` — routing model/role và các pitfall CLI Windows đã được rút gọn từ workflow thực tế.
