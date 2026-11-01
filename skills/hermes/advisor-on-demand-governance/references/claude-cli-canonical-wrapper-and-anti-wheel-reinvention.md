# Triệt Tiêu Lỗi Treo Claude CLI & Cấm Chế Bánh Xe Rác Gọi Advisor

## 1. Bản Chất Sự Cố
- **Nguyên nhân treo và lỗi:** Trong hệ thống đã có sẵn `D:/Taadaa/tools/claude_worker.py` là canonical wrapper cho Claude CLI trên Windows. Tuy nhiên, Agent tự ý "chế lại bánh xe" bằng hàm `subprocess.run(shell=True)` trong `consult_advisor.py`.
- **Hậu quả của shell=True trên Windows:** `cmd.exe` tự động cắt cụt chuỗi prompt nhiều dòng tại dấu xuống dòng đầu tiên, khiến Claude CLI chỉ nhận được câu chào vô nghĩa và hỏi lại "bạn muốn làm gì?".
- **Kẹt Model Catalog:** Trong `claude_worker.py`, mapping model cũ `claude-sonnet-5-5` không còn trong catalog của Claude Code CLI 2.1.281, gây warning và ngậm luồng stdin/stdout chờ timeout 60s.

## 2. Quy Tắc Triển Khai Chuẩn Xác (Invariant)
1. **Duy Nhất 1 Entrypoint Cho Claude CLI:**
   - BẮT BUỘC dùng `python D:/Taadaa/tools/claude_worker.py --role reviewer --on-demand --max-turns 1 "<prompt>"`.
   - CẤM TUYỆT ĐỐI tự viết subprocess riêng hoặc cố tình ép người dùng dùng proxy `ag-claude` khi người dùng yêu cầu dùng Claude CLI native.
2. **Model Catalog Mapping Chuẩn Hóa:**
   - `planner`: `"sonnet"` (hoặc alias native của Claude Code).
   - `reviewer`: `"sonnet"`.
   - `worker`: `"haiku"`.
3. **Giới Hạn Turns Khi Review Tư Vấn:**
   - Khi gọi Advisor Claude phản biện kiến trúc, bắt buộc truyền `--max-turns 1` và timeout <= 45s để Claude trả lời trực tiếp trong 1 lượt, cấm để Claude tự ý chạy bash/tool khám phá đĩa làm vượt quá trần timeout 60s của foreground terminal.
4. **Lọc Dữ Liệu Trả Về:**
   - Script gọi bắt buộc lọc bỏ các dòng metadata của worker: `{"event": ...}`, `[NOTICE]`, warning catalog để trích xuất sạch sẽ 100% văn bản tư vấn của Claude.
