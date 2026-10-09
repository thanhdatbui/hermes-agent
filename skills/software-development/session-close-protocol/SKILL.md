---
name: session-close-protocol
description: "Use when the user says 'chốt phiên', 'chốt', 'done', 'wrap up', asks whether the current deliverable is done, or requests closeout. Runs closeout_gate.py (Sol Web/OmniRoute :20129) scoped with --files; REJECTED/<85 enters a remediation loop (not BLOCKED) until APPROVED>=85 exit 0, then auto commit/push/verify remote SHA. Progress questions remain status-only."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [session-close, review, git, handoff, taadaa]
    related_skills: [taadaa-farm-ops-rules, verification-evidence, concurrent-workspace-safety]
---

# Session-close protocol

> **Canonical policy precedence:** Follow `D:\Taadaa\HERMES_SUBAGENT_RULES.md` marker `CANONICAL-POLICY-PRECEDENCE-2026-10-05`; this skill implements that policy and must not override it.

References:
- `references/auto-remediation-until-approved-gate-loop.md` — User mandate 03/10/2026: Khi Closeout Gate chưa đủ điểm (< 85) BẮT BUỘC tự sửa đến khi đủ điểm >= 85; cơ chế --auto-remediate đa vòng qua Claude Code CLI trong closeout_gate.py.
- `references/closeout-gate-score-supremacy-and-anti-truncation-trap.md`
- `references/automatic-push-after-closeout.md` — Chốt phiên đạt Gate >= 85đ tự động git push.
- `references/ownership-aware-closeout.md` — Close/done semantics & remediation loop.
- `references/strict-reviewer-schema-enforcement.md` — Reviewer schema enforcement.
- `references/read-only-closeout-triage.md` — Quy trình & mẫu báo cáo triage closeout-gate ở chế độ read-only (tách biệt transient vs structural, điều tra mock side_effect StopIteration, và lập bounded remediation contract).
- `references/polluted-repo-diff-isolation-and-closeout.md` — Phục hồi & cô lập patch sạch khi repo bị ô nhiễm diff lớn (1000+ files / CRLF churn / mixed reset) để đạt gate closeout >= 85 mà không xóa working changes (26/09/2026).
- `references/capture-before-cleanup-and-budget-discipline.md` — Quy chuẩn CAPTURE-BEFORE-CLEANUP (chụp ảnh màn hình đích trước teardown/HOME) & kỷ luật chia turn budget chống 0 files modified (20/09/2026).
- `references/sol-auditor-scorecard-and-telemetry-pitfalls.md` — Quy chuẩn Telemetry/Observability & bài học vượt gate Sol Auditor (82->86, 76->86, 41->92, 73->93, 81->87, 82->90), bẫy test monolith pre-existing failures, STDOUT leak "sida khó hiểu", pre-push hook race; see `references/mixed-worktree-closeout-gate.md`ng bypass diverged history (19/09 - 25/09/2026).
- `references/closeout-gate-rejection-evasion-and-safety-regression.md` — Xử lý Gate REJECTED (<85đ), cấm rollback né review, Clean Git Fallacy, Stop-the-line khi Timeout, điều tra pháp y INC-HERMES-2026-001, và Hard Guard vật lý 4 tầng (Audit Log SHA-256 chain, hook chặn git destructive, pre-push gate).
- `references/multi-shift-watchdog-state-contracts.md` — Quy chuẩn phân ca động (Sáng/Trưa/Tối), state transition cô lập từng ca, và fail-closed soak gate cho watchdog (20/09/2026).

## Kỷ luật bảo toàn logic người dùng (No-Regression Contract)
- **Tuyệt đối không đảo ngược yêu cầu tùy biến của User khi đóng phiên**:
  - Khi user yêu cầu một quy tắc logic cụ thể (ví dụ: *mật khẩu ChatGPT bắt buộc tạo theo mật khẩu Gmail, cấm hardcode*), Agent tuyệt đối KHÔNG được quay lại code cũ hay ghi đè lên các quy ước này trong quá trình commit/closeout.
  - Phải kiểm tra git diff (`git diff HEAD~N`) để đảm bảo logic user yêu cầu vẫn được bảo toàn nguyên vẹn trước khi push.
  - Fail-fast ngay nếu phát hiện thiếu tham số cấu hình tùy biến của user, tuyệt đối không dùng giá trị mặc định tùy tiện.

## ⚠️ HARD INVARIANT: CHỐT PHIÊN BẮT BUỘC CHẠY CLOSEOUT GATE (SCORECARD 100Đ)
**Precedence: TỐI CAO.** Áp dụng khi user phát lệnh bằng bất kỳ từ khóa nào: `chốt phiên`, `chốt`, `đóng phiên`, `xong phiên`, `kết thúc phiên`, `done`, `wrap up`.
**CANNOT PROCEED TO SESSION END WITHOUT `closeout_gate.py` EXIT CODE 0.**

Trước mọi lần `git push` hoặc báo cáo chốt phiên:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo <đường_dẫn_repo> --base <BASE> --files <target_file_1> [<target_file_2> ...] --json-output
# <BASE> = $(git merge-base HEAD '@{u}' 2>/dev/null || git merge-base HEAD origin/main)
```
- **Reviewer:** Sol Web qua OmniRoute `:20129` (model `review`, Tier 0 `chatgpt-web/gpt-5.6-sol-high`) — đây là reviewer canonical của closeout gate. Các dòng `plan-review`/9Router phía dưới chỉ áp dụng cho plan review ngoài `closeout_gate.py`.
- **`--files` bắt buộc:** chỉ liệt kê target files của candidate đang chốt (từ change ledger của task hiện tại). Không để dirty/untracked/unrelated diff lọt vào payload làm reviewer chấm sai candidate.
- **Điều kiện commit/push (đủ cả 3):** `verdict == APPROVED`, `score >= 85`, `exit code == 0`. Khi đủ -> tự commit exact scope, fetch + `pull --rebase`, push, đối soát `git ls-remote` SHA == HEAD.
- **Nếu Verdict: REJECTED hoặc Score < 85:** KHÔNG PUSH, KHÔNG báo BLOCKED, KHÔNG dừng chờ User — vào **Remediation Loop** (mục ngay dưới) cho tới khi APPROVED hoặc gặp hard blocker thật.
- **CẤM TUYỆT ĐỐI:** Tự ý commit + push rồi báo xong mà bỏ qua bước reviewer chấm điểm!
- **CẤM TUYỆT ĐỐI NGỤY TẠO PHIÊN SẠCH (ANTI-EVASION):** CẤM chạy `git checkout`, `git restore`, `git stash` hay xóa working tree về trạng thái sạch bóng (`working tree clean`) sau khi Reviewer đã REJECTED để trốn bước chấm điểm rồi tuyên bố "phiên đã hoàn tất". Khi bị REJECT, BẮT BUỘC in bảng điểm chi tiết (Scorecard, Judge Notes, Key Findings) cho User thấy và tiếp tục ở lại vòng lặp remediation cho đến khi đạt APPROVED (>= 85đ).

## ⚠️ CLOSEOUT REMEDIATION LOOP v1.2 (CANONICAL — SUPERSEDES mọi dòng cũ trong file này nói "tối đa 2/3 vòng", "dừng khi REJECT", "closeout failure is terminal")
**Precedence:** Mục này thắng mọi câu mâu thuẫn bên dưới (kể cả "Closeout failure is terminal for this turn", "Gate-failure exit", "Reject-Loop ... tối đa 3 vòng", "Vòng lặp tự sửa lỗi khi REJECT (Tối đa 3 vòng lặp)"). Các invariant an toàn cấp cao (worker/Coordinator role, scope lock, no broad disk scan, no unsafe UI/ADB, no secret) vẫn giữ nguyên.

**State machine:**
| Gate output | State | Hành động |
|---|---|---|
| APPROVED + score >= 85 + exit 0 | `CLOSEOUT_APPROVED` | commit exact scope -> fetch/pull --rebase -> push -> verify remote SHA |
| REJECTED hoặc score < 85 | `REMEDIATION` | remediation loop, rồi chạy lại gate |
| timeout / network / 5xx / 429 / empty / unparseable | `REVIEW_TRANSIENT` | retry bounded rồi quay lại state trước |
| hard blocker thật | `BLOCKED_AT_<STEP>` | dừng kèm evidence |

**Remediation loop (mỗi vòng):**
1. Đọc nguyên văn `key_findings`, `judge_notes`, scorecard từ JSON; in cho User.
2. Phân loại finding: lỗi thật trong candidate / false-reject thiếu context (bổ sung `--system-prompt`, không thêm code thừa) / ngoài scope (ghi NOTE riêng, không mở rộng scope).
3. Lập Patch Contract: `target_files` ⊆ allowlist candidate, finding, `max_lines`, `focused_test` < 30s, stop condition.
4. Dispatch fresh Implementation Worker (`delegate_task`) là executor duy nhất để sửa candidate code; Claude CLI chỉ advisory/read-only khi User hoặc active contract yêu cầu; Coordinator không tự sửa candidate code; Worker self-report/exit code không phải proof.
5. Verify diff thật của thợ + chạy focused test; vô hiệu hóa verdict/test cũ (gắn bytes cũ).
6. Chạy lại `closeout_gate.py ... --files <target_files> --json-output`.

**Không trần cứng:** không có giới hạn "2 vòng"/"3 vòng" khiến Coordinator đầu hàng khi vẫn còn đường sửa hợp lệ. Reviewer trả < 85 (dù lặp lại) KHÔNG BAO GIỜ một mình là lý do BLOCKED.
**Anti-spin (hard invariant, không phải cớ dừng):** 2 vòng liên tiếp cùng finding + cùng điểm + diff không đổi bytes -> bắt buộc đổi chiến lược (bổ sung context, tách finding, đổi thợ Worker <-> Claude CLI trong quyền đã cấp, thu hẹp contract). Hết mọi chiến lược hợp lệ mới được `NO_VALID_REMEDIATION_PATH` kèm evidence từng vòng.
**Giới hạn cấp cao** (Tier budget/checkpoint 25-30 calls, watchdog 5/10/30 phút, quota Claude 85%/90%): làm đúng thủ tục của invariant đó (checkpoint, chuyển route), không dùng làm cớ tuyên bố BLOCKED vì điểm thấp.

**Transient:** timeout/network/5xx/429/empty -> retry tối đa 3 lần (backoff 30s -> 60s -> 120s) trên OmniRoute `:20129`; hết retry -> route reviewer độc lập kế tiếp theo policy (ghi đúng nhãn provider thật); chỉ khi mọi route hợp lệ fail mới `BLOCKED_AT_REVIEW_ROUTE`. Transient không phải REJECT, không phải APPROVED.

**Hard blocker hợp lệ (duy nhất):** mọi route reviewer fail sau retry; fix bắt buộc ngoài allowlist/ngoài quyền User cấp (`SCOPE_EXPANSION_REQUIRED` -> hỏi 1 câu); xung đột ownership thật (active writer/branch tip đổi) `BLOCKED_AT_RECONCILIATION`; vi phạm invariant an toàn (secret, unsafe UI/ADB, device lock ca chính, file hệ thống bảo vệ); `NO_VALID_REMEDIATION_PATH`. Mọi BLOCKED phải kèm evidence: lệnh, exit code, score/findings JSON, diff hash.

**Tách bạch task:** "Sửa rule điều phối" (TIERED_WORKFLOW.md, SKILL.md, AGENTS.md) và "sửa candidate code được closeout chấm" là 2 task, 2 allowlist, 2 lần closeout riêng. CẤM trộn file rule vào `--files` của candidate code và ngược lại; CẤM sửa logic `closeout_gate.py` khi task chỉ là sửa rule. Dirty/unrelated diff = `OUT_OF_SCOPE`, giữ nguyên, không stage, không đưa vào review, không là blocker.

**Claude session:** khi được gọi làm thợ sửa rule/candidate, Claude KHÔNG tự `git commit`/`git push`; commit/push thuộc Coordinator sau khi gate đạt đủ 3 điều kiện.

References:
- `references/closeout-gate-reviewer-truncate-trap-and-gemphone-cleanup-20260919.md` — **[19/09/2026]** Khắc phục lỗi bỏ qua Reviewer chấm điểm do file SKILL.md bị truncate >100KB (đưa lệnh lên top 20 dòng), Claude CLI audit & 4-layer hard guard, dọn sạch tàn dư GemPhone `verify-bar-close` và sửa bẫy alert P0 mất phiên giả khi lướt feed.
- `references/closeout-gate-scorecard-rubric-and-universal-resolver.md` — Scorecard 100đ Sol Auditor, Rubric 5 tiêu chí, Universal Resolver.
- `references/guard-model-drift-hook.md` — Pre-tool Hook guard_model_drift.py chặn model cấm (sol-pro/instant).
- `references/closeout-gate-runner-and-5-bottlenecks.md` — Giải quyết triệt để 5 điểm nghẽn chốt phiên kéo dài 1 tiếng (Opus Thinking timeout 300s, bash escaping diff, git context out-of-sync, pytest wrong cwd, git index.lock) bằng runner chuẩn hóa duy nhất.
- `references/documentation-only-closeout-gate.md` — Quy chuẩn vượt Closeout Gate cho commit tài liệu hóa (documentation-only update), tránh rớt điểm Test Evidence hoặc rơi vào Verdict UNKNOWN do thiếu format JSON.
- `references/identical-tree-commit-divergence-synchronization.md` — Quy trình xử lý phân nhánh commit có cùng tree hash (git reset --mixed) và cô lập unstaged changes qua git stash khi chốt phiên trong môi trường concurrent farm.
- `references/omniroute-combo-review-and-claude-cli-guard.md` — Gate 1 dùng combo `review` trên OmniRoute :20129. **Canonical Sol/GPT Web Sol invariant:** “hỏi Sol”, “Sol High” và “GPT Web Sol” luôn nghĩa là gọi trực tiếp OmniRoute/OpenAI-compatible :20129 với alias `review`/`chatgpt-web/gpt-5.6-sol-high`, không mở ChatGPT Web/Chrome/CDP trừ khi user nói rõ. Bắt buộc lưu HTTP/model evidence; không được báo đã hỏi Sol nếu route chưa trả response.
- `references/claude-cli-bounded-review-loop.md` (trong `farm-anti-overengineering`) — Quy chuẩn review độc lập với Claude CLI thật qua Python subprocess, chống lỗi bash và cấm Coordinator tự review mạo danh.
- `references/farm-alert-codebase-fix-and-canary-closeout.md` — Quy tắc ép sửa codebase thay vì chạy lệnh ADB ngoài khi nhận Farm Alert, tuân thủ nghiêm ngặt 5 bước recovery; cập nhật Case 141 về chống sa đà over-engineering (DoD report-biased "terminal state = done", bẫy hard block guard gây ngọng subagent, và bẫy Samsung launcher Base32 false-positive).
- `references/plan-review-diff-scoped-payload-safety.md` — Quy tắc diff-scoped payload và socket timeout an toàn khi gọi Gate 1 Plan-Review qua 9Router tránh nghẽn context và timeout.
- `references/incident-evidence-live-canary-protocol.md` — Quy trình bắt buộc chạy Live Canary đầy đủ (runner swipe + cleanup home + unlock) khi có incident evidence / ảnh lỗi hiện trường.
- `references/sol-auditor-scorecard-integration-closeout-gate-20260917.md` — Tích hợp Scorecard 100đ từ Sol Auditor vào closeout_gate.py thay thế phán quyết nhị phân APPROVED mù; kiến trúc Universal Network Resolver (localhost vs LAN IP 192.168.110.123:20129) cho cả Kibe và Admin.
- `references/multi-repo-rebase-and-chained-token-closeout.md` — Quy trình commit trước pull/rebase đa repo kèm cơ chế token authorization cho chuỗi popup liên hoàn.
- `references/reviewer-finding-triage.md` — Phân loại finding REJECT (reproduce, baseline-check, f-string continuation pitfall, stale git lock) trước khi sửa; cấm push khi còn REJECTED; quy tắc Bouncer & Canary Pass = Code Freeze chống review scope creep kéo dài 3 tiếng (06/09/2026).
- `references/closeout-gate-stream-false-and-cases-rebase-reorder.md` — Quy chuẩn closeout_gate.py bắt buộc truyền stream: False chống lỗi SSE stream Extra data/JSONDecodeError trên proxy :20128/:20129, và quy trình giải quyết conflict docs/farm-automation-cases.md tịnh tiến số Case (N -> N+1) khi cả local và remote cùng thêm case mới (14/09/2026).
- Case 165 (14/09/2026): Phân nhánh thẻ đề xuất bạn bè / follow lại trên feed (`follow_back_suggestion` trong `feed_swipe_smoke.py`) theo trạng thái cooldown: nick đang dính phạt thì bấm "Không quan tâm" để đóng thẻ, nick sạch (không có cooldown) thì bấm "Follow lại" để tương tác tự nhiên.
- Case UI-62 (14/09/2026): Bổ sung resource-id `id/u68` vào `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` (`follow_runner/core/selectors.py`) trên TikTok v46.9.3, khắc phục sự cố 27 máy dừng phiên với cảnh báo `MANUAL_REVIEW: follower row không có nút follow semantic`.
- Case 79 (14/09/2026): Chuẩn hóa watchdog đọc SSD State DB `state.db` và khóa tần suất 30 workers cho Watchdog Avatar ca tối chống spam cảnh báo Telegram.
- Case 99 (14/09/2026): Windows Console Subprocess `CREATE_NO_WINDOW` (`0x08000000`) flag cho toàn bộ các lệnh gọi `ffmpeg`/`ffprobe` qua `subprocess.run` trong `Tiktok-video` (`random_batch_render.py`, `media_probe.py`, `download_by_niche.py`, `pipeline_common.py`), triệt tiêu hiện tượng cửa sổ command prompt (`cmd.exe`/`conhost.exe`) nháy lên màn hình desktop và icon chớp giật trên thanh Taskbar khi đang render hoặc tải video nền.
- **Closeout Gate Review Prompt Context Invariant (14/09/2026):** Khi gọi `closeout_gate.py` để thẩm định diff sửa đổi cục bộ trong các hàm (ví dụ chêm `kwargs` dùng `sys.platform`), Reviewer có thể reject nhầm do không thấy `import sys` trong diff (`NameError`). Luôn sử dụng `--system-prompt <file_or_text>` để cung cấp context rõ ràng (các module đã import sẵn `sys` ở top-level) hoặc tạo helper chung để reviewer thẩm định đúng bản chất logic.
- `references/lease-release-review-pattern.md` — Pattern chuẩn failed-session lease release đúc từ 4 vòng REJECT liên tiếp của OmniRoute review (Case 163, 13/09/2026): giữ `succeeded=False`, release ngoài publication gate, release trong `finally`, fenced-log trước release nhưng bọc trong outer try/finally, quét hết `set_status("blocked")` toàn file; build scoped diff `--input` khi worktree bẩn ngoài scope.
- `references/reviewer-policy-moralizing-and-docs-pii.md` — Xử lý verdict REJECT mang tính policy/moralizing (không phải kỹ thuật) như review-route failure; quy tắc che PII serial/nick và kiểm tra cấu trúc docs trước review.
- Case GPM-WATCHDOG-SILENT-01 (14/09/2026): Khắc phục lỗi watchdog `post_evening_gpm_login_watchdog.py` bắn spam tin nhắn Farm Alert sau mỗi batch lẻ do `no_agent=True` in stdout; chuẩn hóa silent batching qua stderr và chỉ in đúng 1 lần tổng kết toàn ca khi hoàn tất hoặc sau 23:30.
- `references/follow-friends-reason-normalization-and-profile-guard-closeout.md` — Phân biệt chuẩn xác dismiss reason giữa UI back tap và hardware key Back, Profile Guard chống false-positive detector, và quy chuẩn tạo script review ngoài working tree (06/09/2026).
- `references/media-evidence-gate-protocol.md` — Quy chuẩn nghiệm thu bằng chứng ảnh màn hình thật (MEDIA Evidence Gate): cấm bẫy tùy chọn "khi cần", phân công Worker capture / Coordinator deliver, hard reject báo cáo thiếu thẻ MEDIA: (12/09/2026).
- `references/idle-restart-and-grep-timeout-freeze-prevention.md` — Bài học chống treo phiên 4 tiếng: Cấm chạy grep -rn quét đĩa khi chốt phiên (kẹt timeout 900s) và cơ chế vô hiệu hóa script restart gateway ngầm (restart-when-idle.ps1) tránh kill gateway làm mồ côi turn và treo bong bóng Telegram (06/09/2026).
- Case 81 (15/09/2026): Khắc phục lỗi watchdog `post_evening_avatar_watchdog.py` gửi lặp báo cáo do vừa tự gọi Telegram Bot API vừa `print` ra stdout khi Hermes Cron Scheduler chạy `no_agent=True` (vốn tự động bắt stdout gửi Telegram); chuẩn hóa cơ chế chỉ print ra stdout một lần duy nhất khi kết ca hoặc chốt giờ và cung cấp context architecture qua `--system-prompt` cho `closeout_gate.py` để reviewer không reject nhầm việc bỏ API call trực tiếp.
- **GitHub REST API Commit/Push Safe Fallback (15/09/2026):** Khi môi trường Git-Bash / MSYS trên Windows bị nghẽn mạng hoặc treo `git push` / `git fetch` (timeout 30s-180s qua HTTPS dù gh token hợp lệ do Git Credential Manager hoặc Windows socket hang), sử dụng trực tiếp GitHub REST API (`POST /git/trees` -> `POST /git/commits` -> `PATCH /git/refs/heads/<branch>`) qua Python `urllib.request` để push commit và cập nhật ref tức thì (< 3s), bảo đảm 100% hoàn thành Gate 4 và xác thực remote SHA mà không bị kẹt phiên.
- **Hermes Cron no_agent=True Empty Stdout Guard (15/09/2026):** Khi viết watchdog script chạy qua Hermes Cron Scheduler (`no_agent: True`), TUYỆT ĐỐI CẤM in template rỗng (ví dụ: `Tổng máy đủ điều kiện: 0`, `Success: []`, `Fail: []`) ra stdout. Khi không có máy nào cần xử lý hoặc chưa phát sinh hành động, script BẮT BUỘC phải im lặng hoàn toàn (exit 0 không print). Việc in template rỗng sẽ làm scheduler tự động bắt stdout và gửi tin nhắn rác định kỳ mỗi 5 phút vào kênh Telegram của user/nhóm alert.
- `references/sensitive-marker-exemption-and-mixed-ui-review-pattern.md` — Quy chuẩn phân tầng hành động nhạy cảm thực sự (`real_sensitive_actions`) trước khi miễn trừ popup lành tính (Case 174: tránh lỗ hổng bỏ lọt màn hình nhạy cảm khi giao diện xuất hiện đồng thời cả gợi ý bạn bè lẫn prompt đăng nhập/captcha).

## 0. LIVE CANARY & MEDIA EVIDENCE (BẮT BUỘC KHI CÓ TARGET LIVE HOẶC INCIDENT EVIDENCE)
- **Quy tắc Kiểm Chứng Cron / Watchdog (CẤM MOCK/DRY-RUN):** Khi sửa hoặc setup cron/watchdog, TUYỆT ĐỐI CẤM dùng mock string hoặc cờ `--dry-run` để kết luận đã hết lỗi. BẮT BUỘC chạy giả lập thực tế (live simulation) trên 1-2 máy rảnh bằng chính lệnh của scheduler (`--force` hoặc gọi runner với `--limit 1-2`) để phát hiện lỗi môi trường (`cwd`), argument parser CLI, và lock resolution trước khi chốt phiên.
Khi phiên có sửa code tính năng/farm hoặc logic runtime:
- **BẮT BUỘC chạy Live Canary bằng RUNNER CHÍNH THỨC của repo** (TUYỆT ĐỐI CẤM dùng ad-hoc tap/script lẻ thay thế):
  1. **Với `tiktok-luot nuoi acc` (Feed):** Chạy runner với `--max-swipes 2` (hoặc `--recovery-test-swipes 2`, Case 131 tự động random 2-3 swipes khi truyền 2) + `--cleanup-on-stop` → Tự động đóng popup → Swipe đủ video ngẫu nhiên → Tự động dọn dẹp về Home và nhả lock.
  2. **Với các script nghiệp vụ khác (`Tiktok_Reg`, `tiktok-follow`, `Tiktok-video`, `Hotmail`, `tiktok-add-bao-mat-f2a`, `register gmail`...):** Chạy runner chính thức trên máy target → Vượt qua đúng điểm nghẽn/lỗi đã fix → Chạy tiếp đến khi hoàn thành trọn vẹn nhiệm vụ của script (Task Completion) → Tự động dọn dẹp và nhả lock.
- **NGHIỆM THU ẢNH BẮT BUỘC (`MEDIA:<path>`):** Kết thúc canary hoặc task farm, BẮT BUỘC chụp ảnh screencap màn hình máy thật và đính kèm vào tin nhắn báo cáo kết quả theo cú pháp `MEDIA:<đường_dẫn_tuyệt_đối_ảnh_local>` ở dòng riêng biệt. Báo cáo task farm thiếu thẻ `MEDIA:` = VI PHẠM GATE NGHIỆM THU, CHƯA ĐƯỢC CHỐT PHIÊN.
- **Quy tắc Staging an toàn (Tránh bẫy DENYLIST .ps1 khi dùng `git -C`):** Khi stage các file có đuôi `.ps1` (như `scripts/run-feed-session.ps1`), BẮT BUỘC gọi tool `terminal` với tham số `workdir="D:/Taadaa/..."` kèm lệnh `git add <files>`. TUYỆT ĐỐI KHÔNG dùng inline `git -C "..." add ... .ps1` vì cờ `-C` làm lệch regex của `ALLOWLIST_PATTERNS`, khiến lệnh trôi xuống Tầng 3 Denylist và bị Farm Guard chặn đứng nhầm.
- Với **code-only thuần túy** (không có target máy, không có ảnh/log hiện trường từ user), mới ghi `CANARY_NOT_APPLICABLE`.
- **Target-resolution gate chỉ áp dụng khi target đến từ task hoặc incident evidence:** resolve `<row>` bằng hàm mapping canonical và nguồn workbook/device-map thực tế. Nếu resolver lỗi khi target đã được xác định, báo `TARGET_RESOLUTION_UNPROVEN`.
- **Preflight bằng đúng interpreter trước live canary:** trước khi gọi PowerShell/runner có thể chạm thiết bị, chạy một import/entrypoint smoke bằng chính executable mà launcher sẽ truyền cho runner, kèm kiểm tra dependency bắt buộc tối thiểu. Nếu lỗi import/setup xảy ra trước target action (ví dụ thiếu native dependency của PIL), phân loại là `BLOCKED_AT_GATE_0_PREFLIGHT`, ghi rõ `no device action occurred`, và không tiếp tục review/commit/push. Không nhầm lỗi môi trường với lỗi UI/popup; khi setup được sửa ở phiên khác, phải chạy lại preflight rồi mới canary.
- **Phân loại canary failure theo stage:** tách `target resolution`, `runner/import preflight`, `device preflight`, và `runtime/UI`. Wrapper exit 1 không đủ để kết luận popup hoặc thiết bị lỗi; phải đọc traceback và artifact stage thực tế.
- Khi canary được chạy, chỉ kết quả `status: success`, `final_status: success`, `stop_reason: ""` mới mở các gate review/commit/push. Nếu canary fail/blocked, dừng release actions và báo đúng blocker.

## Purpose

## All-repository policy propagation lesson

When a user asks to update a rule across all repositories, do not limit the inventory to `AGENTS.md` and `PROJECT_RULES.md`. Enumerate every active top-level Git checkout under the workspace, then inspect tracked `AGENTS.md`, `CLAUDE.md`, `PROJECT_RULES.md`, nested app context files, and explicitly discovered workspace policy files. Distinguish policy adapters from non-policy templates (for example a design-system `templates/claude.md`) before editing. Capture byte/hash/EOL baselines, append one markered canonical block without normalization churn, preserve unrelated dirty work, and verify marker uniqueness plus idempotence across the complete allowlist. During closeout, commit each repo's exact policy candidate separately, resolve the configured upstream per repo instead of assuming `origin/<current-branch>`, and verify the policy commit by exact subject/path scope plus ancestry on both local and remote refs; a later concurrent commit may legitimately move `HEAD` beyond the policy commit. If normal `git commit` is blocked by a stale temporary index lock, do not remove locks blindly: prove no active writer owns that temporary index, use a fresh isolated index, and preserve the real worktree/index state. Use `references/all-repo-rule-propagation.md` for the inventory, baseline, append, and verification procedure.

## Closeout lessons from farm alert and swipe-cap work

### Target resolution and blocker separation

- Resolve the target from the repository's canonical resolver and authoritative runtime/source artifacts before classifying a canary blocker. A missing guessed config filename, truncated search result, stale report, or wrong state-root lookup is not evidence that a row is absent.
- Keep these states separate: candidate row exists; incident-specific row is identified; target machine is in the frozen cohort; device lock is active; canary preflight is configured. They are independent gates and must not be collapsed into one blocker.
- When the user reports that an operation such as Reg has stopped, re-read live lock metadata and owner state before treating that operation as the current blocker. An expired/stale lock still requires the owner/controller release path; do not delete it manually or assume stopping the operation updates lock metadata.
- Validate a frozen cohort against the assignment manifest whose `assignment_id` and `manifest_digest` match the cohort. Do not validate against a convenient global/AppData manifest. If the target machine is not in the frozen cohort, report `BLOCKED_AT_GATE_0_COHORT_TARGET`; do not mutate the frozen artifact, invent a cohort, or bypass with a local-run flag.
- If a canary stops before target selection, report the exact preflight stage and explicitly state that no device action occurred. Do not describe it as a UI, ADB, lock, row, or code failure without evidence.
- After a mistaken diagnosis, keep the correction short and direct: acknowledge the incorrect claim, state the corrected evidence, and give only the current blocker and next safe action.

- Run Gate 0 only when the current task has an explicit live machine/row/serial/device target, the user explicitly requests real-device validation, or user-provided incident evidence (opening-session screenshot/alert/log) identifies a machine/target plus a concrete runtime failure being debugged. For code-only/general flow work without such target or incident evidence, record `CANARY_NOT_APPLICABLE`; the exact diff still requires focused tests and an independent parseable review.
- **User correction — no target is not a canary blocker:** If the user says there is no machine/target, do not invent one from repo names, workbooks, cron state, stale locks, or historical artifacts. Mark `CANARY_NOT_APPLICABLE` and continue to model review → focused verification → exact-scope commit → rebase → push. Do not stop closeout at Gate 0 merely because the code touches farm/runtime paths.
- If the review route cannot authenticate or returns no parseable verdict, classify the closeout as `BLOCKED_AT_REVIEW`; never commit/push and never soften the result into “chốt xong”. Preserve the exact route blocker without printing credentials.
- When a concurrent writer changes a scoped file after a prior commit, re-read the full file, freeze the new exact diff, and invalidate old review/test evidence. Re-check the invariant after each rebase/merge; this prevents a later timeout commit from reverting `FEED_SESSION_MAX_SWIPES` from 15 to 16.
- A full-suite timeout is also not a pass; report the command and the bounded evidence.
- If Gate 0 fails for a machine-specific blocker (for example, that machine's VPN/proxy), do not misclassify it as a candidate-code failure. Preserve the failed target artifact, and when the user explicitly authorizes choosing another machine, resolve a fresh machine+row target from runtime evidence, preflight the replacement, and rerun the same canary contract there. Keep the original target's blocker separate from the replacement target's pass/fail.
- A transient device lock must be rechecked live before reporting it as the current blocker; an old canary artifact is historical evidence, not present state. Never unlock, kill, reboot, or force-takeover merely to manufacture a Gate 0 pass.
- **Live-cron lock is not a canary pass and not a kill target:** if the target machine is held by a live cron (`multi-machine-feed-session --machines ...` with a running pid, e.g. pid 201676 holding 74 machines), do NOT use `--full-scope-takeover`, kill the pid, or delete the lock to force a canary. Classify `BLOCKED_AT_GATE_0_LOCKED_BY_LIVE_CRON`, preserve the cron/lock untouched, use focused tests as substitute evidence, and report it in Blocker. Verify lock owner live via `tasklist` / process CommandLine before concluding.
- Keep the final user report short and structured: `Mục đích → Kết quả → Blocker → Remote`. Put the direct status in the first sentence.


“Closeout” is an internal label for the final release pass:
**Gate 0: live canary only when the current task has an explicit live machine/row/serial/device target, the user explicitly requests real-device validation, or user-provided incident evidence identifies a machine/target plus a concrete runtime failure being debugged → Gate 0.5 (Automation Tasks Only): cập nhật Case Fix thực tế & Anti-Pattern tương ứng vào `docs/farm-automation-cases.md` (alias `docs/uiautomator.md`) → Gate 1: review the final candidate → Gate 2: commit the exact scope → Gate 3: git pull --rebase → Gate 4: push → verify the remote SHA**.
For code-only/general flow changes without such target or incident evidence, record `CANARY_NOT_APPLICABLE` and go directly to farm automation catalog update (if automation-related) → review → test → commit → rebase → push. Never infer a target from repository name, config, workbook, historical artifacts, or nearby machine files. The user does not need to know or repeat the word `closeout`. Use plain Vietnamese when explaining it.

## Trigger and auto-close intent

This workflow is activated by explicit closeout commands (`chốt phiên`, `đóng phiên`, `kết thúc phiên`, `xong phiên`) and by completion-status questions about the current deliverable (`xong hết chưa?`, `đã xong chưa để chốt phiên?`, `xong chưa?`) only when all auto-close gates pass: the original-deliverable ledger is complete, focused evidence is present, no current-task worker is active, and no unresolved blocker exists. When those conditions pass, report `Đã xong — đang chốt phiên` and immediately run the existing Gate 0/0.5/1/... applicability sequence; do not require a second explicit `chốt phiên` message.

If any auto-close gate is missing, report the exact blocker and do not commit, rebase, or push. Plain progress questions such as `tiến độ sao?` and `đang làm tới đâu?` remain status-only. Preserve `closeout_gate.py` before commit/push/successful closeout. Canonical Sol/GPT Web Sol means the direct OmniRoute route; do not open ChatGPT Web/Chrome/CDP unless explicitly requested.

### Auto-close execution and exact-scope candidate gate
When an auto-close question passes the four readiness gates, execute closeout immediately in the same turn; do not merely report that the work is ready. Before Gate 2, stage only the confirmed deliverable files/hunks and verify `git diff --cached --name-only` against the original change ledger. Unrelated dirty files must remain unstaged and must not cause their tests to be pulled into the closeout candidate. Run focused tests selected from the staged candidate, then run `closeout_gate.py` against that exact staged scope. If the gate reports failures from an unrelated dirty file, rebuild the staged candidate rather than expanding scope or fixing unrelated work.

### Closeout incident handling
A stale `.git/index.lock` is a concrete closeout blocker only while an active Git writer owns it. Inspect lock age and active Git processes first; after proving the lock is stale and no writer owns it, remove only that stale lock, restage the exact allowlist, and continue. Never reset, stash, clean, or revert unrelated dirty work merely to make the tree appear clean.

**Closeout evidence is gate-specific:** a previously passing focused test does not satisfy Gate 2 if `closeout_gate.py` selects a broader or different focused set. Treat the exact command and exit code run by the closeout gate as authoritative for closeout. If its test command times out, errors, or covers unintended dirty files, stop at `BLOCKED_AT_GATE_2`; do not report DONE, proceed to review/commit/push, or silently substitute an earlier test result. First report the selected test command, timeout/error, and candidate file scope; only retry after reconciling the exact candidate scope and test selection.

Phân biệt rạch ròi: Bước "B5 (Closeout / Báo cáo phục hồi)" trong chu trình 5 bước Farm Alert chỉ là **báo cáo kết quả phục hồi hiện trường và kết quả canary test** cho user, KHÔNG ĐƯỢC nhầm lẫn với quy trình "Chốt phiên 6 Gate" (commit, review, rebase, push). Khi báo cáo B5, ghi rõ nhãn "B5 (Báo cáo Phục hồi / Incident Recovery Report)" để tránh gây hiểu nhầm là đã commit/push.

**Closeout scope:** Reconstruct the original deliverable and exact change ledger before review or Git actions; preserve unrelated candidates. Do not expand remediation or dispatch multiple writers. Concurrent scoped changes invalidate prior evidence and require reconciliation. See `references/closeout-scope-recovery.md`.

**Closeout scope:** Reconstruct the original deliverable and exact change ledger before review or Git actions; preserve unrelated candidates. Do not expand remediation or dispatch multiple writers. Concurrent scoped changes invalidate prior evidence and require reconciliation. See `references/closeout-scope-recovery.md`.

If the user asks what the rule means, explain it without running the workflow.

When policy choices are unclear, ask **one decision question at a time** in plain language. Do not dump a list of unrelated policy questions or introduce internal jargon without explaining it. **Override khi CLOSEOUT_ACTIVE:** CẤM clarify khi closeout bị REJECTED/<85; tiếp tục remediation loop. Clarify chỉ được phép khi gặp SCOPE_EXPANSION_REQUIRED, thiếu quyền, hoặc thao tác tốn phí/không thể đảo ngược theo canonical policy.

## Closeout lessons from the failed mixed-candidate attempt

**Candidate extraction precedes all release gates:** In a dirty/shared checkout, freeze the original deliverable before review or final testing. Verify that the isolated worktree/clone path exists and is the path actually being used; never silently fall back to the shared checkout when a path is missing. Materialize the candidate from the actual current upstream/base plus only the confirmed deliverable hunks. A staged file with the right filename is not proof of the right candidate: exclude older fixes, unrelated docs/config, sibling-worker tests, and mixed same-file hunks. Run tests and review only against the materialized exact tree, recording its SHA/tree identity.

**Closeout failure handling (superseded by Remediation Loop v1.2):** A failed focused test or a REJECTED/<85 review is a `REMEDIATION` state, not a terminal stop: do not commit, rebase, push, or claim “đã chốt” for the failing bytes, but continue the remediation loop (Patch Contract -> worker/Claude CLI per granted authority -> focused test -> rerun gate). Stop at `BLOCKED_AT_<GATE>` only for a hard blocker listed in the Remediation Loop section, with evidence. Keep the user-facing report short and direct: first line = gate status; then only `Mục đích → Kết quả → Blocker → Remote`, without progress narration or a long internal transcript.

**Remote/base reconciliation:** Before reviewing or committing, compare local `HEAD`, the actual upstream SHA, and the candidate base. If upstream is ahead, rebuild the candidate on that upstream and invalidate earlier tests/review. Do not absorb every dirty/staged path just because it overlaps the same files; compare exact hunks and preserve unrelated work untouched.

## User-decided policy

- **User communication style:** The user wants simple, minimal reports focused on task purpose and result (`Mục đích → Kết quả → Blocker → Remote`).

A dirty worktree is evidence to classify, not an automatic stop. If unrelated staged/unstaged paths or non-overlapping hunks exist, preserve them and continue the requested closeout by reconstructing the exact candidate in a clean temporary worktree or isolated index. Stop only when a same-file overlap, active writer, branch-tip change, or other condition makes the requested bytes unprovable. Do not turn unrelated dirt, a sibling candidate, or a concurrent edit in another region into `BLOCKED`; do not reset, clean, stash, or overwrite it.

### User correction: explicit canary waiver

When the user explicitly says to skip/bỏ qua canary, record `CANARY_WAIVED_BY_USER`, perform no live device action, and continue the remaining non-live gates: exact-scope candidate verification, independent review, commit, rebase, push, and remote-SHA verification. Do not silently reintroduce the canary later or classify the waiver as target-resolution failure. Report the waiver clearly.

- **User communication style:** The user wants simple, minimal reports focused on task purpose and result (`Mục đích → Kết quả → Blocker → Remote`). CẤM TUYỆT ĐỐI dùng cú pháp LaTeX math (`$\rightarrow$`, `$ ... $`) vì Telegram không render mà hiển thị chuỗi thô rất khó đọc; luôn dùng ký tự Unicode thật (`→`) hoặc text thuần (`->`). Do NOT flood the user with internal workflow details, tool outputs, or technical option lists. When guiding an interactive Windows operation, give exactly one concrete next action or one copy-paste command at a time, then wait for the observed result; never tell the user to run a command without actually providing it. If the user says a command is still at a continuation prompt (`>>`), first provide the cancel/recovery action, then provide a complete single-line replacement command in the next step. The assistant autonomously decides technical choices (routing, testing, staging, isolated patching) based on project rules and executes safely.
- **Remote-host evidence boundary:** Do not claim that a remote PC, service, or Hermes instance was configured merely because the current machine can inspect a local checkout or reach a LAN port. Separate local evidence from user-executed remote actions. For remote setup, verify each stage with an explicit output from the target host: config path/value presence without printing secrets, authenticated endpoint response, then one real end-to-end model/tool call. Treat placeholders or dummy API keys as non-working until the target service's auth database explicitly accepts them; never assume LAN reachability bypasses authentication.
- When the user says `chốt phiên`, treat it as full closeout, not merely cleanup: freeze exact scope, reconcile live/runtime state, review and verify the final candidate, then commit/rebase/push only if the gates pass; otherwise report the exact blocked gate. Never claim closeout from a worktree deletion or summary alone.
- **Hard trigger interpretation:** `chốt phiên đi` is the same executable closeout trigger as `chốt phiên`; it is not a request to stop work, give a progress summary, or continue an older investigation. On receipt, immediately enter the closeout state machine and do not start, resume, or delegate unrelated remediation.
- **Closeout ownership fence:** before any closeout action, reconcile and shut down active workers/processes created for the current task, then freeze the exact candidate. A worker completion message is not permission to resume its old task after the user has triggered closeout. If a newly discovered process belongs to an unrelated cron/project, preserve it and report it rather than taking ownership.
- **Gate-failure exit:** if a mandatory gate fails, cancel downstream release steps (commit, rebase, push, “đã chốt” claim) for the failing bytes. A REJECTED/<85 review or a fixable test failure enters the Remediation Loop v1.2 (continue fixing within the current scope and granted authority). Finish with `BLOCKED_AT_<STEP>` only for a hard blocker (e.g. Gate 0 device/target blocker, review routes all down, scope expansion needed, ownership conflict, safety invariant) with concrete evidence; after that blocked report, do not keep polling or open a new investigation unless the user issues a new task.
- **User-facing closeout response:** report only `Mục đích → Kết quả → Blocker → Remote`; state the gate result in the first sentence. Do not narrate internal plans or repeatedly ask the user to confirm a command when the trigger is already explicit.
- For farm alert/recovery work, distinguish source code from the interpreter's installed/editable runtime package. Verify the module path and loaded flag with the same interpreter used by the live runner; if runtime was patched directly, preserve an external backup and report that it is not a Git commit until integrated.
- Dirty files **outside the exact task scope are not blockers** by default. Preserve them untouched; stage and commit only the explicit allowlist. This rule is semantic, not model-specific: a worker or reviewer must not convert an unrelated `git status` entry into `BLOCKED` merely because it exists. If the user explicitly authorizes committing additional non-conflicting dirty paths, treat that as a deliberate scope expansion—not permission for `git add .`: audit every added path first for secrets/credentials, local state/log/cache/runtime artifacts, generated data, large binaries/models, active writers, and missing/broken fixtures or manifests. Include only audited, parseable, non-sensitive paths; document excluded paths and the reason. Re-check the expanded allowlist immediately before staging because concurrent writers can add a dirty dependency file or untracked artifact after the first snapshot.
- **Explicit main-branch authorization overrides the default shared-checkout preference:** when the user directly orders “sửa trên main”, “merge vào main”, or equivalent, `main` is the authorized target. Do not keep refusing or deflecting to a worktree merely because the checkout is shared. Snapshot `HEAD`, staged/unstaged paths, and active worktrees first; preserve unrelated dirty paths, stage only the approved allowlist, and stop only for a real same-file/staged ownership conflict. Report the exact main commit/merge result and preserved outside-scope paths.
- Direct-main authorization does not permit broad staging or cleanup. Never use `git add -A`, `git reset`, `git clean`, or stash unrelated work to make `main` clean; use exact path/hunk staging and verify the resulting commit with `git show --name-status`.
- **Model Stability & No-Silent-Downgrade Invariant:** Model active trong phiên do user/config chỉ định (ví dụ `ag/gemini-3.7-flash-high`) là bất biến. CẤM tự ý chuyển sang model khác (như `gpt-5.6-luna` hay fallback ngầm) khi gặp lỗi prompt/timeout/compaction trừ khi có lệnh rõ ràng từ user. Nếu tool call fail do format/timeout, phải retry hoặc xử lý lỗi kỹ thuật trên chính model hiện tại, không silent failover.
- **Releasing Device Locks vs Cohort Preflight Separation:** Khi user yêu cầu "nhả lock" hoặc "release all lock", thực thi mở khóa đích danh/hàng loạt qua backup timestamp ngay lập tức mà không kéo các kiểm tra phức tạp như frozen cohort, manifest digest hay scheduler state vào làm blocker giả. Lock release là tác vụ vận hành thiết bị độc lập.
- For Hermes configuration-only fixes, treat the active config as the exact allowlist and do not invent a repository closeout: use `hermes config set <key> <value>` rather than hand-editing `config.yaml`, then parse/validate the config and verify the persisted key. A global `agent.system_prompt` can be superseded by a platform/channel `system_prompt` override, so inspect the effective override before claiming the rule applies everywhere; existing conversations may retain cached prompts and require a new session.
- When an in-scope file also contains unrelated dirty hunks, do not rely on an interactive partial stage alone. Build the staged candidate from `HEAD` (or use a precise patch/index operation), apply only the approved hunks, and verify `git diff --cached --name-status` plus the staged diff before testing. If unrelated hunks were accidentally staged, reset only the affected paths in the index and rebuild the exact staged blobs; never reset, stash, or clean the worktree.
- Bind every final test and review to the exact staged candidate, not merely the working-tree view: materialize/check the staged tree (for example with `git write-tree` + `git archive` into a temporary directory), run the focused tests and compile checks there, then obtain a fresh parseable reviewer verdict after any index rebuild. A prior approval is stale if the staged bytes or scope change.
- If a reviewer is dispatched asynchronously, report `REVIEW_PENDING` rather than `BLOCKED` while it is still running. Once it returns, independently verify its verdict is parseable and matches the final staged scope before committing.
- **Review routing**:
  - **Review bình thường / Ca dễ (mặc định):** BẮT BUỘC gọi combo `review` trên OmniRoute (`http://localhost:20129/v1/chat/completions`). Combo `review` được tối ưu hóa: Tier 0 là `chatgpt-web/gpt-5.6-sol-high` (pool 5 acc Web sống khỏe, zero cost, reasoning Sol đỉnh cao); Tier 1 là `gpt-5.6-terra-high` (Codex Farm pool); Tier 2 là `ag-opus-pool` (Claude Opus 4.6 Thinking qua pool 78 acc); Tier 3-6 là các fallback free tier (Nemotron 3.5 Lightning, Nemotron Super 120B, Muse Spark 1.3/1.2). Đã gỡ bỏ sạch sẽ Gemini Pool khỏi chuỗi review do thiếu tư duy phản biện. TUYỆT ĐỐI KHÔNG tự ý gọi Claude CLI native cho ca dễ để tránh lãng phí quota 5h Claude Pro.
  - **Review Hard hoặc khi user ra lệnh:** CHỈ KHI làm tác vụ review hard (kiến trúc guard, thay đổi core, multi-repo, device-lock phức tạp) hoặc khi Tad trực tiếp chỉ định ("gọi claude cli", "kêu claude kiểm tra") mới được gọi Claude Code CLI native (`claude -p --model opus --effort high`), tuân thủ chặn ở mức 85% limit. Phân biệt rõ: Claude CLI là app native của Anthropic, KHÔNG đi qua OmniRoute.
  - **Kỷ luật trung thực báo cáo Gate 1:** Báo cáo Gate 1 phải ghi đúng 100% reviewer thực tế (OmniRoute :20129 vs Claude CLI native). CẤM TUYỆT ĐỐI copy-paste template cũ từ phiên khác ghi nhận ảo "Claude Opus High thẩm định" cho các ca dễ hoặc ca chưa từng chạy Claude CLI.
  - `plan-review` cho ordinary/single-repository work;
  - `plan-review-hard` cho core, multi-repository, state-machine, lock, recovery, or similarly sensitive work;
  - **The named plan-review model must be called through 9Router, not replaced by the session model or an implementation worker.** For hard review, send `model: plan-review-hard` to the configured 9Router endpoint and capture the parseable verdict bound to the exact staged candidate. Do not use Luna/Flash or the current implementation model as an auditor.
  - A worker/subagent audit is not the model review gate. Its `APPROVED`/`REJECT` is diagnostic input only; it never satisfies `plan-review`.
  - Before accepting a verdict, verify three separate facts: (1) the request used the named `plan-review`/`plan-review-hard` model, (2) 9Router returned a parseable verdict for the exact staged hash/tree, and (3) the response was actually served by the requested review route and did not silently downgrade or remap to an unsupported implementation model. If the named route is unavailable, malformed, rejected, or transparently maps to an unsupported implementation model, record `BLOCKED_AT_REVIEW` and use only the documented independent audit fallback; never call Luna/Flash as the auditor and never relabel a Luna/Flash response as plan-review approval.
  - **Routing correction learned from user feedback:** when the user asks for plan review, explicitly report the 9Router model identifier and transport before/after the call. A review sent with `cx/gpt-5.6-luna` is an implementation-worker review, not plan review, even if it returns a detailed `REJECT`. For this user's lock/recovery work, use `plan-review-hard` through 9Router first; if that route fails, preserve the exact route error and use the documented fallback only, with its actual model name labeled.
  - **For this user's lock/recovery work, prefer the hard review route and include the exact current bytes/diff plus the regression-test scope. If the primary AG route has no active credentials, record that route failure and use the configured independent fallback; do not silently call the worker review instead.**
  - **Plan-review model used in this session: `plan-review` via 9Router (port 20128). The route returned parseable `VERDICT: APPROVED` with findings. This is the correct route for TikTok follow runner fixes. Do not use the session model or implementation worker as auditor.**
  - See `references/plan-review-routing.md` for the route-selection, downgrade-detection, and evidence checklist.
  - **Call the review before repeated polling or downstream Git actions.** Once a candidate is stable, bind its hashes, invoke the review model, and stop/reconcile if a concurrent writer changes either scoped file; do not burn turns waiting while no review request is in flight.
  - **Review Payload & Socket Timeout Safety:**
    - **Diff-scoped payload:** Chỉ gửi `git diff -U3`/`-U5` của các file sửa đổi và test case mới; KHÔNG đẩy toàn bộ repo diff lớn kèm hàng nghìn dòng mock/fixture boilerplate cũ khiến model bị nghẽn context hoặc timeout.
    - **Fail-Fast Socket Timeout:** Script gọi review (Python `urllib.request` / `requests`) BẮT BUỘC đặt `timeout=45` hoặc `timeout=60` trực tiếp ở socket layer để ngắt sớm và fail-fast/retry khi proxy/upstream bị kẹt socket, tránh block tiến trình terminal vô hạn.
    - **Ưu tiên OmniRoute (:20129) khi tải nặng:** OmniRoute có cơ chế Ordered Concurrency Spillover (`priority` combo strategy, maxConcurrent=5/account qua 8 tài khoản Antigravity) và `failoverBeforeRetry: true` lập tức nhảy sang account tiếp theo khi gặp 429/503, giải quyết triệt để nguy cơ treo socket khi 9Router (:20128) bị nghẽn. Khi route `plan-review` trên 9Router bị timeout quá 60s, sử dụng model `ag-claude` trên OmniRoute (:20129) làm reviewer độc lập đạt chuẩn.
    - **Testing Speed vs Full Gate Verification & Pytest Timeout Prevention:**
      - Trong các vòng lặp debug/sửa lỗi của worker và khâu verification chốt phiên (Gate 2), **CẤM TUYỆT ĐỐI chạy bare `pytest` trên toàn bộ monorepo lớn (như `tiktok-luot nuoi acc` với 2000+ tests)** vì sẽ bị dính **Timeout 900s (15 phút)** hoặc làm phiên kéo dài hơn 60 phút khiến user bức xúc.
      - **BẮT BUỘC CHỈ chạy focused test suites** bao gồm: (1) Các test file tương ứng trực tiếp với các module vừa sửa, (2) Các test integration liên quan trực tiếp đến luồng chính (ví dụ: `pytest python_runner/tests/test_observe.py python_runner/tests/test_classifier.py python_runner/tests/test_safety.py python_runner/tests/test_feed_session_watchdog.py`).
      - **Giới hạn thời gian test:** Tổng thời gian chạy test suite ở Gate 2 phải **dưới 2 phút**. Không chạy các test suite chậm/cũ không liên quan.
    - **Subprocess Diff Extraction Safe Pattern:** Khi lấy diff để gửi Plan-Review trong Python, luôn dùng `subprocess.run(['git', 'diff', ...], capture_output=True, text=True, encoding='utf-8')` để đảm bảo diff đầy đủ và không bị rỗng do encoding hay subshell buffering.
    - **CẤM Inline Bash `python -c` / Heredoc khi gửi Diff cho Plan-Review:** Trong Git-Bash / MSYS trên Windows, không nhúng chuỗi `git diff` trực tiếp vào lệnh terminal `python -c "..."` hoặc bash heredoc. Bash sẽ diễn giải ký tự curly braces `{}`, backticks, nháy kép `"` hoặc `<N>` trong nội dung diff, gây lỗi cú pháp (`diff: missing operand`, `{diff}: command not found`) hoặc làm rỗng diff khiến Reviewer trả `VERDICT: REJECTED` giả. Bắt buộc dùng tool `write_file` tạo file script Python riêng (như `tmp_run_review.py`), chạy script đó rồi xóa sau khi hoàn tất.
  - if calling 9Router HTTP API (`:20128`), ensure `NINEROUTER_API_KEY` is sourced from `.env`; for large diffs or reasoning models (`plan-review`, Sol/Opus, DeepSeek), set timeout to 300-900s (or background runner) as reasoning and token generation can exceed 60s;
  - if the selected route fails, record the fallback and keep the fallback reviewer read-only with respect to the main worktree and remote.
  - **Plan-Review Pitfalls & Verification Invariants:**
    - **Idempotency Receipt Scoping & Strict Schema Defense-in-Depth:** When scoping durable idempotency receipts by `target_account`, untagged legacy receipts must be excluded when a specific `target_account` is requested (`return bool(receipt_acc and receipt_acc == target_acc)`), while matching all receipts when `target_account` is empty to prevent cross-blocking on multi-account shared machines. In schema validators, keep `machine` and `video_number` validated strictly rather than optionalizing them.
    - **Hashtag Verification & Pill Caption Truncation:** When adapting caption confirmation for UI builds that truncate text or format hashtags as pills, avoid overly permissive `any()` checks. Use structured verification: full string match fallback -> prefix matching (first 3-4 words) -> majority hashtag matching (`len(matching) >= max(1, (len(hashtags) + 1) // 2)`).
    - **Bounded UI Recovery vs Modulo Loop Traps:** In polling wait loops (e.g. `_wait_for_feed`), avoid modulo-based repeating triggers (`consecutive_failures % 3 == 2`) that repeatedly kill/restart backend services (like `atx-agent`). Always use bounded or one-shot flags (`atx_recovered = True`) to prevent hardware stress and infinite recovery loops.
    - **Test Mock Boolean Accuracy:** When implementing handlers requiring `getattr(res, 'ok', False) is True`, ensure unit tests explicitly configure `mock_res.ok = True` instead of relying on default `MagicMock` truthiness.
    - **Unique Integer Priority for Popup Registries:** Every newly added entry in `BENIGN_POPUP_REGISTRY` MUST have a unique integer priority that does not collide with existing entries. Duplicate priorities cause silent shadowing or non-deterministic handler ordering.
    - **High-Priority Overlay vs Modal Dialog Exclusions:** When registering full-screen or creation overlays at high priority (e.g. video editor / camera at priority 90+), always include explicit negative exclusions for nested/follow-up modal dialogs (such as draft continuation prompts: "tiếp tục chỉnh sửa bài đăng này?", "save draft", "hủy bản nháp") to avoid shadowing specific modal handlers.
    - **O(n) Set-Based Element Attribute Checks:** Use set operations (`{desc.lower() for ...} & {"trang chủ", "home"}`) rather than nested `any(any(...))` loops across `iter_elements(root)` to prevent O(n²) complexity and timeout risks on dense XML trees.
    - **Focus Detection Prioritization over System UI Overlays:** When parsing focused activities from `dumpsys window windows` (e.g. `parse_focused_activity`), use `re.findall` and prioritize matching target application package variants (`KNOWN_TIKTOK_PACKAGES`) over system overlays (`StatusBar`, `com.android.systemui`). Under system overlays, allow popup recovery if UI XML confirms a known app screen while failing closed for third-party apps.
    - **In-Flight Session Diff Scoping for Review:** When changes have already been committed locally during the turn/session, never send bare `git diff HEAD` (which is empty); always diff against the session baseline commit (`git diff <base_commit> HEAD`) so Plan-Review receives the complete candidate code.
    - **Exact Type Check for Return Codes (Bool vs Int Subclass):** In Python, `bool` is an `int` subclass (`issubclass(bool, int) is True`), so `isinstance(val, int)` matches `False`, and `False == 0` evaluates `True`. When validating ADB/transport exit codes, strictly use `type(val) is int and val == 0` or `type(res.ok) is bool and res.ok is True` to prevent unverified boolean/mock transport results from passing fail-closed checks.
    - **Immutable XML Element Inspection & UIElement Wrappers:** Detectors must never mutate parsed `ET.Element` nodes (e.g., adding `__ignored_subtree__` to `node.attrib`). Note that `iter_elements(root)` creates fresh `UIElement` wrapper objects, so `id(node)` on raw `ET.Element` will not match `id(wrapper)`; when filtering subtrees (e.g. captions/comments) traverse raw `ET.Element` directly. Also `UIElement.__init__` does not accept `center` as an argument (`center` is a computed property from `bounds`).
    - **Post-Condition Fail-Closed Verification on Dismissers:** A popup/overlay dismisser must NEVER return `dismissed=True` simply because the target overlay is no longer matching. It MUST verify: (1) hierarchy dump and parse succeed, (2) foreground package remains verified target app, (3) no transition to system dialog/launcher or sensitive screens (login, OTP, captcha, verification), and (4) the screen returned to a valid feed/home/target state (`classify_tiktok_screen(root)` non-manual-needed). Any unexpected transition or failed dump MUST fail closed (`dismissed=False`).
    - **Synchronous Selector and Popup_Type on Dismiss Success:** Every registry dismisser returning `PopupDismissResult(dismissed=True, ...)` MUST explicitly populate `selector={"action": "allowlist_dismiss", "popup_type": "<popup_name>"}`. Missing `selector` causes downstream callers (`_apply_popup_dismiss_result`) to receive `popup_type=None`, causing retry guards (`_is_allowed_popup_retry_allowed`) to treat successful dismisses as blocked (`manual-needed` / `known TikTok screen` freeze as seen in Case 67). Public dismissers (`dismiss_allowed_generic_popup`, `dismiss_any_popup`) must defensive-normalize `selector` if missing or non-dict.
    - **Display Name Exclusion from Switcher Anchors:** When detecting profile header anchors for account switching (`find_switcher_anchor`, `_find_sticky_profile_header`), explicitly exclude display-name node resource IDs (`:id/pkh`, `:id/pke`, `:id/pau`, `:id/s9b`, `tv_content_name`). On new accounts lacking `@username` headers, tapping a display name opens the Edit Name Subpage overlay ("Thêm tên bạn mong muốn") with soft keyboard, blocking the account switcher.
    - **Multiprocess Subprocess Fixtures on Windows:** When authoring concurrent multiprocess tests (`subprocess.Popen` running scripts written to `tmp_path`), always normalize all interpolated paths with `.replace('\\', '/')` and explicitly inject `sys.path.insert(0, ...)` for both `automation-core` and consumer repo roots to ensure child processes never fail with unhandled `ModuleNotFoundError` or backslash escaping bugs.
    - **Dynamic Resolution for Modal Bottom Sheet Bounds:** Never hard-code modal coordinate thresholds (e.g. `bounds.top >= 1650` or `c_bounds[1] >= 600`). Compute screen dimensions dynamically from root bounds (`screen_h = root_b[3] - root_b[1]`, `min_modal_y = int(screen_h * 0.25)`) to support varying screen resolutions.
    - **Bounded Modal Container Enforcement:** Multi-marker popup detectors must verify that candidate labels belong to a common bounded modal container (`c_bounds[1] >= min_modal_y` and not the full-screen root `[0,0,W,H]`), preventing disconnected option labels scattered across the feed from triggering false-positive `KEYCODE_BACK` dismissal.
    - **UiAutomator XML Attribute Access:** Standard `xml.etree.ElementTree.Element` nodes in UiAutomator dumps store strings in attributes (`node.attrib.get("text")` and `node.attrib.get("content-desc")`), not element attributes (`node.content_desc` raises `AttributeError`). Always use `.attrib.get(...)` with fallback to `getattr(node, "text", "")`.
    - **Dynamic Resolution Call Assertion:** When handlers query `wm size` or screen dimensions dynamically prior to an action, use `mock.adb.shell.assert_any_call(...)` instead of `assert_called_once_with(...)` to account for preceding dimension probe commands.
    - **Overlay Fail-Closed Scope:** Detectors must never accept OCR alone without validating target package ownership in XML; dismissers must verify target package foreground focus both before and after actions, failing closed if third-party/system/permission dialogs appear.
    - **Document Gate Scope Fidelity:** Never document fixes or test passes in `docs/farm-automation-cases.md` (alias `docs/uiautomator.md`) for external repos (e.g. `automation-core`) unless those changes are actually committed in the active candidate.
    - **Redundant Bounds & Tautology Pitfall:** When filtering parsed nodes by coordinate bounds, use clean expressions like `node.get("bounds") and node["bounds"][1] < 1200`. Avoid tautological boolean constructs such as `node.get("bounds") and (not node.get("bounds") or ...)` which cause plan-review rejection.
    - **Defense-in-Depth Coordinate Bounding on Whitelisted Action Nodes:** When selecting action nodes via helper predicates (`_is_profile_action_node`), also enforce coordinate bounds (`y < 1200`) as defense-in-depth against suggested-account cards or nested items that share the same resource-id.
    - **Fail-Closed Ancestor Traversal Continuity:** When resolving clickable ancestors for label nodes in UiAutomator dumps, unclickable leaf nodes without clickable parents must trigger `continue` (skipping only that unclickable node) rather than `return []` (which aborts the entire candidate list).
    - **Namespace Import Verification:** Verify `import xml.etree.ElementTree as ET` exists in all modules calling `ET.fromstring(...)` to prevent latent `NameError` from being silently swallowed by generic exception boundaries.
    - **Strict Fail-Closed Package Override Boundaries in Safety Checks:** In safety check flows (`safety_check`), overriding `focus_pkg = expected` under system overlays (`com.android.systemui`, `android`) or missing focus MUST be strictly gated by verified recognized screens (`is_known_tiktok_screen` matching explicit known screens / reasons). NEVER use broad negative conditions (e.g. `not _is_google_or_account_package`) as a fallback seam, which turns safety checks into fail-open and triggers Plan-Review rejection.
    - **Fail-Closed Action Validation in Dismissers:** A popup/overlay dismisser must verify that at least one action (element tap, coordinate tap, or keyevent) actually executed successfully (`action_performed is True`). If no action capability is available or clicks fail, it must return `PopupDismissResult(dismissed=False, reason="no_action_capability_...")` instead of returning `dismissed=True` unconditionally (fail-open bug).
    - **Network Error Retry Feed Recovery:** On TikTok network-error/retry overlays ("Không có kết nối Internet", "Lỗi mạng", "Chạm để thử lại"), standard feed swipes do not reload videos; the handler must specifically tap the "Thử lại" / "Chạm để thử lại" button node (or fallback reload coordinates) while enforcing negative exclusions for login/captcha/OTP.
    - **Current vs Historical Activity Focus Tokens in Regex:** When expanding window focus regular expressions (`FOCUS_RE`), include only current/active foreground window states (`mFocusedWindow`, `mTopFullscreenOpaqueWindowState`, `mResumedActivity`). NEVER add `mLastResumedActivity` as it references the previously active activity and produces stale package attribution.
    - **Dual Attribute Access in XML Element Filtering:** In UI element filters (e.g. `_is_account_switcher_sheet`), check both dict-based `.attrib.get(...)` and object attribute `getattr(...)` (e.g. `res_id = getattr(element, "resource_id", "") or (element.attrib.get("resource-id") if hasattr(element, "attrib") else "")`) to prevent filters from silently failing when inspecting raw `ET.Element` vs wrapped `UIElement` objects.
    - **Playwright & Consumer Import Safety Invariants for Review (2026-09-06)**:
      1. **Playwright `locator.get_attribute(name)`**: KHÔNG truyền keyword argument `timeout=...` (e.g. `get_attribute("href", timeout=5000)`), vì Playwright Python `Locator.get_attribute()` không nhận timeout kwarg trong nhiều phiên bản và sẽ gây `TypeError` lúc runtime.
      2. **Playwright Event Listener Cleanup**: Trong Playwright Python sync API, `Page` object có thể thiếu `remove_listener` hoặc `off` tùy phiên bản. Khối `finally` dọn dẹp listener BẮT BUỘC dùng duck-typing kiểm tra `hasattr(page, fn_name)` trước khi gọi:
         ```python
         finally:
             for fn_name in ["remove_listener", "off"]:
                 for evt, handler in [("request", on_request), ("response", on_response)]:
                     if hasattr(page, fn_name):
                         try: getattr(page, fn_name)(evt, handler)
                         except Exception: pass
         ```
      3. **Unguarded Top-Level Import in Consumer Scripts**: Khi tích hợp module hook mới vào các runner batch (như `run_batch_turn2_gmails.py`), TUYỆT ĐỐI CẤM import trần ở top-level (`from hot_session_oauth import trigger_hot_session_oauth`). Nếu module mới thiếu thư viện hoặc lỗi cú pháp, toàn bộ batch runner sẽ crash ngay khi khởi động. BẮT BUỘC dùng guard:
         ```python
         try:
             from hot_session_oauth import trigger_hot_session_oauth
         except Exception:
             trigger_hot_session_oauth = None
         ```
         và tại call-site kiểm tra `if trigger_hot_session_oauth:`.
      4. **Destructive Device Lock Defense**: Tuyệt đối KHÔNG dùng no-op context manager (`yield`) làm fallback cho `acquire_device_lock` khi thực hiện các tác vụ can thiệp phần cứng hoặc xóa dữ liệu (gỡ account, xóa cache, reboot). Nếu thiếu module lock, BẮT BUỘC `raise ImportError` để chặn đứng tiến trình.
      5. **Subprocess UTF-8 Output Decoding on Windows**: Trên Windows, `subprocess.run(..., text=True)` mặc định sử dụng ANSI codepage của hệ điều hành (`cp1252`), làm crash hoặc corrupt khi decode XML tiếng Việt từ ADB. BẮT BUỘC truyền `encoding="utf-8", errors="replace"`.
      6. **Re-entrant Loop Cap for CAPTCHA/OAuth**: Mọi vòng lặp giải CAPTCHA hoặc xử lý challenge trong luồng OAuth bắt buộc có biến đếm số lần thử tối đa (`recaptcha_attempts < 2`), tránh spin loop vô hạn đốt hết timeout phiên.
    - **Samsung Stay-On Anti-Lock Multi-Layer Configuration:** To prevent Samsung devices from locking during micro-drops in USB power, configure `svc power stayon true`, `settings put global stay_on_while_plugged_in 7` (all power sources: AC+USB+Wireless), `settings put system screen_off_timeout 1800000`, `settings put secure lockscreen.disabled 1`, `settings put secure lock_screen_lock_after_timeout 2147483647`, and `locksettings set-disabled true` in shared device prep (`automation-core/device.py` and `device_prepare.py`).
    - **Ordered Keyguard & Power-Overlay Dismissal:** Under `locked_or_secure` states, always send `input keyevent 4` (Back-first) to dismiss GemPhoneFarm power-menu overlays before attempting `wm dismiss-keyguard` and `input keyevent 82` (unlock). Do not fire `keyevent 82` unconditionally on waking an already-unlocked screen to prevent opening OneUI app switchers.
    - **Account Switcher Flexible Matching & Inner TextView Tap Target:** When matching account identities where display names differ from handles, pass normalized strings (`_normalize(val).lstrip("@")`) to `matches_switcher_identity`, prioritize exact tappable nodes over fuzzy matches, and ensure tap bounds isolate the inner TextView rather than full-width container centers.
    - **Photo-Mode Feed Detail Controls & Dead-Code Subsumption:** When expanding feed controls for photo-mode or novel post types: (1) separate markers into independent categories (`repost_marker`, `photo_marker`) and never overlap substrings (e.g. "đăng lại" in both) to avoid artificial double-counting; (2) use strict matching (`value in {"ảnh", "photo"}` or prefix `ảnh,`/`photo,`) rather than substring `in value` on common Vietnamese words; (3) avoid ambiguous substrings (e.g. bare "lưu" or "yêu thích"); (4) when adding combined verification conditions before an old `return bool(...)`, remove the redundant old return to avoid dead-code subsumption; (5) ensure Case documentation count and marker definitions match code 100%.
    - **Concurrent Background Writer Stash & Rebase Pattern:** When concurrent background daemons (e.g. reaper locks or feed workers) touch working-tree files during Gate 3 rebase, `git pull --rebase` will be blocked by unstaged changes. Use `git stash push --include-untracked -m "stash_concurrent_worker_edits"` to isolate them cleanly, rebase and push, then immediately `git stash pop` to restore concurrent worker runtime state without losing work.
    - **Git Fsmonitor Daemon Lock & Timeout Resolution on Windows:** On Windows Git-Bash environments, `git add` or `git commit` can hang indefinitely or time out after 10-15s if a background `git fsmonitor--daemon` holds `.git/index.lock` or deadlocks IPC threads. To resolve: inspect processes for `git fsmonitor--daemon`, kill it with `taskkill -F -PID <pid>` (or `git fsmonitor--daemon stop`), remove stale `.git/index.lock`, and pass `-c core.fsmonitor=false` to git commands to prevent further hangs.
    - **Focused Package Recovery Under Floating Widgets & Transition Animation:** When floating overlays (e.g. "Nhấp ngay có thưởng", rewards, floating PIP) or animation transitions cause `dumpsys window` to drop `mCurrentFocus` (`focus_pkg is None`), do not fail closed prematurely with `SAFETY_FAILED: focused package unavailable`. Verify UI XML (`raw_xml` / parsed root); if XML contains active TikTok package identifiers (`KNOWN_TIKTOK_PACKAGES`) or core feed markers ("Đề xuất", "Bạn bè", "Following", "For You"), recover `focus_pkg = expected` with a warning log to allow feed session continuity.
    - **Follow-Friends Reason Normalization & UI vs Hardware Back Distinction:** Khi triển khai navigation fallback cho các popup dạng kết bạn/gợi ý (`follow_friends_suggestion_popup`), phân biệt chặt chẽ `reason` giữa việc tap UI navigation back button (`followed_{count}_friends_and_dismissed`) và việc gửi phím cứng `send_device_back_key` (`followed_{count}_friends_and_dismissed_via_back`). Không gắn đuôi `_via_back` cho nhánh tap UI vì sẽ làm gãy unit test Gate 2 (`test_dismiss_follow_friends_button_with_low_x_and_back_target`). Đồng thời, luôn bổ sung Profile Guard (`_is_main_feed_or_profile_screen`) để tránh detector nhận diện nhầm các nhãn tĩnh ("Tìm bạn bè", "Mời bạn bè") trên trang Profile làm kẹt flow lướt feed.
    - **External Scripting for Gate 1 & Gate 2 via closeout_gate.py:** Không bao giờ tạo file script test review tạm (`tmp_run_review.py`) trực tiếp trong working tree của git repo vì sẽ gây untracked file và làm sai lệch git status; cũng CẤM TUYỆT ĐỐI nhúng git diff vào inline bash `python -c "..."` hoặc bash heredoc (gây lỗi bash escaping ký tự cú pháp). BẮT BUỘC sử dụng công cụ đóng gói chuẩn hóa duy nhất `python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/<repo>" --base origin/main` để tự động hóa toàn bộ: dọn stale index.lock an toàn (kiểm tra psutil), trích xuất candidate diff ra file tạm (so với base origin/main..HEAD), tự cd vào repo root và chạy focused test < 90s, và gửi diff lên OmniRoute (:20129) model `review` với timeout 300s (đáp ứng model Opus 4.6 Thinking cần 60-180s mà không bị timeout hay probe cổng).
    - **Closeout_gate --input path form (Case 162, 13/09/2026):** Khi dùng `closeout_gate.py --input <diff_file>` thay vì `--repo`, BẮT BUỘC truyền path dạng Windows (`D:/Taadaa/tmp/xxx.diff`); path POSIX (`/d/Taadaa/...`) khiến gate báo `Input file not found` dù file tồn tại trên đĩa.
  - A reviewer timeout, empty response, malformed response, missing parseable verdict, or a background reviewer that has not returned yet is a **review-route failure**, not a rejection and not an approval. Immediately retry through a different independent reviewer route with a compact forced-output format (for example: `VERDICT: APPROVED|REJECTED|BLOCKED` plus one findings line). Dispatching a reviewer is not evidence of approval; do not commit or push until a valid verdict is obtained.
  - If a fallback reviewer also returns empty/malformed output, try one more independent route before declaring `BLOCKED_AT_REVIEW`; preserve the exact evidence (timeout/empty) in the final report.
- A reviewer may fix a small review finding only in an isolated copy/worktree and must return a patch. The coordinator independently checks and applies that patch; the reviewer does not commit or push.
- After merge/apply/rebase, review and test the exact final candidate before push. If the SHA or tree changes, repeat the gate.
- **Reject-Loop Freshness:** Sau mỗi lần sửa finding từ reviewer, vô hiệu hóa các bằng chứng review cũ, kiểm tra syntax (`py_compile`), chạy focused test suite, và chạy lại `closeout_gate.py --files <target_files>`. Không có trần cứng số vòng; áp dụng anti-spin và danh sách hard blocker của Remediation Loop v1.2.
- **Effective-route identity is part of verdict validity:** A response that says `VERDICT: APPROVED`/`REJECT` is not a valid plan-review result if the requested `plan-review`/`plan-review-hard` route was silently served by a different implementation model. Record both requested and effective model; if they differ without an explicitly supported route mapping, classify `BLOCKED_AT_REVIEW_ROUTE`, not reviewer approval/rejection, and do not use the content to authorize Git actions. A 200 response alone never proves the requested reviewer ran.
- **Candidate snapshot commands must use index-safe forms:** `git hash-object :path` is not a valid portable way to hash an index entry. Use `git ls-files -s -- <allowlist>` plus `git cat-file blob <INDEX_BLOB_SHA>` (or materialize `git write-tree`/`git archive`) and record the resulting tree/blob hashes. If a file is staged and also has unstaged edits (`MM`), the staged candidate and working tree are different byte sets; review/test/commit only after explicitly choosing and freezing one set.
- **Closeout scope is current-session-only:** derive the exact allowlist from the user's current request and the session change ledger. Historical remediation candidates, prior-session errors, worker handoffs, old rejected diffs, and newly discovered adjacent findings are evidence to report—not implementation scope. If the small change being closed cannot be identified without guessing, ask one narrow scope question or report `BLOCKED_AT_SCOPE_RECONCILIATION`; do not dispatch workers or patch broadly.
- **One writer and no scope drift:** during closeout, use at most one owned writer for the candidate. Stop/reconcile any worker before review or Git actions. Never dispatch multiple workers against the same shared worktree, and never continue editing a scoped file after a concurrent writer or commit changes it until the exact candidate is rebuilt and re-reviewed.
- **Review-model evidence gate:** A worker/subagent review is diagnostic input only. The closeout gate requires a parseable verdict from the configured `plan-review`/`plan-review-hard` model over the configured transport (normally 9Router HTTP). Record the actual model/route, candidate hash or staged tree, verdict, and route errors. Never claim “review đã gọi plan-review” merely because a delegation completed, and never convert a 200 response, passing tests, or a worker `APPROVED` into model approval.
- **Audit-route/model separation (user correction):** For Taadaa lock/recovery work, implementation workers may use Luna, but the review gate must call the named `plan-review` or `plan-review-hard` model through 9Router. Never substitute the current session model or a worker model (especially `gpt-5.6-luna`) as an auditor. If the named route fails, record the exact transport/model error, then use the configured audit fallback in the routing policy; do not silently downgrade to an implementation model. Bind the verdict to the exact staged bytes and report the route explicitly.
- **Reject-loop freshness:** After every remediation edit, invalidate all prior review and test evidence. Re-read the full scoped files, compare hashes, rebuild the exact staged candidate, run focused tests on that candidate, then issue a fresh review request. Do not keep polling while no valid review request is in flight; do not commit a candidate whose latest bytes were never reviewed.
- **Review-route fallback:** If the primary AG review route is unavailable, record the exact auth/transport failure and use the configured independent fallback reviewer without silently presenting it as AG. If every allowed route fails to return a parseable verdict, stop at `BLOCKED_AT_REVIEW`; do not commit/push or soften the result into “chốt xong”.
- If review or test hits a hard blocker (Remediation Loop v1.2 list) that cannot be resolved, push is forbidden; report `BLOCKED_AT_<STEP>` with real evidence. A reviewer score < 85 alone is never "cannot be resolved". Any commit (including checkpoint) requires APPROVED + score >= 85 + exit 0 unless the user explicitly authorizes a checkpoint commit.
- Focused tests may be sufficient for push when they pass and any full-suite failures are proven baseline or environment failures, not new regressions. Report those classifications explicitly.
- When removing a merged branch/worktree, require `absorbed`/`superseded` evidence **after integration and before removal**, never before the merge.

For authorized dirty-worktree scope expansion and downloader-only canaries, follow [`references/scope-expanded-downloader-closeout.md`](references/scope-expanded-downloader-closeout.md). For repairing a rejected review before re-review, follow [`references/review-rejection-repair.md`](references/review-rejection-repair.md). For preserving an in-scope dirty worktree while resolving a live target and running Gate 0, see [`references/closeout-candidate-and-canary.md`](references/closeout-candidate-and-canary.md). For code-only/general-flow tasks without an explicit live target or qualifying incident evidence, use focused semantic verification (tests/compile/static checks), not a device canary. A fresh reviewer verdict is required after any candidate fix.

## Required workflow

### 0. Live Canary Test (chỉ khi task có target live hoặc incident evidence)

- Chỉ chạy live canary nếu task hiện tại nêu machine/row/serial/device target cụ thể, user yêu cầu kiểm chứng máy thật, hoặc incident evidence do user cung cấp ở đầu session (ảnh/screenshot/alert/log) xác định được máy/target và lỗi runtime cụ thể đang debug.
- Với code-only/general-flow task không có target live hoặc incident evidence, ghi `CANARY_NOT_APPLICABLE` và tiếp tục Gate 0.5.

### 0.5. Cập nhật & Rà Soát Case Fix & Anti-Pattern Catalog (BẮT BUỘC cho Farm Automation)

- **Quy tắc đọc trước khi sửa (Pre-read Catalog):** Trước khi sửa bất kỳ bug nào trên farm (UI, selector, navigation, recovery), BẮT BUỘC phải đọc kỹ `docs/farm-automation-cases.md` (hoặc `docs/uiautomator.md`) và `AGENTS.md` trước để đối chiếu xem lỗi hiện tại có thuộc case nào đã xử lý hay chưa, tránh viết đè/trùng lặp code hoặc phá vỡ các case cũ.
- **Vị trí tài liệu:** `docs/farm-automation-cases.md` (alias `docs/uiautomator.md`).
- **Phạm vi bắt buộc:** MỌI task có sửa code/logic liên quan đến farm automation (UI, Popup, Keyboard, Switcher, Cron, Sync, Cohort, Device Lock, ADB, Follow, Upload, Reg, Mail...).
- **Nội dung yêu cầu:** Ghi rõ (1) Vị trí áp dụng, (2) Nguyên nhân gây lỗi / Anti-Pattern, (3) Giải pháp chuẩn / Case Fix thực tế, (4) Kiểm tra không trùng lặp với các case trước đó.
- **Quy tắc chặn Gate:** Nếu phiên có sửa logic farm mà CHƯA có file diff cập nhật `docs/farm-automation-cases.md` $\rightarrow$ **CẤM Commit và CẤM Push**, dừng ngay ở Gate 0.5.
- **Quy tắc giữ nguyên backtick khi ghi docs:** CẤM dùng bash heredoc / `python -c` qua terminal để append `docs/farm-automation-cases.md` vì bash strip toàn bộ backtick/code token (Case 98 tại bd6b78f mất serial/nick/tên hàm). BẮT BUỘC dùng `patch` tool (mode replace) rồi verify bằng `tail` + `git diff`.
- **Quy tắc Báo Cáo Chốt Phiên:** Khi báo cáo chốt phiên, BẮT BUỘC phải nêu rõ đích danh số Case vừa ghi nhận / cập nhật (ví dụ: Case 56, Case 57) trong `docs/farm-automation-cases.md` (hoặc nêu rõ số Case hiện tại trong catalog nếu phiên không thêm case mới).

### 1. Freeze the exact scope

Before mutating Git state, record:

- repository root, current branch, actual upstream remote/branch, and `HEAD`;
- `git status --short --untracked-files=all`;
- worktree/merge/conflict state;
- the exact production, rule, and test allowlist;
- foreign or concurrent-owned paths that must remain untouched.

Do not use `git add .`, `git add -A`, broad globs, or an inferred “all changed files” scope. Never read, print, stage, or commit secrets, credentials, OAuth state, workbooks, local session state, logs, caches, backups, or generated runtime artifacts. For cross-repository rule propagation, use the inventory/allowlist/EOL procedure in `references/all-repo-rule-propagation.md`.

A dirty path outside the allowlist is preserved, not reset, stashed, cleaned, or absorbed into the candidate. It is **not a blocker**: do not wait on unrelated test/build processes, inspect unrelated failures, or let foreign paths widen the candidate. Classify those paths as `OUT_OF_SCOPE` and continue. A staged/unstaged path inside the allowlist is also not automatically a conflict; staged state, an old mtime, or a non-empty status only becomes a stop condition when the requested hunk is actively owned, content changes during the current ownership window, or the candidate cannot be separated safely. If an active writer owns a path or overlapping region in the requested scope, stop and report the ownership conflict rather than clobbering it.

**Dirty-tree classification checkpoint:** before each review/commit boundary, report three separate sets: `unrelated dirty preserved`, `in-scope candidate`, and `proven overlapping conflict`. Never collapse them into one generic `BLOCKED` state. `SCOPE_DRIFT` means this agent/worker changed outside its own allowlist; it does not mean pre-existing foreign dirt exists.

**Concurrent-writer freeze gate:** record `HEAD`, branch, status, and the staged candidate before review. Re-check `HEAD`, `git status --porcelain=v2 --branch`, and staged paths immediately before every review, commit, rebase, and push boundary. If another process commits, changes the branch tip, changes a scoped file, or introduces a staged/unstaged path while closeout is in progress, invalidate all previous review/test evidence and stop for reconciliation. Do not continue patching against the old candidate, do not push a local branch that is ahead with unreviewed mixed-scope commits, and do not claim exact-scope closeout when the requested fix is only embedded inside a broad concurrent commit. Preserve the new dirty state untouched and report `BLOCKED_AT_RECONCILIATION` with the old/new SHAs and paths.

**Candidate-byte reconciliation gate:** a reviewer approval and test result bind to exact bytes, not merely to the same filenames or unchanged `HEAD`. Immediately before staging, hash or otherwise compare every scoped candidate file against the bytes supplied to the reviewer. If any scoped file differs—even when `HEAD == origin/<branch>`—invalidate the approval and prior tests, re-read the current diff, reconstruct the candidate from current `HEAD` plus only the intended hunks, and obtain a fresh review. Never whole-file-stage a mixed dirty file just to recover an approved change; preserve unrelated same-file hunks unstaged. The reusable reconstruction and verification recipe is in `references/candidate-byte-reconciliation.md`.

Allowlists are file-granular, but candidates can be hunk-granular. When a file inside the requested scope mixes candidate hunks with unrelated dirty hunks, do not treat the file as fully owned: name the split in the review findings, keep the unrelated hunks preserved, and stage with hunk-level selection (`git add -p` or equivalent) — never a whole-file add. For read-only review requests (no commit authorized), prove zero mutation: snapshot `git status --porcelain` before and after and require identical output; prefer artifact-free checks (AST parse, `python -B`) over commands that write bytecode or caches into the worktree.

### Route-scoped disable closeouts

For a disable/fail-closed fix that names one alert, trigger, or route, treat the route boundary as semantic scope—not merely a list of files:

- Name the producer route, the exact side effect to block, and the sibling routes that must remain live. A producer guard that blocks Farm Alerts' recovery `Popen` while preserving alert delivery is in scope; an unconditional early return in a shared consumer entrypoint is not, even if it stops the symptom.
- Before touching a consumer, inventory direct callers and prove how the target route is distinguished. If it cannot be distinguished safely, keep the fix at the producer seam or add an explicit invocation marker/adapter plus a focused preservation test; never blanket-disable the consumer.
- When source and installed/runtime copies may differ, inspect the actual production interpreter/module path and compare raw file hashes. A runtime hotfix must be backed up outside the repository and reconciled with the committed source; stage and commit only the explicit source/test allowlist.
- A reviewer verdict binds to the exact candidate bytes. Any edit, reversion, or scope change invalidates it: re-read the full affected files, confirm byte identity for reverted paths, rerun the focused gate, and obtain a fresh verdict. Do not carry a rejection or approval from a stale diff into commit/push.

See `references/route-scoped-disable-closeout.md` for the producer/consumer matrix, runtime-provenance checks, and the clean-worktree rebase recipe.

### 2. Inspect and independently review the candidate

- **Canary Pass = Code Freeze & Bouncer Review (Chống dây dưa 3 tiếng):** Khi Live Canary trên thiết bị thật đã PASS (video đã đăng / log xác nhận / artifact hợp lệ), toàn bộ code logic lập tức chuyển sang trạng thái ĐÓNG BĂNG (Code Freeze). Lúc này Reviewer đóng vai trò Bouncer kiểm tra nhị phân (Đúng root cause ban đầu? Canary pass? Không crash máy khác?). CẤM TUYỆT ĐỐI sửa thêm các lỗi ngoài scope do Reviewer bới thêm (như draft cleanup, hashtag threshold, style) trong phiên này; đẩy vào ticket P3 riêng và chốt phiên ngay.

Review the exact current diff and allowlist with the correct route:

- `plan-review` for ordinary/single-repository work;
- `plan-review-hard` for core, multi-repository, state, lock, or recovery work.

The HTTP request must use `stream: false`, `tools: []`, and `tool_choice: "none"`; `Authorization: Bearer ...` is an HTTP header, not request-body content; include the required `reasoning_effort`. Pass review prompts through stdin or a file, never by unsafe shell interpolation.
- **Diff Scope for Multi-Repo / In-Flight Commits:** Khi review diff đa repo hoặc diff đã có commit dở dang trong phiên, so sánh diff với commit base đầu phiên (`git diff <base_commit> HEAD` hoặc `git diff origin/master HEAD`) thay vì chỉ `git diff HEAD` (vốn rỗng nếu đã commit local), để reviewer nhìn thấy đầy đủ toàn bộ candidate code (tránh false-rejection "diff is empty").
- **OmniRoute (:20129) Plan-Review Dispatch:** Khi gọi qua OmniRoute, sử dụng `model: review`, đọc `OMNIROUTE_BASE_URL` và `OMNIROUTE_API_KEY` từ `C:/Users/Kibe/AppData/Local/hermes/.env`. BẮT BUỘC chuẩn hóa URL: nếu `base_url.endswith('/v1')` thì gọi `/chat/completions` (tránh bị lỗi lặp path `/v1/v1/chat/completions`). Đặt `tools: []` và `tool_choice: "none"` trong payload.
- **PowerShell Canary Isolation (CẤM dot-source script batch PS1):** Khi viết canary test cho hàm PowerShell trong các script chạy batch (như `run_parallel.ps1`, `run_all.ps1`), CẤM TUYỆT ĐỐI dot-source file (`. 'script.ps1'`) vì sẽ thực thi toàn bộ logic top-level và vô tình kích hoạt các worker chạy máy thật. BẮT BUỘC dùng PowerShell AST Parser (`[System.Management.Automation.Language.Parser]::ParseFile`) bóc tách riêng function AST cần test rồi `Invoke-Expression` trong isolated session.
- **Multi-Repo Release Sync (Core + Consumer):** Khi sửa đổi detector/rules tại `automation-core` kèm logic tích hợp tại consumer repo (ví dụ `tiktok-luot nuoi acc`), BẮT BUỘC thực hiện tuần tự: (1) Test & commit `automation-core`, (2) Test & commit consumer repo, (3) Rebase & push cả 2 repo, (4) Verify `git ls-remote` trên cả 2 repo. Tuyệt đối không để sót commit ở repo core làm hỏng build/runtime của farm. Khi chốt phiên các tác vụ consumer repo, luôn chạy `git -C "D:/Taadaa/automation-core" status --short` để rà soát dirty changes trên repo core (như startup, device prep, lock), tránh tình trạng consumer đã commit/push nhưng core primitives bị bỏ quên ở uncommitted state.
- **Xác thực Git Diff Thật Của Worker Trước Khi Chốt Phiên:** Sau khi worker subagent báo cáo đã hoàn tất bước sửa code / canary test, Coordinator BẮT BUỘC dùng `git diff` kiểm tra xem file code đã thực sự được sửa đổi hay worker chỉ mới phân tích và chạy canary test trên thiết bị thật mà chưa áp code.
- **Vòng lặp tự sửa lỗi khi REJECT (không trần cứng — xem Remediation Loop v1.2):** Khi reviewer trả về `REJECTED` hoặc score < 85, Coordinator BẮT BUỘC đọc `key_findings`/`judge_notes`, phân loại finding (syntax, fail-closed, scoping, timeout, regression, thiếu context), lập Patch Contract, dispatch Worker/Claude CLI theo quyền đã cấp, chạy lại focused tests và chạy lại `closeout_gate.py --files ...` cho đến khi APPROVED + >= 85 + exit 0. CẤM báo `BLOCKED_AT_REVIEW` chỉ vì điểm thấp (kể cả sau nhiều vòng); chỉ dừng khi gặp hard blocker thật kèm evidence.
- **Sanitized Passphrase & Hardware PII in Config/Docs Commits (Trừ Repo Cá Nhân Chứa Full Config):** Khi commit tài liệu hoặc cấu hình mạng (Wi-Fi, router, proxy) theo yêu cầu lưu trữ của user, TUYỆT ĐỐI KHÔNG commit mật khẩu plaintext vào git và CẤM nhúng mật khẩu thực vào prompt review nếu là repo chia sẻ/public. **TUY NHIÊN (User Correction 13/09/2026):** Đối với các repository cấu hình cá nhân nội bộ (như `thanhdatbui/AI-Tools`), khi user yêu cầu lưu backup cấu hình router (như `mikrotik_config_hardened_20260913.rsc`), **TUYỆT ĐỐI KHÔNG ĐƯỢC TỰ Ý LỌC (SANITIZE) THÀNH `***`**, vì việc lọc làm các máy trạm khác (máy admin) hoặc script phục hồi tự động không thể import restore được cấu hình hoạt động đầy đủ. Bắt buộc giữ 100% full raw export.
- **Review Diff Payload Completeness Invariant:** Khi gửi diff cho Plan-Review, BẮT BUỘC gửi đầy đủ file diff hoàn chỉnh của các file trong allowlist. Tuyệt đối CẤM cắt cụt diff bằng các lệnh slice thô bạo (như `[:20000]`) gây đứt gãy cú pháp hoặc làm reviewer báo lỗi thiếu code / syntax error giả.
- **Git Push & ls-remote Auth trên Windows:** Khi thực hiện `git push` hoặc `git ls-remote` trong môi trường Git-Bash Windows, sử dụng token xác thực trực tiếp từ `TOKEN=$(gh auth token)` qua URL `https://${TOKEN}@github.com/<org>/<repo>.git` để tránh nghẽn / treo timeout bởi Git Credential Manager UI.

The reviewer must return a parseable verdict and findings. A reviewer may make a small correction only in an isolated copy/worktree, then return a patch. The coordinator must inspect the patch, apply only the approved exact scope, and rerun the relevant checks. No reviewer may commit or push.

Do not fabricate `APPROVED`. An unavailable or malformed review is a review failure, not an approval.

### 3. Integrate before the final gate

If merge/apply is required, verify ownership, allowlist, branch mapping, and conflict state first. Merge only owned branches/worktrees. Do not require `absorbed`/`superseded` before merging; that evidence is checked only after integration and before any requested branch/worktree removal.

After integration, stage only the exact allowlist and create a local checkpoint commit if appropriate. Verify `git show --name-status` contains only the allowlist. A checkpoint commit is not a release approval.

### 4. Commit exact scope before Pull & Rebase

**User correction (mandatory): pull/rebase before push is part of execution, not a reason to stop.** After closeout approval, fetch the remote, record ahead/behind and dirty paths, then pull/rebase or merge as required before pushing. Re-run focused verification and bind the APPROVED review to the post-rebase diff. If push times out, verify with `git ls-remote` plus local HEAD/remote refs before reporting failure; never infer push status from timeout alone. Preserve unrelated dirty paths with explicit allowlists/autostash and never force-push unless explicitly directed.

Khi làm việc trong môi trường đa máy (2+ PC dùng chung repo), thứ tự chuẩn là:
1. **Commit local trước:** Đóng băng các thay đổi và test đã pass vào commit local (`git commit -m "..."`), tuyệt đối không pull khi working tree chưa commit sạch phần cho phép để tránh conflict/mất code.
- **CẤM TUYỆT ĐỐI `git commit` thiếu cờ `-m` (Bẫy Notepad / Editor Interactive Lock trên Windows)**:
  - Khi chạy lệnh commit trên môi trường Windows (Git-Bash / MSYS), nếu thiếu cờ message (`-m "..."`), Git sẽ tự động mở trình soạn thảo đồ họa (`notepad.exe .git/COMMIT_EDITMSG`) trong tiến trình ngầm.
  - Hậu quả: Tiến trình Notepad bị treo vô hạn trong background, giữ khóa cứng file `.git/index.lock` (`fatal: Unable to create '.git/index.lock': File exists`), làm đóng băng toàn bộ các tiến trình worker, cron và làm tê liệt quy trình chốt phiên.
  - Khắc phục: Dùng `psutil` tìm và kill triệt để các PID `notepad.exe` trỏ vào `COMMIT_EDITMSG` và dọn file `.git/index.lock` stale. Luôn bắt buộc truyền cờ `-m` cho mọi lệnh `git commit`.
- **CẤM TUYỆT ĐỐI `git rebase --continue` thiếu `GIT_EDITOR=true` (Interactive Editor Freeze trên Windows MSYS)**:
  - Khi chạy `git rebase --continue` hoặc `git commit --amend`, Git tự động gọi `git commit -F ... -e` để mở trình soạn thảo chỉnh sửa commit message.
  - Trong subshell bash không có TTY tương tác, Git sẽ bị block vĩnh viễn hoặc dính timeout 15-30s.
  - Bắt buộc luôn truyền `GIT_EDITOR=true GIT_SEQUENCE_EDITOR=true` (ví dụ `GIT_EDITOR=true git -c core.fsmonitor=false rebase --continue`) hoặc cờ `--no-edit`.
- **Quy trình Fetch & Rebase an toàn với URL có Auth Token**:
  - Khi remote yêu cầu token GitHub (`gh auth token`), lệnh `git pull --rebase <auth_url> <branch>` dễ gây lỗi `fatal: Cannot rebase onto multiple branches`.
  - Quy trình chuẩn: (1) `git fetch <auth_url> <branch>:refs/remotes/origin/<branch>`, (2) `git rebase origin/<branch>`, (3) `git push <auth_url> HEAD:<branch>`.

- **CẤM TUYỆT ĐỐI `git commit --amend` sau khi commit đã push lên remote**:
   - Nếu commit trước đó đã được push lên `origin/<branch>`, việc chạy `git commit --amend` sẽ tạo SHA mới tại local, dẫn đến trạng thái phân nhánh (`Your branch and 'origin/master' have diverged, and have 1 and 1 different commits each`).
   - Mọi thay đổi bổ sung (như cập nhật docs Gate 0.5, test mới, fix thêm) BẮT BUỘC phải tạo commit mới (`git commit -m "..."`) thay vì amend.
   - **Xử lý sự cố khi lỡ amend commit đã push:** Nếu lỡ amend và bị diverged, KHÔNG được `git push --force`. Cách khắc phục an toàn là chạy `git reset --soft origin/<branch>` để kéo `HEAD` về khớp với remote mà vẫn giữ nguyên các thay đổi mới trong staging, sau đó tạo commit mới cho các thay đổi đó rồi `git push`.
- **Xử lý xung đột số Case khi Rebase `docs/farm-automation-cases.md`**:
  - Khi cả nhánh local và upstream remote đều commit thêm case mới cùng số thứ tự (ví dụ cùng ghi nhận `Case REG-12`), lệnh `git pull --rebase` sẽ bị conflict tại file catalog markdown.
  - Quy trình xử lý chuẩn: Giữ nguyên Case từ upstream, tịnh tiến số Case của local lên +1 (ví dụ đổi thành `Case REG-13`), giải quyết conflict, hoàn tất rebase (`GIT_EDITOR=true git rebase --continue`), chạy lại verification test độc lập, và dùng `git commit --amend -m "..."` để đồng bộ số Case trong commit message trước khi push lên remote (chỉ amend khi commit chưa từng được push).
- **OmniRoute Bearer Auth & Claude CLI Fallback Gate 1**:
  - Gọi OmniRoute `:20129` bắt buộc truyền header `Authorization: Bearer <OMNIROUTE_API_KEY>` từ `.env` (nếu thiếu header sẽ bị 401 Unauthorized hoặc timeout).
  - Nếu OmniRoute `:20129` gặp tình trạng upstream thinking quá lâu (>120s) hoặc timeout, fallback ngay sang Claude CLI Opus High native (`claude -p --model opus --effort high --append-system-prompt-file <prompt.txt>`) để lấy verdict độc lập có cấu trúc (`VERDICT: APPROVED | REJECTED`) mà không làm nghẽn tiến trình chốt phiên.
- **Tách riêng luồng công việc (Code-surgery vs Batch-job trước khi chốt phiên)**:
  - Khi phiên làm việc bao gồm cả Code-surgery (sửa hook/bug vài phút) và Batch-job (render/download hàng chục GB), BẮT BUỘC chốt phiên trọn vẹn phần code trước (`commit -> review -> rebase -> push`), sau đó mới khởi chạy Batch-job nền độc lập. CẤM gộp chung hoặc chờ batch job hoàn thành mới chốt phiên code.
3. **Xử lý dirty files ngoài allowlist trước khi pull:** Nếu working tree còn uncommitted changes hoặc untracked files ngoài allowlist mà `git pull --rebase` từ chối thực hiện, dùng `git stash push -m "unrelated-dirty"` để tạm cất các file ngoài scope, sau đó `git pull --rebase <remote> <branch>`, rồi `git stash pop` để khôi phục nguyên vẹn.
4. **Pull rebase sau:** Kéo commit mới nhất từ remote về và rebase commit local lên đầu (`git pull --rebase <upstream-remote> <upstream-branch>`).
5. Nếu sau rebase có commit mới từ remote kéo về, chạy lại quick test/compile để bảo đảm tính tương thích trước khi push.

### 5. Final review and verification on the exact candidate

Review and test the candidate **after** merge/apply/rebase and before push. The final candidate is the tree that will be pushed, not the pre-rebase diff.

Minimum evidence:

- if the final suite exposes legacy fixtures that mock `_capture_xml_text` without satisfying a newly enforced artifact-first validator, update the fixtures minimally (exact XML+screenshot artifact or a documented validator mock); never weaken production validation to preserve stale fixtures;
- **Untracked Scratch Test Artifacts Cleanup Gate**: Trước khi chạy test suite Gate 2 hoặc commit, BẮT BUỘC kiểm tra `git status` và dọn dẹp các file test nháp untracked (như `test_*_recovery.py` dở dang do worker/subagent bỏ lại nhưng mock sai attribute hoặc chưa hoàn thiện). Tuyệt đối không `git add` mù quáng các file test lỗi này vào commit làm gãy test suite chốt phiên.
- focused regression tests for the changed behavior;
- compile/typecheck/lint or equivalent checks where applicable;
- `git diff --check`;
- full-suite result when affordable, with baseline/environment failures separated from new regressions;
- final staged path allowlist and SHA/tree identity.

If review or test fails, do not push; enter the Remediation Loop v1.2 and report `BLOCKED_AT_<STEP>` only for a hard blocker, with the command and actual failure. Never downgrade a failed final gate to “done” because a wrapper exited zero.

### 6. Push explicitly, verify the remote, and synchronize local main worktree

Only after the final review/test gate passes:

```bash
git push <upstream-remote> HEAD:<upstream-branch>
git ls-remote <upstream-remote> <upstream-branch>
```

The `ls-remote` SHA must equal the pushed commit SHA. Never use force-push unless the user explicitly authorizes it.

**Local-Only Repos (No Remote Upstream Configured):**
Khi repo làm việc là repo local nội bộ (chưa add remote `origin`, ví dụ `git remote -v` rỗng như `D:\Taadaa\GPM auto`):
- Gate 3 (Rebase) và Gate 4 (Push) ghi nhận `REMOTE_NOT_CONFIGURED` / `LOCAL_ONLY_REPO`.
- Không cố gắng push hay coi thiếu remote là lỗi; verify commit an toàn tại local branch bằng `git log -n 1 --stat` và `git show --name-status`.
- Handoff commit SHA local trong báo cáo chốt phiên: `Remote: Local-only repo (<local_commit_sha>)`.

**Local Worktree Synchronization Gate:**
When a candidate was reviewed and pushed from an isolated temporary worktree or clone, the main worktree's local branch may remain behind `origin/<branch>`. Before declaring closeout complete:
1. Reconcile the local main branch: if the main worktree has unrelated dirty work, stash it (`git stash`), fast-forward/rebase local branch to the newly pushed remote commit (`git pull --rebase <upstream-remote> <branch>`), and pop stash (`git stash pop`).
2. Resolve any non-conflicting merge markers in preserved tests/files, mark resolved, and run test verification.
3. Verify `git rev-parse HEAD` on the local main branch equals `origin/<branch>` and matches the remote SHA. A session is fully closed only when both remote and local main checkout are synchronized.

### 7. Optional branch/worktree removal

Do not remove unrelated or concurrently owned branches/worktrees. If removal is part of the requested closeout, first verify the integrated work is `absorbed` or `superseded`, then remove only the owned target and verify the resulting worktree state.

## Final report contract

Keep the report concise and factual. Include:

1. trigger and exact repository/scope;
2. số Case cụ thể (Case N) vừa ghi nhận / cập nhật trong docs/farm-automation-cases.md (Gate 0.5);
3. independent review route and parseable verdict (PHẢI phản ánh chính xác 100% reviewer thực tế đã chạy trong phiên: OmniRoute :20129 hay Claude CLI native; CẤM TUYỆT ĐỐI copy-paste dòng review cũ từ phiên trước làm sai lệch tên model);
4. focused/full test evidence and any classified baseline/environment failures;
5. branch/upstream/rebase state;
6. exact committed paths and local commit SHA;
7. push result and verified remote SHA;
8. preserved outside-scope dirty paths or the exact `BLOCKED` gate.

Never claim `đã chốt`, `đã xong`, or `đã hoàn tất` from a summary alone. The final state is either verified closeout or `BLOCKED_AT_<STEP>`.

## Non-negotiable safety

- **THỰC HIỆN TRỰC TIẾP TẠI MAIN SESSION (CẤM delegate_task CHO CHỐT PHIÊN):** Khi nhận lệnh `chốt phiên`, Coordinator BẮT BUỘC thực thi trực tiếp toàn bộ quy trình 6 Gate (Gate 0 Canary -> Gate 0.5 Docs -> Gate 1 Plan-Review -> Gate 2 Test/Commit -> Gate 3 Rebase -> Gate 4 Push & Remote Verify) ngay tại main session. CẤM TUYỆT ĐỐI delegate_task hoặc spawn subagent cho khâu closeout. Delegate chốt phiên làm mất toàn bộ context của session, buộc subagent phải khởi tạo lại từ đầu tốn 70+ tool calls và kéo dài thời gian từ 1-2 phút lên hơn 30 phút.
- **Xử lý Stale Worker Phase trong farm_coordinator_phase.json**: Khi Coordinator chạy lệnh terminal mà bị chặn bởi `⛔ [FARM GUARD - PHASE: WORKER_RUNNING]` trong khi trên thực tế không còn subagent nào đang chạy, kiểm tra file `C:/Users/Kibe/AppData/Local/hermes/farm_coordinator_phase.json` và cập nhật các session có `phase: "WORKER_RUNNING"` về `"IDLE"` để giải phóng khóa Farm Guard lập tức.
- **Khôi phục File Code từ SQLite state.db khi bị xóa nhầm**: Nếu một file script/công cụ vừa tạo bị phiên khác hoặc cron dọn dẹp xóa mất (`can't open file ... [Errno 2] No such file or directory`), không viết lại từ đầu: truy vấn trực tiếp payload tool calls từ SQLite `C:/Users/Kibe/AppData/Local/hermes/state.db` (`SELECT tool_calls FROM messages WHERE tool_calls LIKE '%<filename>%' AND tool_calls LIKE '%write_file%' ORDER BY id DESC LIMIT 1`) để trích xuất và khôi phục nguyên vẹn 100% mã nguồn trong < 2 giây.
- **LIVE CANARY CÓ ĐIỀU KIỆN:** Chỉ bắt buộc chạy canary khi task hiện tại nêu machine/row/serial/device target cụ thể, user yêu cầu kiểm chứng máy thật, hoặc incident evidence do user cung cấp ở đầu session xác định machine/target cùng lỗi runtime cụ thể đang debug. Với code-only/general flow không có target live hoặc incident evidence, ghi `CANARY_NOT_APPLICABLE` và tiếp tục review/test/commit/rebase/push; không coi mọi ảnh TikTok/farm là target, không biến thiếu target thành blocker và không chạy mù.
- Never run live registration, device automation, workbook mutation, account actions, or lock deletion merely to close a coding session.
- Never reset, clean, stash, or stage unrelated dirty files.
- **CẤM TỰ Ý `git reset --hard` / `git clean -fd`:** Tuyệt đối không bao giờ tự ý chạy các lệnh destructive như `git reset --hard` hoặc `git clean -fd` trên live farm repos khi gặp trạng thái branch diverged hoặc rebase conflict. Luôn bảo toàn diff, kiểm tra `git diff origin/<branch> HEAD` và giải thích rõ nguyên nhân cho user thay vì phá hủy lịch sử/working tree.
- Never push an unreviewed or untested final candidate.
- Never treat HTTP 200, process exit 0, or a passing wrapper as an `APPROVED` verdict without reading and parsing the actual evidence.

## Verification checklist

### Case 131: AI Review Reject vì thiếu Context Vòng Đời (Lifecycle Blindness)
- **Hiện tượng**: Khi diff gửi sang OmniRoute AI Review (`closeout_gate.py`) chỉ chứa một đoạn code surgery nhỏ (ví dụ sửa `fill_password` thành `fill_password_and_login`), mô hình review có thể từ chối (REJECT) vì cho rằng "tại sao không thấy lưu password vào database/file ngay tại đây, nếu flow sau fail thì mất pass". Thực tế kiến trúc codebase xử lý lưu metadata/pass ở cuối lifecycle (hàm `ensure_profile_completed_and_track()`).
- **Giải pháp**:
  1. Khi gặp false rejection do thiếu bối cảnh kiến trúc/lifecycle, KHÔNG vội thêm code thừa phá vỡ kiến trúc.
  2. Dùng file text/script (`prepare_review.py`) chuẩn bị file prompt có kèm bối cảnh kiến trúc rõ ràng cho reviewer: giải thích rõ lifecycle, điểm persist dữ liệu, mục đích của patch và phạm vi unit test.
  3. Gửi qua `python D:/Taadaa/tools/closeout_gate.py --input <file_path>` để tránh bash string escaping/substitution lỗi ký tự đặc biệt.

- [ ] A close-session trigger (`chốt phiên`, `chốt`, `đóng phiên`, `xong phiên`, `kết thúc phiên`, `done`, `wrap up`) started the workflow.
- [ ] `closeout_gate.py` ran with `--files` scoped to the current candidate only (rule task and candidate-code task never mixed).
- [ ] REJECTED/<85 went through the Remediation Loop (findings read, Patch Contract, worker/Claude CLI, focused test, gate rerun) — not reported as BLOCKED for low score alone.
- [ ] Commit/push happened only after APPROVED + score >= 85 + exit 0; remote SHA verified.
- [ ] Progress questions did not trigger Git mutations.
- [ ] Automation task: Đã đọc trước file MD catalog và cập nhật Case Fix & Anti-Pattern tương ứng vào `docs/farm-automation-cases.md` (alias `docs/uiautomator.md`), đảm bảo không trùng lặp code/case cũ.
- [ ] Media Evidence Gate: MỌI task can thiệp máy farm (test, run, canary, recovery) BẮT BUỘC chụp screencap máy thật và gắn thẻ `MEDIA:<path>` trong tin nhắn báo cáo nghiệm thu. Thiếu `MEDIA:` = Không đạt Gate.
- [ ] Exact allowlist and outside-scope dirty paths were frozen.
- [ ] Correct independent review route was used.
- [ ] Any reviewer patch came from an isolated copy and was rechecked.
- [ ] Merge/apply/rebase happened before the final review/test gate.
- [ ] Focused tests passed; broader failures were classified honestly.
- [ ] Exact-scope checkpoint/commit was verified.
- [ ] Push used `HEAD:<actual-upstream-branch>`.
- [ ] Remote SHA matched local `HEAD`.
- [ ] Absorbed/superseded was checked before any branch/worktree removal.
