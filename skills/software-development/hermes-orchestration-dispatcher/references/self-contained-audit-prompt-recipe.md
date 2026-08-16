# Self-Contained Audit Prompt Recipe (2026-08-16, verified 3 vòng)

Bối cảnh: audit plan đổi device-lock (automation-core) bằng model ngoài — AG hallucinate toàn bộ, Claude "File access denied", cx route fail. Prompt self-contained đã cứu cả chuỗi: REJECT → MINOR_FIXES → MINOR_FIXES (findings giảm dần, APPROVED sau vòng 4).

## Bằng chứng lỗi (cùng session)

1. **AG `ag/claude-opus-4-6-thinking` HALLUCINATE source ảo toàn bộ**: response chứa một `device_lock.py` hoàn toàn khác (API `device_name`/`lock_file`/`_try_acquire`/`_StaleLockReaped`/single-file lease — KHÔNG tồn tại trong repo thật; line numbers + docstring khác hẳn). `AG_AUDIT_VERDICT=UNPARSEABLE`, stdout lẫn source (wrapper regex không khớp markdown). Auditor KHÔNG đọc được file thật (D:\ path + tool read_file không dùng được trong env audit) nên tự bịa. **KHÔNG BAO GIỜ tin response audit có source dump lạ — đối chiếu API reference với repo thật trước khi dùng verdict.**
2. **Claude CLI opus-5 vòng 3**: `File access was denied. Rendering the verdict purely from the verified code facts and v3 resolution descriptions in the prompt` — vẫn cho verdict dùng được (MINOR_FIXES) vì prompt đã paste đủ verified facts. Chứng minh prompt self-contained hoạt động kể cả khi auditor không đọc được file.
3. **cx route**: `cat prompt.md | codex exec --ephemeral --sandbox read-only --model gpt-5.6-terra` → `ERROR: stream disconnected before completion` (cockpit :60818) — GPT route down (user: "gpt sol hết quota r"). Đúng ladder: chuyển Claude CLI opus-5. Không phải lỗi prompt — không retry cùng thứ.

## Recipe (đã verify)

1. **Prompt = paste REAL source**: file path + line numbers thật + nguyên hàm/signature/status sets + đánh dấu rõ "đây là API THẬT (verified bởi coordinator); đừng bịa API khác". Nếu có response audit trước bịa API, ghi "API X không tồn tại — bỏ qua, đó là hallucination".
2. **Báo auditor**: "Do NOT read external files; review only what is pasted below."
3. **Plan summary** ngắn đi kèm + **open questions** cụ thể (Q1..QN) để auditor trả lời có cấu trúc.
4. **Pitfalls repo** (CRLF, PYTHONPATH=src, param-order contract test, baseline counts) liệt kê trong prompt — auditor kiểm được trực tiếp.
5. Verdict yêu cầu dòng đầu `APPROVED | MINOR_FIXES | REJECT`; findings định dạng `severity | file | issue | fix`.
6. Chạy: `claude -p --settings '{"reasoning":{"effort":"high"}}' --append-system-prompt-file <prompt.txt> "..." > out.md 2>&1` — redirect file, KHÔNG pipe tail (pitfall cũ vẫn áp dụng).
7. **Verify assumption của auditor bằng code thật TRƯỚC khi sửa plan**: auditor giả định "state.json gate failed-locked chặn re-run" → đọc `serve()` thấy KHÔNG có gate → resolution = user intent (retry daily intentional) chứ KHÔNG thêm gate ngoài yêu cầu. Ghi "VERIFIED/SUPERSEDED by code" vào plan cho từng finding.
8. **Re-audit chỉ audit Δ**: vòng sau chỉ gửi "v2 findings → v3 resolutions + verified facts mới + checklist" — vòng 3 nhanh hơn nhiều. Findings giảm dần + design không đổi = đúng quỹ đạo (ngưỡng dừng: findings mới toàn bộ + design đổi mỗi vòng).
9. Đừng quên: prompt audit code KHÔNG nên kèm diff quá lớn (>30KB argv limit) — dùng `--append-system-prompt-file` (đã có pitfall riêng).

## Prompt skeleton (đã dùng, cắt ngắn)

```
You are auditing an implementation PLAN ... READ-ONLY. Verdict FIRST LINE: APPROVED | MINOR_FIXES | REJECT, then findings (severity, file/line, issue, required fix). Review the ACTUAL source below — do not invent APIs. Do NOT read external files.

REAL SOURCE (verified by coordinator, master @ <sha>):
<paste file path + line numbers + functions + signatures + status sets + payload fields>
Note: there is NO "<bịa API>" — that was another model's hallucination — ignore it.

<rules/pitfalls list>

THE PLAN (SUMMARY): <tasks tóm tắt>

QUESTIONS: Q1..QN (the coordinator needs answered)
```