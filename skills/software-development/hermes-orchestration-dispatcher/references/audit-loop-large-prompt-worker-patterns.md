# Audit loop 2026-08-09 — lessons đúc từ 6 vòng Sol REJECT → fix (đợt ladder per-signature + caption verifier)

> NOTE: file này + `references/audit-loop-large-prompt-pitfalls.md` phủ cùng chủ đề (prompt lớn,
> worker chết mid-run, Sol loop) — curator nên gộp. File này giữ phần worker-patterns chi tiết,
> file kia giữ phần validator/REJECT-loop.

## Số findings theo vòng (thực tế 2026-08-09) — tăng/giảm KHÔNG phải tín hiệu hội tụ

```
R1: 14 findings (REJECT) → fix
R2: 12 findings (REJECT) → fix  → gồm sanitizer mất `#` (bug chết người caption)
R3: 6 findings (REJECT)  → fix  → gồm reboot marker intent-only, validator "**"=value
R4: 8 findings (REJECT)  → fix  → TĂNG lại — bình thường, diff mới sinh đường bug mới
R5: 7 findings (REJECT)  → fix  → gồm checkpoint reconcile RECOVERY_RESERVED, tap is-not-True
R6: chờ verdict
```
Mỗi vòng REJECT = worker sửa hết findings → re-audit (evidence mới = slot mới). Sol xuyên suốt
(user chốt 08-09: 1 task = 1 model, muốn Claude phải nhắc). KHÔNG dừng hỏi user giữa vòng
("tiếp nhé?") — làm tới APPROVED rồi báo tổng kết.

## Prompt >47KB: argv limit (gặp THẬT — cả claude CLI lẫn codex exec)

Git-bash fail `Argument list too long` khi đưa prompt 47KB+ qua argv:
`claude -p "$(cat big.txt)"` ❌ và `codex exec ... "$(cat big.txt)"` ❌.

Đúng cách:
- **codex exec (Sol)**: `cat prompt.txt | codex exec --ephemeral --sandbox read-only --model gpt-5.6-sol -c model_reasoning_effort="high"` — stdin tự thành prompt khi không truyền `[PROMPT]`. Đây là route audit ổn nhất (Sol xuyên suốt, user chốt 08-09).
- **claude CLI**: `claude -p "..." --append-system-prompt-file prompt.txt` — đọc file, không qua argv. (Trong vòng đó Claude trả `API Error: Internal server error` — transient 500, smoke `-p "Reply with exactly: CONNECTED"` vẫn OK → phân biệt lỗi server vs mất kết nối.)
- **AG**: `invoke-ag-audit.ps1 -PromptFile prompt.txt`.

`Argument list too long` = lỗi SHELL, không phải model chết. Không kết luận "route hỏng" từ đó.

## AG stall signature (Antigravity qua 9router)

- Prompt 47KB+ reasoning high → wrapper chạy 500s+ (timeout 480-600) mà file kết quả **0 bytes**.
- Smoke prompt nhỏ (`Reply with exactly: APPROVED`) → HTTP 200 trong ~2s.
- Kết luận: model SỐNG, prompt quá lớn → kill + route-switch là fail-closed ĐÚNG (file 0 byte = chưa có verdict, không mất gì).
- Đừng kill khi file đã có verdict — đọc file trước khi quyết.

## Parallel worker: CHỈ theo repo/file, không theo "phần đầu / phần cuối" cùng file

Worker sửa file = đọc cả file → ghi cả file (bắt buộc python binary để giữ EOL). 2 worker cùng 1 file (dù khác section) = lost update: worker ghi sau clobber thay đổi worker trước, working tree chưa commit nên không có snapshot để merge.

- Cùng file → 1 worker duy nhất (vd toàn bộ `state_machine.py` 12K dòng, kể cả khi sửa nhiều phần khác nhau).
- Khác repo / khác file → chạy song song an toàn (vd Tiktok-video + automation-core).

## Worker chết vì iteration limit (status=failed, no summary) — pattern lặp lại

Worker có giới hạn tool-calls (~50). Với file LỚN (state_machine.py 12K dòng), worker thường:
1. Kịp sửa CODE (áp edit thành công, py_compile OK) — 
2. Chết trước khi viết test/docs/full suite/summary.

Xử lý đúng (đã verify 334/334):
1. **Verify hiện trạng thật**: `git diff --stat` + chạy pytest — đừng tin trạng thái báo cáo (worker nói "chưa commit" nhưng code có thể đã xong).
2. Kiểm tra worker có để sót fix-script chưa chạy (vd `fix_chunk_landed.py`) → chạy nó.
3. Phần còn lại NHỎ (sửa vài test fail cho API mới) → session tự làm tại chỗ.
4. Phần còn lại LỚN → dispatch worker MỚI với spec rõ: "code ĐÃ sửa xong (list API mới/behavior), CHỈ làm test+docs+full suite" — để worker không đọc lại 12K dòng đốt hết vòng tool-calling. KHÔNG re-dispatch worker đã chết (lặp lại y hệt).
5. Với delegate batch: nếu worker chết "no summary", check `git diff` — việc có thể đã xong 90% dù báo failed.

## EOL-safe quick-fix recipe (test file, khi session tự sửa)

- Đọc bytes → assert EOL thuần (`assert b"\r\n" not in raw` cho file LF; `count == crlf` cho CRLF) → decode → replace EXACT block (in đúng text từ file trước, đừng đoán escape) → encode → write.
- Với literal backslash/escape phức tạp: đừng thủ công đếm dấu gạch — chạy hàm thật qua terminal lấy repr, rồi dựng expected từ repr đó.
- Replacer dùng `state.global` center-block với `assert old in text` trước replace — fail sớm khi anchor lệch do escape/indent/tiếng Việt.
- Không dùng patch tool/sed trên file EOL-nhạy — worker BẮT BUỘC python binary.