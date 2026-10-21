# Tri-Party Mechanical Gate & Anti-Paralysis Architecture (`plan_exec_gate.py`)

## 1. Bối Cảnh & Chấn Chỉnh Của Operator (21/10/2026)
Operator đã chấn chỉnh gay gắt và trực diện:
> *"Gọi 3 bên vào thống nhất r thiết kế gate cơ học. Chứ đéo phải mày ghi nhớ mõm. Vẫn yêu cầu cấm khóc lóc block dừng lại!"*

- **Bẫy ghi nhớ mõm (The Soft-Memory Trap):** Khi phát hiện quy trình mới (Gemini gom Evidence -> Sonnet lập Plan -> Agy CLI thi công), Coordinator có phản xạ "tôi xin ghi nhớ điều này vào prompt/memory". Đây là sai lầm nghiêm trọng vì:
  1. LLM sẽ drift hoặc quên khi ngữ cảnh dồn dày.
  2. Không có gì ngăn chặn vật lý việc Gemini tự ý bịa evidence rác hoặc Sonnet nhả plan lý thuyết suông.
  3. Worker Agy CLI vẫn có thể sửa lan man ngoài scope mà không bị chặn ở tầng OS.
- **Kỷ luật bất biến:** MỌI THỎA THUẬN GIỮA CÁC BÊN BẮT BUỘC PHẢI ĐƯỢC CƠ GIỚI HÓA THÀNH SCRIPT HOẶC HOOK CƠ HỌC FAIL-CLOSED (`plan_exec_gate.py`), CHẶN BẰNG RETURNCODE CỨNG VÀ TEST KIỂM CHỨNG TỰ ĐỘNG.

---

## 2. Kiến Trúc 3 Cổng Kiểm Soát Cơ Học (`plan_exec_gate.py`)

Toàn bộ luồng từ điều tra đến thi công và nghiệm thu được bảo vệ bởi 3 Gate cơ học:

```
[Gemini Coordinator]
       │
       ▼ (Tạo evidence_pack.json)
┌────────────────────────────────────────────────────────┐
│ GATE A: python plan_exec_gate.py A --task-id <id>     │
│ ❌ REJECT (Exit 2) nếu:                                │
│   - claims[] rỗng hoặc thiếu statement                 │
│   - File path không tồn tại trên đĩa                   │
│   - SHA-256 tính lại từ file/line không khớp claim    │
│   - Claim OCR không có text readback thật             │
└────────────────────────────────────────────────────────┘
       │ PASS (Exit 0) -> Cho phép dispatch claude_worker.py --role planner
       ▼
[Claude Sonnet Planner]
       │
       ▼ (Xuất plan.json)
┌────────────────────────────────────────────────────────┐
│ GATE B: python plan_exec_gate.py B --task-id <id>     │
│ ❌ REJECT (Exit 2) nếu:                                │
│   - files_to_edit[] rỗng hoặc vượt scope_allowlist    │
│   - evidence_refs trỏ tới claim không có thật ở Gate A │
│   - KHÔNG CÓ acceptance[] hoặc command không chạy được │
│   - Thiếu expected_exit_code / predicate kiểm chứng    │
└────────────────────────────────────────────────────────┘
       │ PASS (Exit 0) -> Cho phép dispatch ag_cli.py fix
       ▼
[Agy CLI Worker Thi Công]
       │
       ▼ (Thi công xong)
┌────────────────────────────────────────────────────────┐
│ GATE C: python plan_exec_gate.py C --task-id <id>     │
│ ❌ REJECT (Exit 2) nếu:                                │
│   - git diff --name-only lọt file ngoài files_to_edit │
│   - Chạy test command của Plan bị FAIL (!= expect)     │
│   - numstat > 30 dòng (vi phạm ngân sách O(1))         │
│                                                        │
│ ⚠️ HÀNH ĐỘNG KHI GATE C REJECT:                        │
│   - CẤM Gemini và Agy tự ý cãi nhau hay sửa mò         │
│   - Kích hoạt NGAY sol_repair.py tạo proposal O(1)     │
└────────────────────────────────────────────────────────┘
       │ PASS (Exit 0)
       ▼
[Closeout Gate Sol/Sonnet chấm điểm >= 85 -> safe_push.py]
```

---

## 3. Đặc Tả JSON Schema Fail-Closed

### Schema Gate A: `evidence_pack.json`
- `schema_version: 1`
- `task_id: string`
- `claims: list[Claim]` (bắt buộc non-empty):
  - `id`: Định danh duy nhất (`c1`, `c2`...)
  - `statement`: Mô tả triệu chứng cụ thể
  - `source_type`: `file | cmd | ocr | log`
  - Nếu `file`: bắt buộc `path`, `line_range: [start, end]`, `sha256`. Python gate tự đọc file, bóc line range và hash SHA-256 đối soát. Mismatch -> REJECT.
  - Nếu `cmd`: bắt buộc `command`, `exit_code` (repro command đang đỏ).
  - Nếu `ocr`: bắt buộc `path`, `ocr_text` thật từ WinRT OCR.

### Schema Gate B: `plan.json`
- `schema_version: 1`
- `task_id: string`
- `goal`: Mục tiêu ngắn gọn
- `files_to_edit: list[string]` (bắt buộc $\le 2$ files, thuộc allowlist)
- `evidence_refs: list[string]` (mọi ref bắt buộc map trúng claim id của Gate A)
- `steps: list[Step]`: `{id, action, anchor, replacement}`
- `acceptance: list[AcceptanceCriteria]` (bắt buộc non-empty):
  - `{id, cmd, expect_exit_code, predicate}`
  - Command bắt buộc là lệnh thực thi được (<30s).
- `rollback`: Lệnh hoàn nguyên sạch (e.g. `git checkout -- <file>`)

### Schema Gate C: Hậu Kiểm Diff & Verification
- So sánh `git diff --name-only` với `files_to_edit`. Có file lạ -> REJECT.
- Chạy lần lượt từng lệnh `acceptance.cmd` trong môi trường độc lập.
- Kiểm tra exit code và output regex. Không khớp -> REJECT.
- Kiểm tra `git diff --numstat` $\le 30$ dòng. Vượt -> REJECT.

---

## 4. Nguyên Tắc "Cấm Khóc Lóc / Cấm Bại Liệt Báo Blocked"
Mọi điểm REJECT của 3 Gate đều có hành động tiếp nối máy tự động chạy được (**Zero-Waiting-State FSM**), tuyệt đối cấm dừng lại hỏi Operator hay than phiền:
1. **Gate A REJECT:** Coordinator tự động chạy inspect O(1) để lấy đúng sha256 và line range thực tế của file, không được bỏ cuộc.
2. **Gate B REJECT:** Sonnet Planner nhận feedback cụ thể từ gate (ví dụ: thiếu lệnh test acceptance), tự động sinh lại Plan có lệnh test.
3. **Gate C REJECT:** Không để Agy CLI thử lại mò mẫm làm cháy profile. Chuyển giao độc quyền ngay cho `python D:/Taadaa/tools/sol_repair.py` (:20129) tạo proposal in-memory AST O(1).
