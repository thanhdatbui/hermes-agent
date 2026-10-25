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
