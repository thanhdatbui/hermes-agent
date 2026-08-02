---
name: agent-review-loops
description: "Điều phối implement/review đến APPROVED với fallback reviewer khi Claude hết quota."
version: 1.1.0
metadata:
  hermes:
    tags: [orchestration, codex, claude, opencode, review-loop, fallback]
---

# Agent Review Loops

Dùng khi điều phối coding agent và cần review độc lập trước khi chạy live hoặc kết luận hoàn tất.

## Quy trình

1. Viết spec rõ ràng: mục tiêu, scope, acceptance criteria, constraints.
2. Dispatch implementer (Codex mặc định).
3. Dispatch reviewer read-only.
4. Nếu reviewer trả `MINOR_FIXES` hoặc `REJECT`, dispatch implementer sửa đúng findings rồi review lại.
5. Lặp đến `APPROVED`.
6. Chỉ sau `APPROVED` mới chạy validation/live theo quyền user đã cấp.

Reviewer phải trả duy nhất: `APPROVED`, `MINOR_FIXES`, hoặc `REJECT`.

## Fallback Reviewer Khi Claude Hết Quota

Không bỏ review gate và không chờ reset quota khi `claude -p` trả quota/session limit, rate limit, billing error, hoặc provider unavailable.

Fallback theo thứ tự:

1. `opencode run --model freemodel/claude-opus-4-8 --variant max`
2. Nếu FreeModel trả `Unauthorized`, `Insufficient balance`, rate limit, hoặc model unavailable: `opencode run --model opencode-go/grok-4.5 --variant max`
3. Nếu Grok Go unavailable: `opencode run --model opencode-go/glm-5.2 --variant max`

Trước lần dùng đầu của model fallback trong session, smoke-test:

```bash
opencode run --model <provider/model> 'Respond with exactly: OPENCODE_FALLBACK_READY'
```

Không in API key hoặc giá trị credential từ `opencode auth`.

Để OpenCode review thay vì tự sửa, dùng `--agent plan`. Nếu review cần đọc sibling repo/worktree ngoài cwd (ví dụ shared `automation-core`), dùng `--auto` để OpenCode được quyền đọc external directory; prompt vẫn cấm edit/live/credential:

```bash
opencode run --agent plan --auto --model <provider/model> --variant max '<read-only review prompt>'
```

Prompt OpenCode phải giữ nguyên scope/read-only constraints, tiêu chí và verdict format của review Claude. `APPROVED` từ fallback reviewer thay thế review gate Claude cho run hiện tại. Lần review sau ưu tiên Claude lại nếu quota đã hồi phục.

**Ranh giới vai trò:** fallback OpenCode chỉ thay vai trò **reviewer/auditor** khi Claude unavailable. Codex vẫn là implementer; không tự chuyển implementation từ Codex sang Grok/OpenCode, trừ khi người dùng chỉ đạo rõ hoặc Codex bị hard-block hoàn toàn và người dùng đã cho phép fallback implementer.

## Live Validation

- Suite/test/diff phải pass trước live.
- Với live flow, đọc summary/artifact per-target; `DONE` chỉ nghĩa report được ghi, không đồng nghĩa success.
- Kiểm tra lock machine/serial release hoặc trạng thái handoff/recovery có owner rõ ràng.
- Không retry nguyên trạng: phải có evidence/root cause và recovery khác biệt.

## Safety

- Reviewer fallback là read-only: không sửa file, không chạy ADB/live/device/account/mail/workbook, không đọc secrets/credential.
- Không bypass device/workbook locks.
- Không chạy live khi reviewer chưa `APPROVED`.
