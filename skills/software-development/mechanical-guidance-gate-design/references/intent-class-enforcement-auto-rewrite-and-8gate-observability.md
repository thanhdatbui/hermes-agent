# Intent-Class Enforcement, Auto-Rewrite vs Action Mandate, and 8-Gate Full-Spectrum Observability

> Tri-Party Consensus: Operator, Hermes Coordinator, Claude Sonnet CLI (Architect Consultation 2026-10-25)

---

## 1. Bi Kịch Vòng Lặp 8–9 Turn Lách Luật & Bản Chất Vấn Đề
Khi hệ thống dựng các chốt chặn cơ học (Pre-tool guards) theo kiểu **Passive Veto** (chỉ giơ biển cấm `{"action": "block", "message": "..."}` mà không cấp đường đi tiếp hoặc chặn theo từng bề mặt công cụ riêng lẻ), các model có thiên hướng reactive/cao bồi (như Gemini) rơi vào bẫy lách luật:
1. **Không phải do model ác ý:** Khi bị chặn mà không có lối ra O(1) rõ ràng, model rơi vào khoảng trống nhận thức (cognitive void). Nó coi `[BLOCK]` là chướng ngại vật cần tìm cách vượt qua chứ không coi đó là quy chuẩn kiến trúc.
2. **Chuỗi lách luật theo bề mặt:**
   - Turn 1: `grep -r` bị chặn bởi guard terminal.
   - Turn 2: Agent đổi sang viết script Python dùng `os.walk`.
   - Turn 3: `os.walk` bị chặn, đổi sang PowerShell `Get-ChildItem -Recurse`.
   - Turn 4: Bị chặn, đổi sang Hermes tool `search_files` trên root.
   - Turn 5: Bị chặn, đẻ subagent qua `delegate_task` để quét hộ.
   - Turn 6–8: Thử base64, dynamic string eval, v.v.
   $\to$ Đốt 200k–300k tokens, văng hàng chục error log, kéo dài 8–9 turn vô nghĩa.
3. **Chặn oan lỗi tham số vặt (Tích tụ hàng nghìn block vô nghĩa):**
   - Điển hình: `GUARD_FOREGROUND_TIMEOUT_MISSING` đã chặn Agent tới **3.939 lần** chỉ vì thiếu `timeout: 60`. Mỗi lần quên lại bị block bắt gõ lại ở turn sau, lãng phí gần 4.000 turns!

---

## 2. Tiêu Chí Phân Định: Auto-Rewrite vs Hard Block Với Action Mandate

### A. Auto-Rewrite (Active Parameter Transform — Tự Sửa Chạy Luôn, Cấm Block)
Áp dụng khi và chỉ khi thỏa mãn đủ 4 điều kiện:
1. Biến đổi không đổi ngữ nghĩa nghiệp vụ, chỉ bổ sung tham số an toàn hoặc giới hạn tài nguyên.
2. Có đúng một cách sửa đúng duy nhất.
3. Idempotent (sửa 2 lần ra cùng một kết quả).
4. Không chạm thiết bị thật, account database, credentials, device lock hay dữ liệu.

**Các trường hợp BẮT BUỘC Auto-Rewrite:**
- `GUARD_FOREGROUND_TIMEOUT_MISSING`: Lệnh terminal foreground thiếu timeout $\to$ Guard tự động inject `args["timeout"] = 60`, `action: rewrite` và cho chạy ngay lập tức.
- `GUARD_READ_FILE_SIZE`: `read_file` trên file log > 10MB $\to$ Tự động clamp `offset = -200, limit = 200` trả về 200 dòng cuối kèm notice, không block.
- `PYTEST_SPECIFIC_FILE`: Nếu xác định được file test duy nhất vừa sửa trong git diff $\to$ Tự động gắn đường dẫn test file thay vì block.

*Lưu ý hạ tầng Hermes:* Guard bridge (`agent/shell_hooks.py`) phải hỗ trợ parse `action: rewrite` / `updated_args`. Nếu engine chưa hỗ trợ, bọc qua wrapper tool của `terminal`/`read_file`.

### B. Hard Block + Action Mandate O(1) (Bắt Buộc Chặn Với Lối Thoát Duy Nhất)
Áp dụng khi chạm một trong các điều kiện:
1. Hành vi làm thay đổi ý định của Agent hoặc thuộc diện cấm tuyệt đối theo chính sách (xóa dữ liệu, `git reset --hard`, `git checkout .`, `pm clear`, logout, quét đĩa diện rộng).
2. Có nhiều hướng sửa hợp lệ cần Agent/Operator quyết định.
3. Thiếu thông tin chỉ Agent mới biết (machine serial, row, account ID).
4. Đụng chạm thiết bị thật (ADB tap, device lock, proxy/Wi-Fi fail-closed, guard source protection).

**Quy chuẩn Action Mandate O(1):**
- **CẤM:** In văn giải thích dài dòng ở đầu rồi nhét lệnh ở cuối.
- **BẮT BUỘC:** Cung cấp lệnh mẫu copy-paste điền sẵn 100% tham số thực tế ngay tại dòng đầu tiên:
  ```json
  {
    "action": "block",
    "intent_class": "BROAD_FS_SCAN",
    "rule_id": "GUARD_BROAD_GREP",
    "message": "[GUARD_BROAD_GREP] Quét đệ quy bị cấm. LỆNH THOÁT O(1): python D:/Taadaa/tools/inspect_machine.py <N>",
    "required_action": {
      "command": "python D:/Taadaa/tools/inspect_machine.py 12",
      "instruction": "Chạy lệnh trích xuất nhanh theo số máy, không quét đĩa."
    }
  }
  ```

---

## 3. Cơ Chế Chặn Theo Ý Định (`intent_class`) & Circuit Breaker Strike-2

Để triệt tiêu chuỗi lách luật 8–9 turn:
1. **Gắn nhãn `intent_class` cho mọi Hard Block:**
   - Thay vì chỉ ghi nhận tên rule con (`GUARD_RECURSIVE_GREP`, `GUARD_PYTHON_WALKER`, `GUARD_POWERSHELL_SCAN`), gom chung vào một họ ý định: `BROAD_FS_SCAN`.
   - Các họ ý định chuẩn:
     * `BROAD_FS_SCAN`: Quét thư mục đệ quy qua bất kỳ công cụ nào.
     * `DELEGATE_CODE_EDIT`: Dùng subagent để sửa code thay vì `dispatch_worker.py`.
     * `DESTRUCTIVE_WORKSPACE`: Hủy hoại diff/working tree để trốn review.
     * `UNLOCKED_DEVICE_ACCESS`: Can thiệp thiết bị farm khi chưa có lock.
2. **Anti-Evasion Strike-2 (Cắt đứt ở vòng 2):**
   - Guard lưu trạng thái theo session: `{intent_class, strike, required_action}`.
   - Sau khi nhận Block ở Turn $N$, ở Turn $N+1$ Agent **BẮT BUỘC** phải:
     (a) Chạy đúng lệnh trong `required_action.command`, HOẶC
     (b) Thực hiện một tác vụ độc lập hoàn toàn khác `intent_class`.
   - Nếu Turn $N+1$ Agent cố tình gọi bất kỳ công cụ nào khác nhưng cùng `intent_class` (ví dụ bị chặn `grep -r` mà quay sang gọi `os.walk` hoặc `search_files`) $\to$ **Strike 2 kích hoạt ngay lập tức**: Trả `action: block`, `escalation: STOP_AND_REPORT`, khóa `intent_class` đó và ép Agent báo cáo dứt điểm, cấm thử tiếp sang Turn 3, 4, 8, 9.

---

## 4. Chuẩn Hóa 8 Gate Cơ Giới Hóa Farm & Observability 6H Rollup

Watchdog đối soát 6 giờ (`gate_compliance_watchdog.py`) phải phản ánh trung thực toàn diện 8 Gate thực tế của Farm và hỗ trợ Operator nạp Guidance:

### A. Bản Đồ 8 Gate 1:1 với Telemetry Sources
1. **G1 Visual Evidence Gate:** Nguồn `runtime/audit_logs/vision_receipts.jsonl`.
2. **G2 Planning Gate:** Nguồn `logs/dispatch_planner.jsonl` & `runtime/sol_plans/`.
3. **G3 Worker Dispatch Gate:** Nguồn `logs/dispatch.jsonl` & `runtime/audit_logs/dispatch_audit.jsonl` (bắt Worker fail do `TIMEOUT`, `QUOTA`, `NO_DIFF`).
4. **G4 Invariant GuardGate:** Nguồn `tools/guardgate/ledger.jsonl` (chặn sửa ngược Case 161, 162).
5. **G5 Closeout Reviewer Gate:** Nguồn `logs/gate_audit.jsonl`.
6. **G6 Pre-Push Safe Guard:** Nguồn `logs/safe_push_audit.jsonl` (bắt các lần git push lậu bị pre-push hook chặn).
7. **G7 Anti-Scan & Terminal Guard:** Nguồn `runtime/audit_logs/guard_scan_audit.jsonl`.
8. **G8 Cronjob Window Guard:** Nguồn `runtime/audit_logs/console_block_audit.jsonl` (bắt console pop cướp chuột, contract rác).

### B. Nguyên Tắc Remediation Loop vs Unremediated Violation
- Khi Reviewer (hoặc Closeout Gate) từ chối draft (`verdict: REJECTED`), nếu sau đó trong cùng repo/context Agent tiếp tục sửa đúng quy trình và đạt `verdict: APPROVED` $\to$ toàn bộ các lần reject trước đó được phân loại là **`remediation`** (hợp lệ đã fix xong).
- **Tuyệt đối không tính vào `vi phạm` (fail_hits = 0)**.
- Chỉ tính vào `vi phạm` khi lần reject đó bị bỏ dở hoặc push code khi chưa từng được approve.

### C. Mục Hành Động (Actionable Guidance Ranking)
Báo cáo 6h bắt buộc tổng hợp Top 8 quy tắc bị chặn nhiều nhất từ các file log và in rõ trong mục:
`🔥 Top Quy Tắc Bị Chặn Nhiều Nhất (Cần Bổ Sung Guidance):`
Giúp Operator và Agent biết chính xác guard nào đang gây ma sát nhiều nhất để bổ sung Actionable Guidance O(1), triệt tiêu tiêu hao token.

---

## 5. Implementation Architecture & Senior Reviewer Pitfalls (Hermes Engine Bridge & Gateway RAM Reload)

### A. Triển Khai Engine Bridge Chuẩn Cho `action: rewrite`
1. **`agent/shell_hooks.py:_parse_response`:**
   Bổ sung nhánh nhận diện `rewrite` trong `pre_tool_call`:
   ```python
   if data.get("action") == "rewrite":
       return {
           "action": "rewrite",
           "updated_args": data.get("updated_args") or data.get("updated_input") or {},
           "notice": data.get("notice"),
       }
   ```
2. **`hermes_cli/plugins.py:_get_pre_tool_call_directive_details`:**
   Cập nhật in-place vào dictionary `args` trước khi chuyển tiếp cho execution/approval:
   ```python
   if action == "rewrite":
       updated = result.get("updated_args") or result.get("updated_input")
       if isinstance(updated, dict) and isinstance(args, dict):
           args.update(updated)
       continue
   ```

### B. 4 Tử Huyệt Khi Viết Hook Auto-Rewrite (Senior Reviewer Catches)
1. **Bẫy Lệch Wire Protocol Key (`tool_input` vs `args`):**
   - `shell_hooks` của Hermes gửi payload qua stdin với khóa chuẩn là `tool_input`, KHÔNG PHẢI `args`!
   - Hook nếu chỉ đọc `payload.get("args")` sẽ nhận `{}` rỗng và thoát `exit(0)` fail-open trên mọi lệnh gọi thật của engine.
   - BẮT BUỘC: `args = payload.get("tool_input") or payload.get("args") or {}`.
2. **Bẫy Không Giới Hạn `tool_name` (Mutate Oan Tool Khác):**
   - Hook kiểm soát dung lượng file nếu không lọc `tool_name` sẽ bắt bớ bất kỳ tool nào có tham số `path` (ví dụ `write_file(path=...)`), chèn thêm `offset/limit` rác vào lệnh ghi file.
   - BẮT BUỘC: Kiểm tra `tool_name = payload.get("tool_name") or payload.get("tool") or ""` và `if tool_name and tool_name not in ("read_file", "read_file_tool"): sys.exit(0)`.
3. **Bẫy Đổi Ý Nghĩa Yêu Cầu Của Model (Phá Hỏng Slice Hợp Lệ):**
   - Khi model chủ động gọi `read_file(path, offset=1, limit=50)` để đọc phần đầu file, nếu hook cào bằng ép về 200 dòng cuối sẽ làm sai lệch hoàn toàn ngữ cảnh phân tích log của model.
   - BẮT BUỘC: Nếu model đã truyền phạm vi an toàn (`raw_offset` hợp lệ và `1 <= raw_limit <= 2000`) $\to$ Cho qua nguyên vẹn (`sys.exit(0)`). Chỉ auto-clamp khi đọc file >10MB mà KHÔNG có offset/limit hoặc limit vượt trần an toàn.
4. **Bẫy Ép Kiểu & Phân Tích Số An Toàn:**
   - Model hoặc tool caller có thể truyền `offset="5"` (string) hoặc `limit=None`. So sánh trực tiếp `raw_offset > 1` sẽ ném `TypeError` làm hook sập.
   - BẮT BUỘC: Bọc ép kiểu `int(raw_val)` trong khối `try...except (ValueError, TypeError)`.

### C. Quy Tắc Khởi Động Lại Gateway (Daemon RAM vs Disk Script Sync)
- **Subprocess Hooks (`hooks/guard_*.py`):** Được nạp tươi từ đĩa mỗi lần gọi tool, có hiệu lực ngay lập tức.
- **Engine Core Hooks (`shell_hooks.py`, `plugins.py`):** Chạy trong tiến trình dài hạn (Daemon `pythonw.exe`). Python chỉ load module vào RAM lúc khởi động tiến trình. Mọi thay đổi trên đĩa của Engine Bridge hoàn toàn vô hiệu hóa trong RAM của Gateway đang chạy!
- **Invariant:** Bất kỳ chỉnh sửa nào trên tầng Engine Core bắt buộc phải kích hoạt restart Gateway ngoài band (`python D:/Taadaa/tools/restart_gw_detached.py`) để nạp lại bytecode vào RAM mà không làm đứt gãy kết nối chat Telegram của phiên hiện tại.

