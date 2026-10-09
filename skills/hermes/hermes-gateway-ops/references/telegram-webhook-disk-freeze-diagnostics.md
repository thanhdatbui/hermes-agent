# Telegram Webhook, Disk Starvation & Event Loop Diagnostic Guide

## 1. Triệu chứng & Bản chất (Treo 5-10 phút trên Telegram)
Khi người dùng phản ánh: *"Bot Telegram thỉnh thoảng treo cứng 5-10 phút không trả lời, trên OmniRoute không thấy có request nào"*, quy trình điều tra cần rà soát theo 3 chặng độc lập:

1. **Chặng 1 (Mạng & Webhook Telegram):**
   - **Silent Drop Long-polling:** Mạng ISP (FPT/VNPT) ngắt ngầm socket TCP Long-polling (`getUpdates`) mà không gửi RST packet $\rightarrow$ Bot ngâm socket 5-10 phút chờ timeout.
   - **Fix dứt điểm:** Chuyển sang Telegram Webhook qua Cloudflare Tunnel (`bot.domain.com` $\rightarrow$ `127.0.0.1:8443`).
   - **Telegram Error: "Read timeout expired":** Khi Webhook nhận tin, nếu Event Loop trên máy bị block đồng bộ $> 5s$, Telegram Server không nhận được `HTTP 200` và sẽ phạt Exponential Backoff: `1s -> 2s -> 5s -> 10s -> 30s -> 60s -> 300s (5 phút)`. Trong suốt thời gian này, Telegram ngừng bắn tin về máy!

2. **Chặng 2 (Disk Starvation / Out of Space [Errno 28]):**
   - **Thủ phạm:** Các thư mục tự động backup SQLite (ví dụ `C:\Users\<user>\.omniroute\db_backups`) tích tụ hàng trăm file backup nặng 2.7GB, nuốt trọn 100% ổ C (`0 bytes free`).
   - **Hậu quả:** Mọi lệnh ghi file, append log, commit SQLite (`state.db`, `storage.sqlite`) bị treo cứng ở tầng OS Kernel I/O.
   - **Dấu hiệu:** Log gateway báo `[Errno 28] No space left on device` hoặc `kanban dispatcher: tick failed`. Toàn bộ 10+ session bị freeze đồng loạt.
   - **Fix:** Xóa các file `.bak` cũ, giữ lại tối đa 5 bản backup mới nhất.

3. **Chặng 3 (Event Loop Sync Block do Disk I/O Media):**
   - Thao tác `cache_image_from_bytes(bytes(image_bytes))` nếu gọi trực tiếp trên main thread sẽ block toàn bộ Event loop khi ghi file lớn.
   - **Fix:** Luôn bọc qua `await loop.run_in_executor(None, cache_image_from_bytes, image_bytes, ext)`.

4. **Chặng 4 (Regex Hook Escaping / Word Boundary Trap):**
   - Các hook chặn quét đĩa `guard_broad_grep.py` dễ bị lọt nếu dùng `r"D:[\\/]?$"` (có dấu `$` cứng) hoặc `\b` bị chuyển thành `\x08` (backspace).
   - Phải thiết kế regex theo 4 tầng: (1) Detect binary (`grep`, `grep.exe`, `rg`), (2) Detect flag recursive (`-r`, `-rn`, `-R`, `--recursive`), (3) Normalize paths, (4) Block protected roots.
