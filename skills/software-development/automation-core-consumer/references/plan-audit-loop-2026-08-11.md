# Plan-audit loop — AG opus + Claude CLI (proven 2026-08-11, tiktok-follow build plan)

Khi user yêu cầu audit PLAN BUILD (chưa có code/diff): chạy vòng lặp
AG opus → Claude CLI → fix plan → re-audit CÙNG model tới APPROVED.
Plan thật chạy 5 vòng (AG v1 MINOR_FIXES → v2 APPROVED; Claude r2 REJECT →
r3/r4 APPROVE_WITH_NOTES → r5 quota blocked; AG re-confirm v5 APPROVED).

## AG opus (primary, không quota-block)

Prompt file ghép plan (bash, không write_file lớn — tránh stream timeout):

```bash
OUT="/d/taadaa/reports/ag-audit"; OUTW="D:/Taadaa/reports/ag-audit"
STAMP=$(date +%Y%m%d-%H%M%S)
PROMPT="$OUT/audit-<slug>-$STAMP-prompt.txt"; PROMPTW="$OUTW/audit-<slug>-$STAMP-prompt.txt"
RESPW="$OUTW/audit-<slug>-$STAMP-response.txt"; LOGW="$OUTW/audit-<slug>-$STAMP.log"
{ echo "Bạn là auditor read-only... (role, context, NHIỆM VỤ, phân loại MAJOR/MINOR/NIT, DÒNG ĐẦU TIÊN: APPROVED / MINOR_FIXES / REJECT)";
  echo; echo "=== BEGIN PLAN ==="; cat <plan.md>; echo "=== END PLAN ==="; } > "$PROMPT"
python "$OUTW/ag_audit_direct.py" "$PROMPTW" "ag/claude-opus-4-6-thinking" "$RESPW" 480 > "$LOGW" 2>&1
grep -E "^AG_AUDIT_(ELAPSED|VERDICT)=" "$LOG"   # APPROVED|MINOR_FIXES|REJECT|UNPARSEABLE
```

- **PITFALL MSYS**: mọi arg của ag_audit_direct.py phải Windows path (`D:/...`);
  `/d/...` → python báo `D:\d\...` FileNotFoundError.
- Findings AG: MAJOR (block build) / MINOR (nên sửa) / NIT; verdict dòng đầu.

## Claude CLI (user yêu cầu hoặc hard trigger — bắt buộc opus high)

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File \
  "C:\Users\Kibe\.codex\skills\claude-final-audit\scripts\invoke-claude-final-audit.ps1" \
  -Mode Plan -RepoRoot "D:\Taadaa\<repo>" -PlanFile "D:\Taadaa\<repo>\.hermes\plans\<plan>.md" -Effort high
```

- Wrapper tự chạy quota preflight + monitor (5h <85%, weekly <90%). Quota chặn →
  `CLAUDE_AUDIT_STATUS: QUOTA_GATE_BLOCKED` + `FALLBACK: USE_CODEX_SOL_MAX_PLAN_AUDITOR`.
  Không chờ reset 5h (vài giờ) — chuyển fallback (AG re-confirm nhanh nhất).
- **Verđict thật nằm trong stdout artifact** (wrapper luôn báo
  `PARTIAL_NO_VERDICT/PROCESS_FAILED` vì claude CLI dùng format riêng
  `## 1. VERDICT: APPROVE_WITH_NOTES`):
  `D:\CodexRuntime\<repo>\audit\claude\claude-audit-<ts>.stdout.txt`.
- Findings Claude: P0 (block) / P1 (sửa trước phase tương ứng) / P2 (nên sửa)
  / P3 (ghi nhận); kèm line-ref VERIFY trong source thật (grep decrypted.json /
  core source) — auditor thật sự đọc file, không bịa.

## Vòng lặp & kỷ luật

1. REJECT/MINOR_FIXES/APPROVE_WITH_NOTES → sửa plan cho TỪNG finding (MAJOR/P1
   trước), commit plan riêng (`docs(<repo>): plan vN — fix audit rN (...)`), rồi
   re-audit CÙNG model (AG opus lại; Claude lại).
2. REJECT nghĩa là có P1 thật — ví dụ session này: config trỏ thẳng credential
   workbook vi phạm rule safe-workbook Non-Negotiable → phải đổi sang safe
   workbook + state JSON, không phải biện minh.
3. Findings phổ biến khi audit plan consumer TikTok (đã gặp, nên có sẵn trong
   plan từ đầu):
   - Safe-workbook boundary (runner CHỈ đọc `data/taikhoan_run_safe.xlsx`,
     không path credential trong config runner; state không ghi vào credential book).
   - Follow/Follow lại/Đã follow: "Follow lại" = CHƯA follow → set not-followed,
     không silent-success; dump lạ → MANUAL_REVIEW.
   - Identity handle: flow gốc lưu bare handle, prepend `@` lúc check → so sánh
     strip-and-compare; không assert "ID phải dạng @handle".
   - Selector kết quả search: `@index="1"` ≠ XPath `[1]` (index trong parent) —
     giữ semantics flow gốc làm primary.
   - Ladder UI đúng 4 bước (ATX-kill → force-stop 1 → reboot nếu allow →
     coordinate fallback CÓ EVIDENCE); CẤM coordinate fallback cho nút Follow /
     tap list item (follow nhầm nick).
   - Mode 2 verify: inline button đổi optimistic → first-follow Path B bắt buộc
     + sampling reload; device-busy guard KÉP (lock store + wmic tiktok_workflow)
     trong ACQUIRE_LOCKS, không chỉ preflight tay; budget reset theo HOST clock
     trong timezone config (emulator sai giờ).
4. Sau APPROVED → commit plan + bắt đầu build (TDD từng phase, COMMIT GATE:
   suite xanh mới commit).

## Prompt template (auditor role) — tái sử dụng

"Bạn là auditor read-only chuyên automation Android/TikTok (automation-core,
consumer runner, device lock, recovery ladder). Đây là audit PLAN BUILD trước
khi triển khai (chưa có code/diff). [nếu re-audit: liệt kê findings vòng trước
đã fix — yêu cầu verify]. NHIỆM VỤ: 1) tìm thiếu sót logic vận hành, mâu thuẫn
Startup Contract/recovery ladder, rủi ro die acc, thiếu test/verify/safety gate;
2) chỉ report finding có LOCATOR THẬT (mục/task/selector/config trong plan) +
trigger + hậu quả, CẤM suy đoán; 3) phân loại; 4) không còn blocker → APPROVED
và dừng. DÒNG ĐẦU TIÊN: APPROVED / MINOR_FIXES / REJECT."
