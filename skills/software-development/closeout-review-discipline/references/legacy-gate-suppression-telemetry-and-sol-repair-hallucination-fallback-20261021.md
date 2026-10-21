# Legacy Gate Suppression Telemetry & Sol Repair Hallucination Fallback (2026-10-21)

## 1. Bối Cảnh Sự Cố & Tín Hiệu Người Dùng
- **Hiện tượng:** Người dùng yêu cầu gỡ bỏ cảnh báo đỏ của gate text cũ (`🛑 [EVIDENCE FIRST GATE — FAIL-CLOSED VIOLATION]`) trong plugin guard vì hệ thống đã có chốt chặn cơ học (`guard_media_vision_gate.py`) kiểm tra chữ ký HMAC, SHA256 và WinRT OCR ở tầng receipt/tool. Gate text bằng regex liên tục gây false positive khi Coordinator giải trình kỹ thuật hoặc phân tích log lỗi.
- **Biện pháp thi công ban đầu:** Worker gỡ bỏ nhánh `if ev_res: return f"{ev_res}..."` trong `transform_output_hook`, chỉ gọi hàm `_enforce_evidence_first_gate(response_text, session_id=session_id)`.
- **Phản ứng của Closeout Gate Reviewer:** Sol High chấm **68 / 100 (REJECTED)** với nhận xét:
  > *"Vấn đề nghiêm trọng nhất là kết quả của _enforce_evidence_first_gate bị bỏ qua hoàn toàn: nếu giá trị trả về chính là tín hiệu phát hiện vi phạm, hook hiện không còn hành động dựa trên tín hiệu đó... Chưa có đủ bằng chứng để khẳng định không tồn tại bypass, regression hoặc suy giảm khả năng quan sát."*

## 2. Bài Học 1: Legacy Gate Deprecation / Suppression Telemetry Rubric
Khi một gate kiểm tra (đặc biệt là gate text-based) được bãi bỏ hoặc chuyển giao sang cơ chế cơ học khác:
1. **CẤM nuốt mù giá trị trả về (Discarding Return Value without Telemetry):**
   Nếu hàm trả về tín hiệu vi phạm nhưng hook cố tình bỏ qua không chặn, Reviewer sẽ coi đây là lỗ hổng logic/bypass an toàn nghiêm trọng (trừ 15-20đ `logic_correctness` và `farm_safety`).
2. **Bắt buộc emit Structured Telemetry:**
   Khi bỏ qua kết quả của gate, BẮT BUỘC phải ghi nhận sự kiện có cấu trúc:
   ```python
   ev_res = _enforce_evidence_first_gate(response_text, session_id=session_id)
   if ev_res:
       logger.info(
           "[FARM_GUARD] Evidence-first text warning bypassed (superseded by guard_media_vision_gate): %s",
           ev_res[:80],
           extra={"event": "evidence_gate_banner_suppressed", "session_id": session_id},
       )
   ```
3. **Bắt buộc có Unit Test chứng minh hành vi Suppression trong Diff:**
   Reviewer đòi hỏi bằng chứng test mới xuất hiện trong git diff để xác nhận khi gate trả về truthy thì hook không chèn đè banner mà vẫn xử lý êm thuận:
   ```python
   def test_transform_output_hook_bypasses_text_warning_banner(self):
       with patch("__init__._enforce_evidence_first_gate", return_value="🛑 [VIOLATION]"):
           res = transform_hook(response_text="Phan tich ky thuat", session_id="c_ok")
           self.assertIsNone(res)
   ```

## 3. Bài Học 2: Sol Repair Variable/Template Hallucination Trap
Trong quy trình Strike 1 Remediation (`sol_repair.py`):
1. **Hiện tượng ảo giác biến:** Sol High khi sinh patch proposal cho hàm `transform_output_hook` đã tự bịa ra các biến không tồn tại trong codebase (`FAIL_CLOSED_MESSAGE`, `return original_output`).
2. **Hậu quả:** Patch nếu áp dụng mù quáng sẽ ném `NameError` khi chạy test.
3. **Quy tắc kích hoạt Worker Fallback:**
   Theo invariant điều phối, khi patch của Sol Repair không khớp signature thật hoặc gây lỗi syntax/test, Coordinator **ĐƯỢC PHÉP NGAY LẬP TỨC kích hoạt Fallback sang Worker CLI** (`dispatch_worker.py` - Haiku 5.5 / Agy pool) để thi công patch chuẩn xác O(1) theo đúng AST hiện hữu của file. Cấm cố chấp nhồi lại prompt cũ cho Sol.

## 4. Bài Học 3: Bẫy Glob Đường Dẫn Trong `--files` Khi Chạy Ngoài Repo Root
- **Hiện tượng:** Khi chạy `python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --files <glob>` với `workdir` nằm ngoài repository (ví dụ ở `C:\Users\Kibe`), bash không tìm thấy pattern tương ứng ở cwd nên giữ nguyên chuỗi glob (ví dụ `deploy/.../*guard*/...`).
- **Hậu quả:** `closeout_gate.py` hàm `targeted_candidate()` so sánh chuỗi literal với danh sách tệp commit thật (`committed_scope`), phát hiện không khớp và ném lỗi fail-fast:
  `Failed to extract diff: committed ... scope [...] != --files targets [...]; refusing partial committed scope`
- **Khắc phục:** BẮT BUỘC chỉ định `workdir=<repo_root>` cho lệnh terminal hoặc `cd /d <repo_root>` trước khi chạy gate để bash tự động mở rộng glob thành đường dẫn tuyệt đối/chuẩn hóa khớp byte-exact với `committed_scope`.
