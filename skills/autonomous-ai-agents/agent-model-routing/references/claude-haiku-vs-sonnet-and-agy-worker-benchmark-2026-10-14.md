# Claude Haiku 5.5 vs Sonnet 5 vs Antigravity CLI (agy) Worker Benchmark & Advisor Quota Invariants (14/10/2026)

## 1. Bối cảnh & Mục tiêu Thực nghiệm
Đánh giá vai trò Worker lập trình Phone Farm Taadaa giữa 3 phương án:
1. **Claude Haiku 5.5** qua Claude Code CLI (`claude -p --model claude-haiku-5-5 --effort medium`).
2. **Claude Sonnet 5** qua Claude Code CLI (`claude -p --model sonnet --effort medium`).
3. **Google Antigravity CLI** (`agy.exe` qua wrapper `D:/Taadaa/tools/ag_cli.py`, pool 7 acc Pro).

---

## 2. Bẫy Cố Vấn Ngầm (Advisor Trap) trong Claude Code CLI

### A. Triệu chứng & Nguyên nhân
- Khi file `~/.claude/settings.json` chứa `"advisorModel": "sonnet"`, mỗi lần gọi `--model sonnet` trên các task kỹ thuật Farm, Claude Code CLI tự động kích hoạt **Sonnet Advisor** ngầm.
- **Hậu quả đo lường thực tế:**
  * Kéo theo lượt gọi cố vấn phụ nuốt hơn **13.395 input tokens** và **4.073 output tokens**.
  * Thời gian phản hồi bị kéo lê thê từ **6.5s lên 56s – 103s** (chậm gấp 8–16 lần).
  * **Bẫy Paranoia / Safety Refusal:** Khi 2 model Sonnet "hội chẩn" qua lại, chúng tự phóng đại rủi ro bảo mật (nhận diện logic xoay proxy/ẩn danh IP thiết bị farm là hành vi mờ ám) dẫn đến việc **từ chối sửa code (Refusal)**.
- **Tại sao Haiku 5.5 không bị ảnh hưởng khi bật settings này?**
  * Do `claude-haiku-5-5` chưa có rank trong bảng catalog advisor mặc định của CLI v2.1.281, CLI tự động vô hiệu hóa (`Warning: Advisor disabled — base model has no advisor rank`). Nhờ vậy Haiku chạy 1-shot tức thì trong **6s – 15s**.

### B. Giải pháp: Tắt Vĩnh Viễn Advisor (`advisorModel: "off"`)
Trong `C:\Users\<User>\.claude\settings.json`:
```json
{
  "advisorModel": "off"
}
```
**Kết quả sau khi tắt Advisor:**
- Sonnet 5 phục hồi 100% công lực: thời gian phản xạ tụt từ **56.8s xuống 6.48s** ở bài toán Atomic File Lock, và từ **103.1s xuống 6.47s** ở bài toán XML Bounds.
- Sonnet 5 ở bài toán Proxy Surgery **hết sạch triệu chứng từ chối (0% refusal)**, giải quyết dứt điểm 3 lỗi trong 28.5s.

### C. Tại sao cấm dùng Haiku + Advisor?
- Anthropic chỉ cho phép các model cao cấp làm Advisor (`["opus", "sonnet", "fable", "off"]`).
- Nếu bật Advisor cho Haiku, Haiku buộc phải gọi Sonnet/Opus làm cố vấn $\to$ Toàn bộ context bị gửi sang model đắt tiền, Anthropic tính điểm tải quota 5h theo giá phạt của Sonnet/Opus.
- Chi phí tăng gấp 5–10 lần và thời gian ngâm lên 60s–80s, triệt tiêu 100% lợi thế của Haiku. Haiku bắt buộc phải chạy **ĐƠN ĐỘC 100% (TẮT ADVISOR)**.

---

## 3. Bảng Kết Quả Benchmark Đối Đầu Thực Tế (Ground Truth)

| Tiêu chí | Claude Haiku 5.5 | Claude Sonnet 5 (Tắt Advisor) | Antigravity CLI (`agy.exe` 7 Acc Pro) |
| :--- | :---: | :---: | :---: |
| **Atomic File Lock (Bài 1)** | 10.8s | ⚡ **6.48s** | 16.8s |
| **ATX XML UI Bounds (Bài 2)** | ⚡ **6.47s** | ⚡ **6.47s** | 1.8s (ask) / 22.3s (fix) |
| **Code Surgery O(1) Proxy (Bài 3)** | 15.6s | 28.5s (Code Senior chuẩn) | 17.3s |
| **Tỷ lệ tiêu thụ Quota Pro** | Cực thấp (~$0.07-$0.12/task) | Trung bình (~$0.35-$0.55/task) | **0đ chi phí** (Pool Google Pro) |
| **Khả năng chịu tải liên tục** | 120–150 tasks/ngày | 25–35 tasks/ngày | Không giới hạn nhờ LRU 7 acc |

---

## 4. Tử Huyệt Named Pipe IPC trên Antigravity CLI (`agy.exe`) & Bản Vá

### A. Căn nguyên kẹt Named Pipe trên Windows
- `agy.exe` (~194 MB) chứa background daemon ngầm giao tiếp qua Windows Named Pipe (`\\.\pipe\antigravity-...`).
- Khi tiến trình bị ngắt bởi timeout của wrapper Python hoặc Hermes, lệnh kill mặc định bỏ sót daemon con của `agy.exe`.
- Tiến trình ma tiếp tục giữ chặt Named Pipe, khiến các lượt gọi `agy` tiếp theo bị kẹt vĩnh viễn (Infinite Blocking Wait).
- File `.profile.lock` bị sót trên đĩa khiến các lượt sau hiểu nhầm profile đang bị tiến trình khác chiếm giữ.

### B. Bản vá triệt để trong `D:/Taadaa/tools/ag_cli.py`:
1. **Dùng `subprocess.Popen` kèm `stdin=subprocess.DEVNULL`:** Ngắt hoàn toàn bẫy chờ input bàn phím khi chạy headless.
2. **Quét sạch Process Tree bằng `taskkill /F /T` khi dính Timeout:**
   ```python
   except subprocess.TimeoutExpired:
       try:
           subprocess.run(f"taskkill /F /T /PID {proc.pid}", shell=True, capture_output=True)
           proc.communicate(timeout=5)
       except Exception:
           pass
       raise
   ```
3. **Giữ nguyên 7 tài khoản Pro (gồm cả Direct IP `acc_01` và Proxy 5104 `acc_05`):** Kiểm chứng thực tế chứng minh Direct IP kết nối Google cực nhanh (2.1s), lỗi trước đó là do lock file mồ côi chứ không phải do Google chặn IP.

---

## 5. Chiến Lược Phân Bổ Worker Cho Farm Taadaa
1. **Coordinator Phiên Chính (Hermes 24/7):** Bắt buộc chạy model 0đ có Context Window lớn (`Gemini 3.8 Flash` qua OmniRoute `:20129`). Coordinator gánh lịch sử chat và context lớn gấp 30 lần Worker, cấm dùng Claude Pro ngồi ghế này.
2. **Worker Thi Công Thường Nhật (90% công việc):** Gọi `python D:/Taadaa/tools/haiku_worker.py` (Claude Haiku 5.5 1-shot). Tốc độ 6s–15s, diff O(1) siêu sạch, tốn rất ít quota Claude Pro.
3. **Worker Hạng Nặng / Batch Lớn:** Gọi `python D:/Taadaa/tools/ag_cli.py` (Pool 7 Acc Pro xoay vòng LRU + Proxy 4G). Hoàn toàn miễn phí, cày cuốc thâu đêm không sợ chạm trần quota.
