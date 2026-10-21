# Claude Sonnet Planner Zero-Tool Pure-Reasoning & Max-Turns Pitfall (2026-10-21)

## 1. Hiện Tượng Sự Cố & Operator Chấn Chỉnh
Khi Operator ra lệnh: *"Gọi planner vào"*, Coordinator dispatch Claude Sonnet 5.5 qua lệnh:
```bash
python D:/Taadaa/tools/claude_worker.py --role planner --max-turns 10 --timeout 1200 "Read D:/Taadaa/tools/evidence_planner_prompt.txt and design the complete architectural plan. Write the final markdown plan to D:/Taadaa/.hermes/plans/..."
```
Tiến trình chạy nền 115s và kết thúc với `exit code 1`:
`Error: Reached max turns (10)`
Khi Coordinator tự ý fallback sang Antigravity Planner (`gemini-3.8-flash-high`) để sinh plan, Operator đã phản ứng gay gắt và bác bỏ:
> *"Đéo nhé t yêu cầu sonnet plan"*
> *"Lí do trc đó gọi plan sonnet lỗi?"*

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (RCA)

1. **Khóa công cụ ghi file của vai Planner:**
   Trong `claude_worker.py`:
   ```python
   if role in ("planner", "reviewer"):
       cmd += ["--disallowedTools", "Edit,Write,NotebookEdit"]
   ```
   Vai `planner` bị tước quyền `Write` và `Edit` để bảo vệ mã nguồn không bị ghi đè ngoài ý muốn.
2. **Bẫy yêu cầu Agent "Đọc file X và Ghi file Y":**
   Khi prompt bảo Sonnet "Read file X ... Write file Y", Sonnet rơi vào vòng lặp ReAct:
   - Turn 1: Gọi `Read` đọc `evidence_planner_prompt.txt`.
   - Turn 2–5: Thấy file nhắc tới `state_machine.py`, `vpn_preflight.py`, Sonnet tiếp tục gọi `Read` đọc thêm các file liên quan trong repo.
   - Turn 6–10: Vì không có quyền `Write`, Sonnet cố gắng dùng các lệnh `Bash` (`cat << 'EOF' > plan.md`, python script tạm...) để ghi file.
   - Khi chạm trần cứng `--max-turns 10`, Claude Code CLI cưỡng chế ngắt tiến trình: `Error: Reached max turns (10)`.
3. **Cảnh báo catalog SDK:**
   Tham số `--model claude-sonnet-5-5` gây cảnh báo `unrecognized_model` trên Claude Code CLI v2.1.281 và auto-compact 200k context. Cần truyền `--model sonnet` để map chuẩn tức thì.

---

## 3. Quy Chuẩn Khắc Phục Chuẩn Xác: Zero-Tool Pure-Reasoning Invariant

Để Claude Sonnet 5.5 xuất bản kế hoạch kiến trúc 100% thành công mà không bao giờ bị cháy turns:

1. **Nạp toàn bộ context vào prompt hoặc stdin:**
   Caller (script wrapper hoặc Coordinator) tự đọc file evidence và ghép vào prompt, không bắt Sonnet tự đi đọc.
2. **Chỉ thị cưỡng chế tước quyền Tool Call trong Prompt:**
   BẮT BUỘC kẹp directive ở đầu prompt:
   ```text
   [YÊU CẦU BẮT BUỘC CHO CLAUDE SONNET 5.5 PLANNER]:
   Bạn là Principal System & Infrastructure Architect của Taadaa Phone Farm.
   Hãy suy luận sâu sắc và xuất bản trực tiếp toàn văn bản kế hoạch kiến trúc hoàn chỉnh
   ra câu trả lời (stdout) dưới định dạng Markdown chuẩn.
   TUYỆT ĐỐI KHÔNG GỌI BẤT KỲ CÔNG CỤ NÀO (không gọi Bash, không gọi Read, không gọi tool nào).
   Chỉ suy luận và nhả toàn bộ text kế hoạch chi tiết ngay trong câu trả lời.
   ```
3. **Caller Wrapper chịu trách nhiệm ghi file:**
   Caller đọc stdout của Sonnet và tự ghi vào file target (`.hermes/plans/<name>.md`).
4. **Kết quả kiểm chứng thực tế:**
   Khi áp dụng qua `run_sonnet_planner.py`:
   - Sonnet chỉ tốn **1 turn suy luận duy nhất** (0 tool calls).
   - Xuất bản trọn vẹn bản vẽ kiến trúc 6 phần (13.469 ký tự).
   - Hoàn thành với `exit code 0` mượt mà, không lỗi catalog, không tốn turns.

---

## 4. Operator Mandate về Giải Thích Kế Hoạch
Khi Operator hỏi: *"Ủa mà m đang plan cái gì v"*:
- **CẤM** trần thuật nguyên văn bản kế hoạch học thuật 6 phần dài dòng làm ngợp màn hình chat.
- **BẮT BUỘC** tóm tắt gãy gọn đúng 2–3 mục tiêu hành động thực tế (Problem $\rightarrow$ Solution):
  1. *Cứu máy điện thoại treo ADB trước mỗi ca chạy.*
  2. *Dọn bẫy receipt kẹt đăng bài > 24h để không bị đóng băng nick.*
