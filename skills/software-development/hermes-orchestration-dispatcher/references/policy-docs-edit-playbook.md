# Policy docs edit playbook (core contract + consumer rule sync)

Trigger: user yêu cầu THÊM/SỬA một rule áp dụng toàn hệ D:\Taadaa — canonical
`automation-core/docs/ui-compatibility-contract.md` + consumer `AGENTS.md` /
`PROJECT_RULES.md` / `docs/*ui-compatibility*.md` (Ui.md). Ví dụ đã chạy thành công:
2026-08-08 rule "coordinate tap fallback sau khi UI recovery ladder cạn" (8 file .md).

## Sequence (proven 2026-08-08)

1. **Load skill này (bước 0)** — mọi write trong Taadaa bắt buộc.
2. **Audit read-only trước** (coordinator được phép): rg canonical contract + mọi
   consumer AGENTS.md/PROJECT_RULES.md/Ui.md cho text rule hiện tại; **verify code
   thật** (vd ladder recovery trong `src/automation_core/ui.py`) trước khi kết luận
   "rule chưa có" hay "core đã có bước X". Đừng đoán từ tên file.
3. **Git status mọi repo sẽ đụng**: KHÔNG bao giờ sửa file đang dirty bởi session
   khác (automation-core hay có 6+ file modified sẵn — AGENTS.md, development-guide,
   global_recovery.py, tests...). Chỉ sửa file CLEAN.
4. **Line ending từng file** (`file <path>` → CRLF/LF): ghi rõ file nào CRLF, file
   nào LF; spec cho worker phải liệt kê từng file (6 CRLF + 2 LF điển hình).
5. **Viết PLAN** (flash tại session — plan không phải write) + **SPEC implement**
   (text thay thế CHÍNH XÁC từng amend, anchor nội dung unique — không line number).
6. **Audit gate** (case khó thật policy/core → BẮT BUỘC):
   - Luna/max audit qua 9router HTTP (script background → verdict file)
   - Sửa plan theo findings → Sol audit gate → APPROVED mới dispatch worker
   - REJECT → sửa plan + re-audit, KHÔNG implement plan bị reject.
7. **Dispatch worker** (delegate_task leaf, inherit session model): spec kèm theo,
   scope độc quyền 8 file, cấm đụng file khác, cấm commit.
8. **Verify độc lập** (không tin self-report): validator + grep + diff so baseline +
   CRLF check (chi tiết dưới).

## Contract record format (bắt buộc — validator `tools/check_ui_compatibility.py`)

Record mới trong canonical contract phải đủ **9 concepts** (REQUIRED_CONCEPTS):
`id/owner`, `ui signature`, `evidence`, `selector/fallback` (ordered), `safety bounds`,
`post-action verification`, `regression tests`, `preserved branches` (nhánh cũ phải
giữ / không được làm), `affected consumers` (consumer bị ảnh hưởng / core version).
Dùng đúng marker validator nhận diện (vd "ID/owner:", "UI signature:", "Safety bounds:",
"Post-action verification:", "Regression tests:", "Existing branches preserved:",
"Affected consumers/minimum version:"). Chạy:
`cd D:\Taadaa\automation-core && python tools/check_ui_compatibility.py --workspace-root "D:\Taadaa"` → 0 findings.
Validator cũng check consumer AGENTS.md chứa canonical name + registry name (binding).

## Worker spec bắt buộc có

- **Baseline snapshot TRƯỚC khi sửa**: `git status --short` + `git diff --stat` từng
  repo + CRLF/LF từng file → `D:\Taadaa\<slug>-baseline-<ts>.txt`.
- **Backup NGOÀI repo** (`D:\Taadaa\<slug>-backup-<ts>\`) — backup cạnh file tạo
  untracked trong repo = nhiễu git diff, auditor bắt.
- **Canonical ID đồng bộ N/N**: record ID (vd `ui-coordinate-fallback-after-recovery-ladder-20260808`)
  phải xuất hiện ở CẢ 8 file (contract = định nghĩa; consumer = tham chiếu) để grep
  verify N/N khớp và validator binding đủ.
- **Giữ line ending từng file**: python mở với `newline=''` hoặc binary replace
  bytes (`d.replace(b'old', b'new')` rồi ghi `wb`); cấm sed (phá CRLF).
- Anchor bằng nội dung unique; nếu anchor không khớp → đọc lại file, anchor ngắn hơn.

## Pitfalls (đúc kết 2026-08-08)

- **grep verify phải quote path có space**: `"tiktok-luot nuoi acc/PROJECT_RULES.md"`.
- **Check string tiếng Việt + xuống dòng**: exact substring fail vì line wrap cắt
  giữa chữ — dùng regex `re.search(r"coordinate\s+CŨNG\s+bị\s+cấm")` trong verify script.
- **9router 502/401 transient trên sol**: smoke-test model bằng curl (`Reply with
  exactly: READY`) trước khi retry full audit; luna/terra có thể 200 trong khi sol
  401 vài phút rồi tự hết.
- **Script tạm phải dọn**: `audit_*.py` + `hermes-verify-*.py` dùng xong xoá — verdict
  file là evidence, script không phải. Hệ thống yêu cầu verify cho scaffolding: viết
  `hermes-verify-<slug>.py` dưới Temp, chạy, báo "ad-hoc, không phải suite green",
  rồi xoá.
- **Không đụng file dirty của session khác** (AGENTS.md core, global_recovery.py,
  gan_proxy_fleet.py...) — dùng file clean duy nhất (vd contract md thường clean).
- **Docs-only rule không enforce script cũ**: ghi rõ giới hạn trong plan/báo cáo —
  tuân thủ script hiện hữu = bước audit riêng, không claim đã enforce.
- **Validator nâng cấp CHẶT HƠN phải có cutover theo ngày, KHÔNG retroactive**
  (2026-08-09, P2-02 `check_ui_compatibility.py`): khi thêm per-record check (parse
  từng heading + đòi đủ concept), áp lên record cũ → 66 findings `registry_record_incomplete`
  toàn là debt CÓ SẴN (record cũ viết trước khi validator chặt). User rule: "contract
  chỉ là tham khảo — ưu tiên vận hành trơn", KHÔNG sửa 66 record cũ. Thiết kế chuẩn:
  **record MỚI (heading chứa ngày/ID >= ngày cutover) thiếu concept → FAIL (fail-closed);
  record CŨ (ngày < cutover hoặc không có ngày) → chỉ warning `..._legacy`, không tính
  findings, exit vẫn 0**. Parsing: heading có ngày trực tiếp, hoặc ID bên trong
  (`ui-...-20260809`); không có ngày + không có ID → CŨ. Check core contract
  (record mới nhất `### ui-...` đủ 9 concepts) giữ nguyên strict. Bài học: validator
  "đúng như spec" nhưng fail 66 chỗ là thiết kế SAI (đánh retroactive debt) — Sol
  re-audit sẽ bắt, phải nới trước khi re-audit.
- **Carve-out read-only visual verification vs coordinate action (P1-08, contract
  `ui-coordinate-fallback-after-recovery-ladder-20260808`)**: contract cũ cấm
  coordinate/visual fallback trước ladder cạn, contract mới giữ visual gate →
  Sol REJECT vì tự mâu thuẫn. Chốt đúng: phân biệt 2 khái niệm — (a) **read-only
  visual verification** (screenshot + visual-gate/foreground check, KHÔNG side effect)
  được chạy bất kỳ lúc nào (không tính là fallback action; dùng để GIẢM số vòng
  ladder, không để bỏ qua fail-closed; vẫn cần foreground proof + screenshot
  immutable, không thay thế verifier); (b) **coordinate action** (tap/swipe side
  effect) CHỈ sau ladder cạn. Ghi rõ carve-out không nới lỏng rule coordinate cũ.

## Binding canonical/registry cho consumer AGENTS.md (validator check_ui_compatibility.py — verify 2026-08-09)

Khi thêm rule mới vào canonical contract, validator `automation-core/tools/check_ui_compatibility.py --workspace-root D:\Taadaa` yêu cầu MỌI consumer repo có **2 dòng binding** trong AGENTS.md:
```
- Canonical contract: `D:\Taadaa\automation-core\docs\ui-compatibility-contract.md`.
- Local registry: `docs/ui-compatibility.md`.
```
- Binding là dòng THAM CHIẾU (chỉ dẫn tìm rule), KHÔNG phải code fix. Rule thật nằm ở canonical; consumer binding tới canonical = tự áp dụng cho phần app-neutral (UI capture ladder, reboot, coordinate generic). **Step riêng của consumer (CAPTION_FILL, login OTP, reconcile...) core KHÔNG xử lý được** — consumer phải có handler riêng + COMPAT entry riêng trong registry của nó; thiếu → `NO_HANDLER_IMPLEMENTED` → MANUAL_REVIEW (đúng fail-closed).
- Validator CONSUMERS list 9 repo: `add mail khoi phuc`, `gan-proxy`, `Hotmail`, `register gmail`, `Tiktok_Reg`, `tiktok-add-bao-mat-f2a`, `tiktok-log-in`, `tiktok-luot nuoi acc`, `Tiktok-video` (registry override `docs/tiktok-ui-compatibility.md`; các repo khác mặc định `docs/ui-compatibility.md`). Chỉ `Tiktok-video` có workflow state_machine tiktok_workflow — các repo kia chỉ cần binding docs, không cần code ladder.
- Findings điển hình: `agents_missing_canonical_binding` + `agents_missing_registry_binding`. 2 repo thiếu binding 2026-08-09: Tiktok_Reg + tiktok-log-in (AGENTS.md dirty sẵn NHƯNG user xác nhận không ai đang chỉnh 2 repo đó → được sửa: backup NGOÀI repo `D:\Taadaa\binding-backup-<ts>\` + thêm đúng 2 dòng + commit riêng từng repo `41d48c9` + `e62d9f0`).
- **EOL từng file**: Tiktok_Reg AGENTS.md = LF THUẦN (176 dòng), tiktok-log-in AGENTS.md = CRLF THUẦN (124 dòng) — python binary replace bytes giữ nguyên, CẤM patch tool/sed. Chèn sau heading `## Coordinator -> direct worker boundary (canonical)`. Branch KHÁC nhau: Tiktok_Reg master, tiktok-log-in main — đừng giả định cùng branch.
- Sau sửa: chạy validator → `OK: 9/9 consumers` (exit 0). File registry `docs/ui-compatibility.md` (Tiktok_Reg dirty sẵn) → KHÔNG đụng nếu không thuộc scope.
- **Khi validator còn findings trên file dirty của session khác**: ghi nhận pre-existing, KHÔNG sửa (luật không đụng file dirty) — trừ khi user xác nhận không ai đang chỉnh repo đó; khi đó backup + evidence + chỉ thêm đúng phần cần.
- Context ban đầu (đọc khi cần): máy 6/9/20/46 fail OPEN_TIKTOK_FAILED vì uiautomator_null_root_node + màn đen 90s trong khi feed thật ĐÃ render (window focus stale) — fix = ladder 4 tầng per-signature (chi tiết skill `tiktok-upload-ui-recovery` §14 + COMPAT-OPEN-TIKTOK-002).

## Rule nội dung đã chốt (UI recovery coordinate fallback, 2026-08-08)

Canonical: `ui-coordinate-fallback-after-recovery-ladder-20260808`.
- Ladder UI recovery BẮT BUỘC khi capture fail: persistent+shell retry → ATX/UiAutomator
  SIGKILL (`_recover_uiautomator`: pkill -9 atx-agent + uiautomator + force-stop
  com.github.uiautomator* + uiautomator quit) → app force-stop/relaunch (≤3) → device
  reboot (khi được phép) → CHỈ SAU ĐÓ mới được coordinate tap.
- Reboot là bước bắt buộc cuối TRƯỚC coordinate; `allow_device_reboot_recovery=False`
  → coordinate cũng bị cấm → FINAL_BLOCKED (không coordinate sau relaunch khi chưa reboot).
- Coordinate tap: evidence-backed (screenshot xác nhận màn hình + target, scale theo
  wm size), recapture/verify sau tap, tap fail/non-zero/không verify → FINAL_BLOCKED
  ngay (không retry cùng toạ độ), tap exit code ≠ success.
- Cấm tap mù + action nguy hiểm (Post/Đăng, Xoá, payment, credential, OTP submit,
  switch account sai). Không branch theo máy/account. Handler ghi đủ
  precondition/action/toạ độ/expected postcondition/recapture/side effect.
- Precedence cứng: popup/flow-specific "no coordinate fallback" records (terms,
  contacts, account-update, reward, switcher...) luôn THẮNG generic fallback này.
- Rule áp dụng cho build script (thiết kế mới), recovery handler, runtime handle.
- Core `capture_ui_xml` giữ fail-closed mặc định (app-neutral); coordinate là
  consumer-adapter handler sau ladder cạn.
