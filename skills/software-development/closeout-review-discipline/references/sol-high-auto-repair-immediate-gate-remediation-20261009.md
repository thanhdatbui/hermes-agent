# Sol High Auto-Repair Immediate Gate Remediation (2026-10-09 Incident & Architecture)

## 1. Bối cảnh Sự cố (Incident Context)
- Trong phiên làm việc ngày 09/10/2026, Closeout Gate trả về điểm số **82/100** (REJECTED) do thiếu telemetry/logging semaphore và test concurrency chuyên biệt.
- **Hành vi sai lầm của Coordinator:** Thay vì kích hoạt công cụ tự sửa của Sol High đã được thiết kế sẵn, Coordinator lại tự biên soạn contract rồi dispatch worker Gemini (`deleg_e873a9dd`, `deleg_bc5a478b`) để sửa code. Hậu quả là subagent Gemini bị kẹt vòng lặp phân tích và timeout 600s, làm đình trệ phiên chốt.
- **User chấn chỉnh gay gắt:**
  > *"là sao t nhớ thiết kế clouseout sol high tự làm luôn r mà sao mày lại làm"*
  > *"Gate reject: Sol High (:20129) vá thẳng, cấm Gemini mò 3 vòng, cấm BLOCKED bỏ dở; Claude CLI CHỈ dùng khi user cho phép."*

---

## 2. Bản chất Thiết kế Kiến trúc (Design Invariant)
Hệ thống Taadaa Phone Farm đã có module chuyên dụng **`D:\Taadaa\tools\sol_repair.py`** và cờ `--auto-repair` trong `closeout_gate.py`:
1. **Sol High (:20129) là engine sửa lỗi độc quyền:**
   - Được huấn luyện và cấp prompt nghiêm ngặt để phân tích scorecard/findings của Reviewer.
   - Trực tiếp đối soát AST Python, kiểm tra cú pháp và đảm bảo tính nguyên tử (atomic) của code trước khi xuất bản vá.
   - Thời gian phản hồi chỉ 15–25 giây, độ chính xác logic tuyệt đối.
2. **Cấm Gemini can thiệp sau Gate Reject:**
   - Gemini (coordinator hoặc subagent) có xu hướng hallucinate hoặc tốn nhiều tool calls để đọc hiểu repo lớn, dẫn đến timeout 10 phút hoặc cạn kiệt budget 15 calls mà không sửa được gì.
   - Sau khi Gate Reject: **Không có giai đoạn "Gemini thử sửa"**. Phải chuyển giao ngay lập tức cho Sol High.

---

## 3. Quy trình Vận hành Chuẩn (Automated Workflow)
Khi `closeout_gate.py` trả về `Verdict: REJECTED` hoặc điểm `< 85`:

1. **Bước 1 — Kích hoạt Sol High Auto-Repair:**
   Chạy lệnh trích xuất bản vá từ findings của Scorecard:
   ```bash
   python D:/Taadaa/tools/sol_repair.py \
     --repo "<đường_dẫn_repo>" \
     --files <các_file_mục_tiêu> \
     --findings "<finding_1>" "<finding_2>" ... \
     --output "D:/Taadaa/logs/repair_proposal.json"
   ```
   *(Hoặc chạy `closeout_gate.py` với cờ `--auto-repair`)*.

2. **Bước 2 — Áp dụng Bản vá & Kiểm thử:**
   Sử dụng công cụ an toàn `apply_patch.py` (có cơ chế backup `.bak` và auto-rollback nếu test fail):
   ```bash
   python D:/Taadaa/tools/apply_patch.py "D:/Taadaa/logs/repair_proposal.json"
   ```

3. **Bước 3 — Chạy Lại Focused Test & Re-run Gate:**
   - Chạy lệnh focused test < 10s.
   - Chạy lại `closeout_gate.py --repo ... --base HEAD~1 --json-output`.
   - Lặp lại quy trình này hoàn toàn tự động cho đến khi Reviewer chấm `APPROVED` ($\ge 85$).
