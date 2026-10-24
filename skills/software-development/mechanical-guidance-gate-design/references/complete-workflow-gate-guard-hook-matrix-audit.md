# Complete Workflow Gate, Guard, Hook & GuardGate Matrix Audit

Tài liệu đối soát toàn diện về ma trận kiểm soát (Defense-in-Depth) đang trực tiếp vận hành trên Taadaa Farm và Hermes Coordinator (Cập nhật 25/10/2026).

---

## 1. Bảng Tổng Hợp Số Lượng

- **Hooks (19)**: 9 Pre-tool shell hooks + 1 Post-tool shell hook + 4 Plugin lifecycle hooks (Coordinator Plugin v2.3.1) + 5 Git hooks hoạt động (`tools`, `Hermes`, `tiktok-luot nuoi acc`, `Tiktok-video`).
- **Gates (23)**: 6 Gates điều phối Coordinator + 8 Gates cơ giới hóa (6h Watchdog) + 3 Pipeline Gates (A/B/C `plan_exec_gate.py`) + 1 Closeout Gate (`closeout_gate.py`) + 5 Cổng kiểm định chuyên dụng (`done_gate.py`, `pre_session_device_gate.py`, `farm_network_gate.py`, `evidence_gate_verifier.py`, `pyrightconfig.gate.json`).
- **Guards (16)**: 5 Guards nội tại Coordinator Plugin Policy + 11 Guards độc lập / Farm Automation.
- **GuardGate / Guardrails (4)**: Dynamic Rule Engine `guardgate/`, Telegram Channel Isolation Guardrail (Case 94), OmniRoute Vision Bridge Guardrail (`:20129`), Core Shield Invariant.
- **TỔNG CỘNG: 62 chốt chặn phòng thủ đa tầng.**

---

## 2. Danh Mục Chi Tiết 19 Hooks

### A. Pre-Tool Shell Hooks (9 hooks - nạp trong runtime config pre_tool_call)
1. `guard_read_file_size.py` (*matcher: `read_file`*): Chặn đọc file quá lớn gây phình context.
2. `guard_broad_grep.py` (*matcher: `terminal|search_files`*): Chặn quét mù diện rộng (`grep -r`, `find`, `os.walk`).
3. `guard_device_bulkhead.py` (*matcher: `terminal`*): Cô lập máy farm, chặn can thiệp đa thiết bị bừa bãi.
4. `guard_dispatch_contract.py` (*matcher: `delegate_task`*): Ép hợp đồng Worker O(1), bắt buộc `TASK_KIND`, `FAIL_FAST`, ngân sách cuộc gọi.
5. `guard_closeout_discipline.py` (*matcher: `terminal|clarify`*): Chặn né Closeout Gate / lạm dụng clarify.
6. `guard_cronjob_safety.py` (*matcher: `cronjob|terminal`*): Ép cờ ẩn `CREATE_NO_WINDOW` (0x08000000) và `Hidden` cho mọi tiến trình ngầm.
7. `guard_android_proxy.py` (*matcher: `terminal`*): Giám sát và chặn cấu hình sai proxy/mạng Android.
8. `guard_pytest_scope.py` (*matcher: `terminal`*): Chặn full-suite pytest > 30s, ép focused test.
9. `guard_model_drift.py` (*matcher: `terminal`*): Giám sát và chặn trôi vai trò giữa Coordinator và Worker.

### B. Post-Tool Shell Hook (1 hook - nạp trong runtime config post_tool_call)
10. `record_device_failure.py` (*matcher: `terminal`*): Tự động bắt lỗi thiết bị và ghi vào audit trail ngay sau lệnh terminal.

### C. Coordinator Plugin Lifecycle Hooks (4 hooks - plugin v2.3.1)
11. `pre_tool_call`: Kiểm duyệt tool call (chặn đụng vùng cấm, ép allowlist terminal, kiểm soát ngân sách write L2).
12. `post_tool_call`: Cập nhật state machine và đối soát sau khi tool chạy.
13. `transform_llm_output`: Gác cổng kép cấp độ Output text:
    - **Evidence-First & Media Vision Gate**: Chặn gửi `MEDIA:<path>` nếu chưa gọi `browser_vision` / WinRT OCR soi mắt ảnh.
    - **Advisor Dual-Answer Gate**: Ép định dạng phản hồi khi có tư vấn kiến trúc.
14. `pre_llm_call`: Hook vòng đời trước khi Hermes gửi prompt sang model.

### D. Git Repositories Active Hooks (5 hooks)
15. `pre-push` (`tools/.git/hooks`): Chặn `git push` nếu `closeout_gate.py` chưa đạt `APPROVED` ($\ge 80$).
16. `pre-push` (`Hermes/.git/hooks`): Chặn `git push` nếu thiếu biên bản kiểm định Closeout Gate.
17. `pre-commit` (`tiktok-luot nuoi acc/.git/hooks`): Chặn `uiautomator dump` và `adb.dump_ui`, ép dùng WinRT OCR / ATX-Agent port 7912.
18. `pre-push` (`tiktok-luot nuoi acc/.git/hooks`): Khớp `audit_binding` (commit_sha + scope_hash) $\ge 85$ điểm mới cho push.
19. `pre-commit` (`Tiktok-video/.git/hooks`): Kích hoạt `guard_selector_change.py` chặn đổi selector UI tùy tiện.

---

## 3. Danh Mục Chi Tiết 23 Gates

### A. 6 Gates Điều Phối Coordinator (Anti-Insanity Invariants)
1. **Gate 1 (Decompose trước Dispatch):** Phân rã Code-surgery ngắn hạn vs Batch-job dài hạn.
2. **Gate 2 (Patch Contract cho Monolith > 1.500 dòng):** Grep anchor tuyệt đối (`wc -l == 1`), cấp exact diff O(1).
3. **Gate 3 (Circuit Breaker & Transient Exclusion):** Phân loại lỗi Transient (retry $\le 2$) vs Structural (tối đa 2 lần).
4. **Gate 4 (Worker Fail-Fast Injection):** Tiêm lệnh dừng ngay trong $\le 3$ vòng lặp nếu scope bất khả thi.
5. **Gate 5 (Checklist 5 câu hỏi):** Checklist cứng trước khi dispatch.
6. **Gate 6 (Step-by-Step Visual Evidence Invariant):** Max blind steps = 1, bắt buộc ảnh `MEDIA:` và soi mắt trước khi gửi.

### B. 8 Gates Cơ Giới Hóa Kiểm Soát Farm (`gate_compliance_watchdog.py` - 6h Report)
7. **G0 (Live Canary):** Kiểm chứng trên 1 máy đại diện trước khi mở fleet.
8. **G1 (Model Review):** Thẩm định độc lập qua Sol Auditor hoặc Claude Reviewer.
9. **G2 (Commit Scope):** Ngân sách thay đổi khống chế $\le 2$ files và $\le 30$ dòng (L2).
10. **G3 (Push Verified):** Remote commit SHA khớp tuyệt đối với local HEAD.
11. **G4 (Evidence Media):** Ảnh hiện trường có thật, WinRT OCR xác nhận.
12. **G5 (Closeout Score):** Điểm đánh giá $\ge 85$ (hoặc Grace Band 80–84 đủ 5 điều kiện).
13. **G6 (Case Doc Update):** Ghi chép case sự cố vào `farm-automation-cases.md` / `uiautomator.md`.
14. **G7 (Claude Quota Gate):** Kiểm soát hạn mức token của Claude CLI.

### C. 3 Pipeline Execution Gates (`plan_exec_gate.py` & `gate_pipeline.py`)
15. **Gate A (Evidence Collection):** Gom hiện trường, OCR đối soát chữ, chốt `base_commit_sha`, ký số HMAC `gate_a.json`.
16. **Gate B (Plan Generation):** Claude Sonnet / Sol lập kế hoạch, ký HMAC `gate_b.json`, khóa rollback và scope.
17. **Gate C (Execution & Acceptance):** Worker thi công, kiểm tra diff against base commit, untracked files, chạy acceptance test, ký HMAC `gate_c.json`.

### D. Closeout Gate & 5 Cổng Kiểm Định Chuyên Dụng
18. **Closeout Gate (`closeout_gate.py`):** Cổng tối cao chấm 5 tiêu chí (Logic 35, Test 25, Telemetry 15, Safety 15, Arch 10), phát hành token HMAC `[CLOSEOUT_TOKEN]`.
19. **Done Gate (`done_gate.py`):** Cổng cơ học kiểm tra điều kiện nghiệm thu trước khi tuyên bố DONE.
20. **Pre-Session Device Gate (`pre_session_device_gate.py`):** Thăm dò & cứu hộ máy trước ca chạy, chặn chạy trong khung giờ reboot.
21. **Farm Network Gate (`farm_network_gate.py`):** SSOT giải quyết profile Wi-Fi Aruba / proxy và phân loại sự cố mạng L2/L3/L4.
22. **Evidence Gate Verifier (`evidence_gate_verifier.py`):** Đối soát marker thành công 1-1 và chuỗi audit chain.
23. **Pyright Gate (`pyrightconfig.gate.json`):** Phân tích tĩnh AST quét toàn bộ nhánh rẽ, chặn lỗi biến possibly unbound.

---

## 4. Danh Mục Chi Tiết 16 Guards

### A. 5 Guards Nội Tại Coordinator Plugin
1. **Coordinator Write Gate:** Khóa quyền sửa code của Coordinator trong session chính; chỉ cho phép L2 Emergency Surgery ($\le 2$ files, $\le 30$ dòng).
2. **Coordinator Terminal Default-Deny Guard:** Chặn lệnh terminal ngoài allowlist; cấm `python -c` chứa subprocess/ghi file; bắt buộc timeout $\le 60$s.
3. **Guard Source Blacklist Shield (Grail Shield):** Bảo vệ bất khả xâm phạm các file hệ thống, source hooks, config, rules, SSH keys.
4. **Value-Scanned Ancestor Shield:** Quét đệ quy chuỗi đối số của mọi tool call để chống bypass qua path traversal / alias.
5. **Fail-Closed Write Target Resolution:** Quét alias (`path`, `file_path`, `filename`, `target`), nếu thiếu path đích thì block fail-closed ngay lập tức.

### B. 11 Guards Độc Lập / Farm Automation
6. **Anti-Hang Guard (`anti_hang_guard.py`):** Chống treo tiến trình và bẻ gãy vòng lặp sự cố (3-Strike Loop Breaker).
7. **Claude Quota Guard (`claude_quota_guard.py`):** Canh gác hạn mức token/lượt gọi của Claude CLI, chống cạn quota đột ngột.
8. **Deploy Game Guard Render (`deploy_game_guard_render.py`):** Tự động hoãn/dừng render video khi máy đang chơi game (LoL, TFT, War3).
9. **Sol Payload Guard (`sol_payload_guard.py`):** Lọc bỏ secrets, giới hạn payload $\le 16$KB và băm SHA-256 audit trail trước khi gửi lên Sol Reviewer.
10. **Media Vision Guard (`guard_media_vision_gate.py`):** Ép Coordinator gọi `browser_vision` hoặc WinRT OCR đọc ảnh trước khi gửi `MEDIA:`.
11. **Cronjob Safety Guard (`guard_cronjob_safety.py`):** Cưỡng chế chạy ngầm không cửa sổ cho mọi cronjob.
12. **Android Proxy Guard (`guard_android_proxy.py`):** Kiểm tra cấu hình proxy Sing-box / MobiProxy trên thiết bị thật.
13. **Device Lock Hard Guard (`with_device_lock.py` / `watch_device_locks.py`):** Mutex khóa thiết bị 2 chiều, chống tranh chấp và chống parasite account.
14. **Diff Guard (`diff_guard.py`):** So sánh chữ ký hàm bằng AST, bắt lỗi quên sửa caller và thiếu recovery ATX trước khi merge.
15. **Selector Change Guard (`guard_selector_change.py`):** Chặn sửa đổi tùy tiện các UI selector chuẩn hóa trên TikTok farm.
16. **Mikrotik Scan Guard (`update_mikrotik_scan_guard.py`):** Tự động cập nhật whitelist IP và firewall trên router Mikrotik.

---

## 5. Danh Mục Chi Tiết 4 Cơ Chế GuardGate & Guardrails

1. **GuardGate Engine (`guardgate/`):**
   - Động cơ thực thi quy tắc an toàn động (`engine.py`, `runner.py`, `predicates.py`).
   - Tự động nạp quy tắc mới từ sự cố hiện trường (*Incident-to-Guard*, ví dụ: `case_161`, `case_162`).
   - Quản lý sổ cái `ledger.jsonl` có chữ ký HMAC (`RECEIPT_KEY`), cập nhật chỉ dẫn tự động qua `update_guidance.py`.
2. **Telegram Channel Isolation Guardrail (`automation_core/alerts.py` — Case 94):**
   - Chặn tuyệt đối mọi lệnh manual/canary/test/subagent bắn tin/ảnh vào nhóm Report Cron (`-5188753741`) và Farm Alerts (`-5373649734`) khi thiếu `EXEC_MODE=CRON_AUTOMATED`.
3. **OmniRoute Vision Bridge Guardrail (`:20129`):**
   - Tầng middleware trên proxy OmniRoute kiểm soát và phân luồng payload hình ảnh giữa các model pool.
4. **Core Shield / GrailGuard Invariant:**
   - Khiên bảo vệ toàn vẹn: Tự động từ chối bất kỳ hành động nào (kể cả đọc/sửa/xóa) từ Agent nhắm vào mã nguồn của chính các guard, hooks, config và quy tắc tối cao.
