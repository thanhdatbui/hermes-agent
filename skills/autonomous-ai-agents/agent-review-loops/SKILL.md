---
name: agent-review-loops
description: "Điều phối implement/review đến APPROVED với fallback reviewer khi Claude hết quota."
version: 1.2.0
metadata:
  hermes:
    tags: [orchestration, codex, claude, opencode, review-loop, preflight, live-validation]
    related_skills: [claude-code, codex, agent-model-routing, hermes-orchestration-dispatcher]
---

# Agent Review Loops

Dùng khi user yêu cầu điều phối coding agent, review chéo, hoặc làm đến khi hoàn tất.

## Quy trình bắt buộc

0. **Phân loại task**: SIMPLE (1-2 file, mechanical, không đụng shared core/sensitive) hay COMPLEX (core/shared/sensitive/multi-machine/architecture).
1. **Chọn owner đúng policy**: COMPLEX phải có task spec rõ ràng (`Goal`, `Scope`, `Acceptance Criteria`, `Constraints`) rồi dispatch worker implement (background, `pty=true`, `notify_on_complete=true`). Khi coordinator-write guard đang active, không tự write chỉ vì task được gọi là SIMPLE; tuân thủ skill dispatcher và chuyển mọi write cho một worker độc quyền.
2. **Tách vai trò**: Claude/OpenCode/Sol/Terra chỉ audit/read-only; worker không tự duyệt thay đổi của chính mình. Reviewer phải xem code/spec thực tế, không chỉ tin self-report hoặc exit code.
3. Nếu reviewer trả `REJECT` hoặc `MINOR_FIXES`, chạy **spec/implementation ratchet**: mỗi finding phải có locator, nhánh/input/state, hậu quả cụ thể và evidence; sửa đúng finding bằng một điều khoản/API/schema/state rõ ràng kèm acceptance test; sau đó tạo evidence mới và re-review. Không dispatch implementation khi gate của plan/spec còn `REJECT`/`MINOR_FIXES`.
   - Đối chiếu finding với code thật trước khi sửa: audit có thể hiểu sai representation nội bộ (ví dụ bounds đã được normalize thành `(x, y, width, height)`) hoặc đề xuất contract mới nhưng chưa kiểm tra caller. Finding false-positive/speculative phải đóng bằng evidence; finding thật phải có regression test ở đúng branch.
   - Với orchestration/lock: giữ invariant terminal-state độc lập với việc test xanh — chỉ release device khi có success proof; `MANUAL_REVIEW`, `CONFIG_ERROR`, `FOLLOW_BLOCKED`, release không verify phải giữ lease theo handoff/audit, không force-unlock. Khi audit đề xuất đổi outcome string, search toàn bộ caller trước và test cả caller escalation để tránh loop hoặc silent skip.
   - Sau mỗi vòng audit material, coordinator tự chạy canonical suite trên working tree/commit thật; worker/ad-hoc report, exit 0, hoặc số test tự kê không thay thế được full-suite evidence. Checklist cụ thể nằm ở `references/review-loop-verification.md`.
4. Lặp đến khi reviewer trả `APPROVED`; suite xanh, process exit `0`, `completed normally`, hoặc file output tồn tại **không phải verdict**. Đọc artifact review và kiểm tra verdict theo format yêu cầu (thường dòng đầu); nếu verdict chưa đọc được thì trạng thái vẫn là `BLOCKED/UNKNOWN`.
   - **Plan artifact existence is a hard gate:** never accept a planner/worker summary claiming a plan was written. Independently read/stat the exact path, confirm nonzero content and expected sections, and record line count/hash for important plans. If the artifact is absent, stop at `BLOCKED/UNKNOWN`; do not dispatch an auditor against a nonexistent plan or proceed to implementation.
  - **Exact-target reconciliation is also a hard gate:** a worker summary, test count, or commit report is not evidence that a patch landed in the coordinator's target worktree. Before accepting any worker result, resolve the absolute repo/worktree path, branch, and HEAD; independently check target files, inspect target status/diff, and run canonical tests from that exact target. If a worker reports tests passed but the target file is absent or unchanged, classify the result as `WORKER_ARTIFACT_NOT_LANDED`, do not commit or audit it, and re-dispatch only after exact-scope reconciliation. For untracked files, use `git status --short --untracked-files=all` and inspect the file directly; `git diff --name-only` omits untracked test files.
  - **Worker-side path claims are not proof:** require a final absolute-path marker check in the target worktree (file existence plus a distinctive source marker), then independently reproduce the focused test and regression suite. A temporary/ad-hoc probe may support diagnosis but never substitutes for canonical suite evidence.
   - **Worker báo "đã tạo plan" nhưng file không tồn tại — yêu cầu proof khi dispatch (hit 2 lần 2026-08-11, automation-core plan):** worker summary nói "plan đã viết xong" nhưng `read_file` trả File not found (2 worker liên tiếp). Fix: ngay từ brief yêu cầu worker "bắt buộc dùng công cụ ghi file → đọc/stat lại → trả absolute path + line count + SHA256; không được báo thành công nếu không stat/read được". Worker thứ 3 tuân thủ → artifact thật (280 dòng). Trước khi audit bất kỳ plan nào: tự `wc -l` + `sha256sum` file rồi đối chiếu summary — không tin chữ "đã tạo".
5. Với audit prompt lớn, ghi prompt ra file và truyền qua stdin/file API; không nhét prompt dài vào argv. Lưu riêng prompt/result, model, effort, repo, iteration và verdict để tiếp quản được sau context compaction.
6. Nếu 2+ vòng liên tiếp lặp cùng kiểu finding cấu trúc (thiếu canonical source, schema/API chưa self-contained, hoặc mâu thuẫn cross-section), không tiếp tục nối thêm prose vô hạn: đổi cách tiếp cận sang một nguồn chuẩn + reference, đơn giản hóa contract, hoặc bỏ phần không cần thiết; ghi rõ `what-was-tried/why-failed/materially-different-plan` rồi audit lại.
7. Chỉ sau `APPROVED` mới dispatch worker implementation; sau worker phải review evidence mới, rồi verify độc lập bằng diff/test/artifact. Không coi audit plan `APPROVED` là bằng chứng code đã chạy.
8. Không hỏi user giữa loop nếu finding có thể đóng bằng contract/evidence; chỉ báo kết quả `APPROVED/DONE` hoặc hard stop an toàn.

### Pre-dispatch overlap gate cho scheduler/orchestrator

Trước khi dispatch worker cho bất kỳ task scheduler/orchestration nào, phải kiểm tra **active goal và các workstream/session song song**, không chỉ git status:

1. Xác định deliverable thật: đang build schedule random farm, đang harden core state-machine, hay đang cấu hình Hermes cron live. Đây là các lớp khác nhau nhưng có thể sửa cùng `picker/runner/watcher/manifest`.
2. Dùng `session_search` để tìm session gần đây theo các từ khóa `schedule`, `random`, `picker`, `runner`, `watcher`, `Hermes cron`, `feed_then_post`; đọc goal/acceptance của session đang hoạt động.
3. Kiểm tra cron jobs hiện có và process/worker artifacts trước khi viết. Phân biệt **cron đang chạy live** với code harness mới chỉ offline; không suy ra hai hệ không trùng chỉ vì chưa có cron live.
4. Nếu hai task cùng tạo scheduler hoặc cùng sở hữu một file/contract, chọn một owner duy nhất và lập bảng ownership. Hợp nhất core dùng chung vào owner đó; dừng/pause workstream trùng, không dispatch thêm P1/Rn song song.
5. Chỉ tiếp tục audit/harden `hermes_cron` nếu nó là dependency dùng chung đã được owner schedule chấp nhận; nếu không, báo overlap và chuyển thành design/reconciliation, không tiếp tục build một scheduler thứ hai.
6. Khi báo user, nói thẳng: `trùng mục đích`, `chưa trùng runtime`, hoặc `không trùng`; kèm action cụ thể. Không báo tiến độ implementation như thể task độc lập nếu ownership chưa được reconcile.

Chi tiết checklist reconcile scheduler nằm ở `references/scheduler-workstream-overlap.md`.

### Large-job pipeline bắt buộc (user chốt 2026-08-10: "Job lớn thì chia plan ra — gọi agent lập plan, gọi agent KHÁC audit, đến khi ok hết bắt đầu build từng phase theo plan, phase nào xong gọi audit phase đó")

Cho job lớn (scheduler/refactor multi-phase), user yêu cầu chuỗi CỨNG sau, không tự ý đổi:
1. **Planner agent** (leaf, đọc repo với 0-context assumption) viết plan markdown đầy đủ — mỗi phase có file/red-test/green-code/verify/acceptance/commit message tiếng Việt; lưu `.hermes/plans/YYYY-MM-DD_<slug>.md`.
2. **Audit agent RIÊNG** (fresh leaf, không phải planner) đọc plan + đối chiếu acceptance criteria nguồn (vd file handoff invariants) → verdict `APPROVED|MINOR_FIXES|REJECT` dòng đầu kèm locator.
3. MINOR_FIXES/REJECT → planner sửa plan → audit lại (mỗi vòng material change = slot mới). Chỉ APPROVED mới build.
4. Build TUẦN TỰ từng phase (worker TDD), mỗi phase xong → audit phase đó → mới sang phase kế; commit từng phase theo message trong plan.
5. Coordinator không vượt gate: chưa APPROVED thì không dispatch worker build.

**Auditor phải RE-VERIFY con số thật của plan, không chỉ cấu trúc (hit 2026-08-10, plan fleet scheduler):** planner viết 3 lỗi fact mà audit bắt được bằng cách tự chạy/re-compute:
- **Baseline sai**: plan ghi "117 passed, 3 failed" nhưng chạy thật `121 passed` (worker R10 đã fix từ trước — plan copy số cũ). Auditor phải chạy lại suite, không tin số plan tự kê; Phase 0 "dọn 3 test đỏ" biến thành verification-only.
- **Math formula sai**: `S2_start = S1_end + pair_gap` (gap nằm GIỮA 2 phiên), plan viết thành cộng gap sau S2 → block 3 kết thúc 01:00 thay vì 00:30, vi phạm window 02:00. Auditor tự tính lại bằng python và đối chiếu bảng feasibility/expected values của từng test trong plan.
- **Hằng số lệch giữa phase**: đổi window 06:00–02:00 làm mốc cũ `01:30` (từng là ngoài-window) thành TRONG window — phải chọn mốc mới `02:30` thống nhất ĐÚNG MỘT chỗ, các phase khác chỉ tham chiếu. Auditor check cross-phase consistency của mọi constant/số magic.
- **Test skeleton `...` trong plan** = worker sẽ tự bịa behavior — auditor phải bắt và yêu cầu điền body đầy đủ (arrange/act/assert), không bao giờ APPROVED plan còn placeholder.

Khi dispatch audit plan: context phải kèm acceptance criteria nguồn (invariant file path hoặc nội dung) + yêu cầu "chạy baseline thật + tự tính toán lại mọi công thức trong plan trước khi verdict". Ví dụ end-to-end 8 phase hoàn chỉnh (runtime thật từng bước, chuỗi commit, mẫu loop đóng gate Phase 3, hit counts): `references/fleet-account-block-scheduler-20260811.md`.

### Standing-goal / “tự chạy đến xong” contract (user correction)

Khi user nói “tự chạy tự audit cho đến khi xong”, đó là **standing goal**, không phải yêu cầu cho một vòng thử. Coordinator phải giữ vòng kín `audit → worker → independent verify → re-audit` cho tới khi có terminal proof:

- Chỉ hai kết quả được báo là hoàn tất: `APPROVED` kèm test/diff/proof độc lập, hoặc `FINAL_BLOCKED` kèm blocker thật, locator, số lần thử và hiện vật. `process exit 0`, worker tự báo xong, test pass, context compaction, hoặc hết một lượt tool **không phải terminal state**.
- Không gửi recap tiến độ giữa vòng, không hỏi lại user về các finding có thể đóng bằng code/fixture/evidence. Nếu cần nói, chỉ báo milestone/blocker thật; tiếp tục gọi tool ngay trong cùng lượt.
- Trước mỗi lượt coordinator, ưu tiên theo thứ tự: (1) đọc verdict/findings hiện có, (2) reconcile process/artifact/worktree, (3) dispatch đúng role, (4) verify độc lập. Không tiêu ngân sách tool bằng cách dump lặp lại log/diff khổng lồ hoặc poll mù.
- Nếu context/tool limit cắt ngang, ghi/đọc checkpoint và artifact để **tiếp tục** ở lượt sau; tuyệt đối không biến “chưa kịp gọi tool” thành báo cáo `Chưa xong` cuối cùng khi worker/audit còn có thể tiếp tục.
- Nếu có nhiều finding lặp cấu trúc, chuyển sang một patch root-cause + regression/adversarial probe; không kéo dài prompt bằng cách nối thêm prose qua R2…Rn.

### CLI-contract verification before accepting audit findings

- Với plan có lệnh CLI/scheduler, auditor phải phân biệt finding fabricated thật với false positive bằng cách chạy `--help` hoặc probe trên máy thật trước khi yêu cầu sửa plan. Nếu audit nói flag/subcommand không tồn tại, xác minh đúng lệnh trước; chỉ giữ finding khi probe thật thất bại.
- Ghi command/output làm evidence trong plan hoặc audit artifact. Không sửa valid CLI chỉ vì auditor suy đoán; ngược lại không chấp nhận plan tự ghi “đã verify” nếu chưa có capture thật.
- Safety race phải audit riêng dù CLI hợp lệ: create→pause cần staging schedule không imminent, kill-switch mặc định OFF, capture ID, pause, status verification và rollback. `--help` đúng không chứng minh sequence an toàn.
- Khi re-audit sau fix, truyền các probe facts đã xác minh và yêu cầu auditor không lặp false positive; vẫn kiểm tra cross-section, boundary và race độc lập.

### Prompt-boundary and audit-artifact discipline

- Không bao giờ nối nguyên một audit prompt (đặc biệt phần `Bạn là auditor read-only`, verdict schema, hoặc output cũ) vào prompt worker. Hãy tạo **worker brief riêng**, self-contained, chỉ gồm scope/acceptance/constraints/finding; role worker và role auditor phải tách tuyệt đối.
- Mỗi reviewer/worker dùng artifact riêng: `prompt`, `result`, model, effort, repo, iteration. Với output lớn, dùng một extractor có điều kiện để lấy dòng verdict đầu tiên, headings và finding locators; không đọc lại toàn bộ file ở nhiều offset.
- Đọc verdict từ **dòng đầu tiên không rỗng của phản hồi cuối**, không suy luận từ exit code, tail, hay dòng `tokens used`. Nếu process vẫn chạy nhưng artifact đã có verdict rõ ràng, kiểm tra tính đầy đủ của phần findings trước khi quyết định chờ/kill/fallback.
- Self-report của worker/HANDOFF chỉ là hint. Coordinator bắt buộc chạy import/compile, targeted tests, `git diff --check`, allowlist/status và ít nhất một nhóm **adversarial probes** cho invariant fail-closed trước khi coi là đạt.

### Worker báo "ad-hoc verification PASS" ≠ suite green — coordinator tự chạy lại (hit 7+ lần 2026-08-10/-11: Phase 1, fix residual, Phase 3 continuation, Phase 5, Phase 6, Phase 7 fleet scheduler)

Worker (kể cả model mạnh — ĐẶC BIỆT worker luna subagent, gần như MẶC ĐỊNH) thay vì chạy canonical suite tự viết `tempfile` script verify vài hàm rồi báo **"Ad-hoc verification: PASS — không phải suite green"**; có worker báo **"Không chỉnh sửa thêm code hoặc commit mới"** trong khi thực tế ĐÃ sửa + commit (hit thật: worker fix-residual báo "không commit" nhưng `git log` có commit `d039f53` đủ 3 file; worker Phase 5/6/7 báo ad-hoc probe pass trong khi commit đã nằm ở HEAD và suite thật 162/166/173 xanh). Bài học: ad-hoc probe của worker thường vẫn đúng behavior, NHƯNG **không bao giờ được tính là suite green** — đây là hành vi mặc định, đừng ngạc nhiên, đừng tin; muốn biết trạng thái thật thì phải tự chạy. Nếu báo cáo worker không kèm con số full suite → coi như chưa verify, chạy lại ngay (ĐỪNG hỏi user hoặc yêu cầu lại worker cho lần thứ n — tự chạy 3 lệnh dưới đây rẻ hơn 1 vòng delegation).

**Khi ANY worker báo dạng này, coordinator chạy NGAY 3 lệnh độc lập (không tin lời báo):**
1. `git log --oneline -3` + `git show --stat HEAD` — xác nhận commit THẬT hay chưa (đừng tin "chưa commit"/"không thay đổi file");
2. Full suite chuẩn của repo (lệnh pytest liệt kê 4 file, KHÔNG phải script ad-hoc) — chỉ con số này mới là suite green;
3. Grep residual theo đúng finding (vd `grep -rn "01:00" file`) — xác nhận đóng thật.
Chỉ khi cả 3 xanh mới dispatch audit phase / chuyển phase kế. Nếu worker báo "ad-hoc verify PASS" mà không có 3 evidence trên → coi như chưa verify, yêu cầu lại hoặc tự chạy.

### Adversarial verification for fail-closed harnesses

Với scheduler/orchestrator/core harness, test pass không đủ. Reproduce trực tiếp các input bị sửa/tampered và crash windows:

- Manifest: đổi slot vào reserved/sub-minute, ID traversal, idempotency/assignment/source revision lệch, timestamp sai zone/future, row ngoài range.
- State/mapping: state revision không khớp payload, machine↔serial one-to-many, duplicate/missing account mapping, active pointer torn/ambiguous.
- Runner: dry-run phải return trước lock/prepare/spawn; entry object bị sửa phải bị từ chối; mốc 00:00–05:59 phải giữ đúng manifest logical-day.
- Journal/recovery: malformed JSONL phải fail-closed; reservation crash và terminal duplicate không được gọi bridge lần hai; cap 2..8 phải được bảo vệ dưới concurrency.
- Verifier/watcher: artifact shape thật và identity ambiguity, sensitive/unknown classification, `UNKNOWN` recovery result, path/secret/workbook sanitizer, reordered notification target.

Chi tiết reproduction/checklist của vòng P1 offline nằm ở `references/p1-offline-harness-audit-checklist.md`.

**Gate-masking trong adversarial test (hit thật 2026-08-11, Phase 3 manifest — 3 vòng audit cùng kiểu finding):** test tamper mutate nhiều field cùng lúc rồi chỉ `pytest.raises(ValueError)` có thể PASS ở gate SỚM hơn branch đích mà không bao giờ chứng minh branch định test: (a) đổi cả `day` → fail ngay day/slot gate; (b) đổi `machine`/`account_row` mà không đồng bộ `feed.machines/row` → fail ở entry feed-mapping check; cả hai đều trả cùng reason `MAPPING_CONFLICT` nên suite vẫn xanh nhưng test vô nghĩa. Quy tắc viết adversarial test fail-closed: mutate ĐÚNG MỘT field, đồng bộ MỌI dependent field để payload đi qua các gate trước (feed.machines/row, lock.machine/serial, entry_id + idempotency rehash, block_id/block.entry_ids/block.seed rehash khi field đó tham gia hash), rồi reject ĐÚNG branch đích với exact reason (`excinfo.value.args[0] == "<REASON>"`), không chỉ ValueError. Auditor phải đọc line reject thực tế (branch reachability), không chỉ assert reason; test chứng minh được branch nào thì ghi đúng branch đó trong tên/comment, đừng để test pass "cho may" ở gate sớm.

**Probe xác nhận BRANCH reject — recipe chuẩn (hit 2026-08-11, 3 mutation machine/account/account_row):** sau khi reshape test, coordinator tự chạy probe từng mutation rồi in dòng reject THẬT (không chỉ reason — reason giống nhau giữa 2 branch nên không phân biệt được):
```python
import sys, tempfile, traceback
sys.path.insert(0, r"D:\Taadaa\tiktok-luot nuoi acc")
from python_runner.tests.test_hermes_cron_fleet import _pick, fleet_source, fleet_feed, fleet_post, _tamper, _rehash_block_identity
from python_runner.hermes_cron.manifest import validate_manifest
# ... mutate đúng 1 field + sync dependent fields + _rehash_block_identity ...
try:
    validate_manifest(payload, fleet_source()); print("NO REJECT - FAIL")
except ValueError as ex:
    lines = [l.strip() for l in traceback.format_exc().splitlines() if "manifest.py" in l and "in " in l]
    print(f"reason={ex.args[0]} reject_line={lines[-1] if lines else '?'}")
```
Dependent-field sync table (mutate field → các field phải đồng bộ để đi qua gate trước): `machine` → `feed.machines`, `lock.machine`, entry_id/idempotency rehash, block_id rehash + `block.seed` (= machine_day_seed(day, machine_moi, payload_seed)); `serial` → `lock.serial` (entry_id có serial); `account_row` → `feed.row` (block_id KHÔNG dùng account_row); `account` → block_id (có account), entry_ids; `day` → block_id, session_slots, seed. Trick tạo account khác có source-row khác nhưng không trùng account của block khác: `new_acct_idx = (orig_row % 6) + 1` — fixture rows 1..6 luôn ≠ orig_row; kèm `assert new_acct_idx != orig_row` phòng thủ. Chi tiết: `references/gate-masking-adversarial-tests.md`.

### Claude CLI print-mode làm implementer phase khó (user yêu cầu 2026-08-11 — yêu cầu THEO PHIÊN, không phải policy, xem pitfall "session-scoped ≠ policy")

Khi user yêu cầu "task khó gọi Claude CLI sửa code" cho phiên này, dùng (đã chứng minh: test reshape `904ae86`, assert fix `dd8db90`, Phase 4 manifest validation build — đúng scope/allowlist/commit message):

```bash
cd "<repo>" && claude -p "$(cat <prompt-file>.md)" --allowedTools "Read,Edit,Write,Bash" --max-turns N
```
- Viết task spec ra FILE trước (scope/acceptance/finding cần đóng + red/green/verify bắt buộc + commit message tiếng Việt, giống brief worker subagent) — tránh shell quote, giữ prompt gọn.
- Chạy background + `notify_on_complete=true` (phase lớn 5–15 phút, max-turns 40–60).
- Claude CLI print-mode thực hiện đúng TDD RED→GREEN + commit; KHÔNG đụng file ngoài allowlist (đã kiểm chứng nhiều lần).
- Sau khi xong: coordinator vẫn verify độc lập (git log/stat, full suite, py_compile, diff --check) — self-report của Claude CLI cũng không phải proof.
- Audit phase khó vẫn dùng AG Claude (`run-ag-audit.sh`) — implement Claude CLI, audit AG Claude, coordinator verify cả hai. Task vừa/nhỏ vẫn luna subagent.
- **Claude CLI session limit ≠ AG 9router (hit 2026-08-11, Phase 4 fix):** "You've hit your session limit · resets <giờ địa phương>" = giới hạn OAuth Pro/Max của CLI, reset theo giờ — fallback NGAY luna subagent (delegate_task) với CÙNG task spec, đừng chờ reset. AG Claude audit qua 9router dùng `NINEROUTER_API_KEY` nên KHÔNG bị session-limit CLI — vẫn chạy `run-ag-audit.sh` bình thường trong lúc CLI nghỉ.
- **Delegation model KHÔNG kế thừa model session** (user hỏi 2026-08-11: "model audit là gì cũng ds v4 flash à?"): config.yaml `delegation.provider=cockpit, model=gpt-5.6-luna` — session chạy deepseek-v4-flash nhưng MỌI subagent CHẠY luna. Trước khi trả lời "auditor dùng model nào" phải kiểm tra `grep -A3 delegation ~/AppData/Local/hermes/config.yaml`, không suy diễn từ session model. Summary delegation luôn ghi `Model: <tên>` — đọc dòng đó làm bằng chứng.
- **Audit KHÔNG dùng luna subagent — gọi ĐÚNG route qua 9router (user correction 2026-08-11, 2 lần: "audit gọi terra/sol đi", "làm gì có set cho gọi luna audit")**: vì delegation pin luna, `delegate_task(role=leaf)` chỉ sinh WORKER luna (đọc file + có thể patch) — không phải auditor hợp lệ dù là read-only. Audit plan/phase gọi `run-ag-audit.sh` (AG Opus primary `ag/claude-opus-4-6-thinking`) hoặc `ag_audit_direct.py` với model `cx/gpt-5.6-terra-review` (thường)/`cx/gpt-5.6-sol-review` (khó) → fallback `opencode-audit`; Luna/Flash KHÔNG BAO GIỜ audit (chi tiết: `agent-model-routing` Pitfalls). PITFALL path: khi gọi `ag_audit_direct.py` từ MSYS bash, truyền path **Windows `D:/...`** (KHÔNG `/d/...` — Python Windows đọc sai thành `D:\d\...` → FileNotFoundError, hit thật 2026-08-11 Phase 1 audit).
- **Audit phase CHƯA commit (worktree/branch riêng, chờ gate):** `run-ag-audit.sh` chỉ nhúng diff 1 COMMIT (`git show $COMMIT`). Khi worker chưa commit vì chờ audit APPROVED (đúng quy trình), tự dựng prompt file: `git diff <baseline-commit>` inline vào prompt, gọi `ag_audit_direct.py` trực tiếp — APPROVED mới cho worker commit (hit 2026-08-11 Phase 1 FAILED_LOCKED trên worktree `codex/failed-locked-phase1`, audit vòng 1 MINOR_FIXES → fix → re-audit APPROVED → commit sau).
- **Audit PLAN chưa có code/diff (hit 2026-08-11, tiktok-follow build plan):** `run-ag-audit.sh` KHÔNG dùng được cho plan chưa commit (bắt buộc `<commit>` + `git show`). Dựng prompt file riêng: nhúng TOÀN BỘ plan markdown inline giữa `=== BEGIN PLAN ===`/`=== END PLAN ===` (không diff), kèm role auditor + verdict schema dòng đầu `APPROVED / MINOR_FIXES / REJECT` + "CẤM suy đoán không locator", rồi gọi `python "D:/Taadaa/reports/ag-audit/ag_audit_direct.py" <prompt> ag/claude-opus-4-6-thinking <resp> <timeout>`. Verdict loop y hệt diff audit: MINOR_FIXES → sửa plan theo từng finding (locator thật) → re-audit CÙNG model → APPROVED → CHỈ LÚC ĐÓ mới commit plan. Thực tế: r1 MINOR_FIXES (3 MAJOR: recapture-sau-tap, mode2 verify path, VERIFY_IDENTITY; 6 MINOR: locale selectors, lock release qua finally, swipe clarify, timezone budget, write retry, search selector position) → fix → r2 APPROVED 32s → commit plan.

**Claude CLI final-audit wrapper (`invoke-claude-final-audit.ps1`) — quirks thật (hit 2026-08-11, tiktok-follow plan r2→r5):**
- **Wrapper mặc định: `-Model claude-opus-4-8`, `-Effort 'high'`** (default Effort đã patch `medium`→`high` 2026-08-11 — user: *"phải set gọi opus high nhé, nếu k đúng sửa rule luôn"*). Claude CLI audit LUÔN opus high; thấy `Effort = 'medium'` trong log = wrapper chưa patch. Cách gọi: `powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Kibe\.codex\skills\claude-final-audit\scripts\invoke-claude-final-audit.ps1" -Mode Plan -RepoRoot <repo> -PlanFile <plan.md> -Effort high` (Mode Plan|Code; quota preflight + monitor tự chạy bên trong).
- **`PARTIAL_NO_VERDICT` + `PROCESS_FAILED` là NORMAL, KHÔNG phải audit fail**: Claude CLI trả verdict dạng heading `## 1. VERDICT: **APPROVE_WITH_NOTES**` — wrapper regex chỉ nhận dòng đầu bare `APPROVED/MINOR_FIXES/REJECT` → parse fail → classification `PARTIAL_NO_VERDICT` + `CLAUDE_AUDIT_STATUS: PROCESS_FAILED:` + in fallback `USE_CODEX_SOL_MAX_PLAN_AUDITOR`. Verdict + findings ĐẦY ĐỦ trong stdout artifact `D:\CodexRuntime\<repo>\audit\claude\claude-audit-<ts>-<hash>.stdout.txt` (stderr thường rỗng). Xử lý: grep `VERDICT` trong stdout → verdict thật (`APPROVE_WITH_NOTES`/`REJECT`/`APPROVED`) → xử lý findings như MINOR_FIXES (fix → re-audit). Không dispatch Codex Sol/max fallback chỉ vì wrapper báo PROCESS_FAILED.
- **`APPROVE_WITH_NOTES` ≈ MINOR_FIXES**: fix từng note (kèm locator) → re-audit cùng wrapper. Chuỗi thật 1 plan: r2 REJECT (P1 safe-workbook) → r3 APPROVE_WITH_NOTES → r4 APPROVE_WITH_NOTES (2 P1 mới: Follow lại vào not-followed set, identity strip-and-compare) → r5 `QUOTA_GATE_BLOCKED:initial` → AG re-confirm APPROVED. Auditor đào sâu mỗi vòng nhưng finding mới có locator/evidence thật = vòng fix bình thường (khác circuit-breaker ngoài matrix).
- **`QUOTA_GATE_BLOCKED:initial` — nhiều vòng opus high đốt hết 5h quota** (4 vòng ~17%→85%): wrapper chặn TRƯỚC khi launch claude (không phải lỗi claude). Không chờ reset (~vài giờ) → fallback AG opus (`python "D:/Taadaa/reports/ag-audit/ag_audit_direct.py" <prompt> ag/claude-opus-4-6-thinking <resp> 480`) với prompt nhúng toàn plan + danh sách finding đã fix để re-confirm.
- **Claude CLI đọc context `.codex\AGENTS.md`** khi cwd trong repo có file đó (in "Subdirectory context discovered" ra stdout) — đó là context của claude, không phải instruction cho Hermes.

**AG audit diff-only trap — production change nằm NGOÀI commit được audit (hit 2026-08-11, Phase 5):** `run-ag-audit.sh` chỉ nhúng diff ĐÚNG 1 commit (`git show $COMMIT`). Khi phase thực chất = test-pin regression mà production đã đúng từ commit CŨ (Phase 5: guard 02:00 đã có từ `d039f53`, commit `0748787` chỉ thêm 4 test), AG auditor thiếu context production → REJECT oan "thiếu production change" hoặc findings hypothetical. Trước khi chọn auditor: xác định bản chất commit — test-only pin → **dùng luna subagent audit** (đọc được toàn bộ code, không giới hạn diff) + ghi rõ baseline trong prompt ("guard đã tồn tại từ commit X — KHÔNG phải baseline trap"). AG dùng tốt khi diff chứa TRỌN production change (Phase 4 `c45e98a`/`6c47826` bắt được MAJOR thật). AG hay trả finding hypothetical khi chỉ thấy diff con (`blocks` scope, `block_count`, "error code có thể khác") — đối chiếu từng finding với code thật (đọc file + probe in line reject) trước khi fix; false positive → không dispatch fix, đưa evidence vào re-audit prompt.

**Cross-machine validation trong manifest multi-machine (hit 2026-08-11, Phase 4):**
- **Inter-block gap phải per-machine**: nhóm blocks theo `machine` trước rồi sort/check theo block_index TỪNG máy. Sort toàn cục gây gap chéo 2 máy (reject oan) VÀ bỏ sót gap 2 block cùng máy khi block máy khác chen giữa sort (fail-open).
- **Duplicate account key = account ĐƠN**, không kèm machine: key `(machine, account)` bỏ lọt cùng account ở 2 máy. Entry-level check (`account_blocks[account] != block_id` → MANIFEST_IDENTITY_MISMATCH) chặn trước; block-level là defense-in-depth — ghi rõ invariant trong comment.
- **`machine_blocks == 3/máy` (exact, KHÔNG đổi thành `> 3`)**: picker design "0 hoặc 3 block/máy" (lane thiếu 3 due → skip cả lane), nên `< 3` chỉ xảy ra khi tamper → reject đúng. Auditor đề xuất `> 3` là false positive theo design — đối chiếu plan trước khi sửa.
- **Chuỗi commit Phase 4 làm ví dụ loop audit đóng gate:** `c45e98a` (6 check + 9 test) → AG REJECT (3 MAJOR: 2 thật cross-machine + 1 false) → fix 2 thật `6c47826` → AG MINOR (2 hypothetical) → đối chiếu false positive, chỉ fix comment + test end-to-end `c212f5c` → AG MINOR (1 hypothetical) → evidence + comment `848fc7f` → AG APPROVED 10s. Pattern: mỗi vòng chỉ fix finding có locator đối chiếu được; hypothetical đóng bằng evidence không bằng code.

### Claude Review Prompt Format

```
claude -p "Bạn là reviewer. Review TOÀN BỘ thay đổi code so với git HEAD.
[context về project và yêu cầu]

Trả lời DUY NHẤT một trong: APPROVED / MINOR_FIXES / REJECT.
Nếu MINOR_FIXES hoặc REJECT: list finding cụ thể, phân loại MAJOR/MINOR/NIT."
--allowedTools "Read,Bash(git *)" --max-turns 15
```

### Codex Fix Round Prompt Format

```
codex exec --sandbox danger-full-access "Sửa các lỗi từ code review:
MAJOR:
1. [finding cụ thể + fix]
MINOR:
2. [finding cụ thể + fix]
Sau khi sửa, chạy pytest verify."
```

## Audit Loop qua 9router HTTP (không cần CLI wrapper)

Khi cần planner/auditor từ Hermes mà model không phải deepseek-cha: gọi thẳng endpoint local 9router `http://127.0.0.1:20128/v1/chat/completions` (key `NINEROUTER_API_KEY`) — KHÔNG qua `codex exec`/CLI. Chi tiết model IDs, workaround, timeout: `references/9router-http-dispatch.md`.

**AG Claude qua HTTP — wrapper treo + ép `tools:[]` + nhúng diff inline (hit thật 2026-08-10):**
- `invoke-ag-audit.ps1` có thể treo cứng ở `Invoke-RestMethod`: log 0 bytes, process sống lâu hơn cả `-TimeoutSeconds` (600s trôi qua không in gì, kể cả `AG_AUDIT_TIMEOUT`), trong khi curl/python cùng model + cùng endpoint xong 4-5s. Timeout wrapper KHÔNG trigger → đừng đợi: kill sau ~3 quan sát 30s không tiến triển, rồi gọi API trực tiếp bằng `scripts/ag-audit-direct.py` (body y hệt wrapper: model, reasoning_effort high, max_tokens 6000, stream false; in `AG_AUDIT_ELAPSED`, content, `AG_AUDIT_VERDICT` từ dòng đầu non-empty).
- **Claude qua 9router (không có tool thật) tự phát minh `<tool_call>` giả và/hoặc hallucinate**: opus-4-6-thinking viết `<tool_call>{"name":"terminal"...}` rồi tự BỊA code/test không tồn tại trong repo thay vì trả verdict; sonnet-4-6 trả findings speculative kiểu "Nếu code dùng falsy check..." không locator thật. Fix 2 mảnh: (1) body request bắt buộc `"tools": [], "tool_choice": "none"` để ép trả text thuần (cùng quirk v4-pro); (2) model không đọc được file → NHÚNG diff/context inline vào prompt (vd `git show <commit> -- <files>` đổ vào giữa `=== BEGIN DIFF ===`/`=== END DIFF ===`), yêu cầu dòng đầu tiên là verdict + CẤM suy đoán "nếu code ở chỗ khác". Vòng đầu UNPARSEABLE vì thiếu 1 trong 2 mảnh → retry với prompt v2, không coi là fail upstream.
- **Findings hypothetical không phải verdict**: auditor trả `REJECT` với toàn findings "Nếu.../Cần xác nhận..." (không locator file:dòng thật, không evidence) → CHƯA dispatch worker fix. Coordinator đối chiếu từng finding với source thật (đọc code + test hiện có) trước; thường đa số thành false positive (gate fail-closed vẫn đóng ở dòng khác, test đã cover). Chỉ fix finding có locator đối chiếu được; "REJECT nhưng 0 MAJOR thật" → audit lại bằng model đọc được code hoặc thêm test cho MINOR thật rồi push.
- **Báo kết quả audit cho user (user correction 2026-08-10 — "Quăng 1 đống tiếng anh bố ai hiểu")**: KHÔNG paste raw output/findings dài vào chat. Báo gọn tiếng Việt: verdict + số MAJOR/MINOR + 1-2 dòng đối chiếu thật + hành động tiếp theo. Chi tiết findings để ở file artifact, nhắc path nếu user cần.
- **Chạy pytest trên máy này**: `PYTHONPATH='D:/Taadaa/<repo>/src'` (forward-slash Windows path). KHÔNG dùng `PYTHONPATH=/d/...` — MSYS convert thành sai (`D:\d\Taadaa\...`) và test im lặng import nhầm bản site-packages cũ → fail oan hoặc pass oan.

**Workflow đã chứng minh (2026-08-06, AGENTS.md scope-split):**
1. **backup + sha256** file policy trước khi làm bất cứ gì (`cp file file.pre-scope-<ts>.bak`).
2. **v4-pro lên plan** (read-only, `tools:[]`, `tool_choice:"none"` — v4-pro tự phát minh `<tool_calls>` giả khi không ép).
3. **Sol/terra audit plan** (khác loài — Sol bắt lỗi v4-pro thật).
4. REJECT → sửa plan theo findings → audit lại (material change = mở slot mới).
5. Chỉ khi APPROVE mới cho worker (flash) thực thi sửa file thật.

**Bẫy Sol audit:**
- Sol chạy lâu (plan 15-30KB → 4-8 phút): chạy background script + `timeout=840`, KHÔNG foreground 300s.
- Output hay bị cắt (`finish=length`) — đọc file artifact đã ghi, không tin tail process; nếu cắt giữa, gọi vòng tiếp "trả lời NGẮN phần còn thiếu".
- Sol audit = gate thật: REJECT 5 vòng liên tiếp nghĩa là **vấn đề cấu trúc, không phải nội dung** (xem Pitfalls).
- **GPT upstream (Sol/Terra) hay 401 `token_invalidated` / 429 khi hết quota trong 9router** — fallback audit theo chuỗi v6 (chốt 2026-08-09): `cx/gpt-5.6-terra-review`/`cx/gpt-5.6-sol-review` → combo `opencode-audit` → `AUDIT_ALL_ROUTES_FAILED`. **KHÔNG dùng `cmc/*` làm fallback** (kể cả `cmc/deepseek/deepseek-v4-pro` hay Kimi `cmc/moonshotai/Kimi-K2.6`) — user xác nhận 2026-08-09: cmc KHÔNG có quota.

**Gemini audit — ĐÃ BỊ LOẠI KHỎI AUDIT ROUTE (2026-08-08, policy v5):** `gemini-3.6-flash` không còn trong audit route ("Removed models" trong AGENTS.md v5). Cả 3 wrapper gemini (`invoke-gemini-9router-audit.ps1`, `invoke-gemini-api-audit.ps1`, `invoke-gemini-audit.ps1`) đã bị ghi đè thành stub `GEMINI_AUDIT_DISABLED_POLICY_V5` + **exit 23** (backup `.bak-v5-<ts>` giữ bản gốc) — gọi chúng luôn exit 23, đừng đổ thời gian retry. Primary Auditor mới: `invoke-ag-audit.ps1` (AG Claude `ag/claude-sonnet-4-6` reasoning high qua 9router; escalation `ag/claude-opus-4-6-thinking`; exit-code taxonomy 0/20/21/22/1 + verify recipe: `9router-proxy-ops` skill §AG audit wrapper).

**CÁCH CHUẨN (2026-08-10, thay wrapper hỏng):** `bash D:/Taadaa/reports/ag-audit/run-ag-audit.sh <repo-path> <commit> [model] [timeout]` — tự nhúng toàn diff inline vào prompt, ép `tools:[]/tool_choice:"none"`, mặc định `ag/claude-opus-4-6-thinking` high, in `AG_AUDIT_VERDICT` dòng cuối + lưu prompt/log/response theo stamp. Smoke-tested OK (11.9s). REJECT/MINOR_FIXES: đối chiếu từng finding với code thật (locator file:dòng) trước khi dispatch fix — findings dạng hypothetical ("nếu code...") = auditor không đọc được code, không phải bug thật. Chi tiết pipeline, model behavior và pitfalls (JSON escape heredoc, CRLF append, verify pre-existing test fail, verdict parse): `references/ag-audit-direct-9router.md`.

**Automation-core recovery — flow thật + root cause "manual hoài" + policy AI escalation/FAILED_LOCKED + fail-closed implementation pitfalls (hit 2026-08-11):** `references/automation-core-recovery-architecture.md`. Tóm tắt: (1) `RecoveryHandlerRegistry.require()` fail → NO_HANDLER_IMPLEMENTED → HARD_STOP (manual) — là do THIẾU handler, không phải đủ 8 vòng (1 detect + 7 live) mà không fix được; (2) classifier trả NON_RETRYABLE/HARD_STOP thì recovery loop chạy ngay cả; (3) fail cuối HIỆN release lock (`recovery_runner._run_one` → `_release(lock, blocked)`) — policy mới đổi thành giữ lock FAILED_LOCKED vĩnh viễn, chờ user mở; (4) AI escalation = dispatch Hermes agent quyền cao (log+UI dump → ATX-kill → force-stop → soft reboot → clear cache → retry, budget ~3 vòng) thay manual, core chỉ cung cấp hook/state/event — adapter consumer thực thi, core KHÔNG spawn Hermes. Reference còn ghi 8 fail-closed pitfalls từ các vòng audit (terminal-state vào mọi status-set, finalizer riêng cho fail sớm, exception pre-record → FAILED_LOCKED không HARD_STOP, cấm except-pass nuốt lỗi, lock giữ explicit, exception type thay string-match, cấm sys.modules patch toàn session, dead-code sau first-hook loop).

## OpenCode Free Audit Layer (2026-08-06 — đã set up, ĐỨNG TRƯỚC Gemini)

User yêu cầu: **lớp audit OpenCode nằm sau GPT review, trước fail-closed**. Audit chain ĐÃ CHỐT v6 (2026-08-09, user chốt sau Sol vs AG cross-exam):
`AG Claude (invoke-ag-audit.ps1, chính) → GPT review (Terra/Sol) → opencode-audit combo → AUDIT_ALL_ROUTES_FAILED`. Gemini/Command Code/`cmc/*` loại hẳn.

**Cách chạy (wrapper đã test OK):**
```
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\tools\invoke-opencode-audit.ps1 \
  -RepoRoot "D:\Taadaa" -Prompt "<audit prompt>" -OutputDirectory "D:\Taadaa\reports\opencode-audit"
```
- **Model cascade (2026-08-09, user chốt — combo `opencode-audit` trong 9Router):**
  `oc/nemotron-3-ultra-free` → `oc/big-pickle` → `oc/longcat-2.0-free` → `oc/ling-3.0-tiny-free`.
  **KHÔNG dùng `oc/deepseek-v4-flash-free`/`opencode-free`** — resolve thành DeepSeek Flash = worker Hermes (user chỉnh 2026-08-09). Có thể ép 1 model bằng `-Model <id>` (phải nằm trong combo).
- **Hồ sơ model free đã test (2026-08-06):** `nemotron-3-ultra-free` = mạnh nhất (NVIDIA) nhưng **hay 502 `ResourceExhausted (32/32)`** khi chạy agent+json — cascade xuống model kế (thử lại lần sau thường OK vì limit reset); `ling-3.0-flash-free` = ổn định, verdict thật; `longcat-2.0-free`/`north-mini-code-free` = verdict thật; **loại:** `mimo-v2.5-free` (trả template verdict giả, chỉ echo format — không audit thật), `laguna-s-2.1-free` (không output), `freemodel/gpt-5.6-*` (401 Insufficient balance — cần key riêng). **Rule: model free hay đổi — trước khi thêm model mới vào cascade phải smoke-test thật** (`opencode run --dir <repo> --agent taadaa-review --format json --model <m> "Reply VERDICT: APPROVE"`), đừng tin tên model.
- **Auto-update model free (user hỏi 2026-08-06):** wrapper đọc `opencode models` LIVE mỗi lần chạy (filter `opencode/.+-free`) nhưng cascade pin model cố định → model mới không tự vào. **Khuyến nghị: tự vào lấy** (`opencode models` + smoke-test) thay vì auto-đổi cascade — model free hay đổi, auto chọn nhầm model dở (như mimo template-giả). Không làm cron auto-sync trừ khi user yêu cầu.
- Agent: `taadaa-review` (đã có ở `~/.config/opencode/agents/taadaa-review.md`).
- **Output JSONL là UTF-16** (`b'\xff\xfe'`) — đọc bằng `open(path, encoding='utf-16')`, parse từng dòng JSON, text nằm trong `part.type=='text'`; verdict + findings ở các text block cuối. Đừng decode utf-8 (UnicodeDecodeError).
- Verdict có thể không đúng chữ `APPROVED` — suy luận từ findings: hết MAJOR/MINOR → APPROVED; P1/P2/P3 là phân loại mức độ (P1 = mâu thuẫn trực tiếp, P3 = cosmetic).

**Giá trị riêng của OpenCode audit:** phát hiện **findings xuyên section** mà ds-pro/Gemini (chỉ xem vùng được trích) không thấy — vụ AGENTS.md v8: OpenCode đọc TOÀN file, bắt 6 findings Luna-only ở các section khác ngoài 2 vùng đã sửa (v4 header, canonical block, "DeepSeek never executor", "remains Luna/high", fallback ordering, watchdog/escalation headings). **Dùng OpenCode khi cần audit policy toàn file / tìm mâu thuẫn cross-section**; ds-pro/gemini khi chỉ cần xác nhận vùng sửa.

**Bẫy:** wrapper Gemini (`invoke-gemini-9router-audit.ps1`) **đã bị stub exit 23** (policy v5, 2026-08-08) — không gọi nữa; dùng `invoke-ag-audit.ps1` (AG Claude) hoặc OpenCode trước. `freemodel/*` (gpt-5.6-luna free) → 401 Insufficient balance — không dùng được.

## Khi nào cần plan + audit (gate, không mặc định)

| Độ khó | Ví dụ | Rescuer/Auditor |
|---|---|---|
| Thường | debug 1 bug, sửa 1 file consumer | KHÔNG audit — flash → v4-pro cứu → xong |
| Khó vừa | nhiều file, logic phức tạp 1 repo | **terra** (plan/audit) |
| Khó thật | policy/core/live/recovery/lock/multi-repo | **sol** (plan/audit BẮT BUỘC) |

- Audit = gate cho case khó thật, không tự chạy cho task thường (debug sửa xong là DONE).
- Khó vừa gọi terra, khó quá mới sol — không đốt sol cho việc terra xử lý được.
- Rescuer/auditor (v4-pro/terra/sol) READ-ONLY — chỉ plan/hướng fix/verdict, worker patch.
- Fallback model (hết quota) = cơ chế **tool layer** (Hermes `fallback_providers`, 9router) — KHÔNG ghi vào policy AGENTS.md; policy chỉ: worker nào làm task nào, spawn fail → `SUBAGENT_RUNTIME_UNAVAILABLE`.

## Model Fallback Khi Claude Review Hết Quota

Khi `claude -p` không review được do quota/session limit, rate limit, billing hoặc provider unavailable, **không chờ reset và không bỏ review gate**.

**Claude audit timeout ≥10 phút (600s):** Full Claude audit có thể chạy vài phút. Luôn set `timeout_ms=600000` (hoặc wait ≥600s) trước khi kết luận Claude fail. **Timeout ngắn của wrapper KHÔNG phải bằng chứng quota/auth/Claude fail** — phải phân loại lỗi thật trước khi fallback (theo `D:\Taadaa\AGENTS.md`).

Quota gate (theo `D:\Taadaa\AGENTS.md`): trước mỗi call Claude chạy `D:\Taadaa\tools\claude-quota-preflight.ps1 <ledger>` — exit 0 = allow; 20 = 5h ≥85% block; **22 = weekly ≥90% block (dừng hẳn Claude, không dùng nữa)**; 21 = unavailable block. Weekly 90% là dừng cứng, không chờ reset 5h.

Fallback chỉ thay vai trò **reviewer/auditor**, không thay Codex implementer.

Thứ tự model fallback:
1. `freemodel/claude-opus-4-8` (`opencode run --agent plan --auto --variant max`)
2. `opencode-go/grok-4.5` (FreeModel thường hết nhanh)
3. `opencode-go/glm-5.2`

Smoke-test trước lần dùng đầu: `opencode run --model <m> 'Respond with exactly: OPENCODE_FALLBACK_READY'`.

Prompt phải giữ scope read-only, verdict `APPROVED | MINOR_FIXES | REJECT` ở dòng đầu.

Nếu shell vỡ quote (dấu nháy đơn), viết prompt ra `.txt` rồi `PROMPT=$(cat file.txt); opencode run --agent plan --auto --model <m> --variant max "${PROMPT}"`.

`APPROVED` từ fallback reviewer thay thế gate Claude cho run hiện tại. Lần sau ưu tiên Claude nếu quota đã hồi phục.

**Khi cần audit model cụ thể (vd second verdict Sol) qua `codex review` — quirks CLI thật (hit 2026-08-12, tiktok-follow final audit):**
- `codex review --commit <sha>` KHÔNG nhận flag `-m/--model` → `error: unexpected argument '-m' found`. Chỉnh model qua config: `codex review --commit <sha> -c 'model="gpt-5.6-sol"' -c 'model_reasoning_effort="high"'`.
- `--commit` KHÔNG kết hợp được với positional prompt (`cannot be used with '[PROMPT]'`) — không truyền custom audit prompt qua stdin khi dùng `--commit`. Prompt mặc định của Codex review đủ cho verdict; muốn nhúng context/bối cảnh riêng → dùng `codex exec --ephemeral --sandbox read-only` với prompt file thay vì `codex review --commit`.
- Codex review sandbox read-only KHÔNG tạo được temp dir → pytest/verify bên trong fail `No usable temporary directory found`; đó là hạn chế sandbox, KHÔNG phải lỗi code. Chạy suite thật ngoài (PYTHONPATH đúng máy target) và so verdict với test thật.
### Codex Reviewer Fallback Cuối

Chi tiết lệnh, schema, Windows sandbox và verification gate: `references/codex-independent-reviewer.md`.

### Codex Implementer Model Escalation (Sol high → extra high → ultra)

Khi dispatch Codex **implementer** và model mặc định fail/treo/không ghi file:

1. Thử trước: model mặc định route được (hiện `gpt-5.6-sol`) + `-c model_reasoning_effort="high"`.
2. Nếu vẫn fail (treo, không ghi file, lỗi liên tục): escalate **extra high**: `-c model_reasoning_effort="extra_high"`.
3. Nếu vẫn fail: escalate **ultra**: `-c model_reasoning_effort="ultra"`.
4. **Mỗi nấc là một phiên Codex MỚI hoàn toàn** (không resume/reuse session fail, không `--continue` session cũ). Chỉ dừng khi hết nấc hoặc xong.
5. **Tăng effort KHÔNG được lặp y hệt prompt/cách làm cũ.** Theo `D:\Taadaa\AGENTS.md`: mỗi handoff phải kèm "what was tried, why it failed, and a materially different next hypothesis/patch/plan". Trước mỗi nấc: phân tích vì sao nấc trước fail (treo ở đâu, file nào chưa ghi, test nào fail) → thay đổi prompt (bớt/dẻo hóa phạm vi, chỉ rõ file/dòng, đưa evidence, đổi hướng implement) hoặc thay cách tiếp cận. Không gửi cùng prompt với model mạnh hơn.
6. Smoke-test trước mỗi nấc: `codex exec -m gpt-5.6-sol -c model_reasoning_effort="<effort>" "Respond with exactly: READY"`.
7. Sol/ultra chỉ dùng khi có independent shards (theo Automatic Ultra Gate trong `D:\Taadaa\AGENTS.md`), không mặc định cho task khó.
8. Codex thường treo ở CUỐI sau khi đã ghi xong code/test (output đứng yên, process còn sống) — trước khi kill, kiểm tra file/test thật; đừng kill vội khi code đã ghi.

### Fallback OpenCode Free Khi Codex + Claude Đều Fail

Theo `D:\Taadaa\AGENTS.md` (audit order Claude → OpenCode → Codex fallback; wrapper `taadaa-review` + `invoke-opencode-audit.ps1`):

- Khi Codex implementer + Claude review đều fail/treo/hết quota → dùng combo **`opencode-audit`** của 9Router làm audit/review (read-only): `oc/nemotron-3-ultra-free → oc/big-pickle → oc/longcat-2.0-free → oc/ling-3.0-tiny-free` (KHÔNG deepseek — tránh trùng worker, xem OpenCode Free Audit Layer).
- Chỉ thay vai trò **audit/review**, không thay implementer.
- Invocation: `opencode run --agent plan --auto --model <free-model> '<prompt>'` (hoặc wrapper `D:\Taadaa\tools\...invoke-opencode-audit.ps1` khi có), read-only, verdict `APPROVED | MINOR_FIXES | REJECT` dòng đầu.
- Smoke-test trước: `opencode run --model <free-model> 'Respond with exactly: OPENCODE_FALLBACK_READY'`.
- Kết quả label `OPENCODE_AUDIT`; không bao giờ gọi là Claude approval.
- Nếu OpenCode cũng unavailable → `OPENCODE_RUNTIME_UNAVAILABLE` → Codex reviewer độc lập fallback cuối (`CODEX_FALLBACK_AUDIT`).

Nếu Claude và toàn bộ OpenCode reviewer đều hết quota, thiếu balance, timeout hoặc unavailable:
- Chạy **Codex phiên mới độc lập**, không resume/reuse session implementer.
- Dùng `codex exec --ephemeral --sandbox read-only -c model_reasoning_effort="high"` với model mặc định đã route được tới Sol (hiện là `gpt-5.6-sol`) và prompt review toàn bộ diff. Không ép `-m sol` nếu alias đó route sang provider thiếu credential. Verdict `APPROVED | MINOR_FIXES | REJECT`.
- Nên dùng `--output-schema` để ép verdict có cấu trúc và `--output-last-message` để lưu artifact review.
- Không dùng subagent do chính implementer spawn làm approval gate chính; shared context/assumptions làm giảm độc lập review.
- Nếu reviewer trả finding, dispatch một phiên Codex implementer mới để sửa; sau đó dùng một phiên Codex reviewer mới review lại đến `APPROVED`.

## Validate `DONE` Trước Khi Gọi Thành Công

Report wrapper/CLI `DONE` chỉ nghĩa report đã được ghi — không đồng nghĩa target `SUCCESS`. Phải đọc summary outcome per-target (JSON/XLSX) trước khi báo thành công. Ví dụ: wrapper in `DONE: result=...xlsx`, nhưng summary bên trong ghi máy `locked`.

Khi user hỏi ngắn như `xong chưa`, `này là lỗi hả`, `có ảnh hưởng không`:
- Trả lời ngay câu đầu theo cực (`Có`/`Không`/`Xong`/`Chưa`) + tối đa 1 dòng lý do, KHÔNG mở đầu bằng diễn giải/lịch sử. User từng phải nhắc lại khi câu trả lời vòng vo (2026-08-10), kể cả câu hỏi trạng thái process: `exit code -15` = process bị kill từ ngoài, không phải lỗi test/code — nói thẳng trước.
- Nếu chưa, chỉ nêu gate còn thiếu và hành động đang chạy; không lặp lại toàn bộ lịch sử.
- Chỉ gọi `Xong` khi test/proof và reviewer gate đều hoàn tất. Nếu code/test pass nhưng reviewer chưa `APPROVED`, trạng thái vẫn là `Chưa`.

## Tiếp Quản Phiên Bị Đứt Context/API

1. Tìm đúng session cũ và đọc cửa sổ cuối cùng, gồm tool output; không dựa riêng vào ảnh chụp hoặc lời tóm tắt.
2. Lập checkpoint gồm: target, action live cuối, process/reviewer đang chờ, diff hiện tại, test đã chạy và completion gate còn thiếu.
3. Process nền thuộc session cũ có thể không còn trong process registry của session mới. Không giả định nó vẫn chạy; xác minh bằng output session cũ và trạng thái thực tế hiện tại.
4. Với trạng thái live có thể đã đổi (VPN/device/lock/process tree), probe lại trực tiếp trước khi retry. Không lặp action live nếu proof hiện tại đã đạt.
5. Tiếp tục đúng target/gate còn dở; không chạy lại toàn batch hoặc phần đã có proof.
6. Mọi báo cáo từ coding agent phải được Hermes kiểm chứng bằng test/diff/proof thật trước review gate.

Chi tiết và checklist: `references/interrupted-session-takeover.md`.

## Reviewer Quota/Treo

- Reviewer process in thông báo quota/session limit nhưng không exit phải được coi là provider-unavailable, không phải review đang tiến triển.
- Poll output sau khoảng chờ hợp lý; nếu thấy quota/rate-limit/billing/session-limit, kill process treo và fallback ngay theo chuỗi model đã định.
- Không báo `APPROVED`, không gọi task `DONE`, và không để user chờ reset quota.
- Smoke-test fallback trước, sau đó review toàn bộ diff thực tế. Nếu fallback cũng lỗi, chuyển model kế tiếp thay vì lặp cùng command.

### Worker checkpoint và gate dừng process (BẮT BUỘC)

Không được coi output đứng yên hoặc `exit code -15` là bằng chứng code lỗi. Worker có thể đã sửa/test xong nhưng treo ở bước ghi report cuối; kill là side effect và chỉ được phép sau khi reconcile đủ bằng chứng.

**Khi khởi chạy worker:**
- Dùng phiên mới, `pty=true`, `background=true`, `notify_on_complete=true`; ghi transcript và result/checkpoint vào artifact riêng ngoài worktree.
- Prompt worker phải yêu cầu checkpoint tối thiểu sau mỗi mốc: đọc spec, RED, GREEN, full test, diff/status; report phải ghi incremental, không chỉ ghi một lần ở cuối.
- Ghi rõ `worker_id`, repo/worktree, allowlist, model/effort, start time và PID/session handle trước khi chờ.

**Mỗi lần poll:** kiểm tra cả bốn mặt, không chỉ stdout:
1. process handle/status và process tree (worker, pytest/python/codex child);
2. mtime + kích thước transcript, checkpoint/result và file trong allowlist;
3. `git status --short --untracked-files=all`, diff stat/check (read-only);
4. dấu hiệu lỗi fatal/quota/transport hoặc tool activity (`node_repl`/`mcp`/test child).

**Cấm kill theo heuristic 2–3 poll.** Chỉ được kill khi một trong hai điều kiện rõ ràng:
- có lỗi fatal/quota/transport machine-readable; hoặc
- ít nhất **3 lần quan sát liên tiếp**, cách nhau tối thiểu **30 giây** (≥90 giây tổng), không có output/checkpoint/file-mtime/process-tree tiến triển, không còn child đang chạy và không có tool activity.

Nếu output đứng yên nhưng còn child/test/tool activity, tiếp tục chờ bounded window; không kill. Nếu process đã tự exit nhưng thiếu report, phân loại `WORKER_EXITED_WITHOUT_REPORT`, không suy ra thất bại và không tự re-dispatch trước khi reconcile exact scope.

**Trước khi kill:** capture đầu log (verdict nếu là reviewer) và cuối log, snapshot status/diff/mtime/process tree, rồi ghi lý do `WORKER_TERMINATED_EXTERNALLY` vào artifact. Không rollback mù; file đã sửa có thể vẫn còn.

**Sau khi kill/exit bất thường:**
- Reconcile exact worktree/allowlist, không để worker thay thế chạy chồng.
- Chạy compile, targeted tests và adversarial probes độc lập nếu worktree đủ; kiểm tra `git diff --check`.
- Chỉ gọi implementation là đạt khi verifier/reviewer độc lập xác nhận; self-report, exit code và test pass đơn lẻ không đủ.
- Không tự động resume cùng session. Re-dispatch chỉ sau khi process/lease/tool-event/action cũ được xác nhận không còn; prompt mới phải nêu `what-was-tried`, `why-it-stopped`, và kế hoạch khác biệt.

**Ngoại lệ reviewer:** nếu artifact đã có verdict đầy đủ nhưng process treo, đọc toàn artifact trước; vẫn phải kiểm tra findings/độ đầy đủ rồi mới kill. `node_repl`/`mcp`/test child đang hoạt động là bằng chứng chưa được kill.

**Worker hết tool-call limit giữa phase (hit thật 2026-08-11, Phase 3 build — api_calls=100, delegation trả "not finished, not committed"):** delegation về giữa chừng KHÔNG phải fail và KHÔNG được reset worktree. Trình tự coordinator: (1) verify thật: `git log --oneline -3` (đã commit chưa), `git status --short` + `git diff --stat` (worker sửa file nào? header có đủ nhưng summary bị cắt), chạy suite thật lấy con số fail cụ thể (21 failed/80 passed) — KHÔNG tin worker tự kê; (2) nếu chưa commit: dispatch worker NỐI TIẾP từ worktree hiện tại, brief mô tả CHÍNH XÁC trạng thái thật (HEAD, file M/??, từng test fail kèm lý do từ traceback thật, allowlist đủ cả file bổ sung ngoài plan, cấm reset/revert, cấm làm yếu production để test cũ pass — test phải migrate theo design mới như "3 due account/lane" thay vì hạ constraint); (3) worker nối tiếp báo xong → vẫn verify độc lập 3 lệnh như mọi worker (git log/stat, full suite, diff-check) trước khi audit. Lưu ý worker nối tiếp thường cũng báo "ad-hoc verification PASS" (+1 lần hit — xem mục ad-hoc verification ở trên).

### Verdict nằm ở ĐẦU buffer log, không phải tail

Reviewer (Claude/OpenCode/Codex) in verdict `APPROVED/MINOR_FIXES/REJECT` ở
**dòng đầu**, rồi liệt kê findings phía sau, rồi TREO. `wait`/`log` (tail) chỉ
hiện findings → tưởng "chưa có verdict" trong khi verdict đã có ở đầu.

- Khi output đứng yên: `process(action="log", limit=40, offset=0)` để đọc ĐẦU
  buffer — verdict nằm đó. Đọc xong mới kill.
- OpenCode free có thể không in verdict dòng đầu
  theo đúng format (viết "Không còn MAJOR/MINOR chặn. Chỉ còn NIT..." =
  APPROVED tương đương) — suy luận từ nội dung findings, không cần chữ
  APPROVED đúng nghĩa.
- Nếu chỉ có NIT → coi là APPROVED (NIT không bắt buộc fix trước merge); có
  MINOR → dispatch Codex sửa rồi review lại; có MAJOR → REJECT.

### Baseline trap khi dispatch reviewer: implementation nằm trong commit, diff HEAD trống

Khi Codex implementer vừa COMMIT xong rồi mới dispatch reviewer độc lập, `git diff HEAD` chỉ còn thay đổi chưa commit (vd chỉ version bump) → reviewer tưởng "implementation chưa có" → REJECT oan.

- Luôn nói rõ baseline trong prompt reviewer: "xem CẢ HAI: `git diff HEAD -- <files>` (working tree) VÀ `git show <commit> --stat` (commit gốc implementation)".
- Nếu reviewer REJECT vì "diff không chứa implementation", kiểm tra `git log --oneline -3` trước — khả năng cao implementation đã commit, chỉ là baseline trap.
- Finding từ review lần đầu vẫn có giá trị (MAJOR/MINOR/NIT thật) — tách riêng phần baseline hiểu lầm với phần finding thật, fix finding rồi review lại.
- `codex exec --sandbox read-only` không chạy được pytest (không tạo được temp/cache) — reviewer báo "test không chạy được do môi trường" là hạn chế sandbox, không phải test fail; tự chạy test bằng tay với PYTHONPATH trỏ `src`.

**Variant 2 — file chưa từng tracked: commit đầu tiên hiện full-file addition (hit thật 2026-08-11, Phase 1 fix residual + Phase 3):** khi commit đưa file UNTRACKED từ trước vào git lần đầu (vd P1 harness chưa từng commit runner.py/watcher.py), `git diff <parent> <commit>` hiện toàn bộ file là additions → auditor tưởng worker sửa 400 dòng lung tung → REJECT oan scope (Phase 1 phải re-audit 2 vòng mới qua). Chứng minh provenance trước khi dispatch/re-audit: (1) `git log --oneline -- <file>` — commit đầu tiên chạm file phải là chính commit đó; (2) `git status --short` trước dispatch — file nằm trong `??`; (3) ghi rõ trong prompt auditor: "<file> là file mới đưa vào git lần đầu tại commit này — diff full-file do provenance, chỉ N dòng thay đổi semantic thực tế tại <locator>". Khi dispatch re-audit sau baseline trap: cung cấp bằng chứng provenance kèm context (git log file + status trước dispatch), yêu cầu auditor kiểm tra nội dung guard hiện tại thay vì chỉ đếm dòng diff.

### Workstream-pollution trap: audit REJECT oan vì dirty file từ workstream khác

Khi dispatch independent audit/verifier cho repo A trong lúc workstream khác (vd policy propagation AGENTS.md all-repos) đang sửa file trong chính repo A, `git status` của auditor sẽ thấy `M AGENTS.md` → auditor REJECT oan "scope escape" (hit thật 2026-08-10: Sol audit R4 REJECT vì `M AGENTS.md` trong repo `tiktok-luot nuoi acc` đúng lúc worker policy đang append 15 AGENTS.md).

- Trước khi dispatch auditor: chạy `git status --short` repo target; nếu có dirty chủ đích từ workstream khác thì (a) ghi rõ trong prompt auditor "thay đổi <path> là intentional từ workstream khác, bỏ qua khỏi scope-escape check", hoặc (b) sequence: để workstream kia hoàn tất (hoặc commit policy) trước khi audit.
- Cron `sync-hermes-skills-to-git` (30') commit mọi staged file trong `D:\Taadaa\Hermes` — khi index bất ngờ sạch, kiểm tra `git log -1 --stat` trước khi kết luận feature chưa commit.

### Finding churn giữa các vòng audit: auditor đào sâu hơn mỗi vòng (hit thật 2026-08-10, P1 harness R4→R5)

Audit độc lập có thể ra `REJECT` với **P1 hoàn toàn MỚI mỗi vòng** dù vòng trước đã fix sạch và được re-probe xác nhận (R4: 5 P1 → worker fix, suite 54→61, probe độc lập pass; R5: 7 P1 MỚI — journal value-proof, picker custom-reader schema, dry-run terminal, logical-day 00:00, watcher CLI, runner containment → worker fix, suite 61→70). Đây KHÔNG phải "loop vô vọng", cũng không phải lặp invariant cũ:

- **Phân loại finding MỚI vs LẶP**: auditor đào sâu hơn qua từng vòng (R3 fail-closed cơ bản → R4 identity/scope → R5 value/path/CLI level). Finding mới có locator + trigger + evidence mới → dispatch vòng fix tiếp bình thường. Chỉ khi **2 chu kỳ liên tiếp ra CONFIRMED P0/P1 mới ngoài invariant matrix** mới chuyển sang impact/design audit (theo rule 8 `D:\Taadaa\AGENTS.md`).
- **Sau mỗi round, coordinator phải tự chạy lại probe từng finding trên máy thật** — audit Sol sandbox read-only không tạo được temp dir nên ghi "suite NEEDS_PROOF"; coordinator chạy suite + probe theo đúng locator/trigger của audit rồi mới dispatch vòng fix (R4 findings được xác nhận fix bằng 5 probe độc lập trước khi vòng R5 bắt đầu).
- Prompt worker mỗi vòng phải nêu rõ "findings vòng trước đã được re-verify pass; chỉ sửa findings vòng này" — tránh worker phá regression đã đóng.
- **Circuit breaker — đừng để churn vượt ngưỡng (hit thật 2026-08-10, R4→R7):** chuỗi REJECT R4 (5 P1 mới) → R5 (7 P1 mới) → R6 (3 P1 mới) → R7 (4 P1 mới), toàn bộ rơi vào cùng cụm file journal.py/watcher.py (recovery state machine). Theo rule 8 `D:\Taadaa\AGENTS.md`, ngưỡng là **2 chu kỳ liên tiếp ra CONFIRMED P0/P1 mới ngoài invariant matrix → dừng dispatch worker, chạy read-only design/impact audit để tái-baseline matrix rồi MỘT consolidated implementation phase**; không tiếp tục dispatch worker thứ N theo từng vòng. Dấu hiệu sớm: findings nhiều vòng liên tiếp cùng cụm file + auditor đào sâu dần (key-set → value → cross-event continuity) = matrix chưa đủ, vòng sau lại ra P1 mới.
- **Phân biệt với "churn TRONG invariant matrix" (hit thật 2026-08-11, Phase 3 manifest — 4 vòng REJECT/MINOR_FIXES cùng cụm validator):** findings mới mỗi vòng nhưng ĐỀU nằm trong matrix đã có (source binding bypass → seed source-less bypass → gate-masked test) với locator/trigger/evidence mới → KHÔNG phải tín hiệu matrix thiếu, vẫn dispatch vòng fix tiếp bình thường. Circuit breaker chỉ áp dụng khi finding CONFIRMED NẰM NGOÀI matrix (như R4→R7 journal/watcher: key-set → value → cross-event = chiều sâu mới). Tiêu chí phân biệt: finding có nằm trong danh sách invariant/acceptance criteria hiện có không + có locator/trigger mới thật không. Cả hai "có" → tiếp tục; tìm thấy chiều mới ngoài matrix → dừng, tái-baseline.

### Coordinator probe: import fixture của test suite, đừng hand-build manifest (hit thật 2026-08-10, R6 probes)

Khi coordinator tự viết adversarial probe trên máy thật (vì audit sandbox read-only không chạy được pytest — cần temp dir), ĐỪNG tự dựng manifest/payload bằng tay. Đã fail 4 lần liên tiếp vì: (a) `build_manifest_payload` với `_entry` dùng manifest_id placeholder → `MANIFEST_IDENTITY_MISMATCH`; (b) `state_snapshot_digest='0'*64` bị normalize thành `None` khi recompute → assignment_id lệch; (c) `StatePaths` signature đổi (`StatePaths(root, offline_root)`); (d) state_revision không khớp source → 0 entries.

Pattern đúng: `sys.path.insert(0, <repo-root>)` rồi import fixture có sẵn trong test files — `from python_runner.tests.test_hermes_cron_p1_r2 import SOURCE, FEED, POST, TARGET, make_snapshot` — dùng `make_snapshot(root)` / `Picker(...).pick(state_paths=StatePaths(root, root))` để sinh manifest hợp lệ, sau đó `copy.deepcopy` + tamper đúng field. Probe chạy được trong vài giây thay vì loay hoay fixture.

## Watcher Validation Checklist

### Lock proxy readiness chặn START_VPN

Lock acquisition đòi `wait_for_proxy_ready` tạo vòng lặp `VPN-off → lock denied → START_VPN never runs`. Fix: per-event proxy-recovery lock dùng `bypass_proxy_readiness=True`, vẫn giữ central machine/serial exclusivity.

### Worker không treo khi lock retained/dead owner

- Dead PID retained lock: takeover theo central policy. Core re-validates atomically.
- Live owner: bounded timeout (10s) → `SKIPPED_DEVICE_LOCKED` → worker tiếp tục poll.

### Worker không chết im lặng

Exception từ `watch_device_reconnect`/`wait_until_unlocked`: bắt per-iteration, telemetry sanitized (machine+serial+status+error ≤300 chars), bounded backoff, re-enter monitoring. Mapping serial đổi → restart worker.

### Telemetry phân biệt nguyên nhân

Lock timeout, readiness failure, mapping reload/mismatch, proxy-set failure, telemetry-write failure — mỗi loại dùng status riêng, không tái sử dụng.

### Verify process tree thật

Task `Enabled` không đủ chứng minh watcher đang chạy. Phải verify scheduler/tray parent, launcher child và worker command cùng sống.

## Pitfalls đã học

- **Audit policy file THẬT phải gồm cả các file con (2026-08-06):** sau khi sửa AGENTS.md v8 (parent), audit bằng nemotron-3-ultra-free đọc TOÀN cây → bắt thêm **3 file con** (automation-core, consumer repos) vẫn giữ "Luna-only worker" trái parent equivalence. Lesson: khi sửa policy parent, **các file con kế thừa có thể giữ policy cũ** — phải grep toàn bộ cây (`rg "Luna/high" --glob 'AGENTS.md'`) + audit bằng model đọc toàn file (OpenCode) trước khi coi là xong. ds-pro/Gemini chỉ xem vùng trích → không bắt được cross-file.
- **Wrapper PowerShell tool có thể hỏng ngoài scope audit (2026-08-06):** `invoke-gemini-9router-audit.ps1` fail vì `[SHA256]::HashData` không tồn tại trên PowerShell cũ + 400 Invalid JSON với body 100KB. Không tự sửa wrapper tool (đã audit, đang dùng) — workaround: gọi API trực tiếp qua curl/urllib, model + reasoning_effort giữ nguyên.
- **Model free của OpenCode thay đổi theo thời gian — smoke-test trước khi tin (2026-08-06):** mimo trả template verdict giả, laguna không output, nemotron 502 khi concurrent — chỉ ling/longcat/north cho verdict thật. Trước khi thêm model vào cascade: `opencode run --dir <repo> --agent taadaa-review --format json --model <m> "Reply VERDICT: APPROVE"` — đọc output thật, đừng tin tên model.

- **Line-ending CRLF/LF của policy file phải GIỮ NGUYÊN khi sửa (2026-08-06):** patch tool / write_file trên Windows hay convert line-ending toàn file (LF→CRLF hoặc ngược) — 1 patch nhỏ có thể đổi 35+ dòng, làm byte-diff lệch backup (vi phạm release gate; Sol v6 từng cảnh báo "byte-diff có BOM/line-ending"). Đã gặp khi sửa 4 file AGENTS.md (parent + 3 con): patch tool LF-hoá/CRLF-hoá 3 file, phải khôi phục từ backup. **Quy trình đúng khi sửa policy file có line-ending hỗn hợp:** (1) backup từng file + sha256; (2) sửa bằng python đọc `open(path,'rb')` → decode → `text.replace(old, new)` — nếu file dùng CRLF, thử variant `old.replace("\n","\r\n")` trước; pattern bị ngắt giữa dòng (`pinned\n  Luna/high`) thì dùng `re.search(r'pinned\s*\n\s*Luna/high worker')`; (3) ghi lại bằng `open(path,'wb').write(text.encode('utf-8'))` — KHÔNG qua patch tool/write_file, KHÔNG dùng `open(...,'w',newline='')` (sẽ LF-hoá); (4) verify: đếm CRLF vs backup (`cur.count(b'\r\n') == bak.count(b'\r\n')`), đếm content-diff line vs backup (phải = số thay đổi chủ đích, không phải 35+), grep remnant sau khi loại cụm hợp lệ (`re.sub(r'\([^)]*Luna/high or flash/max[^)]*\)','',t)` rồi mới tìm term thật — đừng đếm cả cụm hợp lệ làm remnant). Bẫy `\r\r\n` (double CR) xuất hiện sau nhiều lần ghi lẫn lộn — grep `\r\r\n` và replace về `\r\n`. Chạy validator (`check-claude-quota-policy.ps1` exit 0) sau khi sync xong.
- **JSON escape qua terminal heredoc (hit thật 2026-08-10):** viết python `<<'EOF'` qua terminal tool: `\\n` trong tool-call JSON tới shell chỉ còn `\n` 1 backslash → python source `\n` = NEWLINE thật → ghi vào file đích làm hỏng string literal (SyntaxError: unterminated string literal). Muốn ghi literal backslash+n vào file: dùng `chr(92) + "n"` (an toàn tuyệt đối với mọi layer escape) hoặc 4 backslash `\\\\n`. Quy tắc chung: bất kỳ chuỗi escape nào qua terminal heredoc bị bào mòn 1 lớp mỗi layer (JSON → bash → python) — test bằng cách grep file sau khi ghi trước khi chạy pytest.
- **Test fail nghi ngờ pre-existing → verify bằng `git stash` (2026-08-10):** test fail ngoài scope thay đổi: stash working tree (`git stash -q`) → chạy lại đúng test → vẫn fail = pre-existing, không thuộc change của mình → `git stash pop -q` và tiếp tục, ghi chú 1 dòng. Đừng dispatch fix mù cho test không liên quan.
- **Bulk policy sweep toàn cây — 3 bẫy execution (2026-08-09, phủ policy v6 17 file AGENTS.md):**
  (1) **Exclude dir bằng substring, không phải membership**: `any(s in parts for s in skip)` với `scan['/a/b'].split('/')` là exact-match từng element — `'_luna-max-to-high-backup' in ['_luna-max-to-high-backup-20260807']` = False → **sửa nhầm cả thư mục backup**. Đúng: `any(any(s in part for part in parts) for s in skip)`. Nếu lỡ sửa nhầm backup: khôi phục từ manifest sha_before (script lưu `manifest.json` với `sha_before`/`sha_after` mỗi file).
  (2) **Regex escape path Windows trong python source**: `r'D:\\\\Taadaa'` trong file .py = literal 2 backslash, text thật có 1 → không match. Dùng pattern path-agnostic: match từ đầu câu tới term ổn định (`Command Code is only[\s\S]{0,220}?cmc/deepseek/deepseek-v4-flash`) thay vì include path đầy đủ. Xử lý wrap-line: normalise CRLF→LF trước khi regex, ghi lại đúng EOL gốc.
  (3) **Git Windows case-insensitive**: repo track `handoff.md` (thường) nhưng append vào tên `HANDOFF.md` — NTFS coi là cùng file nên content vào đúng file tracked, nhưng `git add HANDOFF.md` (hoa) **silent no-op** (không tìm thấy pathspec). Trước khi append vào file có thể đã track với case khác: `git ls-files | grep -i <name>`; `.gitignore` pattern `handoff.md` cũng chặn cả `HANDOFF.md` (case-insensitive match). Commit theo đúng case file đang track.
- **Yêu cầu session-scoped ≠ policy (user correction 2026-08-11, "cái này t yêu cầu thôi, k phải sửa policy"):** khi user nói "task khó gọi Claude CLI sửa code" — đó là yêu cầu cho phiên/lần này, KHÔNG phải lệnh sửa policy. Đừng tự ghi memory/AGENTS.md/skill thành policy bền vững; áp dụng cho session hiện tại và nêu rõ "áp dụng phiên này, policy giữ nguyên". Nếu user thật sự muốn đổi policy thì sẽ nói "sửa policy"/"từ giờ luôn". Kiểm chứng: agent vừa viết vào memory rồi phải revert ngay khi user đính chính.
- **Policy file 2 section cùng chủ đề → audit REJECT mãi (2026-08-06):** AGENTS.md Taadaa có 2 section cùng nói worker model (Delegation L70-215 + Model Routing L710-770). Mọi bản sửa 2 section đều vô tình DUPLICATE với section còn lại → Sol bắt "lặp contract" mỗi vòng → REJECT 5 vòng liên tiếp dù nội dung mỗi bản tốt hơn. Bài học: trước khi sửa policy file, **inventory toàn file** tìm mọi chỗ nói cùng chủ đề; nếu có ≥2 section cùng chủ đề thì phải sửa ĐỒNG THỜI hoặc thiết kế 1 canonical + các section khác chỉ tham chiếu. Nếu REJECT lặp vì cùng lý do cấu trúc 2 vòng → dừng, đổi cách tiếp cận (đừng sửa mãi trong cùng 2 section).
- **Junction vào git repo (cập nhật 2026-08-09 — THAY cho ghi chú "sync thủ công" 2026-08-03):** profile-local của skill này + `hermes-orchestration-dispatcher` là JUNCTION trỏ thẳng vào `D:\Taadaa\Hermes\skills\` — sửa local = sửa luôn file trong git repo, KHÔNG cần copy sync. Kiểm tra lệch: `git status --short skills/`. LƯU Ý cron `sync-hermes-skills-to-git` (30') commit+push **MỌI thứ đang STAGED** trong repo, không chỉ 2 skill của nó — đừng để staged dở lâu nếu chưa muốn cron commit (đã gặp: staged của mình "biến mất" vì cron commit + push hết).
- **ModuleNotFoundError dù module có trong src** (2026-08-03): env python cài `automation-core` bị **dist-info dở dang** (version 0.4.22 dist-info nhưng site-packages thiếu file `usb_popup.py` — wheel 0.4.22 chưa tồn tại). Import fail `No module named 'automation_core.usb_popup'`. Fix: kiểm tra `pip show automation-core` version vs `ls site-packages/automation_core/` (file thiếu), rồi `pip install --force-reinstall <đúng wheel>` theo pin consumer. Chạy test với `PYTHONPATH=<repo>/src` để dùng bản src thay vì site-packages cũ. Nghi ngờ env nhiễm/lệch: dùng `env -i PATH=... HOME=... USERPROFILE=...` để cô lập sys.path khỏi hermes venv.
- **Đừng giả định format output CLI** (2026-08-03): viết regex parse output của `claude /usage`, `adb`, `dumpsys`... trước tiên PHẢI chạy lệnh thật lấy sample, đừng tự bịa format. Regex `Weekly usage:` sai vì output thật là `Current week (all models):` — mock test pass nhưng end-to-end ra null. Quy tắc: chạy lệnh thật → nhìn raw output → viết regex → test trên sample thật.
- **Android UI selector debugging**: `find_by_fields` dùng exact match; `resource_id=""` không match.
- **`dumpsys window policy` false-positive**: match chỉ `mShowingLockscreen=true`/`isStatusBarKeyguard=true`.
- Không coi `pytest` pass là production-ready nếu chưa đọc workbook/config thật.
- **Soft reboot recovery**: 3× fail → `adb reboot` + 120s wait + 60s boot + wake + swipe.
- **Worker conflict Codex**: dùng `write_file` hoặc dispatch single leaf + kill worker cũ.
- **Lock takeover chỉ khi eligibility khớp chính xác central gate**.

## Merge 2026-08-09 — từ `multi-agent-review-loop` + `role-based-agent-review-loop` (đã xoá sau khi gộp)

- **Standalone runner + `/rl`**: `python <hermes-repo>/scripts/agent_loop/cli.py "<task>" --cwd <repo-path> --max-rounds 3`; state mặc định `<repo>/.hermes/agent-loop` (`--state-root` override, `--state` resume file cụ thể). Backend mặc định cũ: Codex Sol high (plan+code), Claude Opus low (review), OpenCode fallback. Trong Hermes chat: `/skill role-based-agent-review-loop` / `/rl` — skill đã merge vào đây, lệnh cũ chỉ để tương thích.
- **Coordinator STRICT (Phase 3 final gate)**: trong lúc worker↔reviewer loop, Hermes KHÔNG đọc/review/arbitrate code — chỉ relay RAW output giữa 2 bên (không tổng hợp, không cắt nghĩa). Sau khi cả 2 APPROVED: Hermes ĐƯỢC đọc kết quả cuối, có thể đề xuất thay đổi → dispatch Claude thảo luận → đồng thuận → DONE. Max 3 vòng cùng 1 finding không đổi → escalate user.
- **Phase 0: audit plan trước implement** (user đưa plan/spec): dispatch Codex (feasibility/architecture) + Claude (edge cases/safety) song song audit → tổng hợp trình user → user approve → mới dispatch implementation. KHÔNG bao giờ code trước audit + approval.
- **Role separation**: user giao role (Codex coder, Claude auditor) → Hermes CHỈ orchestrator. KHÔNG tự patch code thay worker dù leaf báo không write được file (đó là vấn đề routing, không phải lý do làm thay).
- **Drive-by edits**: sau Codex chạy `git diff --stat` TOÀN repo (không chỉ task-scope) — Codex hay sửa file ngoài scope; revert bằng `git checkout -- <path>` trước khi gọi reviewer.
- **Claude print mode**: review prompt inline >10K chars → `Error: Reached max turns` (KHÔNG phải reject code) — fix: `--max-turns 8-10`, `--verbose`, hoặc split sub-prompts. Inline `-p` dính special chars bash (`()`, `` ` ``, `'`, `$()`) → viết prompt file rồi `claude -p "$(cat prompt.txt)" --max-turns 10`. Template: `references/claude-print-mode-review-prompt.md`.
- **Model pins cũ (role-based, có thể đã đổi — xem `agent-model-routing`)**: Codex plan/code = `gpt-5.6-sol/high`; Codex debug D:/Taadaa = `gpt-5.6-luna/high`; Claude review = `claude-opus-5` low effort.
- **Standing-goal review loop**: `/goal`/“làm đến khi xong” = loop kín — không intermediate summary, không `clarify`, chỉ báo user ở APPROVED/FINAL_BLOCKED/MAX_ROUNDS (chi tiết: `references/standing-goal-review-loop.md`).
- References mới copied: `automation-scheduler-patterns.md`, `claude-print-mode-review-prompt.md`, `tiktok-core-debugging-patterns.md`, `production-consumer-preflight.md`, `session-routing.md`, `standing-goal-review-loop.md`, `workflow-workbook-preflight.md`.
