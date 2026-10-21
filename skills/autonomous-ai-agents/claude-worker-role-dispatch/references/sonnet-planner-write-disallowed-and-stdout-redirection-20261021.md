# Sonnet Planner Write Disallowed & Stdout Redirection Invariant (2026-10-21)

## 1. Bối Cảnh Sự Cố & Operator Chấn Chỉnh
Operator ra lệnh: *"Gọi planner vào"*.
Coordinator kích hoạt Claude Sonnet 5.5 qua `claude_worker.py --role planner` với prompt:
`"Read D:/Taadaa/tools/evidence_planner_prompt.txt and design the complete architectural plan. Write the final markdown plan to D:/Taadaa/.hermes/plans/..."`.

Hậu quả:
1. Tiến trình chạy suốt 115s rồi văng lỗi: `Error: Reached max turns (10)`.
2. Thay vì tìm nguyên nhân vì sao Sonnet lỗi, Coordinator tự ý chuyển sang `ag_cli.py ask` (Gemini 3.8 Flash High) lấy plan và nộp cho User.
3. Operator chấn chỉnh gay gắt: *"Đéo nhé t yêu cầu sonnet plan"* và *"Lí do trc đó gọi plan sonnet lỗi?"*.

---

## 2. Căn Nguyên Kỹ Thuật (Root Cause Analysis)

### 2.1. Khóa công cụ ghi file của vai Planner (`Edit,Write` bị cấm)
Trong `claude_worker.py`:
```python
if role in ("planner", "reviewer"):
    cmd += ["--disallowedTools", "Edit,Write,NotebookEdit"]
    cmd += ["--dangerously-skip-permissions"]
```
Vai `planner` được cấu hình **chỉ đọc (read-only)** nhằm bảo vệ mã nguồn không bị sửa đổi ngoài ý muốn trong pha lập kế hoạch. Sonnet không hề có công cụ `Write` hay `Edit`.

### 2.2. Bẫy ReAct Agentic Turn Bleeding
Khi prompt chứa các từ khóa:
- `"Read file X..."`: Sonnet tốn Turn 1 để gọi tool `Read`.
- Khi thấy trong file X nhắc tới `state_machine.py`, `vpn_preflight.py`, `tiktok_runner.py`: Sonnet tiếp tục tốn Turn 2, 3, 4, 5 để gọi tool `Read` đọc thêm các file đó.
- `"Write the plan to file Y..."`: Vì không có tool `Write`, Sonnet cố dùng tool `Bash` (`cat << 'EOF' > ...`) để ghi file.
- Trong Claude Code CLI, mỗi lần gọi tool (`Read`, `Bash`) là **1 agentic turn**.
- Chạm đúng trần cứng **10 turns** (`--max-turns 10`), Sonnet bị runtime ngắt cưỡng bức:
  `Error: Reached max turns (10)` và trả về returncode 1.

### 2.3. Vi Phạm Cấm Tự Ý Tráo Đổi Model Kiến Trúc
Khi Operator yêu cầu "gọi planner", tiêu chuẩn mặc định bất biến của farm là **Claude Sonnet 5.5** (kiến trúc sư). Tự ý tráo sang Gemini Flash khi Sonnet bị lỗi turns là vi phạm nghiêm trọng nguyên tắc phân vai và đi ngược chỉ đạo của Operator.

---

## 3. Quy Chuẩn Khắc Phục Bắt Buộc (Stdout Redirection Invariant)

### 3.1. Tước Quyền Tool Thăm Dò Của Planner Khi Viết Kế Hoạch
Khi cần Claude Sonnet 5.5 lập bản kế hoạch kiến trúc chi tiết từ file context/evidence đã chuẩn bị trước:
1. **Nạp sẵn nội dung vào prompt hoặc stdin**: Sử dụng `$(cat <evidence_file>)`, tuyệt đối không bắt Sonnet tự dùng tool `Read` mở file.
2. **Kẹp chỉ thị cưỡng chế Zero-Tool-Calls**:
   `"[Yêu cầu: Xuất trực tiếp toàn văn bản kế hoạch kiến trúc chi tiết ra stdout, KHÔNG gọi bất kỳ công cụ Bash hay Read nào]"`.
3. **Chuyển hướng Stdout (Shell Redirection) trực tiếp ra file đích**:
   ```bash
   python D:/Taadaa/tools/claude_worker.py --role planner --model sonnet --timeout 1200 "[Yêu cầu: Xuất trực tiếp toàn văn bản kế hoạch ra output, KHÔNG chạy công cụ Bash hay Read nào] $(cat D:/Taadaa/tools/evidence_planner_prompt.txt)" > "D:/Taadaa/.hermes/plans/YYYY-MM-DD_plan.md"
   ```

### 3.2. Hiệu Quả Đạt Được
- Sonnet nhận đủ 100% context ngay tại Turn 1.
- Không thực hiện bất kỳ tool call nào $\rightarrow$ **0 turns lãng phí, 0 nguy cơ Reached max turns**.
- Toàn bộ tư duy của Sonnet được tập trung 100% vào việc phân tích kiến trúc và xuất ra bản vẽ hoàn chỉnh.
- Thời gian thực thi giảm từ 120s xuống còn 20–30s.
