# Sự cố Windows Terminal _drain GIL Starvation & Gateway Freeze 37 phút (07/10/2026)

## 1. Hiện tượng & Triệu chứng thực tế
- **Thời gian treo cứng:** Gateway Telegram, Cron Scheduler và tất cả session chat bị đóng băng hoàn toàn từ **20:08:51** đến **20:46:12** (~37,6 phút).
- **Log im bặt:** `gateway.log`, `agent.log`, `errors.log` hoàn toàn không ghi nhận thêm bất kỳ dòng nào trong suốt 37 phút.
- **Hồi sinh xả dồn (20:46:12):** Ngay khi hết treo, `agent.log` đồng loạt xả ra hàng chục API calls bị nghẽn với latency ghi nhận vọt lên **2258.0s (~37.6 phút)**, kèm theo hàng loạt thông báo 15+ cron jobs missed schedule kích hoạt cùng 1 giây.
- **Bộ nhớ bất thường:** Private memory của tiến trình Gateway vọt lên **~9.9 GB**, trong khi working set chỉ ~317 MB (hệ thống liên tục swap paging ảo).

## 2. Nguyên nhân gốc rễ (Root Cause Analysis qua Py-Spy & Code Audit)
- **Py-Spy call stack:** Khi gateway còn đang bị treo (~20:44), công cụ `py-spy dump` kiểm tra tiến trình Python cho thấy Main Event Loop hoàn toàn idle (không dính deadlock hay exception), nhưng có duy nhất một thread ở trạng thái `active + GIL`: `Thread-89538 (_drain)`.
- **Đoạn code thắt nút cổ chai (`tools/environments/base.py`):**
  Trong hàm `_wait_for_process`:
  ```python
  def _drain():
      ...
      if os.name == "nt":
          try:
              while True:
                  chunk = os.read(fd, 4096)
                  if not chunk:
                      break
                  output.append(decoder.decode(chunk))
          except (ValueError, OSError):
              pass
  ```
- **Cơ chế gây nghẽn 4 tầng:**
  1. *Hạn chế của Windows OS:* Windows không hỗ trợ `select.select()` trên anonymous pipe file descriptor (chỉ hỗ trợ socket). Vì vậy Hermes phải dùng blocking `os.read(fd, 4096)` trong daemon thread `_drain`.
  2. *Subprocess xả output không kiểm soát:* Một tiến trình con (hoặc script terminal nội bộ) in ra lượng log khổng lồ liên tục ở tốc độ cao mà không có rate limit.
  3. *Hàng triệu chuỗi nhỏ & Paging Disk:* Thread `_drain` liên tục đọc các chunk 4KB và nhét vào danh sách `output`. Hàng chục triệu object chuỗi nhỏ đẩy Private Bytes lên **9.9 GB**.
  4. *GC Thrashing giữ chặt GIL (Global Interpreter Lock):* Garbage Collector của Python liên tục bị kích hoạt để scan hàng chục triệu object trên bộ nhớ phân mảnh (virtual memory swap). Việc dọn rác và phân bổ chuỗi liên tục giữ chặt **GIL**. Vì Python chạy đơn luồng bytecode (GIL), toàn bộ các thread khác (mạng Telegram Webhook/polling, Cron scheduler, luồng stream LLM HTTP) bị **đói CPU (Starvation)** và đóng băng hoàn toàn.

## 3. Dấu hiệu phân biệt với các lỗi treo khác
| Đặc điểm | _drain GIL Starvation | Event Loop Saturation (Subagent) | Disk Full 100% | SQLite WAL Bloat |
|---|---|---|---|---|
| **Private Memory** | **Vọt lên 5GB – 10GB** | Bình thường (~500MB - 1GB) | Bình thường | Tăng nhẹ theo SQLite |
| **Trạng thái log** | **Im bặt 100% mọi log** | Có cảnh báo timeout 600s | Văng `[Errno 28] No space` | Văng `disk I/O error` |
| **Sau khi hồi phục** | **API call latency ~2000s+** | Xả 1 loạt 170+ requests | Trở lại bình thường | Truy vấn DB nhanh lại |
| **Py-Spy profiling** | **Thread `_drain` active+GIL** | Main thread busy coroutines | Kernel I/O wait lock | SQLite C-extension lock |

## 4. Giải pháp khắc phục & Phòng ngừa
1. **Hard Buffer Cap trong `_drain` (`tools/environments/base.py`):** Đặt trần cứng an toàn `max_capture = 100 * 1024 * 1024` (100MB). Khi vượt quá 100MB, output tự động chèn thông báo cắt ngắn `[OUTPUT TRUNCATED BY ENVIRONMENT SAFETY CEILING (100MB)]` và dừng nạp chunk mới vào danh sách `output`, bảo vệ tuyệt đối RAM không bị phình lên hàng GB.
2. **Nhả GIL định kỳ trên Windows:** Trong vòng lặp `os.read(fd, 4096)` trên Windows, chèn `time.sleep(0.0001)` ngay sau mỗi chunk 4KB để nhả GIL cho các luồng mạng Telegram Gateway, Cron jobs và Heartbeat chạy mượt mà, triệt tiêu nguy cơ đói CPU (Starvation).
3. **Đồng bộ song song vào Site-Packages & Git Root:** Vá trực tiếp vào cả `tools/environments/base.py` trong source git và `venv/Lib/site-packages/tools/environments/base.py` để có hiệu lực ngay lập tức trong runtime active.
4. **Kỷ luật Subprocess Output:** Các script chạy nền/download/render dài hạn bắt buộc phải redirect output ra file log hoặc chạy với `python -u` có filter, cấm spam stdout hàng triệu dòng vào pipe của Hermes.
