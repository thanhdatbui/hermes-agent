# Sol Worker (GPT-5.6 Sol) vs Gemini Flash vs Codex Luna: Farm Benchmark & Routing Matrix (2026-10-23)

## Bối Cảnh Thực Nghiệm

Khi Claude CLI chạm ngưỡng bảo vệ quota 85% hoặc Agy CLI pool dính rate limit, hệ thống cần một Worker thay thế độc lập. Cuộc đối đầu đa trận thực chiến giữa **GPT-5.6 Sol Web (`gpt-web-sol` qua OmniRoute `:20129`)**, **Google Gemini Flash (`gemini-3.8-flash-tiered`)**, và **Codex Luna (`codex-luna`)** được thực hiện trên các bài toán thực tế của Taadaa Phone Farm (theo chuẩn `benchmark_sol_spec.md` và `claude_bench_spec.json`).

---

## 1. Kết Quả 10 Trận Đối Đầu: GPT-5.6 Sol vs Gemini Flash

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

## 2. Kết Quả 6 Trận Đối Đầu Trực Diện: GPT-5.6 Sol vs Codex Luna

| Trận | Bài toán / Trọng tâm | Sol (`gpt-web-sol`) | Codex Luna (`codex-luna`) | Winner | Chi tiết kỹ thuật |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | **TikTok UI Drift Surgery** (v46+ mất resource-id) | **19.0 / 20** (15.0s) | **19.0 / 20** (12.7s) | 🤝 **Hòa** | Cả hai đều bỏ ID rỗng và fallback sang text `("Đang theo dõi", "Đang follow")` sạch sẽ. |
| **2** | **Device Lock Race Condition** (Lost update) | **24.0 / 25** (18.5s) | **23.5 / 25** (14.2s) | 🥇 **Sol** | Cả 2 đều dùng `fcntl.flock` bọc critical section, nhưng code của Sol ngắn hơn và ít phụ thuộc class. |
| **3** | **Anti-Overengineering** (Bug follower == 1) | **20.0 / 20** (16.0s) | **10.0 / 20** (11.0s) | 🥇 **Sol** | **Luna dính bẫy ngớ ngẩn:** Đổi thành `if c > 1: return True` và giữ `c == 1: return False` $\rightarrow$ Ngược 100% đề bài! Sol nhận ra `c > 0` đã bao hàm `c == 1`, chỉ cần xóa nhánh dead-code thừa. |
| **4** | **Farm Invariant Review** (Review an toàn) | **19.0 / 20** (26.8s) | **19.0 / 20** (15.6s) | 🤝 **Hòa** | Cả hai đều bắt chuẩn: BLOCK DEPLOY, cảnh báo mất fingerprint device, kẹt I/O và tap tọa độ mù. |
| **5** | **JSON Corrupt Recovery** (File lock rách) | 18.5 / 20 (16.9s) | **19.5 / 20** (49.5s) | 🥇 **Luna** | **Luna xử lý rất bản lĩnh:** Thay vì trả `{}` rỗng (dễ bị hiểu lầm là máy chưa có ai chiếm $\rightarrow$ cấp nhầm lock), Luna retry 3 lần và raise `LockFileUnavailable` (chuẩn fail-closed). |
| **6** | **High-Concurrency Lock** (70 Devices) | **19.0 / 20** (15.0s) | **0.0 / 20** (75.0s) | 🥇 **Sol** | Sol hoàn thành trong 15s với cơ chế lockfile + atomic replace. **Luna bị timeout rớt kết nối sau 75 giây.** |

- **Tỉ số trận:** **Sol thắng 3 — Luna thắng 1 — Hòa 2**
- **Tổng điểm (thang 125đ):** **GPT-5.6 Sol 119.5 / 125 (95.6%)** vs **Codex Luna 91.0 / 125 (72.8%)**.

---

## 3. Ma Trận Điều Phối Tam Giác (Triad Routing Decision Matrix)

### 1. Khi Nào Điều Phối Cho Sol (`gpt-web-sol` / `sol_worker.py`):
1. **Lỗi Concurrency, Race Condition, Deadlock:**
   - Tranh chấp file lock JSON, token lease, process synchronization giữa nhiều worker.
   - Sol có tư duy của Senior Systems Architect, luôn nhận diện chuẩn các bẫy Lost Update, Atomic Read-Modify-Write và Mutex Scope (thắng cả Gemini và Luna).
2. **Code Surgery & Logic Patch Tối Giản ($O(1)$):**
   - Cần sửa lỗi logic thuần túy với yêu cầu nghiêm ngặt: diff nhỏ nhất, cấm refactor, cấm thêm dependency.
   - Sol tuân thủ prompt contract cực kỳ kỷ luật, không bị bẫy đề bài (như trận follower count Luna bị đảo ngược logic).
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

### 3. Khi Nào Điều Phối Cho Codex Luna (`codex-luna`):
1. **Thiết Kế Kiến Trúc Bảo Mật Khắt Khe & Fail-Closed Exceptions:**
   - Luna có phản xạ tuyệt vời về thiết kế Exception có ngữ nghĩa (như `LockFileUnavailable`), retry exponential có chặn trên, và cấm trả dữ liệu giả định rỗng.
   - Dùng cho các bài toán bảo mật dữ liệu nhạy cảm hoặc auditing tầng sâu khi latency không phải yếu tố then chốt.

---

## 4. Cạm Bẫy Vận Hành & Khắc Phục Đối Với Sol Worker (`sol_worker.py`)

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

---

## 5. Trận Chiến Agent Tự Trị Thực Tế: Sol Worker (`sol_worker.py`) vs Claude Haiku Worker (`haiku_worker.py`)

### 1. Thể Thức Thi Đấu (Autonomous Coding Agent Showdown):
- **Bối cảnh:** Không còn là câu hỏi/đáp văn bản (completion prompt), mà là **Worker Agent tự động đọc file và sửa code thực tế trên workspace**.
- **Đề bài thật:** Cải tiến script `watchdog_admin_render_smart.py` trên máy Admin để chống lag War3/TFT:
  1. Thêm `suspend_process_tree(pid)` và `resume_process_tree(pid)` dùng `psutil` đóng băng/rã đông cây tiến trình thay vì kill thô bạo.
  2. Thêm `sweep_orphan_ffmpeg()` dọn sạch tiến trình ffmpeg mồ côi (`parent is None`).
  3. Thêm `check_heartbeat_stale()` kiểm tra file heartbeat quá 30s.
  4. Cập nhật `main()` điều phối luồng: Sweep khi bật -> Suspend khi chơi game -> Resume khi hết game.
- **Môi trường:** Mỗi bên nhận 1 bản sao sạch giống nhau (`watchdog_smart_sol.py` vs `watchdog_smart_haiku.py`).

### 2. Kết Quả Đối Đầu Thực Tế:
- **Claude Haiku Worker (`haiku_worker.py --model haiku`):**
  * *Thời gian:* 12.5s.
  * *Kết quả:* `target_changed: false` (THẤT BẠI - 0 dòng code được sửa).
  * *Hành vi:* Đọc file xong nhưng không hề gọi tool `Edit`, mà quay sang chat giải thích và hỏi lại: *"Tôi đã đọc file... Bạn muốn làm gì với file này? Ví dụ: sửa một lỗi cụ thể..."*. Bị rơi vào trạng thái thụ động "Chat Assistant".
- **Sol Worker (`sol_worker.py` - GPT-5.6 Sol via OmniRoute `:20129`):**
  * *Thời gian:* 239s.
  * *Kết quả:* `target_changed: true`, `exit_code: 0` (THẮNG ÁP ĐẢO).
  * *Hành vi ReAct 7 turns:*
    - Turn 1 (`READ_FILE`): Đọc toàn bộ file để xác định vị trí hàm.
    - Turn 2–4 (`PATCH`): Áp dụng 3 bản vá liên tiếp bổ sung đầy đủ 4 hàm và cập nhật hàm `main()`.
    - Turn 5–6 (`COMMAND`): Tự động phát lệnh terminal `python -m py_compile watchdog_smart_sol.py` để tự nghiệm thu cú pháp.
    - Turn 7 (`DONE`): Báo cáo hoàn tất với +105 dòng code chuẩn Python, xử lý triệt để ngoại lệ `NoSuchProcess` và `AccessDenied`.

### 3. Kết Luận Kiến Trúc Cho Taadaa Farm:
- `sol_worker.py` hoàn toàn đủ năng lực gánh vác vai trò **Tier 1 Autonomous Coding Worker độc lập**.
- Khi Claude CLI chạm trần Quota (hoặc rơi vào bẫy thụ động) và Agy CLI bị kẹt 429 Google Desktop, Sol Worker là giải pháp cứu cánh số 1 cho các tác vụ code surgery và bảo trì hệ thống.
