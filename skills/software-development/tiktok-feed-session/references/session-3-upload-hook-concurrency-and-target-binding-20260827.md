# Session 3 Upload Hook Concurrency & Target Binding Rules

## 1. Bối cảnh sự cố (2026-08-26 / 2026-08-27)
Ở Phiên 3 (phiên cuối của ca), flow nuôi acc `multi_machine_feed_session.py` tự động kích hoạt `_run_upload_hook()` để đăng video cho toàn bộ máy trong cohort.
Tuy nhiên, 62 máy đồng loạt bị `upload-timeout` (1200s) vì:
1. **Unbounded Fan-out**: Không giới hạn số lượng tiến trình upload con chạy song song khiến hàng chục worker `tiktok-video` đè lệnh ADB (screencap, XML dump, ATX JSON-RPC) lên ADB server port 5037 cùng lúc.
2. **Ambiguous Machine Target**: Gọi `scripts.tiktok_workflow` với tham số `--machine` khiến từng child workflow phải tự đọc workbook và resolve lại serial/row từ đầu, dễ bị nghẽn/lệch target trong lúc batch đang chạy.
3. **Mất dấu vết khi Timeout**: `subprocess.run(capture_output=True)` giấu kín stdout/stderr khi timeout 1200s, không để lại nguyên nhân child đang dừng ở state nào.
4. **False-Failed Gate**: Kiểm tra report sau upload dùng sai biến `next_video_num` (đúng là `next_video`), khiến kể cả khi subprocess chạy thành công thì parent vẫn đánh rớt sang `failed`.

---

## 2. Quy tắc chuẩn hóa Hook Upload trong Feed Session

### A. Bound Upload Concurrency (Giới hạn tiến trình đồng thời)
- Tách riêng worker feed (`max_workers` mặc định 40, dispatch cohort 72 máy) và worker upload.
- Upload hook bắt buộc phải đi qua Semaphore / Concurrency Lease độc lập (`DEFAULT_UPLOAD_MAX_CONCURRENCY = 16`, khớp chuẩn `$MaxParallel = 16` của `Tiktok-video`).
- Tránh nghẽn ADB server và giữ ổn định kết nối USB hub khi hàng chục worker feed hoàn tất gần như cùng lúc.

### B. Direct Target Binding
- Phải truyền trực tiếp target đã được xác thực ở bước preflight:
  ```python
  command = [
      ctx.config.get("python_exe") or sys.executable,
      "-m", "scripts.tiktok_workflow",
      "--config", str(config_file),
      "--workflow-workbook", str(workbook_path),
      "--single-device", str(account.serial),
      "--video-number", str(next_video),
      "--allow-device-reboot-recovery",
      "--no-dry-run",
  ]
  ```
- Tuyệt đối không chỉ truyền bare `--machine` khi gọi subprocess trong batch.

### C. Fail-Closed Session 3 Gate
- Upload hook và ngân sách timeout outer watchdog chỉ được kích hoạt khi `_effective_session_index(config) == 3`.
- Nếu thiếu session identity hoặc session 1, session 2: bắt buộc fail-closed (trả về `status="skipped"`, `reason="not-final-session"` hoặc `"missing-session-identity"`).
- Không tự fallback về session 3 khi thiếu cấu hình.

### D. Bắt buộc thu thập Timeout Evidence
- Khi bắt được `subprocess.TimeoutExpired`:
  - Trích xuất 500 ký tự cuối của `exc.stdout` và `exc.stderr`.
  - Ghi nhận `upload_queue_wait_seconds` (thời gian chờ lấy semaphore).
  - Lưu đầy đủ vào `upload_result.json` và log JSONL của máy để phục vụ chẩn đoán tức thì.

### E. Hard Gate Xác minh Report sau Upload
- Lấy exact `run_id` từ stdout (`run_id=(run_[a-zA-Z0-9_]+)`).
- Đọc `report.json` tương ứng trong CodexRuntime:
  - `status == "SUCCESS"`
  - `post_verified == True`
  - `video_number == next_video` (đúng video vừa preflight)
- Phải thỏa mãn cả 3 điều kiện trên + exit code 0 + keyword success mới được kết luận `status = "success"`.
