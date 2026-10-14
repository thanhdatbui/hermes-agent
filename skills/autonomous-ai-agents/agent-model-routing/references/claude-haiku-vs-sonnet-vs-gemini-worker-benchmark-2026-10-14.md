# Claude Haiku 5.5 vs Sonnet 5 vs Gemini 3.8 Flash Worker Benchmark & Advisor Pitfalls (14/10/2026)

## 1. Bối cảnh & Mục tiêu Benchmark
Kiểm chứng thực tế vai trò **Worker lập trình Phone Farm Taadaa** (Code Surgery O(1), parser ADB/XML, concurrency lock, proxy rotary) giữa:
1. **Claude Haiku 5.5** (Medium vs High qua Claude Code CLI `claude -p`).
2. **Claude Sonnet 5** (qua Claude Code CLI `claude -p`).
3. **Gemini 3.8 Flash** (qua OmniRoute `:20129` `ag-gemini-pool-3` và Antigravity CLI `ag_cli.py`).

---

## 2. Dữ liệu thực nghiệm đo lường trực tiếp (Ground Truth)

### A. Nội chiến Haiku 5.5: Medium vs High
- **Haiku Medium:** TB **16.5s**, 1.800–2.500 thinking tokens, chi phí ~$0.07–$0.11/task. Phản xạ nhanh, bám sát Scope Lock O(1), không vẽ vời.
- **Haiku High:** TB **23.8s**, 2.300–4.000 thinking tokens, chi phí ~$0.12–$0.13/task. Chậm hơn 44%, tư duy lý thuyết sâu hơn nhưng dễ sinh văn xuôi phàn nàn và ở bài XML bounds bị ngắt `return None` sớm làm mất element tiếp theo.
- 👑 **Kết luận:** **Haiku 5.5 Medium THẮNG ÁP ĐẢO** cho vai trò Worker.

### B. So găng Haiku 5.5 vs Sonnet 5 & Bẫy Cố Vấn Ngầm (Advisor Trap)
Trong thử nghiệm ban đầu, Sonnet bị chậm bất thường (56.8s ở Bài 1, 103.1s ở Bài 2) và **TỪ CHỐI SỬA CODE (Refusal)** ở Bài 3 (hàm proxy):
- **Nguyên nhân gốc rễ:** File cấu hình toàn cục `~/.claude/settings.json` bị gán cờ `"advisorModel": "sonnet"` từ phiên ngày 07/10. Khi nhận task lập trình kỹ thuật có từ khóa nhạy cảm (`lock`, `proxy`, `bounds`), Sonnet tự động gọi thêm 1 Sonnet Advisor ngầm (`advisor_message` nuốt tới **13.395 tokens** context ngầm).
- Hai con Sonnet "hội chẩn" qua lại làm:
  1. Thời gian đội lên gấp 4–5 lần (từ 15s lên 60s–100s).
  2. Bị bẫy đạo đức kép (Compliance Paranoia): cả hai cùng phóng đại rủi ro ẩn danh IP, dẫn đến việc từ chối sửa hàm `verify_proxy_and_rotate` của Farm.
- **Tháo gỡ bẫy:** Khi tắt hoàn toàn Advisor (`"advisorModel": "off"` trong `settings.json`):
  - Bài 1 (Atomic Lease): Sonnet giảm từ 56.8s xuống **6.48s** (745 tokens).
  - Bài 2 (UI XML Bounds): Sonnet giảm từ 103.1s xuống **6.47s** (598 tokens).
  - Bài 3 (Proxy Surgery): Sonnet chạy xong trong **28.5s**, **100% PASS, HẾT BỊ TỪ CHỐI**.

### C. Cơ chế Advisor trên Claude Code CLI
- Danh sách model được phép làm Advisor chỉ có: `["opus", "sonnet", "fable", "off"]`. **Không có Haiku làm Advisor**.
- Nếu Haiku làm Worker mà bật Advisor, nó bắt buộc phải gọi Sonnet hoặc Opus. Khi đó toàn bộ context sẽ bị tính giá và trừ hạn ngạch tài khoản Claude Pro theo mức phạt của Sonnet/Opus $\to$ Biến Haiku thành con thiêu thân nuốt quota.
- BẮT BUỘC duy trì `"advisorModel": "off"` trong `~/.claude/settings.json` khi chạy Worker automation.

---

## 3. Bản chất Harness: Claude Code CLI vs Antigravity CLI (`agy`) vs Hermes Subagent
- **Claude Code CLI (`claude -p`):** Thiết kế Headless-First xuất sắc, tự quản lý turns, tự chạy bash test nội bộ, tự sửa syntax error trong 4–6 turns, không dính bẫy lock tiến trình.
- **Antigravity CLI (`agy.exe`):** Thiết kế cho IDE desktop. Khi chạy headless ngầm dễ bị nghẽn socket IPC hoặc kẹt lease lock (`.profile.lock`) nếu tiến trình bị kill giữa chừng. Tuy nhiên có lợi thế **Pool 6 tài khoản Pro** xoay tua LRU + Proxy 4G không bao giờ lo cạn quota.
- **Hermes Subagent:** Bị suy hao qua 2 tầng dịch schema OpenAI $\leftrightarrow$ Google Protobuf của OmniRoute, trễ thêm 1–2s/turn.

---

## 4. Công cụ hỗ trợ: `haiku_worker.py`
Đã triển khai script wrapper tại `D:/Taadaa/tools/haiku_worker.py`:
- Tự động gọi `claude -p --model claude-haiku-5-5 --dangerously-skip-permissions`.
- Truyền prompt qua `stdin` an toàn trên Windows chống tràn ký tự dòng lệnh và escape dấu nháy.
- Hỗ trợ `--file`, `--model` (mặc định `claude-haiku-5-5`, linh hoạt chuyển sang `sonnet` khi gặp task thuật toán khó), `--workdir`, `--timeout`.

---

## 5. Chiến lược phân vai tối ưu chốt cho Farm Taadaa
1. **Coordinator:** Giữ nguyên ở **Hermes Agent** (chạy Gemini 3.8 Flash 0đ qua OmniRoute) trực chiến 24/7 Telegram, nhận alert farm, quản lý state machine. CẤM dùng CLI làm Coordinator vì bẫy Agentception và thiếu tool farm.
2. **Primary Worker (90% công việc):** **Claude Haiku 5.5 qua `haiku_worker.py`**. Xong trong 10–15s, diff sạch, không refusal, tiêu thụ < 10% quota Claude Pro/ngày.
3. **Heavy-Duty Fallback Worker:** **Antigravity CLI (`ag_cli.py` Pool 6 Acc Pro)**. Dành cho các đợt refactor diện rộng hàng trăm file hoặc khi Claude bảo trì mạng.
