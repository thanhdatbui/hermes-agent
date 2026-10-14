# Claude Code CLI Advisor Trap, Haiku 5.5 vs Sonnet 5 Benchmark & Antigravity Windows IPC Fix (2026-10-14)

## 1. Bẫy Ngầm Advisor trong Claude Code CLI (`advisorModel: "sonnet"`)

### A. Triệu chứng & Phát hiện
- Khi chạy `claude -p` với `--model sonnet`, thời gian phản hồi bị kéo dài bất thường: **56s – 103s** (trong khi Haiku chỉ mất **6s – 15s**).
- Gói JSON trả về chứa một lượt gọi cố vấn ngầm:
  ```json
  {"type": "advisor_message", "model": "claude-sonnet-5", "input_tokens": 13395}
  ```
- Đặc biệt ở bài toán vá lỗi proxy xoay vòng (`verify_proxy_and_rotate`), Sonnet dính **Safety Refusal** (từ chối sửa code) với lý do logic ẩn danh IP vi phạm chính sách kiểm duyệt.

### B. Căn nguyên kỹ thuật
- Trong `C:\Users\Kibe\.claude\settings.json`, trước đó có cấu hình toàn cục:
  ```json
  "advisorModel": "sonnet"
  ```
- Khi chạy `--model sonnet`, Claude Code kích hoạt cơ chế Dual-Agent (Sonnet thợ chính gọi Sonnet cố vấn). Hai con Sonnet trao đổi qua lại nuốt thêm **13.395 tokens context**, nhân đôi thời gian chờ và tự khuếch đại rủi ro đạo đức dẫn đến từ chối code.
- Ngược lại, model `claude-haiku-5-5` chưa được gán rank trong catalog advisor của Claude Code, nên CLI **tự động vô hiệu hóa Advisor** (`Warning: Advisor disabled`) và chạy 1-shot siêu tốc 6s–15s.

### C. Giải pháp khắc phục triệt để
- Tắt vĩnh viễn Advisor trong `~/.claude/settings.json`:
  ```json
  "advisorModel": "off"
  ```
  *(hoặc truyền cờ runtime `--settings '{"advisorModel":"off"}'`).*
- **Hiệu quả tức thì khi tắt Advisor:**
  - Task 1 (Atomic Lease): Sonnet giảm từ **56.8s** xuống **6.48s**.
  - Task 2 (ATX XML Bounds): Sonnet giảm từ **103.1s** xuống **6.47s**.
  - Task 3 (Proxy Surgery): Sonnet giảm từ **69.5s (Refusal)** xuống **28.5s (Pass 100%, hết bị từ chối)**.

---

## 2. Benchmark Đối Đầu Sòng Phẳng: Claude Sonnet 5 vs Claude Haiku 5.5 (Pure 1-Shot)

| Bài toán thực chiến Farm | Claude Haiku 5.5 | Claude Sonnet 5 (Tắt Advisor) |
| :--- | :--- | :--- |
| **Bài 1: Atomic File Lease** | 10.8s (2.078 tokens) | **6.48s** (745 tokens) |
| **Bài 2: ATX XML Bounds** | **6.47s** (1.083 tokens) | **6.47s** (598 tokens) |
| **Bài 3: Proxy Code Surgery** | 15.6s (2.334 tokens) | 28.5s (Phân loại lỗi sâu hơn) |

### Kinh tế học Quota Claude Pro:
- Giá niêm yết API: Haiku $0.80/$4.00 vs Sonnet $3.00/$15.00 per MTok (Sonnet đắt gấp ~3.75 lần).
- Trên gói Claude Pro (cửa sổ 5h), Anthropic tính điểm tải tỷ lệ thuận với compute token. Haiku bào mòn quota chỉ bằng **1/4 Sonnet**, cho phép chạy **120–150 tasks/ngày** mà không bị lockout.
- Wrapper thực thi chuẩn cho Farm: `D:/Taadaa/tools/haiku_worker.py` (truyền prompt qua stdin, bypass permissions, timeout 60s).

---

## 3. Căn Nguyên Kẹt Socket IPC của Antigravity CLI (`agy.exe`) trên Windows & Bản Vá

### A. Hai nguyên nhân gây treo tiến trình `agy`:
1. **Profile Direct IP (`acc_01` không proxy):** `acc_01` gọi thẳng Google từ host VN mà không qua Proxy 4G, bị Google bóp băng thông/hang TLS handshake dẫn đến kẹt socket 50s.
2. **Tiến trình ma giữ Named Pipe:** Trên Windows, `subprocess.run(timeout=...)` khi hết giờ chỉ kill process cha, để sót daemon con `agy.exe` tiếp tục giữ Named Pipe `\\.\pipe\antigravity-...`. Các lệnh chạy sau cố bind vào pipe đều bị nghẽn dây chuyền.

### B. Bản vá đã kiểm chứng thành công trong `ag_cli.py`:
1. Vô hiệu hóa `acc_01` trong `profiles_config.json` (`"enabled": false`), chỉ điều phối 5 tài khoản Pro chạy qua Proxy 4G (`acc_02`, `acc_03`, `acc_04`, `acc_06`, `acc_07`).
2. Trong `dispatch_task`, chuyển sang `subprocess.Popen` kèm `stdin=subprocess.DEVNULL`.
3. Khi dính `subprocess.TimeoutExpired`: Gọi lệnh cưỡng chế Windows diệt tận gốc toàn bộ cây tiến trình:
   ```python
   subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
   ```
4. **Kết quả:** `ag_cli.py fix` và `ask` chạy ổn định **2.6s – 3.0s**, hoàn toàn không còn hiện tượng kẹt socket hay lock ma.
