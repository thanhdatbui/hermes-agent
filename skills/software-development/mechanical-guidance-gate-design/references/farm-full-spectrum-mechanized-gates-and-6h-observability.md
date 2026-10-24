# Farm Full-Spectrum Mechanized Gates & 6h Observability Standard

## 1. Bản Đồ Toàn Diện Các Gate Đã Cơ Giới Hóa (Farm Mechanized Gates)
Mọi quy chuẩn vận hành trên Farm Taadaa KHÔNG phụ thuộc vào ý thức tự giác của Agent mà ĐÃ ĐƯỢC CƠ GIỚI HÓA (Mechanical Enforcement) qua 8 gate độc lập:

1. **Visual Evidence Gate (Gửi ảnh nghiệm thu UI):**
   - *Engine:* `guard_media_vision_gate.py` / `transform_llm_output_check`
   - *Audit / Receipt:* `D:/Taadaa/runtime/audit_logs/vision_receipts.jsonl`
   - *Cơ chế:* Chặn xuất phản hồi nếu có claim UI mà thiếu `MEDIA:<path>` hoặc ảnh đính kèm chưa có HMAC-SHA256 Vision Receipt hợp lệ (phải qua WinRT OCR / `browser_vision` soi mắt trong TTL <= 300s).

2. **Planning Gate (Planner Sonnet trước khi làm):**
   - *Engine:* `dispatch_planner.py` & `sol_planner.py`
   - *Audit / Receipt:* `D:/Taadaa/logs/dispatch_planner.jsonl` & `D:/Taadaa/runtime/sol_plans/`
   - *Cơ chế:* Tác vụ kiến trúc/sửa lớn bắt buộc qua Tier 1 (Claude Sonnet CLI với Quota 5h < 85%) hoặc Tier 2 (Sol Planner qua `:20129`). Cấm Coordinator tự lao vào cày bừa khi chưa có `SOL_PLAN_ID` và `SOL_PLAN_SOURCE`.

3. **Worker Dispatch Gate (Điều phối thi công):**
   - *Engine:* `dispatch_worker.py`
   - *Audit / Receipt:* `D:/Taadaa/logs/dispatch.jsonl` & `D:/Taadaa/runtime/audit_logs/dispatch_audit.jsonl`
   - *Cơ chế:* 3 Tier (Sol -> Agy CLI -> Haiku). Khóa sàn timeout >= 300s, fail-fast nếu `files_modified == 0`.

4. **Invariant GuardGate (Chống sửa ngược / Phá rào):**
   - *Engine:* `guardgate/runner.py` & `guardgate/rules.json`
   - *Audit / Receipt:* `D:/Taadaa/tools/guardgate/ledger.jsonl`
   - *Cơ chế:* Khóa sàn timeout USB Case 162 (>= 20s), trần follow popup Case 161 (= 0), sàn timeout worker (>= 300s). Khi DENY: Tự động Auto-Quarantine qua Git Stash + trả Action Mandate O(1).

5. **Closeout Reviewer Gate (Thẩm định chốt phiên):**
   - *Engine:* `closeout_gate.py`
   - *Audit / Receipt:* `D:/Taadaa/logs/gate_audit.jsonl`
   - *Cơ chế:* Reviewer độc lập (Sol Reviewer :20129) chấm điểm 5 tiêu chí. Ngưỡng >= 85 (hoặc Grace Band 80-84 cho diff O(1)). Không pass = cấm đóng phiên.

6. **Pre-Push Safe Guard (Chặn đẩy code bậy):**
   - *Engine:* `safe_push.py` & `.git/hooks/pre-push`
   - *Audit / Receipt:* `D:/Taadaa/logs/safe_push_audit.jsonl`
   - *Cơ chế:* Chặn vật lý lệnh git push nếu thiếu bản ghi Closeout APPROVED khớp đúng commit/diff, hoặc thiếu verified Canary máy thật.

7. **Anti-Disk Scan Guard (Chống quét đĩa diện rộng):**
   - *Engine:* `guard_broad_grep.py`
   - *Audit / Receipt:* `D:/Taadaa/runtime/audit_logs/guard_scan_audit.jsonl`
   - *Cơ chế:* Chặn đứng tức thì `os.walk`, `grep -r`, `find` khi nhận Farm Alert [MÁY N], ép dùng `inspect_machine.py <N>`.

8. **Cronjob Window Guard (Bảo vệ focus màn hình):**
   - *Engine:* `guard_cronjob_safety.py`
   - *Audit / Receipt:* `D:/Taadaa/runtime/audit_logs/console_block_audit.jsonl`
   - *Cơ chế:* Ép cứng `CREATE_NO_WINDOW (0x08000000)` và `Hidden`, cấm pop console cướp chuột/focus.

---

## 2. Vì Sao Khóa Vật Lý Khiến Agent Kẹt 9-10 Vòng?
- **Silent Veto Trap:** Khóa vật lý đơn thuần chỉ in lỗi `[DENY]` cụt lủn mà không cung cấp chỉ dẫn khiến Agent rơi vào khoảng trống nhận thức (cognitive void).
- **Vòng lặp tiêu biểu:** Vòng 1-3 đoán mò sửa tiểu tiết -> Vòng 4-6 tìm cách lách luật -> Vòng 7-8 xin lỗi, than vãn -> Vòng 9-10 dán nhãn BLOCKED quan liêu rồi ngồi chờ cứu.
- **Giải pháp Action Mandate O(1):** Mọi gate khi DENY bắt buộc phải trả: (1) Mã lỗi `[VALIDATION_DENY]`, (2) Chi tiết `VIOLATION`, (3) `HƯỚNG DẪN KIẾN TRÚC`, (4) Lệnh mẫu `REQUIRED_ACTION_O1` copy-paste chạy được ngay turn sau.

---

## 3. Kiến Trúc Giám Sát Đối Soát Định Kỳ 6 Giờ (6h Compliance Watchdog)
Để không bị tình trạng "lâu lâu mới nhớ phát hiện ra vi phạm", hệ thống đối soát tự động gom dữ liệu từ cả 8 gate định kỳ mỗi 6h:
- **Chu kỳ:** 00:00, 06:00, 12:00, 18:00 (đồng bộ nhịp ca Farm).
- **Kênh đích:** Telegram Farm Alert (`-5373649734`).
- **Nguồn dữ liệu đối soát:** Quét đuôi JSONL trong 6h qua từ `vision_receipts.jsonl`, `dispatch_planner.jsonl`, `dispatch.jsonl`, `ledger.jsonl`, `gate_audit.jsonl`, `safe_push_audit.jsonl`.
- **Chỉ số trọng yếu:**
  + Tỷ lệ ảnh có Vision Receipt hợp lệ vs vi phạm gửi ảnh mù.
  + Tỷ lệ task có Plan Sonnet/Sol trước khi sửa code.
  + Số lần GuardGate kích hoạt DENY & tỷ lệ tự phục hồi O(1) qua auto-quarantine.
  + Số lần Closeout REJECTED và số lần Pre-push hook chặn thành công.
