# AG audit (ag_audit_direct.py) — path + verdict pitfalls (2026-08-15)

Bối cảnh: audit PLAN (chưa có diff/commit) bằng `ag_audit_direct.py` — prompt file tùy chỉnh,
không qua `run-ag-audit.sh` (cái đó chỉ nhận commit hash + `git show`).

## Pitfall 1 — MSYS `/tmp` path KHÔNG hoạt động với Python trên Windows

```bash
# ❌ FAIL: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/vpn_gate_plan_audit.txt'
python ag_audit_direct.py /tmp/plan.txt ag/claude-opus-4-6-thinking /tmp/response.md 600

# ✅ OK: dùng Windows path thật
python ag_audit_direct.py "C:/Users/Kibe/AppData/Local/Temp/plan.txt" \
  ag/claude-opus-4-6-thinking "C:/Users/Kibe/AppData/Local/Temp/response.md" 600
```

Lý do: git-bash hiểu `/tmp` (map tới MSYS temp), nhưng Python native trên Windows không.
Hệ quả phụ: bash heredoc `cat > /tmp/...` tạo file ở MSYS temp, Python không thấy.
→ Viết prompt bằng `write_file` vào `C:\Users\Kibe\AppData\Local\Temp\` (Windows path), rồi
truyền Windows path cho Python.

## Pitfall 2 — Verdict dòng đầu OK nhưng wrapper in `AG_AUDIT_VERDICT=UNPARSEABLE`

Khi response model trả:

```
## Verdict

**APPROVED** — Thiết kế đúng, fail-closed, scope minimal, không phá baseline. ...
AG_AUDIT_VERDICT=UNPARSEABLE
```

- `AG_AUDIT_VERDICT=UNPARSEABLE` là artifact của wrapper parse (regex tìm dòng
  `Verdict: APPROVED` / `AG_AUDIT_VERDICT=APPROVED` — format markdown `## Verdict` +
  `**APPROVED**` không khớp), KHÔNG phải model từ chối.
- **Đọc file RESPONSE** (`/tmp/...-response.md` hoặc path đã truyền) — nội dung thật:
  `## Verdict` + `**APPROVED**`/`MINOR_FIXES`/`REJECT` + findings.
- Verdict parse từ response file, không từ stdout wrapper.
- Nếu muốn wrapper parse đúng: prompt yêu cầu dòng đầu dạng
  `AG_AUDIT_VERDICT=APPROVED` (format máy đọc được), không dùng markdown `## Verdict`.

## Workflow audit plan không-có-diff

1. Viết prompt file (bối cảnh + thiết kế + scope + câu hỏi audit + yêu cầu verdict dòng đầu)
   bằng `write_file` vào `%TEMP%` (Windows path).
2. `python ag_audit_direct.py <prompt> ag/claude-opus-4-6-thinking <response> 600`
   — thời gian chạy có thể >500s (prompt dài + thinking high): chạy background
   `notify_on_complete=true`; foreground timeout tối đa 600s, không đủ.
3. Đọc `<response>` file → verdict + findings.
4. APPROVED → consensus 2 model đạt (flash plan tại session + AG approve) → dispatch worker.
