# Pre-Tool Auto-Rewrite & 24h Heartbeat Watchdog Architecture

## 1. Engine-Level Pre-Tool Auto-Rewrite (`action: rewrite`)

### Bối cảnh & Vấn đề giải quyết
Trước đây, các hook bảo vệ chạy ở tầng pre-tool chỉ hỗ trợ `action: block` hoặc `action: approve`. Khi một lệnh của Agent thiếu tham số an toàn (ví dụ thiếu `timeout` trong lệnh `terminal`), hook chặn bằng `action: block` thụ động. Điều này dẫn đến:
- Agent mất ít nhất 1 turn đọc lỗi và 1 turn sinh lại câu lệnh.
- Các model như Gemini có xu hướng "lươn lẹo" tìm đường vòng thay vì sửa tham số (ví dụ: bị chặn timeout thì chuyển sang viết script python, gọi PowerShell, hoặc spawn subagent), gây ra vòng lặp lách luật 8–9 turn làm cạn token.
- Lỗi `GUARD_FOREGROUND_TIMEOUT_MISSING` tích tụ tới hơn 3.900 lần block trong lịch sử.

### Cơ chế kỹ thuật trong nhân Hermes
- **`agent/shell_hooks.py` (`_parse_response`):** Hỗ trợ parse response trả về từ hook có `"action": "rewrite"` kèm `"updated_args"` (hoặc `"updated_input"`).
- **`hermes_cli/plugins.py` (`_get_pre_tool_call_directive_details`):** Khi directive là `rewrite`, engine thực hiện in-place mutation trực tiếp vào `tool_input_kwargs`:
  ```python
  if action == "rewrite":
      updated = result.get("updated_args") or result.get("updated_input")
      if isinstance(updated, dict) and isinstance(args, dict):
          args.update(updated)
      continue
  ```
- **Hành vi thực tế:** Tool được cập nhật tham số ngay trong RAM và thực thi ngay lập tức. Agent hoàn toàn không nhận thấy lỗi, không tốn thêm bất kỳ turn nào (`Turn Overhead = 0`).

### 2 Hook đã chuyển đổi sang Auto-Rewrite
1. **`hooks/guard_broad_grep.py`:**
   - Khi lệnh terminal foreground thiếu `timeout`, tự động inject `timeout=60` (hoặc `360s` cho các công cụ allowlist điều phối như `dispatch_worker`, `pytest`, `closeout_gate`).
2. **`hooks/guard_read_file_size.py`:**
   - Khi đọc trần file > 10MB mà không có slice, tự động kẹp `offset = max_lines - 200, limit = 200` để chỉ lấy 200 dòng cuối, chống tràn RAM. Nếu model đã chủ động chỉ định slice hợp lệ (`limit <= 2000`) thì cho qua nguyên vẹn.

---

## 2. Tiêu Chuẩn "Exception-Driven Alerting & 24h Heartbeat" Cho Watchdog

### Vấn đề "Im Lặng Giả Tạo" (False-Negative Masking)
Khi áp dụng nguyên tắc *"Bình thường thì im lặng, chỉ có lỗi mới bắn báo cáo"*, nảy sinh rủi ro: Nếu cronjob bị treo, file log bị mất, hoặc DB rỗng không đọc được, hệ thống cũng "im lặng", khiến Operator tưởng hệ thống bình an vô sự trong khi thực tế đã chết lâm sàng.

### Nguyên tắc cốt lõi (Core Invariants)
1. **Chỉ im lặng khi có bằng chứng dương tính về sức khỏe:** "Không thấy lỗi" không đủ để im lặng. Hệ thống phải chứng minh được: nguồn dữ liệu đọc được, có dữ liệu mới, và các metric nằm trong ngưỡng cho phép.
2. **Hệ thống 3 trạng thái:** `NOMINAL | ANOMALY | UNKNOWN`. Mọi exception chưa bắt, timeout, DB rỗng không rõ lý do đều quy về `UNKNOWN -> ANOMALY` (Fail-Closed).
3. **Dead-Man's Switch (Bảng Heartbeat 24H độc lập):**
   - Một watchdog độc lập (`cron_heartbeat.py`) chạy vào **02:00 UTC (09:00 sáng VN)** hàng ngày (theo yêu cầu vận hành chính thức của Operator).
   - Nó không chạy việc, mà kiểm tra file state JSON (`runtime/cron_health/<script>.json`) của toàn bộ các watchdog.
   - Nếu một watchdog quá `2 * interval + 30 phút` chưa cập nhật state -> Đánh dấu `❌ STALE` và báo động ngay.
   - Nếu toàn bộ đều khỏe -> Gửi đúng 1 bản tin điểm danh 3 dòng lúc 09:00 sáng để xác nhận toàn bộ hệ thống giám sát vẫn đang thở đều.

### Khóa Chống Rớt Vi Phạm Ngầm Trên 10 Gate Cơ Giới Hóa
- **10 Gate Giám Sát:** Bổ sung G9 Android Proxy Guard và G10 Claude Quota Gate vào `gate_compliance_watchdog.py`.
- **Fail-Closed theo File mtime:** Dòng log có chứa từ khóa chặn (`action: block`, `DENY`, `REJECTED`) nhưng timestamp bị dị dạng/không parse được thì đối chiếu mtime của file log (nếu <= 6h) để bắt buộc đếm vào vi phạm, không vứt bỏ dòng log.
- **Cổng Catch-All `[Unclassified]`:** Bắt sạch các lỗi chặn từ hook mới chưa kịp phân loại vào gate cụ thể.
- **Lọc hiển thị vi phạm:** Ẩn hoàn toàn các Gate 0 lỗi, chỉ in danh sách các Gate có vi phạm/remediation để Operator tập trung xử lý.

### Kiến trúc thư viện `CronRun` (`cron_alert_core.py`)
Mọi watchdog script được chuẩn hóa bọc qua context manager:
```python
with CronRun("script_name", force_report="--force" in sys.argv) as run:
    # 1. Kiểm tra nguồn (Fail-Closed nếu rỗng)
    data = run.require_source(load_data, name="database", allow_empty=False)
    
    # 2. Đánh giá metric
    run.check("metric_err_rate", error_rate, ok=lambda v: v <= 0.05, severity="P1")
    
    # 3. Gắn báo cáo tuỳ biến nếu có sự cố
    run.set_report(formatted_report_msg)
```
- Khi `NOMINAL` và không có `--force`: Ghi state file `NOMINAL`, trả stdout rỗng -> Hermes Scheduler tự động im lặng, không spam Telegram.
- Khi `ANOMALY`: Ghi state file `ANOMALY`, in báo cáo ra stdout -> Hermes Scheduler tự động bắn alert về kênh chỉ định.

### Pitfalls & Bài Học Thực Chiến
1. **Xử lý `sys.exit(0)` trong `CronRun.__exit__` (`is_clean_exit`):**
   - Các script cron cũ thường kết thúc bằng `sys.exit(0)`. Trong Python, `sys.exit()` tung ngoại lệ `SystemExit`.
   - Nếu `__exit__` chỉ bắt `if exc_type is not None:`, nó sẽ coi `SystemExit(0)` là lỗi crash `UNHANDLED_EXCEPTION (P0)`.
   - **Bắt buộc phân biệt:**
     ```python
     is_clean_exit = exc_type is not None and issubclass(exc_type, SystemExit) and (exc_val is None or getattr(exc_val, "code", 0) == 0)
     if exc_type is not None and not is_clean_exit:
         # Ghi nhận UNHANDLED_EXCEPTION
     ```
2. **Lịch Heartbeat 09:00 Sáng VN (02:00 UTC):**
   - Scheduler chạy theo múi giờ máy chủ cục bộ (Windows local time). Lịch chuẩn cho Heartbeat là `0 9 * * *` (09:00 sáng VN / 02:00 UTC), đến đúng đầu giờ làm việc sau khi các ca rạng sáng đã hoàn tất.
3. **Mô hình `set_report(msg)` kết hợp `force_report`:**
   - Thay vì in trực tiếp ra stdout, script gọi `run.set_report(msg)`. Nếu bình thường thì `msg` được giấu kín (chống spam); khi có anomaly hoặc khi người dùng chạy tay với `--force`, `msg` mới được bung ra.
