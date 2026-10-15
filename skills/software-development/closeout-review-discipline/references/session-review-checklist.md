# Session Review Checklist & Common Pitfalls

1. **Diff Payload Ceiling:**
   - Trần ngân sách payload Sol High (:20129) là 32KB (`SOL_TARGET_BYTES = 32768`).
   - Diff chiếm tối đa 65% (~21.3 KB). Nếu diff vượt quá, `sol_payload_guard` kích hoạt truncation L4 `(partial)`.
   - File production code bị truncate sẽ bị reviewer trừ điểm nặng (thường kẹt ở 76-82/100).
   - Giải pháp: Tinh gọn test suite, loại bỏ assertion trùng lặp, giữ diff dưới 20.5 KB để đạt `level=L0` (0 truncation).

2. **Watchdog & Farm Process Automation Invariants:**
   - Phải áp dụng tri-state fail-closed (`True` / `False` / `None`).
   - Cleanup action phải ràng buộc với trạng thái action chính (`adb_cleaned` trong telemetry).
   - Telemetry JSON phải có `ts`, `level`, `event`, và `correlation_id` / `run_id`.
   - Timeout đọc từ env var phải clamp range an toàn (`max(5, min(60, val))`).
   - Phải có test regression guard cho các hằng số nhạy cảm (`IDLE_THRESHOLD_SECONDS == 1200`).
