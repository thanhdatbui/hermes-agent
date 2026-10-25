# Full-Spectrum Gate Alignment, Scoped Telemetry Isolation & Actionable Guidance Rollup

## 1. Nỗi Đau Vận Hành & Sai Lầm Thiết Kế Của Watchdog Cũ
Khi hệ thống phone farm phát triển nhiều tầng gate cơ học (Pre-tool hooks, GuardGate AST, Git hooks, Terminal shields, Reviewer gates), việc viết watchdog đối soát 6h nếu thiếu kỷ luật kiến trúc sẽ mắc 3 sai lầm nghiêm trọng:

### Sai Lầm 1: Đánh Đồng Remediation Loop Với Vi Phạm Thật (False Positive In Model Review)
- **Hiện tượng:** Watchdog regex từng dòng đơn lẻ thấy `verdict: REJECTED` là tăng ngay biến `fail_hits` và kết luận `FAIL`.
- **Hậu quả:** Trong quy trình phát triển chuẩn (Step-by-step Fix), việc Reviewer chấm draft 76–78đ (REJECTED), sau đó Agent/Sol Repair sửa tiếp đạt 85–91đ (APPROVED) và commit thành công là **hành vi hoàn toàn hợp lệ và đi đúng quy trình**. Việc watchdog tính 7 lần reject đó thành "7 lần vi phạm" làm sai lệch bức tranh tuân thủ của Farm, biến nỗ lực sửa code đúng quy chuẩn thành cảnh báo đỏ giả tạo.
- **Chuẩn cơ học bắt buộc:** Nhóm các đánh giá theo `repo`. Chỉ tính `fail_hits` khi repo bị REJECTED mà kết thúc phiên không hề có bản ghi `APPROVED` nào đi sau (vi phạm bỏ dở). Nếu có `APPROVED`, toàn bộ các lần reject trước đó phải được ghi nhận là **`remediation_hits`** (bước sửa chữa hợp lệ đạt chuẩn).

### Sai Lầm 2: Regex Cào Bằng Đâm Chéo Giữa Các Log File (Lack of Scoped Source Isolation)
- **Hiện tượng:** Watchdog duyệt qua toàn bộ file log trong `logs/` và `runtime/audit_logs/`, áp các regex chung chung (`returncode: 0`, `action: block`, `decision: allow`) lên mọi dòng.
- **Hậu quả:** Return code của các lệnh SSH con trong `admin_ssh.jsonl` bị tính nhầm thành kết quả của Gate 6 (Pre-Push Safe Guard). Quyết định của Terminal Guard bị tính nhầm sang Cronjob Window Guard. Báo cáo sinh ra hàng trăm số liệu rác không phản ánh đúng thực tế của từng gate.
- **Chuẩn cơ học bắt buộc:** Mỗi Gate bắt buộc khai báo trường `source_file` ràng buộc chặt chẽ với file telemetry duy nhất của nó:
  1. **G1 Visual Evidence Gate:** `runtime/audit_logs/vision_receipts.jsonl`
  2. **G2 Planning Gate:** `logs/dispatch_planner.jsonl` & `runtime/sol_plans/`
  3. **G3 Worker Dispatch Gate:** `logs/dispatch.jsonl` & `runtime/audit_logs/dispatch_audit.jsonl`
  4. **G4 Invariant GuardGate:** `tools/guardgate/ledger.jsonl`
  5. **G5 Closeout Reviewer Gate:** `logs/gate_audit.jsonl`
  6. **G6 Pre-Push Safe Guard:** `logs/safe_push_audit.jsonl`
  7. **G7 Anti-Scan & Terminal Guard:** `runtime/audit_logs/guard_scan_audit.jsonl`
  8. **G8 Cronjob Window Guard:** `runtime/audit_logs/console_block_audit.jsonl`

### Sai Lầm 3: Báo Cáo Kết Luận Suông, Thiếu Bảng Xếp Hạng Rule Bị Chặn (Actionable Guidance Gap)
- **Hiện tượng:** Watchdog chỉ in ra danh sách G1..G8 kèm chữ PASS/FAIL cụt lủn.
- **Nhu cầu thực tế của Operator:** Operator không cần một báo cáo hình thức. Mục tiêu của việc đối soát 6h là **xem tỷ lệ Agent vi phạm và tìm ra top rule/hook nào đang chặn Agent nhiều nhất**, từ đó kịp thời bổ sung Guidance kỹ hơn vào hook đó để Agent biết đường làm ngay trong turn kế tiếp, không loay hoay thử lại gây tiêu hao token.
- **Chuẩn cơ học bắt buộc:** Watchdog bắt buộc bóc tách mã `rule_id` / `category` của mọi lần chặn và xuất bảng xếp hạng **`Top Quy Tắc Bị Chặn Nhiều Nhất (Cần Bổ Sung Guidance)`** ở cuối báo cáo.

---

## 2. Đặc Tả Kiến Trúc 8 Gate Cơ Giới Hóa Farm

```python
GATES = (
    Gate("G1", "Visual Evidence Gate",
         _rx(r"MEDIA:\S+|\"reason_code\":\s*\"OK\"|\"receipt_id\":\s*\"rec_"),
         _rx(r"EVIDENCE_MISSING|VERIFIED_SUCCESS_WITHOUT_EVIDENCE\b"),
         "vision_receipts"),
    Gate("G2", "Planning Gate",
         _rx(r"SOL_PLAN_ID|SOL_PLAN_SOURCE|\"tier\":\s*\"(?:sonnet|sol|coordinator)\""),
         _rx(r"PLAN_MISSING|PLAN_FAILED|PLANNER_BYPASSED\b"),
         "dispatch_planner"),
    Gate("G3", "Worker Dispatch Gate",
         _rx(r"\"category\":\s*\"OK\""),
         _rx(r"\"category\":\s*\"(?:TIMEOUT|QUOTA|NO_DIFF|NEEDS_INPUT|COMMAND_ERROR)\""),
         "dispatch"),
    Gate("G4", "Invariant GuardGate",
         _rx(r"\"status\":\s*\"ALLOW\""),
         _rx(r"\"status\":\s*\"(?:DENY|BLOCK|QUARANTINE)\""),
         "ledger"),
    Gate("G5", "Closeout Reviewer Gate",
         _rx(r"verdict\W+APPROVED\b"),
         _rx(r"verdict\W+(?:REJECTED|CHANGES_REQUESTED|NEEDS_FIX)\b"),
         "gate_audit"),
    Gate("G6", "Pre-Push Safe Guard",
         _rx(r"\"returncode\":\s*0|\"success\":\s*true\b"),
         _rx(r"\"returncode\":\s*[1-9]\d*|\"success\":\s*false\b"),
         "safe_push_audit"),
    Gate("G7", "Anti-Scan & Terminal Guard",
         _rx(r"\"action\":\s*\"allow\""),
         _rx(r"\"action\":\s*\"block\""),
         "guard_scan_audit"),
    Gate("G8", "Cronjob Window Guard",
         _rx(r"\"decision\":\s*\"allow\""),
         _rx(r"\"decision\":\s*\"block\""),
         "console_block_audit"),
)
```

---

## 3. Quy Trình Vận Hành Đóng Vòng (Closed-Loop Guidance Feeding)
1. **Watchdog 6h phát hiện Top Block:**
   ```text
   🔥 Top Quy Tắc Bị Chặn Nhiều Nhất (Cần Bổ Sung Guidance):
   1. `[Cronjob Window] CONSOLE_WINDOW`: 102 lần
   2. `[Cronjob Window] CRON_AGENT_POLICY`: 78 lần
   3. `[Cronjob Window] FARM_CONTRACT_INVALID`: 66 lần
   4. `[Anti-Scan & Terminal] GUARD_SEARCH_FILES_ROOT`: 17 lần
   ```
2. **Operator / Coordinator phản ứng:**
   - Đọc mã lỗi (ví dụ: `FARM_CONTRACT_INVALID`).
   - Mở file hook tương ứng (`guard_cronjob_safety.py`).
   - Cập nhật thông điệp `guidance` và khối `REQUIRED_ACTION_O1` chi tiết hơn (chỉ rõ template contract mẫu cần điền).
3. **Hiệu quả đạt được:** Agent ở các ca sau khi bị chặn lần đầu sẽ nhận được hướng dẫn chính xác $O(1)$, sửa đúng ngay ở turn kế tiếp, triệt tiêu 100% các vòng lặp thử mò làm nghẽn hạ tầng.
