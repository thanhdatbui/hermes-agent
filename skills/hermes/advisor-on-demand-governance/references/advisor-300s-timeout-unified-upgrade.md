# Nâng Sàn Timeout Toàn Diện 300s Cho Hội Đồng Cố Vấn (Sol, Claude CLI, Gemini Argon)

## 1. Bối cảnh & Điểm nghẽn cũ
- Trước đây `consult_advisor.py` cài đặt các mức timeout cục bộ quá ngắn:
  * Sol: `first_token_timeout=80s`, `max_total_timeout=140s`.
  * Gemini: `first_token_timeout=60s`, `max_total_timeout=120s`.
  * Claude CLI: `timeout=40` (gọi claude_worker.py) và `timeout=45` (subprocess).
  * `consult_advisor` điều phối chung: clamp cứng `timeout_sec=120s` và `min(timeout_sec, 60.0)` cho nhánh Claude.
- **Hậu quả:** Khi gặp câu hỏi kiến trúc dài, đọc codebase hoặc khi pool upstream nghẽn hàng đợi, Claude CLI và Sol bị ngắt giữa chừng (văng timeout ở giây thứ 45/60), dẫn đến hiện tượng "Hội đồng 3 cố vấn nhưng chỉ có mỗi Gemini Argon trả lời", gây ngộ nhận là Sol và Claude bị hỏng hoặc mất nick.

## 2. Chuẩn hóa Sàn Timeout 300s (Unified Patch Pipeline Approved)
File `D:/Taadaa/tools/consult_advisor.py` đã được nâng đồng bộ trần timeout lên 300 giây:
1. **Advisor Sol (`_consult_sol_inner`):**
   - `first_token_timeout`: 120.0s
   - `max_total_timeout`: 300.0s
2. **Advisor Gemini (`_consult_gemini_inner`):**
   - `first_token_timeout`: 120.0s
   - `max_total_timeout`: 300.0s
3. **Advisor Claude CLI (`_consult_claude_inner`):**
   - Default `timeout_sec`: 300.0s
   - Tham số gọi `claude_worker.py`: `--timeout 280`
   - Subprocess wall-clock timeout: `timeout=300`
4. **Hàm điều phối song song (`consult_advisor`):**
   - Default `timeout_sec`: 300.0s
   - Nhánh Claude: `min(timeout_sec, 300.0)`
   - `ThreadPoolExecutor(max_workers=3)` đợi cả 3 luồng tối đa 300s trước khi kết luận timeout.

## 3. Quy tắc vận hành
- Khi gọi `consult_advisor.py` từ terminal: Phải cấp timeout terminal $\ge 300\text{s}$ (hoặc chạy qua background=True nếu trong session chính).
- Cấm tự ý hạ timeout dưới 300s khiến Claude và Sol bị ngắt ngang khi đang lập luận sâu.
