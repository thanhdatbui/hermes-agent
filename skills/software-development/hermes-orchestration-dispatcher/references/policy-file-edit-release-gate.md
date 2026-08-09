# Policy-File Edit Release Gate (AGENTS.md / large context files)

Recipe verified 2026-08-06 on `D:\Taadaa\AGENTS.md` (97KB, 1485 dòng, không thuộc git —
bản đĩa canonical, user chỉnh tay trong lúc làm). Dùng cho MỌI lần sửa file policy/large
context có tooling tham chiếu marker/heading (validator, grep, launcher).

## Tại sao phải có gate

- File đang bị user/tool khác chỉnh tay → hash đổi giữa session (đã gặp: AGENTS.md đổi
  hash 2 lần trong 1 session). Snapshot SHA-256 NGAY TRƯỚC edit, không dùng backup cũ.
- Line number trượt sau mỗi edit (vùng 1 sửa xong → vùng 2/3 lệch dòng). **Anchor bằng
  unique heading sentinel, KHÔNG bao giờ dùng line number** làm selector.
- Tooling (validator `check-claude-quota-policy.ps1`, Codex setup, launcher) grep marker/
  heading cụ thể → mất marker = vỡ enforcement âm thầm.

## Quy trình 7 bước (release gate)

### Bước 0 — Snapshot
```bash
ts=$(date +%Y%m%d-%H%M%S)
cp AGENTS.md "AGENTS.md.pre-<scope>-$ts.bak"
sha256sum AGENTS.md "AGENTS.md.pre-<scope>-$ts.bak"   # phải khớp nhau
```

### Bước 1 — Inventory marker TRƯỚC edit
```bash
for m in SUBAGENT_RUNTIME_UNAVAILABLE WORKER_PROFILE_MISMATCH \
         COORDINATOR_LOCAL_MAINTENANCE_FALLBACK FINAL_BLOCKED \
         LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH; do echo -n "$m: "; grep -c "$m" AGENTS.md; done
```
Ghi pre-count cho TỪNG marker. Inventory toàn file các câu quy phạm cùng chủ đề —
≥2 section cùng chủ đề → sửa ĐỒNG THỜI hoặc 1 canonical + section khác chỉ tham chiếu
(REJECT lặp vì duplicate là lỗi cấu trúc, không phải nội dung).

### Bước 2 — Baseline validator
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\tools\check-claude-quota-policy.ps1
# exit code PHẢI = 0; ≠0 → DỪNG (không dùng equality làm waiver). Lưu output để so semantic.
```

### Bước 3 — Sửa bằng heading sentinel
- Tìm sentinel bằng `grep -n "^### Heading"` TRƯỚC khi sửa; assert unique + đúng thứ tự.
- Thay block TỪ sentinel-start ĐẾN TRƯỚC sentinel-end (end = heading kế tiếp). KHÔNG đưa
  heading kế tiếp vào payload (tránh nuốt section — lỗi Sol bắt nhiều lần).
- Sau mỗi patch: `grep -c` sentinel = 1 để xác nhận không nhân đôi.

### Bước 4 — Verify cấu trúc (script ad-hoc `hermes-verify-` dưới Temp)
1. **Sentinel unique**: mỗi heading đúng 1 lần (post).
2. **Byte-identical ngoài vùng sửa**: so prefix/middle/suffix raw-byte với snapshot
   (bao gồm BOM + line endings) — KHÔNG phải so text-normalized.
3. **Marker manifest**: post-count = pre-count − (count trong vùng đã XOÁ chủ ý) HOẶC tăng.
   Marker giảm PHẢI khớp đúng count trong block đã xoá; giảm ngoài vùng sửa = FAIL.
4. **Forbidden-pattern grep CHỈ trong vùng sửa** — check toàn-file là FALSE POSITIVE
   (vd `9router`/`fallback_providers` HỢP LỆ ở section audit wrapper, không thuộc vùng sửa).
5. `side-effacing`/typo = 0 toàn file.
6. **Validator lại** → exit 0 + so normalized output với baseline (violation/warning IDs,
   allowed delta = rỗng).

### Bước 5 — Audit file THẬT (không chỉ plan)
- Plan APPROVE ≠ file thật đúng — luôn audit nội dung THỰC TẾ sau khi sửa (trích 2-3 vùng
  đã sửa gửi auditor). GPT upstream (Sol/Terra) hay 401/429 → fallback `cmc/deepseek/
  deepseek-v4-pro` (khác loài với planer; nếu planer cũng deepseek thì đổi Kimi
  `cmc/moonshotai/Kimi-K2.6`).
- APPROVE_WITH_FIXES với lỗi heading/nit → sửa xong chạy lại verify.

### Bước 6 — Bind hash
- Ghi SHA-256 cuối sau audit APPROVE; release CHỈ khi hash cuối = hash đã audit.

## Pitfall đã học

- **Verify script check toàn-file = false positive** (lần đầu 24-check fail 2 cái oan:
  `9router` ở section audit wrapper + marker giảm chủ ý). Sửa script: grep cấm giới hạn
  trong vùng sửa; marker manifest tính expected = pre − count-trong-vùng-xoá.
- **Xoá section → marker giảm là CHỦ Ý**: xác minh giảm đúng bằng count trong block đã xoá
  (VD xoá `Session-as-Worker Reference` → mỗi marker giảm đúng 1). Không phải lỗi.
- **Line number trượt**: sau khi patch vùng 1, vùng 2/3 lệch — luôn `grep -n` lại trước
  mỗi patch, không dùng số dòng cũ.
- **User chỉnh tay file song song**: nếu hash AGENTS.md ≠ backup dù chưa sửa gì → cảnh báo
  user, snapshot mới ngay trước edit, không đè.
- **Giảm phạm vi > tăng độ chặt**: REJECT ≥3 vòng cùng gốc cấu trúc → đề xuất user bỏ
  spec/gate (bản đơn giản audit PASS vòng đầu). Xem `policy-change-audit-loop.md`.

## 2026-08-08 — policy v4→v5 (AGENTS.md + SKILL.md, 2 file EOL KHÁC NHAU)

Recipe: thay block policy trong AGENTS.md (heading sentinel `### Active Audit Routing
Policy v4 ...` → v5) + đồng bộ skill (12 patch mô tả route). Các điểm MỚI so với quy
trình 7 bước trên:

1. **Probe EOL TRƯỚC edit, đừng tin giả định/task context**: AGENTS.md là **LF-ONLY**
   (CRLF=0, LF=1526) dù task context ghi "giữ CRLF của file gốc (Windows)"; SKILL.md là
   **CRLF-ONLY** (466). Probe từng file: `d.count(b'\r\n')` vs `d.count(b'\n')`. Block mới
   build đúng EOL file; sau ghi assert `b'\r\n' not in out` (file LF) /
   `out.count(b'\r\n') == out.count(b'\n') > 0` (file CRLF). Đếm LF/CRLF thay đổi = đúng
   số dòng thêm/bớt trong block (LF 1526→1524 = −2 dòng block, không phải lỗi).
2. **Sentinel assert count==1 cho CẢ start lẫn end anchor** trước replace
   (`d.count(START)==1 and d.count(END_ANCHOR)==1`). End = dòng CUỐI block cũ (tới hết
   newline), KHÔNG nuốt dòng trống kế tiếp → dòng trống + "These rules apply..." giữ
   nguyên → suffix byte-identical tự động.
3. **Terminal guard chặn `&` trong heredoc**: python heredoc chứa `&` (VD nội dung block
   có "Implementation & Patch Execution") bị reject
   `Foreground command uses '&' backgrounding`. Workaround: write_file script vào %TEMP%
   (prefix `hermes-verify-`) → `python script.py` → xoá. Heredoc chỉ an toàn khi body
   không chứa `&` (lần chạy đầu không có `&` thì OK).
4. **Báo cáo hash KHÔNG ghi tay**: sinh report bằng script f-string
   (`hashlib.sha256(open(p,'rb').read()).hexdigest()` computed từ file). Đã viết report
   tay với hex sai → phải sinh lại programmatically. Hash là evidence → phải computed,
   không transcribed. Cũng đừng gõ lại hash trong verify script — luôn đọc từ file.
5. **Verify: difflib thay cho reverse-replace gõ tay**: reverse-replace proof (áp patch
   ngược → bằng bytes backup) là chuẩn vàng NHƯNG gõ tay chuỗi reverse dễ typo (fail 1
   lần vì sai vài từ trong paragraph dài). Cách bền: `difflib.unified_diff(bak.split('\n'),
   new.split('\n'), lineterm='', n=0)` rồi đối chiếu từng REM/ADD hunk với patch chủ đích.
   Chú ý: 1 dòng dài (paragraph guard block) có thể chứa ≥2 patch → số dòng diff < số
   patch (đã gặp: 12 patch = 9 REM + 11 ADD vì 2 cặp patch nằm trong cùng dòng).
6. **"Bỏ model khỏi route" ≠ xoá mọi mention**: policy mới GIỮ dòng "Removed models:
   `gemini-3.6-flash` no longer part of the audit route ..." (tài liệu hoá việc bỏ) → grep
   verify "không còn trong block" phải hiểu là không còn trong route ACTIVE (item 1-3),
   mention trong dòng Removed models + bài học lịch sử có ngày = chủ ý giữ. Các section
   policy khác ngoài vùng sửa (VD `## Gemini Delegation and Read-only Audit`) GIỮ NGUYÊN
   bytes — không sweep cả file khi task chỉ định 1 block.
7. **Wrapper hardcode model cũ trái policy mới → ghi chú report, sửa riêng**: khi bỏ model
   khỏi route, wrapper CLI (VD `tools/invoke-gemini-9router-audit.ps1`,
   `invoke-opencode-audit.ps1` cascade free cũ) vẫn trỏ route cũ → note trong report là
   "cần test/cập nhật riêng", KHÔNG sửa trong cùng edit (ngoài scope, không có test).
