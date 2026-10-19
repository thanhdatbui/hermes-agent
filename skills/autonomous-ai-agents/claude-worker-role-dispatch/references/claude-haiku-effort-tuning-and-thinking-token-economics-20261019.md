# Claude Haiku Effort Tuning, Thinking Token Economics & Dual-Judge Protocol (19/10/2026)

## 1. Bối cảnh & Hiện trường thực nghiệm
Trong phiên benchmark 10 hiệp giữa Claude Haiku Medium (`--effort medium`) vs Claude Haiku High (`--effort high`) và AGY CLI (Gemini 3.8 Flash Medium):
- Đã đo lường chính xác lượng token suy luận (Thinking Tokens) sinh ra qua flag `--output-format json` của Claude Code CLI.
- Đã đối chiếu phán quyết giữa 2 Trọng tài độc lập: Hermes Coordinator (Gemini) và Claude Code CLI (Sonnet Principal Architect).

---

## 2. Hạch toán Token Suy Luận (Thinking Token Economics)
Anthropic tính toàn bộ `thinking_tokens` vào đơn giá **Output Tokens** (mức giá đắt nhất):
- **Medium (`--effort medium`):**
  - Prompt đơn giản: 77 thinking tokens.
  - Phép tính số học: 0 thinking tokens.
- **High (`--effort high`):**
  - Prompt đơn giản: 232 thinking tokens (**gấp đúng 3.0 lần**).
  - Phép tính số học: 98 thinking tokens.

### Phân tích đánh đổi Chi phí vs Tác vụ:
1. **Với Module lớn (Full Library / Monolith > 20k-40k chars):**
   - Token mã nguồn hiển thị (visible output) chiếm ~85-90% tổng token (5.000 - 9.000 tokens).
   - Phần thinking tokens (~500 - 1.500 tokens) chiếm tỷ trọng nhỏ, nên mức tụt quota 5h giữa Medium và High nhìn qua có vẻ tương đương nhau (~70% cho 10 module lớn).
2. **Với Task sửa bug O(1) thường ngày (10 - 30 dòng):**
   - Code sinh ra rất ngắn (~100 - 200 tokens).
   - Khi đó, thinking tokens của High (200 - 500 tokens) chiếm hơn 70% tổng chi phí!
   - 👉 **Haiku High sẽ ngốn quota 5h gấp 2 đến 3 lần Haiku Medium** đối với các task fix bug nhanh.

---

## 3. Kỷ luật Định dạng & Bẫy Hội Thoại của Haiku Medium
Trong Hiệp 3 (Windows Atomic JSON Writer), khi được giao viết module và test:
- **Haiku Medium:** Bị phân tâm vào cơ chế xin quyền thực thi/ghi đĩa của Claude Code CLI, tự ý xuất văn bản hội thoại ("I couldn't write... because write permission was denied..."), làm hỏng việc kiểm tra cú pháp AST (`SyntaxError: unterminated string literal`).
- **Haiku High:** Đạt tỷ lệ 100% hợp lệ cú pháp (10/10 hiệp), hoàn toàn kỷ luật, chỉ xuất đúng khối code Python được bọc fenced markdown ````python ... ````.

---

## 4. Bẫy Chiều Dài Command Line trên Windows (`lpCommandLine` 32,767 ký tự)
Khi gọi Claude CLI để review/chấm điểm đối chiếu 2 đoạn code lớn (> 20.000 ký tự):
- **Lỗi:** Lệnh `claude -p "<prompt chứa toàn bộ code A + code B>"` bị Windows `CreateProcess` từ chối với lỗi:
  `ERROR: The command line is too long.`
- **Giải pháp chuẩn:**
  1. Ghi 2 mã nguồn ra 2 file tạm trên đĩa (ví dụ: `r3_candidate_a.py` và `r3_candidate_b.py`).
  2. Truyền đường dẫn file vào prompt ngắn (< 500 ký tự) kèm cờ `--dangerously-skip-permissions`.
  3. Claude Code CLI sẽ dùng tool đọc file trực tiếp từ đĩa, hoàn toàn không bị giới hạn chiều dài command line.

---

## 5. Đối Chiếu Góc Nhìn 2 Trọng Tài (Dual-Judge Invariant)
- **Hermes Coordinator (Gemini):** Đánh giá theo triết lý *Thực dụng & Sản xuất*: Ưu tiên tốc độ phản xạ (27s là xong việc), code súc tích, test happy path chạy qua là đạt.
- **Claude Sonnet CLI:** Đánh giá theo triết lý *Phòng thủ Hệ điều hành & Độ bền Kỹ nghệ*:
  - Soi từng mã lỗi nội bộ Windows NT (WinError 5, 32, 33, 170, 303, 1224).
  - Bắt lỗi lãng phí I/O: Chỉ trích việc retry lại toàn bộ vòng ghi đĩa file tạm, yêu cầu chỉ retry đúng lệnh `os.replace`.
  - Đòi hỏi Unit test phải có Mocking phá hoại (mock `os.replace` ném lỗi 3 lần liên tiếp để thử thách thuật toán backoff).
- 👉 **Công thức chuẩn cho Farm:** Gemini làm thợ thi công nhanh (O(1) builder), Claude CLI làm người gác cổng chất lượng (Closeout Reviewer).

---

## 6. Quyết Định Thiết Kế Lock Cứng Vào Hệ Thống (Production Standards)
Sau khi cân nhắc giữa Thinking Token Economics và độ tin cậy thực chiến:
1. **Tier 1 Worker (`claude_worker.py` / `haiku_worker.py`):**
   - **Khóa cứng:** `--effort high`.
   - **Lý do:** Chấp nhận tốn thêm ~150-200 thinking tokens để đổi lấy **First-Shot Success (10/10 pass)**, triệt tiêu 100% việc nói nhảm xin quyền tool dẫn đến phải retry đốt lại 80.000 input tokens.
   - **Van an toàn:** `CLAUDE_QUOTA_GUARD` kẹp trần 85%; chạm trần tự động chuyển Tier 2.
2. **Tier 2 Worker & 24/7 Workhorse (`ag_cli.py`):**
   - **Khóa cứng:** `DEFAULT_MODEL = "gemini-3.8-flash-medium"`.
   - **Nâng trần timeout:** `ask` = 1200s, `fix` = 1500s.
   - **Lý do:** Tuyệt đối không dùng High để tránh bẫy suy nghĩ lan man ngâm stream 10 phút và đứt đuôi code do chạm trần token của 1 turn. Medium đạt tỷ lệ sống sót 100% tuyệt đối trên toàn bộ 22 profiles.
