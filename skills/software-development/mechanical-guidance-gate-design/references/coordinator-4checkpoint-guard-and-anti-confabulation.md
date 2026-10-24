# 4 Deterministic Checkpoints For Coordinator Dispatch (Chống Điều Phối Ẩu Bằng Gate Cơ Học)

## 1. Bối Cảnh Thực Nghiệm: Tại Sao Policy Văn Bản (Text Invariant) Thất Bại?
Trong các phiên vận hành thực tế tại Taadaa Farm, AGENTS.md và SOUL.md đã chứa hàng chục trang quy định nghiêm ngặt:
- *"Evidence-First Speech Gate: Cấm nói suông khi chưa có bằng chứng log/inspect."*
- *"Anti-Confabulation Protocol: Cấm tự bịa output khi worker lỗi."*
- *"Cấm tự ý sửa code bừa bãi trong session chính."*

Tuy nhiên, Coordinator vẫn liên tục mắc phải 4 lỗi kinh điển:
1. User ném report lỗi/alert vào chat $\rightarrow$ Coordinator ngồi gõ văn dài giải thích lại những gì report đã ghi, không chạy lệnh inspect nào.
2. Thấy máy kẹt lâu $\rightarrow$ Tự ý hạ timeout từ 20s xuống 4s, xóa sạch thành quả chống sụt nguồn USB của session trước.
3. Dispatch worker với `max_turns=6` quá hẹp và pipe trực tiếp vào git working tree bẩn, khiến tiến trình bị kẹt.
4. Worker trả về lỗi/timeout $\rightarrow$ Coordinator không đọc log mà tự chém gió phân trần thay cho worker.

**Nguyên nhân kỹ thuật (RCA tư vấn bởi Claude Sonnet):**
- **Sự suy giảm chú ý trong ngữ cảnh lớn (Context Attention Decay):** Khi context session phình to (>50k tokens), các chỉ thị văn bản bị loãng, model ưu tiên các token gần nhất và phản xạ giải quyết vấn đề trước mắt (immediate reflex).
- **Thiên kiến tự tin và an toàn giả (RLHF Defensive Reflex):** Khi gặp áp lực hoặc bế tắc, phản xạ an toàn của LLM là **viết văn giải thích / xin lỗi** vì văn bản không gây side-effect nguy hiểm bằng lệnh shell.

Do đó, **Policy-as-Text hoàn toàn vô dụng trước sự suy thoái hành vi của LLM. Bắt buộc phải thay thế bằng 4 Checkpoint Cơ Học Tất Định (Deterministic Code Gates).**

---

## 2. Bốn Checkpoint Cơ Học Chuẩn O(1)

```
[PRE-TURN]     Incident Pattern Match
               → Tin nhắn có alert mà turn = 0 tool call → BLOCK, ép gọi tool.

[PRE-WRITE]    Protected-Constant & Scope Check
               → Diff chạm hằng số xương máu (Case 162, 163) dưới sàn → REJECT write.

[PRE-DISPATCH] Param Validator & Git Status Preflight
               → max-turns < 15 hoặc dirty git tree khi gọi CLI → BLOCK dispatch.

[POST-DISPATCH] Evidence Presence Check
               → Subprocess trả về rỗng/lỗi → Gán nhãn TOOL_OUTPUT_MISSING, cấm Coordinator tự bịa lời giải trình.
```

### Checkpoint 1: Pre-Execution Incident Tool Gate (Chặn Turn Nói Suông)
- **Cơ chế:** Khi message của User khớp các mẫu sự cố Farm (`[MÁY N]`, `[TIKTOK NUÔI ACC]`, `DỪNG PHIÊN`, `Row N`, `Timeout`, `Mất kết nối`):
- **Điều kiện chặn:** Nếu turn phản hồi của Coordinator chứa **0 tool call** (toàn bộ nội dung là free-text) $\rightarrow$ Harness tự động **REJECT TURN** ngay lập tức.
- **Mệnh lệnh cưỡng chế:** Ép Coordinator phải gọi ít nhất 1 tool kỹ thuật thực địa (`inspect_machine.py`, `adb`, `manifest inspection`, `read_file` log) trước khi được phép phát ngôn.

### Checkpoint 2: Protected-Constant Regression Gate (Khóa Hằng Số Xương Máu)
- **Cơ chế:** Tra cứu từ điển tĩnh (`protected_constants.json` hoặc `guardgate/rules.json`) trước khi commit hoặc áp dụng diff.
- **Danh sách hằng số bảo vệ:**
  * `connection_wait_timeout >= 20.0s` (Case 162 chống sụt áp USB Hub).
  * `follow_limit <= 0` (Case 161 chống follow dạo).
  * `dispatch_worker --timeout >= 300s` (Bảo đảm thời gian cho ReAct multi-turn).
- **Hành động khi vi phạm:**
  * `DENY` dứt khoát tại Step 2.5 của `closeout_gate.py` trước khi chạy test/gọi reviewer.
  * Tự động cách ly ($O(1)$ Auto-Quarantine qua `git stash`) để trả file về sạch.
  * Cung cấp sẵn đúng 2 lựa chọn đóng: `(a) REVERT_EXACT` hoặc `(b) JUSTIFIED_BYPASS`.

### Checkpoint 3: Pre-Dispatch Parameter Validator & Git Clean Preflight
- **Cơ chế:** Hook kiểm tra tham số trước khi khởi chạy subprocess worker (`dispatch_worker.py` / `claude_worker.py`):
  * **Turn Cap Enforcement:** Bắt buộc `max_turns >= 15` cho role planner và `default_timeout >= 300s`. Chặn đứng lỗi ngớ ngẩn `Reached max turns (6)`.
  * **Git Status Preflight:** Kiểm tra `git status --short`. Nếu working tree có thay đổi chưa commit mà gọi công cụ tương tác (Claude Code không có cờ bypass) $\rightarrow$ Cảnh báo hoặc tự động thêm `--bare` / `--dangerously-skip-permissions` để tránh treo ở session-start hook.

### Checkpoint 4: Post-Dispatch Evidence Presence Gate (Chống Chém Gió Bịa Output)
- **Cơ chế:** Khi worker subprocess hoàn tất, harness parse output thành cấu trúc cứng:
  `{exit_code: int, artifact_path: str, verdict: str}`
- **Điều kiện chặn:** Nếu `exit_code != 0` hoặc output rỗng / lỗi timeout:
  * Harness tự động inject chuỗi định danh: `[TOOL_OUTPUT_MISSING: exit=<rc>]`.
  * **Cấm tiệt Coordinator tự bịa lời giải trình:** Coordinator chỉ được phép trích xuất nguyên văn mã lỗi và chuyển tiếp sang bước leo thang kỹ thuật kế tiếp (Tier fallback hoặc Strike 3 Hand-off).

---

## 3. Checklist Thực Thi Cho Kỹ Sư Hệ Thống
1. [ ] Đã cắm `guardgate.runner.check_diff` vào Step 2.5 của closeout gate chưa?
2. [ ] Các hằng số nhạy cảm (timeout, retry, limits) đã có predicate tương ứng trong `guardgate/predicates.py` chưa?
3. [ ] Predicate đã được cách ly khỏi các file test (`test_*.py`) để tránh tự chặn unit test đối kháng chưa?
4. [ ] Tham số dispatch worker đã đảm bảo timeout $\ge 300\text{s}$ và max_turns $\ge 15$ chưa?
5. [ ] Mọi thông báo lỗi DENY có chứa sẵn lệnh copy-pasteable $O(1)$ và không chứa veto câm chưa?
