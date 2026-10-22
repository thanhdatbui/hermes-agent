# Sol Worker (GPT-5.6 Sol) vs Gemini Flash: 10-Round Farm Benchmark & Routing Matrix (2026-10-23)

## Bối Cảnh Thực Nghiệm

Khi Claude CLI chạm ngưỡng bảo vệ quota 85% hoặc Agy CLI pool dính rate limit, hệ thống cần một Worker thay thế độc lập. Cuộc đối đầu 10 trận thực chiến giữa **GPT-5.6 Sol Web (`gpt-web-sol` qua OmniRoute `:20129`)** và **Google Gemini Flash (`gemini-3.8-flash-tiered`)** được thực hiện trên các bài toán thực tế của Taadaa Phone Farm (theo chuẩn `benchmark_sol_spec.md` và `claude_bench_spec.json`).

---

## Kết Quả 10 Trận Đối Đầu Chi Tiết

| Trận | Đề bài / Trọng tâm | Điểm Sol | Điểm Gemini | Winner | Nhận xét mấu chốt |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | **TikTok UI Drift Surgery** (v46+ rỗng `resource-id`) | **19.5** | 17.0 | 🥇 **Sol** | Sol bỏ hẳn `resource-id`, gom tuple text gọn trong 6 dòng. Gemini bị lồng if trong nhánh ID cũ. |
| **2** | **Device Lock Race Condition** (Lost Update 70 máy) | **24.0** | 18.0 | 🥇 **Sol** | Sol bắt đúng bản chất Lost Update, dùng `fcntl.flock` bọc toàn bộ chu trình `update_locks(mutator)`. Gemini sót race. |
| **3** | **Anti-Overengineering** (Fix bug count == 1) | **20.0** | **20.0** | 🤝 **Hòa** | Sol xóa dead-code thừa; Gemini rút gọn thành `return count > 0`. Cả 2 đều chuẩn, diff <= 5 dòng. |
| **4** | **Farm Invariant Review** (`pm clear`, `scan disk`) | 18.0 | **19.5** | 🥇 **Gemini** | Gemini am hiểu thực địa farm sâu sắc: SSAID/GAID device churn, host disk I/O spike, DPI Android, anti-cheat. |
| **5** | **Tool Hands & JSON Corrupt Recovery** | **19.0** | 18.5 | 🥇 **Sol** | Sol có insight cảnh báo đắt giá: *"Trả về None không đồng nghĩa với không có owner, dễ cấp nhầm lock"*. |
| **6** | **High-Concurrency Lock (70 Devices)** | 19.0 | **20.0** | 🥇 **Gemini** | Gemini hỗ trợ cả Windows (`msvcrt`) lẫn Linux (`fcntl`), có `f.truncate()` + `os.fsync()` chống rách file. |
| **7** | **Samsung S7 ADB Wake & Splash** | 18.0 | **20.0** | 🥇 **Gemini** | Gemini dùng `KEYCODE_WAKEUP 224` + `wm dismiss-keyguard` gạt khóa vuốt S7, né lag Exynos 8890. |
| **8** | **Anti-Blind Input & Gate 6 Enforcement** | 18.0 | **20.0** | 🥇 **Gemini** | Gemini pipe ảnh vào RAM qua `exec-out screencap -p` (chống hại SSD), WinRT OCR, Max blind step = 1. |
| **9** | **Follow Streak Anti-Overengineering** | 19.0 | **20.0** | 🥇 **Gemini** | Gemini viết 7 dòng, hỗ trợ cả dict lẫn object, giải thích streak invariant và cooldown 86400s. |
| **10** | **State Detection Guard & Fail-Closed** | 19.0 | **20.0** | 🥇 **Gemini** | Gemini tư duy Short-circuit: check từ khóa cấm ("Tạm khóa") trước để thoát ngay, bọc try-catch fail-closed. |

- **Tỉ số trận:** **Gemini Flash thắng 6 — Sol thắng 3 — Hòa 1**
- **Tổng điểm (thang 200đ):** Gemini Flash 193.0 / 200 (96.5%) vs Sol 193.5 / 200 (96.75%).
- **Tốc độ phản hồi:** Sol mất **15s – 32s/turn** qua OmniRoute `:20129`. Timeout per-turn 300s là hoàn toàn an toàn.

---

## Ma Trận Điều Phối (Routing Decision Matrix)

### 1. Khi Nào Điều Phối Cho Sol (`gpt-web-sol` / `sol_worker.py`):
1. **Lỗi Concurrency, Race Condition, Deadlock:**
   - Tranh chấp file lock JSON, token lease, process synchronization giữa nhiều worker.
   - Sol có tư duy của Senior Systems Architect, luôn nhận diện chuẩn các bẫy Lost Update, Atomic Read-Modify-Write và Mutex Scope.
2. **Code Surgery & Logic Patch Tối Giản ($O(1)$):**
   - Cần sửa lỗi logic thuần túy với yêu cầu nghiêm ngặt: diff nhỏ nhất, cấm refactor, cấm thêm dependency.
   - Sol tuân thủ prompt contract cực kỳ kỷ luật, không bao giờ "ngứa tay" viết thêm class thừa.
3. **Phân Tích Kiến Trúc An Toàn & Invariant Review:**
   - Đánh giá thiết kế hệ thống, phân tích rủi ro P0/P1 trước khi triển khai.

### 2. Khi Nào Điều Phối Cho Gemini Flash (`ag_cli.py` / `omniroute`):
1. **Nhiệm Vụ Thực Địa Android Phone Farm & ADB:**
   - Điều khiển thiết bị Samsung S7, xử lý Activity, SplashActivity, keyevents, màn hình khóa vuốt.
   - Gemini nắm vững các đặc tính phần cứng Exynos, lệnh ADB tối ưu IO (pipe screencap qua RAM thay vì ghi disk).
2. **Xử Lý UI Drift, OCR & Gate 6:**
   - Phát hiện màn hình checkpoint, nhận diện văn bản tiếng Việt từ WinRT OCR / UIAutomator XML.
   - Thiết kế luồng Fail-Closed và Short-Circuiting khi tài khoản bị khóa.
3. **Mã Nguồn Đa Nền Tảng (Windows + Linux):**
   - Tự động nhận diện host OS (`sys.platform == 'win32'`) để dùng `msvcrt` thay vì chỉ phụ thuộc `fcntl` của Unix.

---

## Cạm Bẫy Vận Hành & Khắc Phục Đối Với Sol Worker (`sol_worker.py`)

1. **Bẫy Cạn `max_turns` (Lỗi Exit 124):**
   - *Hiện tượng:* `MAX_TURNS_REACHED: Task did not complete within 6 turns`.
   - *Căn nguyên:* Không phải do timeout mạng, mà do Sol thực hiện chu trình ReAct (`READ_FILE` -> `PATCH` -> `COMMAND` test) tốn 4–5 turns. Nếu đặt `max_turns = 6`, Sol sẽ hết lượt trước khi kịp phát lệnh `ACTION: DONE`.
   - *Khắc phục:* BẮT BUỘC đặt `--max-turns` tối thiểu là **8 đến 10 turns**.
2. **Bẫy Ảo Giác Endpoint API:**
   - Khi Sol tự viết code gọi nội bộ, Sol có xu hướng suy diễn sai cổng (`:20128` thay vì `:20129`) hoặc đoán bừa route (`/api/quotas`).
   - *Khắc phục:* Coordinator BẮT BUỘC cung cấp sẵn Exact API Contract (URL đầy đủ và cấu trúc JSON trả về) trong prompt giao việc cho Sol.
3. **Tích Hợp Quota Real-Time Cho Dàn Agy CLI:**
   - OmniRoute `:20129/api/usage/provider-limits` chứa cache live của toàn bộ pool. Key `gemini-3.1-flash-lite` hoặc `gemini-3.7-flash-tiered` dùng chung family bucket với `gemini-3.8-flash-high`.
   - Controller `ag_cli.py` bắt buộc đọc cache này để lọc bỏ acc `remainingPercentage <= 0.0` và ưu tiên acc còn nhiều quota nhất lên đầu, triệt tiêu 100% tình trạng duyệt mù dính 429.
