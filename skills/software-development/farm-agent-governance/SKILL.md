---
name: farm-agent-governance
description: Use when enforcing inter-session & anti-skip farm gates.
---

# Farm Agent Governance & Anti-Skip Hard Enforcement

## Overview

Kỷ luật điều phối và cưỡng chế kỹ thuật cứng (Hard Technical Enforcement) nhằm triệt tiêu vĩnh viễn hiện tượng **Context Amnesia** (mất trí nhớ giữa các phiên chat) và **Safe-Skip** (trốn việc, nuốt exception, fake pass) của AI Agents trên toàn bộ các repository farm.

References:
- `references/coordinator-device-lock-hard-guard-and-operator-discipline-20261009.md` — **[MỚI 09/10/2026 - COORDINATOR DEVICE-LOCK HARD GUARD]** Chấm dứt hành vi cao bồi can thiệp thiết bị trần không lock; bắt buộc bọc `operator_device_lock` cho mọi thao tác ADB mutating/chẩn đoán trên từng máy và cơ chế Hard Guard PreToolUse chặn đứng lệnh adb trần.
- `references/per-repo-telegram-alert-routing.md` — **[MỚI 09/10/2026 - PER-REPO TELEGRAM ALERT ROUTING]** Phân luồng cảnh báo Telegram chính xác theo từng repo/script (Tiktok Luot Nuoi Acc, Tiktok video, Tiktok add 2fa, v.v.), cấm đẩy tràn lan làm ô nhiễm nhóm Farm Alerts (-5373649734).
- `references/control-plane-gates-vs-passive-toolkits-20261006.md` — **[MỚI 06/10/2026 - CONTROL PLANE GATES VS PASSIVE TOOLKITS]** Phân định bản chất giữa "Toolkit bị động" (prompt dặn dò, LLM cãi cùn "do không yêu cầu kế thừa", review loop vô tận) vs "Deterministic Control Plane" (OS/subprocess hooks, O(1) Scope Lock, AST invariants, fail-fast circuit breakers, independent closeout scorecard >=85).
- `references/premature-resolution-and-physical-action-await-discipline-20261006.md` — **[MỚI 06/10/2026 - PREMATURE RESOLUTION & PHYSICAL-ACTION AWAIT]** Cấm khai láo trạng thái (DISPATCH != RUNNING != SUCCESS), bắt buộc await subagent xong thực sự trước khi bảo user thao tác vật lý (rút/cắm dây), và triệt tiêu bẫy over-engineering regex guardrail làm nghẽn farm.
- `references/tiktok-coldstart-network-retry-and-switcher-touch-geometry-20261006.md` — **[MỚI 06/10/2026 - COLD-START RETRY & SWITCHER GEOMETRY]** TikTok cold-start retry overlay `dd9`/`ze3`, Switcher 8-nick geometry x=300, và triệt tiêu bẫy Coordinator ngồi khóc viện cớ BLOCKED khi worker nộp code dở dang.
- `references/retirement-of-uiautomator-md-and-gate-1-blast-radius-20261005.md` — **[MỚI 05/10/2026 - RETIREMENT OF UIAUTOMATOR.MD & GATE 1 CEILING]** Khai tử triệt để 16 file docs/uiautomator.md trên toàn farm (dùng Regression Gate + test suite thay thế), siết cứng trần Blast Radius Gate 1 (<= 2 files tính cả test, <= 100 dòng diff, <= 15KB diff thô) để chống tràn payload Sol Web sang Terra Codex, và cấm gộp việc tuần tự.
- `references/two-tier-guard-model-and-anti-paralysis-20261005.md` — **[MỚI 05/10/2026 - TWO-TIER GUARD MODEL & ANTI-PARALYSIS]** Căn nguyên sự cố Coordinator Paralysis (01/10-05/10), mô hình phân tách 2 Tầng (Tầng 1: Chốt an toàn tài sản chặn cứng; Tầng 2: Chốt quy trình Warn/Audit only, cấm chặn), UX Telegram mobile (cấm paste prompt nguyên khối), và quy tắc giải phóng Gateway.
- `references/sol-web-coordinator-gate-redesign-20261005.md` — **[MỚI 05/10/2026 - SOL WEB GATE REDESIGN]** Phán quyết tái cấu trúc hệ thống Gate từ Chief Architect Sol Web (:20129): triệt tiêu universal Sol planning cho routine code edits, phân tầng High-Risk vs Routine Code Surgery, miễn trừ ảnh cho code-only work (Gate 6), và chuẩn hóa Timeout State Machine (INSPECT_REQUIRED -> VERIFY -> DONE/BLOCKED).
- `references/sol-web-92-approval-and-enterprise-hardening-20261004.md` — **[MỚI 04/10/2026 - SOL WEB 92/100 APPROVED]** Chi tiết phán quyết duyệt 92/100 của Chief Auditor Sol Web (:20129), mô hình 3 Cửa Ngõ Bất Biến (Three-Tier Enforcement), chuẩn hóa 7 tiêu chí A1–A7, khắc phục TOCTOU artifact binding và R0 Pinned Hash Trust Root.
- `references/multi-repo-hook-rollout-and-budget-boundary-20261004.md` — Quy trình nhân rộng Pre-Commit Hook đa repo, kỹ thuật bootstrap hook tự động qua test suite hợp lệ, và xử lý trần Coordinator Dispatch Budget (10/10 workers) an toàn.
- `references/regression-gate-and-server-ab-testing-invariants.md` — **[MỚI 04/10/2026]** Khái niệm Regression Gate, Invariant cấm cập nhật APK đồng loạt (Server-Side A/B testing), Mutually Exclusive Fingerprints & Fail-Closed Quarantine.
- `references/anti-skip-physical-hook-gate-matrix-20261004.md` — Ma trận kiểm thử và triển khai Anti-Skip Physical Hook across repos.
- `references/deeplink-evasion-and-screen-on-canary-invariants.md` — **[MỚI 04/10/2026]** Bẫy bịa đặt deeplink (Case 97), quy tắc Screen-On preflight chống ảnh đen và ma trận Anti-Skip physical hook gates.
- `references/sol-web-architectural-consult-20261004.md` — Biên bản tư vấn kiến trúc phản biện độc lập từ Sol Web (:20129).
- `references/sol-adjudication-no-inspect-no-blocked-20261004.md` — **[MỚI 04/10/2026 - SOL HIGH ADJUDICATION]** Invariant NO INSPECT -> NO BLOCKED, triệt tiêu bẫy bại liệt quan liêu L3 BLOCKED, quy định worker timeout là trigger inspect chứ không phải lý do block, thang điều phối Close-The-Loop.
- `references/coordinator-guard-contract-pitfalls.md` — **[MỚI 05/10/2026]** Cạm bẫy Coordinator Guard khi soạn `delegate_task`: MULTI_FILE_VIOLATION do lặp path trong context, INVESTIGATE_HAS_EDIT_INTENT do từ cấm trong prompt, và bẫy phình diff CRLF trên Windows.
- `references/no-inspect-no-blocked-sol-mandate-20261004.md` — **[MỚI 04/10/2026]** Hướng dẫn thực thi chi tiết Sol High: Phân tích nguyên nhân gốc rễ, 3 bước bắt buộc Live Inspect O(1) + Verify Artifact, thang điều phối Close-The-Loop và checklist thẩm định.

### Triết lý kiến trúc (Sol Web :20129 Architect Invariant)
> **"Không bắt AI nhớ. Ép AI không thể chạy nếu không chứng minh đã load đúng state. Muốn triệt tiêu vĩnh viễn context amnesia và safe-skip, không được xây 'AI thông minh hơn' — phải xây 'AI bị kiểm soát chặt hơn'."**

Persistent memory và prompt hướng dẫn là *ràng buộc mềm* (Soft Constraints), không có giá trị cưỡng chế (`Memory ≠ Enforcement`). Nếu hệ thống cho phép Agent tự quyết định "tôi hiểu rồi", "tôi bỏ qua bước này vì an toàn", Agent sẽ liên tục phá vỡ kiến trúc cũ.

---

## Ba tầng cưỡng chế cứng (Three-Layer Compliance Kernel)

```
                 MANIFEST.lock (SHA256)
                           │
                           ▼
                 Pre-Execution Kernel
             (Kiểm tra hash trước khi cấp quyền)
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
Layout Registry     Golden Corpus       Anti-Skip Hook
(Class độc lập)     (Dump thật + XML)   (.git/hooks/pre-commit)
       └───────────────────┬───────────────────┘
                           │
                           ▼
                  Agent Execution Gate
```

### 1. Tầng 1 — Pre-Execution Gate (Trước khi chạy)
- Mọi session mới bắt buộc thực hiện kiểm tra tính toàn vẹn:
  - `MANIFEST.lock` phải tồn tại và khớp với `git show HEAD:tests/golden/.../MANIFEST.lock`.
  - Nếu phát hiện working tree có mã băm bị sửa đổi trái phép $\rightarrow$ Cắt quyền ghi, chuyển trạng thái READ-ONLY ngay lập tức.

### 2. Tầng 2 — Pre-Commit & Worker Gate Cứng (`cage_gate.py` & `.git/hooks/pre-commit`)
- Chặn đứng vật lý ngay tại máy local trước khi bất kỳ lệnh `git commit` nào có thể ghi vào lịch sử git.
- **Worker Sterile Cage (`tools/cage_gate.py`):** Kiểm tra trực tiếp diff của tệp mục tiêu trong sandbox. Nếu Worker nộp code chứa token trốn việc (`SKIPPED_*`, `safe_skip`, `edit_state == "unavailable" ... return True`) $\rightarrow$ Exit 1 `anti_skip_violation`, cấm merge.
- Hook kích hoạt `python tools/guard_selector_change.py --cached`. Nếu phát hiện bất kỳ pattern trốn việc nào $\rightarrow$ **Exit Code 1, hủy commit lập tức**.

### 3. Tầng 3 — Central Pipeline & Coordinator Gates (`guard_selector_change.py` & `done_gate.py`)
- **Step 2.5 Closeout Gate (`tools/guard_selector_change.py`):** Quy tắc **R6: Anti-Skip Invariant** quét toàn bộ file trong diff (`.py`, `.ps1`, `.sh`). Bất kỳ repo nào có diff chứa pattern trốn việc đều bị REJECT ngay tại Step 2.5 trước khi Sol Auditor chấm điểm.
- **Coordinator Done Gate (`tools/done_gate.py`):** Áp dụng cho toàn bộ các repo automation (`Tiktok-video`, `register gmail`, `tiktok-luot nuoi acc`...). Quét cả unstaged (`git diff HEAD`) và staged (`git diff --cached`). Chặn Coordinator declare DONE ảo nếu còn logic safe-skip hoặc thiếu bằng chứng Canary máy thật trong vòng 2 giờ.
- **Worker Sterile Cage Gate (`tools/cage_gate.py`):** Áp dụng cho Worker subagent khi nộp code. Quét `git diff -U0` của target file trong worktree, chặn `anti_skip_violation` (Exit 1) ngay khi phát hiện `status="SKIPPED_*"`, `action="safe_skip"` hoặc nuốt lỗi `return True`.
- **Anti-Tamper & Ratchet Guard:** Cấm Agent sửa đổi các file guard (`guard_selector_change.py`, `closeout_gate.py`, `cage_gate.py`, `done_gate.py`) và test golden (`test_profile_golden.py`). Bộ test golden chỉ được phép tăng thêm (append), cấm tuyệt đối xóa bớt hoặc sửa đổi kết quả fixture cũ.

---

## 5 Nhóm Anti-Skip Pattern Bắt Buộc Quét

Mọi diff thêm mới (`+`, không tính `+++`) phải được regex quét và từ chối nếu chứa:

1. **Gán trạng thái trốn việc / safe-skip:**
   ```python
   status = "SKIPPED_..."
   avatar_status = "SKIPPED_..."
   action = "safe_skip"
   event = "...safe_skip..."
   ```
2. **Fake Return True khi gặp lỗi (Catch-all & Fake Completion):**
   ```python
   if edit_state == "unavailable":
       return True  # Nuốt lỗi giả mạo thành công
   if not adapter:
       return True
   ```
3. **Nuốt ngoại lệ che giấu hiện trường:**
   ```python
   except Exception:
       pass
   except:
       return True
   ```
4. **Viết test giả để hợp thức hóa:**
   ```python
   assert True
   assert avatar_status == "SKIPPED_..."
   ```
5. **Sửa trực tiếp vào Monolith ngoài fence:**
   - Sửa dòng code nằm trong vùng `PROFILE_SELECTOR_DELEGATE` của file monolith thay vì viết class layout mới.

---

## Cài đặt Pre-Commit Hook & Tích Hợp Test

### 1. Cấu trúc hook vật lý (`.git/hooks/pre-commit`)
```bash
#!/bin/sh
# Taadaa Hard Guard Pre-Commit Hook
python tools/guard_selector_change.py --cached
if [ $? -ne 0 ]; then
    echo "============================================================"
    echo "❌ COMMIT BLOCKED: Vi phạm selector hoặc anti-skip guard!"
    echo "============================================================"
    exit 1
fi
```

### 2. Unit test tự động bảo vệ Hook tồn tại
Trong `tests/test_guard_selector_change.py`, thêm test case kiểm chứng sự tồn tại của hook để nếu có ai xóa hook thì CI/pytest sẽ phát hiện ngay:
```python
def test_pre_commit_hook_installed_and_enforces_guard():
    hook_path = REPO_ROOT / ".git" / "hooks" / "pre-commit"
    assert hook_path.exists(), "Pre-commit hook chưa được cài đặt!"
    content = hook_path.read_text(encoding="utf-8")
    assert "guard_selector_change.py" in content
```

---

## Physical-Gate Deployment Discipline (bài học 2026-10-04)

- **Prompt/memory không phải enforcement:** Không báo "đã ghim" chỉ vì đã ghi memory, PROJECT_RULES hoặc prompt. Anti-skip chỉ được coi là triển khai khi hook/gate runtime thật sự được cài, được gọi trước hành động tương ứng và có test chứng minh `EXIT 1` trên diff vi phạm.
- **Không overclaim phạm vi:** Tích hợp vào `cage_gate.py`, `done_gate.py` hoặc `guard_selector_change.py` không tự động có nghĩa là đã áp dụng cho *mọi repo*. Phải kiểm kê từng repo: hook path tồn tại, executable, gọi đúng guard, và chạy probe pass/block. Repo chưa có bằng chứng phải báo `NOT_DEPLOYED`, không báo DONE.
- **Các gate phải dùng cùng policy engine:** Ưu tiên một module dùng chung (ví dụ `guard_anti_skip.py`) rồi để pre-commit, cage, done và closeout gọi cùng một hàm; không copy regex rời rạc giữa các gate vì sẽ lệch pattern và tạo lỗ bypass.
- **Không chặn nhầm chính gate:** Regex/AST scanner phải bỏ qua chính file policy/guard, test fixture mô tả anti-pattern và diff context; chỉ quét dòng thêm trong file thực thi. Mọi `except Exception: pass` trong gate phải được phân loại rõ là lỗi của guard hay logic sản phẩm; guard lỗi phải fail-closed, không im lặng pass.
- **Binding trước closeout:** Trước khi gọi Closeout Gate, phải bảo đảm staged index và working tree khớp (`git status` không còn `MM` trên target). Nếu Gate báo `binding mismatch`, không retry mù hoặc commit; re-stage đúng target, chạy focused test trên đúng tree, rồi gọi lại Gate với parent commit thực tế.
- **Approval không đồng nghĩa commit:** Chỉ commit khi có output sống chứa `Overall Score >= 85`, `Verdict: APPROVED`, `ready_to_close: true`, và audit entry mà hook commit đang đọc khớp đúng repo. Nếu commit vẫn bị chặn, coi là BLOCKED bởi hook/audit-chain và lấy evidence path/entry; không tự tuyên bố DONE.
- **Canary evidence phải chứng minh hành vi mục tiêu:** Ảnh launcher/thiết bị online chỉ chứng minh teardown hoặc availability, không chứng minh upload thật. Với avatar/upload, DONE cần ảnh sau thao tác + log kết quả upload/Workbook `Avatar=OK`; nếu chỉ có screenshot hiện trường cuối cùng thì báo `CANARY_INCONCLUSIVE`.
- **Screen-On Preflight Invariant (Bẫy ảnh đen màn hình tắt):** Khi thiết bị ở trạng thái Sleep/Dozing (`Screen: OFF`), `screencap` sẽ sinh ra file ảnh đen ~12KB. BẮT BUỘC đánh thức màn hình (`keyevent 224`, `wm dismiss-keyguard`), đưa app mục tiêu lên foreground và xác nhận màn hình sáng thật sự trước khi chụp ảnh nghiệm thu Canary. Cấm tuyệt đối gửi ảnh đen màn hình tắt làm bằng chứng.
- **Bẫy bịa đặt Deeplink & Giả thuyết hoang đường (Deeplink Evasion Trap):** Firing deeplink intent bậy (như `am start -d snssdk1233://profile/edit`) kích hoạt popup TikTok *"Hoạt động này không có sẵn trên tài khoản ban đầu"*. Agent không được tự suy diễn ra các giả thuyết hoang đường (như "tài khoản phụ không hỗ trợ sửa hồ sơ") để bao biện cho việc safe-skip. Mọi flow phải đi qua UI chuẩn của người dùng thật (nút Sửa hồ sơ hoặc tap trực tiếp vòng tròn Avatar); intent thất bại bắt buộc fail-closed, cấm bịa giới hạn nền tảng.
- **Closeout Gate Binding Mismatch Trap:** Khi `closeout_gate.py` báo `binding mismatch: staged files also have unstaged edits (tested tree != reviewed diff)`, nguyên nhân là do staged index và working tree bị lệch (trạng thái `MM`). Tuyệt đối cấm viết test case tự động chạy `git add` trong lúc `pytest` để lách binding này (bị Sol trừ điểm hygiene). Phải điều phối Worker chuyên trách chạy `git add` sạch sẽ ngoài test suite trước khi chạy Closeout Gate.
- **Tránh Hardcode Attributes Ngoại Lệ Trong Test:** Khi viết unit test cho các exception class của farm (ví dụ `WorkflowError`), bắt buộc kiểm tra trường chuẩn hóa `error_code` thay vì tự suy diễn `.code` (tránh `AttributeError` làm gãy test suite).

## Kỷ luật Device Lock Bắt Buộc Cho Coordinator (Operator Lock Invariant - 09/10/2026)

- **CẤM TUYỆT ĐỐI CHẠY LỆNH ADB TRẦN:** Khi Coordinator can thiệp vào bất kỳ thiết bị nào (chẩn đoán mạng, fix Wi-Fi, kiểm tra UI, thao tác app, chạy probe script), BẮT BUỘC phải giữ device lock hợp lệ trong `~/.codex/device-locks/`.
- **Cơ chế 2 tầng chuẩn hóa:**
  * Batch Runner / State Machine: Sử dụng `acquire_device_lock`.
  * Coordinator / Manual Operator: BẮT BUỘC dùng `operator_device_lock(machine="N", serial="...", project="hermes_coord")` trong code Python, HOẶC bọc qua CLI wrapper:
    `python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>`
- **Hard Gate cưỡng chế V2 (`guard_device_bulkhead.py`):**
  * Hook `guard_device_bulkhead.py` chặn đứng vật lý mọi lệnh `adb` mutating/device command nếu không tìm thấy active lock file hợp lệ.
  * **Chống Chaining Bypass:** Tách câu lệnh theo ranh giới `&&`, `||`, `;`, `|`, `\n` và thẩm định độc lập từng statement; cấm bypass bằng `adb devices && adb ...`.
  * **Default-Deny:** Mọi lệnh ADB ngoài server allowlist (`devices`, `version`, `kill-server`...) đều bắt buộc `-s <serial>` và có lock.
  * **Anti-Forgery:** Bắt buộc đối chiếu kernel creation timestamp qua `owner_process_alive(data)`, cấm tin file JSON tự forge.
  * Whitelist an toàn: `adb devices`, `adb version`, `python D:/Taadaa/tools/inspect_machine.py <N>`.
- **Rủi ro khi không lock:** Các batch runner hoặc watchdog cronjob nền quét thấy máy rảnh sẽ nhảy vào cướp máy (`acquire_device_lock`), đè focus, gây race condition, xung đột UI và dẫn đến checkpoint / khóa tài khoản.

## Cross-host media evidence

For Central Controller + remote farm clusters, a local `Path.is_file()` result is not evidence about a remote host's drive. Before classifying `video_not_rendered` as missing media, verify on the host that owns the render root and record both locality results. See `references/cross-host-media-preflight.md`.

## Invariant Cốt Lõi: NO INSPECT -> NO BLOCKED (Chống Bại Liệt Quan Liêu L3)

- **Worker Timeout != Task Fail:** Worker timeout (180s) chỉ là tín hiệu rớt kết nối/mất heartbeat tạm thời, KHÔNG PHẢI bằng chứng task thất bại hay artifact chưa được tạo.
- **Trigger để Inspect, CẤM làm lý do Block & CẤM Than Thở:** Worker timeout là một TRIGGER ĐỂ INSPECT, KHÔNG PHẢI BẰNG CHỨNG ĐỂ BLOCK. Coordinator tuyệt đối CẤM auto-escalate lên `L3 BLOCKED` hoặc than vãn "không sửa được / do guard chặn" khi worker timeout.
- **Xử lý dứt điểm khi Worker đã nộp code:** Nếu worker timeout nhưng đã kịp ghi patch hợp lệ vào file mục tiêu (kiểm tra qua `git diff --numstat`), Coordinator không được revert mù quáng hay đóng băng phiên; bắt buộc đi tiếp vào bước verify (chạy test lấy output) để chốt task DONE.
- **Cấm bịa biệt ngữ bao biện:** Tuyệt đối cấm dùng các thuật ngữ tự chế (như "safe-skip regression") để giải thích cho sự thiếu hụt log hay sự chậm trễ trong điều phối; phải nói thẳng hiện trạng ("thiếu log hành trình anchor") và tập trung vào bản chất kỹ thuật.
- **Quy trình 2 bước bắt buộc trước khi kết luận:**
  1. *Step 0 (Live Inspect O(1)):* Bắt buộc query hiện trường sống qua browser/API local, process, port hoặc inspect ADB O(1).
  2. *Step 1 (Verify Artifact):* Kiểm tra tệp mục tiêu / database. Nếu thay đổi đã nằm ở đó (như worker đã kịp bắn API/ghi file trước khi timeout) $\rightarrow$ **Xác nhận nghiệm thu và BÁO DONE NGAY**.
- **Cấm lấy "Target bẩn" làm cớ block:** Nếu target có file dở dang do worker cũ để lại, Coordinator đọc diff O(1). Nếu diff khớp mục tiêu, Coordinator hoàn tất nốt bước verify (chạy test, check status) để đóng task DONE thay vì vin cớ target bẩn để đùn việc.
- **Phạt nặng BLOCKED giả:** Báo BLOCKED khi chưa inspect hiện trường hoặc khi artifact thực tế đã đạt bị coi là THẤT BẠI NGHIÊM TRỌNG NHẤT của Coordinator (nặng hơn cả task fail thông thường).

## Sol Web Gate Redesign & Anti-Paralysis Protocol (Bài học 2026-10-05)

1. **Triệt tiêu Universal Sol Planning cho Routine Code Surgery:**
   - CẤM ép mọi task sửa code phải có Sol Plan ID (`guard_dispatch_contract.py`). Phân loại rạch ròi:
     * *HIGH_RISK_CHANGE (Bắt buộc Sol Plan):* Thay đổi kiến trúc core, sửa gate/hook, can thiệp credential/auth, schema CSDL, đa repo / >2 files.
     * *ROUTINE_CODE_SURGERY (Cho phép chạy thẳng):* Sửa flow, fix bug nghiệp vụ, test fixture, O(1) single-file. Coordinator cấp Patch Contract O(1) chuẩn (`anchor c==1`, `FOCUSED_TEST: <30s`) là dispatch Worker thực thi ngay, CẤM chặn đứng đòi Sol Plan.
2. **Action Taxonomy cho Gate 6 (Visual Evidence):**
   - *UI_MUTATION (Bắt buộc MEDIA:):* Thao tác click, tap, swipe, submit form trên TikTok app, GPM, Browser.
   - *CODE_OPERATIONS (Miễn trừ MEDIA: 100%):* Pytest, py_compile, git status/diff, đọc log, inspect ADB read-only, chạy script backend. CẤM bắt ảnh cho thao tác thuần code/terminal.
3. **Chuẩn hóa State Machine Timeout:**
   - Worker timeout KHÔNG ĐƯỢC coi là task fail.
   - Luồng bắt buộc: `RUNNING -> TIMEOUT -> INSPECT_REQUIRED (Live Inspect O(1) <= 30s) -> VERIFY -> DONE / BLOCKED có evidence`.
   - Coordinator đọc `git diff` và file đích trước. Nếu artifact đã ghi và test pass -> nghiệm thu DONE ngay, cấm auto-block L3.
4. **Mở rộng Allowlist Terminal cho Coordinator:**
   - Cho phép các lệnh chẩn đoán an toàn: `echo`, `curl --http1.0 -m 5`, `head`, `tail`, `cat`, `which`, `ls` để Coordinator không bị mù hiện trường.
5. **CẤM Lạm Dụng `clarify` Gây Đóng Băng Phiên (Anti-Clarify Hang Invariant):**
   - CẤM TUYỆT ĐỐI gọi tool `clarify` khi đang điều tra sự cố farm alert hoặc chạy canary/recovery tự động.
   - Hành vi gọi `clarify` để hỏi "chọn phương án nào", "có tiếp tục không", "mapping nào đúng" bị coi là đùn đẩy trách nhiệm và gây lỗi treo cứng phiên (orphan recovery hang) khiến User bức xúc ("Lồn mẹ mày lí do treo").
   - Coordinator có toàn quyền tự chủ theo ngân sách L0 (Retry transient), L1 (Re-dispatch), L2 (Emergency Surgery). Nếu mâu thuẫn dữ liệu không thể xử lý, chuyển thẳng sang L3 BLOCKED kèm bằng chứng thực tế, tuyệt đối KHÔNG gọi `clarify` làm tê liệt quy trình.

## Kỷ luật thực thi ("Làm cho tao" — Proactiveness Discipline)

0. **Chống Khai Láo Trạng Thái & Bắt Buộc Await Khi Có Thao Tác Vật Lý (Premature Resolution Trap):**
   - **`DISPATCH` $\neq$ `RUNNING` $\neq$ `SUCCESS`:** Khi vừa phát lệnh cho subagent hoặc background process, trạng thái duy nhất tồn tại là RUNNING. CẤM TUYỆT ĐỐI nói trước "đã nạp xong / đã fix" khi subagent chưa trả kết quả về.
   - **Thao tác vật lý (Rút dây, cắm nguồn, thay SIM, bấm nút):** BẮT BUỘC chạy đồng bộ (`await`) hoặc đợi subagent hoàn tất thật sự, đọc lại bằng chứng máy (exit code, ping/API status) thành công 100% rồi MỚI ĐƯỢC báo User thao tác.
   - **Chống bẫy Over-Engineering Guardrails:** Khi xảy ra lỗi premature resolution, KHÔNG sa đà vào vẽ vời các bộ lọc regex phức tạp ở Gateway gây tê liệt vận hành farm; giải pháp chuẩn duy nhất là **ĐỢI SUBAGENT HOÀN TẤT THỰC SỰ TRƯỚC KHI MỞ MIỆNG**.

1. **Chống nói suông & phân tích kéo dài (Chống Than Thở & Đổ Lỗi Timeout & Cấm Hở Tí Là Blocked):**
   - Khi User hỏi "Làm chưa" hoặc "Xong chưa", câu trả lời duy nhất có giá trị là **bằng chứng thực thi thật** (git status sạch, test output pass, diff cụ thể).
   - **Triệt tiêu bẫy "Ngồi khóc viện cớ rule / Hở tí là bảo BLOCKED":** Khi Worker chạy hết budget/iterations mà mới sửa được một phần (ví dụ sửa xong handler nhưng chưa sửa test), Coordinator TUYỆT ĐỐI CẤM ngồi im viết báo cáo dài dòng than thở "bị giới hạn tool" rồi vội vàng tuyên bố "BLOCKED có evidence".
   - Hành vi "khóc xong đéo chịu làm, hở tí là bảo blocked" bị coi là vi phạm nghiêm trọng kỷ luật proactiveness: Coordinator phải lập tức kích hoạt quyền hạn có sẵn (L2 Emergency Surgery) để tự tay hoàn tất nốt các dòng code/test còn thiếu trong ngân sách O(1), chạy test và kích hoạt ngay Canary nghiệm thu.
   - Khi Worker timeout: Tuyệt đối cấm Coordinator than thở "lỗi r bảo coordinator k sửa đc r khóc". Bắt buộc đi đúng State Machine: inspect git diff O(1), nếu code đã nằm trong target thì chạy focused test để nghiệm thu; nếu thiếu thì re-dispatch/L2 dứt điểm.
   - Cấm đặt dấu chấm (`.`) sát đuôi tên file trong `context` / `goal` (ví dụ `follow_engine.py.`) vì regex guard sẽ bắt nhầm thành file riêng biệt gây lỗi `MULTI_FILE_VIOLATION`.
   - Luôn chèn câu Fail-Fast chuẩn hóa khi dispatch Worker EDIT để vượt qua Gate 4.
2. **Bắt buộc cô lập môi trường Pytest (PYTHONPATH Isolation Trap):**
   - Trên các host Windows có cài đặt nhiều gói toàn cục, chạy `pytest` trần trụi có thể import nhầm package cũ từ `site-packages` thay vì mã nguồn trong repo.
   - **Bắt buộc:** Luôn chạy pytest kèm `-o pythonpath="scripts;tools"` hoặc export `PYTHONPATH`:
     ```bash
     python -m pytest tests/test_profile_golden.py -o pythonpath="scripts;tools" -q
     ```
3. **Canary Verification trước khi báo cáo:**
   - Không được tuyên bố hoàn thành nếu chưa chạy kiểm chứng trên ít nhất 1 thiết bị thật (có log `[METRIC] event=layout_resolved` và ảnh đối soát `MEDIA:`).
