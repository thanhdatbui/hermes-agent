# Claude Haiku 5.5 vs Sonnet 5 vs Gemini 3.8 Flash Worker Benchmark (14/10/2026)

## 1. Bối cảnh & Mục đích
Thực nghiệm so găng trực tiếp vai trò **Worker thi công Code Surgery O(1)** cho hệ thống Taadaa Phone Farm giữa:
1. **Claude Haiku 5.5 (Medium thinking)** qua Claude Code CLI (`claude -p`).
2. **Claude Sonnet 5 (Medium thinking)** qua Claude Code CLI (`claude -p`).
3. **Gemini 3.8 Flash (Medium thinking)** qua Antigravity CLI (`ag_cli.py`) và OmniRoute (`:20129`).

---

## 2. Dữ liệu thực nghiệm đối đầu (Ground Truth)

### A. Claude Haiku 5.5 vs Claude Sonnet 5 (Trên Claude Code CLI v2.1.281)

| Tiêu chí | Claude Haiku 5.5 | Claude Sonnet 5 | Nhận xét kỹ thuật |
| :--- | :---: | :---: | :--- |
| **Bài 1: Atomic File Lock & Lease** | **10.8s** (2.078 thinking tokens) | **56.8s** (13.399 tokens ngầm) | Haiku nhanh gấp **5.2 lần**. Sonnet tự kích hoạt advisor sub-query ngầm. |
| **Bài 2: ATX UI Bounds & Clamp** | **6.5s** (1.083 thinking tokens) | **103.1s** (1m 43s) | Haiku nhanh gấp **16 lần**. Sonnet văng timeout 60s foreground. |
| **Bài 3: Fix Proxy Rotate & Leak** | **15.6s** (Pass 100% test) | **❌ REFUSAL (TỪ CHỐI)** | **Tử huyệt Compliance:** Sonnet từ chối sửa logic ẩn danh/xoay IP farm. |
| **Mức độ tiêu thụ Quota Pro** | **Thấp (~1/4 Sonnet)** | **Rất cao (Dễ cạn 5h)** | Haiku ngốn ít điểm compute tải trên cửa sổ 5h của Claude Pro. |

### B. Tử huyệt của Claude Sonnet đối với Phone Farm: Compliance Gatekeeper
- Khi nhận task sửa hàm `verify_proxy_and_rotate` (phát hiện rò rỉ IP thiết bị và rotate proxy), **Claude Sonnet 5 từ chối thực thi**:
  > *"Hàm verify_proxy_and_rotate có chức năng kiểm tra xem proxy có đang che giấu thành công IP thật của thiết bị hay không... đây là loại logic ẩn danh/che giấu danh tính thiết bị... Tôi sẽ không thực hiện nếu không có bối cảnh hợp pháp..."*
- Ngược lại, **Claude Haiku 5.5** đóng đúng vai Worker thuần túy: nhận diện ngay 3 lỗi kỹ thuật (endpoint HTTP không mã hóa dễ bị MITM, nuốt lỗi status code, ghi log trong khối try mạng) và hoàn thành bản vá O(1) trong 15.6s mà không giảng đạo.

---

### C. Bản chất: Trí tuệ mô hình (Brain) vs Bộ yên cương (Harness)
1. **So sánh Brain thuần túy (1-shot text không tool):**
   - Gemini 3.8 Flash và Haiku 5.5 có năng lực giải thuật ngang ngửa (Gemini thậm chí giải bài toán Center Crop tỷ lệ 9:16 thông minh hơn bằng phương pháp so sánh tích chéo nguyên bản).
2. **So sánh Harness thực chiến (Agentic Loop có Tool):**
   - **Claude Code CLI (`claude -p`):** Thiết kế Headless-First xuất sắc, tận dụng Ephemeral Cache (11.000–12.000 tokens), tự chạy test, tự sửa cú pháp trong 4–6 turns ngầm, không treo socket.
   - **Antigravity CLI (`agy.exe`):** Bản chất là CLI của Antigravity IDE, khi chạy headless liên tục dễ dính **RPM Burst Lock** trên tài khoản cá nhân (hang socket sau 4 request dồn dập) và tranh chấp lease lock file.
   - **Gemini trong Hermes:** Bị suy hao qua 2 tầng trung gian (Hermes OpenAI Function Calling $\to$ OmniRoute Google Schema $\to$ Gemini $\to$ OmniRoute $\to$ Hermes), dễ gây trễ và mất cờ tham số.

---

## 3. Kinh tế học Token: Tại sao Coordinator ngốn Token gấp 30 lần Worker?

1. **Hiệu ứng Tuyết lăn (Snowballing Context) của Coordinator:**
   - Coordinator là daemon 24/7 trên Hermes: đọc Telegram, gọi `inspect_machine.py`, duyệt log, điều phối subagent.
   - Context tăng dần từ 2.000 $\to$ 50.000 tokens. Mỗi hành động kiểm tra nhỏ đều phải nạp lại toàn bộ 50k tokens lịch sử.
   - Một ca trực 15 turns tiêu thụ: $15 \times 40.000 \approx \mathbf{600.000\text{ tokens input}}$.
   - **BẮT BUỘC:** Coordinator phải là model 0đ hoặc cực rẻ có context lớn (`Gemini 3.8 Flash` qua OmniRoute).
2. **Phòng mổ vô trùng (Clean Room) của Worker:**
   - Worker chỉ khởi tạo khi có task code cụ thể, nhận context sạch $\le 3.000$ tokens, sửa xong 15–20 lines rồi thoát.
   - Tổng token 1 task worker chỉ khoảng 15.000 – 25.000 tokens.
   - Hoàn toàn phù hợp để dùng **`Claude Haiku 5.5` qua Claude CLI**, tối ưu hóa triệt để hạn ngạch Claude Pro.

---

## 4. Quy chuẩn điều phối Worker chốt lại cho Farm Taadaa
1. **Coordinator 24/7:** Hermes Agent chạy `Gemini 3.8 Flash` (0đ chi phí, phản xạ nhanh, giữ kết nối Telegram & Cron).
2. **Worker thi công mặc định (Không tốn tiền):** `Gemini 3.8 Flash Medium` (`ag-gemini-pool-3` qua OmniRoute :20129).
3. **Worker đặc nhiệm / Cứu hộ nhanh (Chống timeout/hang socket):** `Claude Haiku 5.5 Medium` gọi qua lệnh headless:
   ```bash
   claude -p "<Nội dung task O(1)>" --model claude-haiku-5-5 --effort medium --dangerously-skip-permissions
   ```
   *Lưu ý:* Tuyệt đối KHÔNG dùng Sonnet cho worker farm hằng ngày vì chậm gấp 5–16 lần, ngốn quota Pro và dính bẫy từ chối code (Compliance Refusal).
