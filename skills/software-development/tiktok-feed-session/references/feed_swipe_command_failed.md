# Root Cause & Recovery: Feed Swipe Command Failed

## Triệu chứng
- Alert log: `feed swipe command failed` kèm `xml_error: swipe-command-failed`, `safety_status: SAFETY_FAILED`.
- Phiên chạy feed bị dừng ngay lập tức tại bước `swipe_<N>_after`.

## Vị trí mã nguồn
- Flow: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`
  - Hàm thực thi: `_perform_feed_swipe(ctx, swipe_count, ...)`
  - Caller xử lý kết quả: `run_feed_session_smoke(...)` (khối kiểm tra `if not _perform_feed_swipe(...)`)

## Phân tích nguyên nhân gốc rễ (Root Cause)
1. Trong `_perform_feed_swipe`:
   ```python
   cmd = ["input", "swipe", str(start[0]), str(start[1]), str(end[0]), str(end[1]), str(duration_ms)]
   try:
       result = ctx.adb.shell(cmd, timeout=swipe_timeout)
   except ADBError as exc:
       # Chỉ retry khi văng ADBError (transport timeout / executable missing)
       ...
   if not result.ok:
       # Không hề có retry khi result.ok == False (exit code != 0 hoặc transient stderr)
       ctx.logger.log(..., error=result.stderr.strip() or "swipe command failed")
       return False
   ```
2. `ctx.adb.shell` trả về `AdbResult(..., exit_code)`. Khi adb daemon gặp lỗi tạm thời (daemon busy, pipe broken, buffer overflow), `result.ok` là `False` nhưng KHÔNG raise `ADBError`.
3. Do thiếu vòng lặp retry cho `not result.ok`, hàm lập tức trả về `False`. Caller coi đây là lỗi nghiêm trọng, ghi nhận `feed swipe command failed` và hủy toàn bộ phiên chạy.

## Giải pháp khắc phục (Standard Fix)
- Bổ sung retry loop (tối đa 2-3 lần, sleep 1.0s) bao phủ cả `not result.ok` lẫn `ADBError`.
- Kiểm tra lại kết nối ADB (`reconnect` nếu cần) giữa các lần thử trước khi fail hẳn.
- Đảm bảo tham số swipe (tọa độ trục X clamped trong dải 450..540, start_x == end_x) không bị biến dạng.

## Lưu ý tra cứu log tránh Tool Timeout
- Tuyệt đối KHÔNG dùng `os.walk`, `rg`, `grep -rn` quét `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs` vì thư mục có hơn 500 runs và hàng chục nghìn artifacts, sẽ gây timeout 900s.
- Lấy folder mới nhất bằng `os.listdir("D:/Taadaa/tiktok-luot nuoi acc/.ai-runs")` và filter tiền tố ngày tháng (VD: `20260906*`), sau đó đọc trực tiếp `machines/machine_<N>/<timestamp>/summary.txt`.
