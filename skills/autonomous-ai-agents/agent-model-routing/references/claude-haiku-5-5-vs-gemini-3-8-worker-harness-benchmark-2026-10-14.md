# Benchmark Thực Chiến: Claude Haiku 5.5 (CLI) vs Gemini 3.8 Flash (OmniRoute / Agy CLI) (14/10/2026)

## 1. Bối cảnh & Mục tiêu Thử nghiệm
Đo lường thực tế năng lực của **Claude Haiku 5.5** và **Gemini 3.8 Flash** trong vai trò **Worker lập trình Phone Farm Taadaa**, phân tích sự khác biệt giữa "Trí tuệ mô hình" (Brain) và "Bộ yên cương Agent" (Harness: Claude Code CLI vs Antigravity CLI vs Hermes Agent Delegation).

---

## 2. Kết quả Đo lường Trực tiếp 5 Hiệp Đấu (Ground Truth)

### Vòng 1: Nội chiến Claude Haiku 5.5 (Medium vs High Reasoning)
- **Haiku 5.5 Medium**: Thời gian trung bình **16.5s**, thinking ~1.9k–2.6k tokens, cost ~$0.07–$0.11/task. Bám sát Scope Lock O(1), không văn xuôi thừa.
- **Haiku 5.5 High**: Thời gian trung bình **23.8s** (chậm hơn 44%), thinking ~2.3k–4.0k tokens. Hay overthinking, có xu hướng ngắt sớm khi bounds UI nằm ngoài màn hình thay vì tìm node tiếp theo.
- 👑 **Quán quân:** **Claude Haiku 5.5 Medium** thắng thuyết phục (2 - 1).

### Vòng 2 & 5 Hiệp So Găng: Claude Code CLI vs Antigravity CLI / Gemini 3.8

| Hiệp đấu | Bài toán thực chiến | Claude Code CLI (Haiku 5.5 Medium) | Gemini 3.8 Flash (OmniRoute / Agy CLI) | Phán quyết |
| :---: | :--- | :---: | :---: | :--- |
| **1** | **Code Surgery Atomic File trên đĩa** (`parse_adb_devices`) | **20.2s** (6 turns): Tự dùng tool `Edit`, chạy test verification ngầm, diff sạch. | **16.8s** (qua `agy fix`): Sửa file trực tiếp, kiểm tra an toàn `startswith("*")` và `len>=2`. | **HÒA (1 - 1)**: Cả hai CLI đều sửa file thật trên đĩa thành công, pass 100% test suite. |
| **2** | **Center Crop Video 9:16** (Hình học tọa độ video TikTok) | **22.1s**: Dùng `math.gcd` chia tỷ lệ nguyên bản, raise `ValueError` khi khung quá bé. | **1.8s** (qua `agy ask`): Dùng **so sánh tích chéo** (`orig_w*ah > orig_h*aw`) triệt tiêu sai số float. | **Gemini thắng về thuật toán**: Logic tích chéo của Gemini thông minh hơn. |
| **3** | **Parse Proxy String Đa Định Dạng** (HTTP/SOCKS5/Auth) | **19.1s**: Kiểm tra range port 1..65535, chặn ký tự cấm, parse cả `@` và `:`. | **17.3s** (qua OmniRoute): Hỗ trợ thêm `socks5h`, `rstrip('/')`, type check chuẩn. | **HÒA (1 - 1)**: Độ sâu logic ngang nhau. |
| **4** | **Safe Stale Temp Files Cleaner** (Hệ thống file Windows) | **13.7s**: Dùng `FILE_ATTRIBUTE_REPARSE_POINT`, `commonpath`, `st_dev` chống symlink escape. | Dính **RPM Burst Lock** trên Antigravity single-account. | **Claude CLI thắng áp đảo**: Tư duy hệ thống Windows cực sâu, tốc độ 13.7s. |
| **5** | **Khả năng Chịu Tải & Độ Ổn Định Harness** | **5/5 task thành công 100%**: Không timeout, không nghẽn socket, cache 12k tokens mượt. | Single profile bị nghẽn socket sau 4 task liên tiếp. | **Claude CLI thắng tuyệt đối**: Harness của Claude Code phục vụ production chịu tải thực tế tốt hơn. |

---

## 3. Bản chất Sự Khác Biệt: Brain vs Harness

1. **Về Năng Lực Giải Thuật (Brain):**
   - Cả hai model đạt điểm ngang ngửa (9.4/10 vs 9.3/10).
   - Gemini có thế mạnh giải toán/tọa độ/hình học bằng các công thức thanh thoát (tích chéo, modulo).
   - Claude Haiku 5.5 có thế mạnh về lập trình hệ thống (Windows file attributes, socket/reparse points, defensiveness).

2. **Về Bộ Yên Cương (Harness):**
   - **Claude Code CLI (`claude -p ... --dangerously-skip-permissions`):** Thiết kế Headless-first. Tự động chia nhỏ turns (4–6 turns), tự dùng tool `Read`/`Edit`/`Bash`, tự chạy test và sửa lỗi, không bị nghẽn PTY hay lock file.
   - **Antigravity CLI (`agy.exe`):** Thiết kế cho môi trường IDE desktop. Chạy headless qua `ag_cli.py` dễ gặp rủi ro dính lease lock khi tiến trình cha bị ngắt đột ngột, và tài khoản Google cá nhân dính RPM burst lock sau 4–5 request dồn dập.
   - **Gemini qua Hermes Subagent (`delegate_task`):** Chịu overhead dịch giao thức (OpenAI schema $\leftrightarrow$ Google Protobuf) qua OmniRoute `:20129`, dễ bị bẫy ghi đè file nếu không có Gate 2 anchor $c==1$.

---

## 4. Quy Chuẩn Phân Vai Cho Farm Taadaa
- **Worker Thường Nhật (Default 100%):** Dùng `Gemini 3.8 Flash Medium` (`ag-gemini-pool-3` trên OmniRoute) để tận dụng **0đ chi phí** và pool 49 accounts xoay tua, bọc trong Patch Contract O(1).
- **Worker Đặc Nhiệm / Cứu Hộ / Code-Surgery Khó:** Khi cần độ tin cậy tuyệt đối, tránh timeout hoặc khi Gemini bị burst lock, kích hoạt **`Claude Haiku 5.5 Medium` qua Claude Code CLI** (`claude -p ... --model claude-haiku-5-5 --effort medium`). Tốc độ 13–20s, cực kỳ bền bỉ và chi phí rất thấp ($0.07–$0.12/task).
