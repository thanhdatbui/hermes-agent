# Headless Incident Auto-Heal Harness & 6-Gate Architecture

## 1. Bản chất Headless Auto-Heal
- Chạy ngầm 100% qua cronjob `incident-auto-heal-dispatcher` (`cron_incident_auto_heal.py`), chu kỳ `*/15 * * * *`, `no_agent: true`.
- Không mở session chat mới trên Telegram để tránh spam và không tranh chấp tài nguyên với session chính.
- Toàn bộ quy trình sao chép 1:1 từ chu trình 5 bước Farm Alert Recovery thủ công sang 6 Cổng tự động.

## 2. Chu trình 6 Cổng Tự Động (Gate 0 -> Gate 5)
1. **Cổng 0 (Telemetry Completeness):**
   - Bắt buộc kiểm tra `completeness_score() >= 2` (có cả screenshot `.png` và UI dump `.xml` > 0 byte).
   - **Bẫy Serial ADB:** Watchdog truyền `machine_id` (vd "48") hoặc "M48". BẮT BUỘC dùng `get_serial_for_machine()` từ `inspect_machine.py` để phân giải thành ADB serial thật (`ce0516...`) và xác định đúng ADB socket (Kibe Local hay Admin Remote `192.168.110.119:5037`). Nếu không, ADB trả về `device not found`, screenshot/xml null và vấp `BLOCKED_PENDING_TELEMETRY`.
2. **Cổng 1 (Planner):**
   - Gọi `dispatch_planner.py` (Claude Sonnet Tier 1, Sol Tier 2) tạo O(1) Patch Contract từ stack trace và file lỗi.
3. **Cổng 2 (Worker):**
   - Gọi `dispatch_worker.py` với workdir repo và target file để sửa code ngầm.
4. **Cổng 3 (Regression GuardGate):**
   - Chạy `guardgate/runner.py` kiểm tra không vi phạm các Invariant của Farm.
5. **Cổng 4 (Canary Test):**
   - Chạy `canary_runner.py` trên chính thiết bị bị lỗi để xác thực app trên máy thật đã hoàn tất và sinh receipt.
6. **Cổng 5 (Closeout Gate):**
   - Chạy `closeout_gate.py` độc lập qua Reviewer Sol (:20129). Phải đạt `VERDICT: APPROVED` và `Score >= 85`.

## 3. Kỷ luật Báo cáo Telegram & Cách ly Hàng đợi
- **Chống Spam Telegram:**
  - Trong `incident_auto_harness.py`: CẤM gọi `notify()` riêng lẻ cho từng incident bị `BLOCKED` hay `FAILED` trong vòng lặp batch `process_queue()`.
  - Chỉ gửi tin Telegram chi tiết đích danh khi `status == "SUCCESS_MERGED"`.
  - Báo cáo tổng kết batch chỉ in ở stdout của `cron_incident_auto_heal.py` khi có thay đổi.
- **Cách ly hàng đợi (Queue Isolation):**
  - Incident hợp lệ vá xong: chuyển từ `pending/` sang `resolved/`.
  - Incident lỗi/blocked: chuyển sang `blocked/` để cách ly ngay, cấm để lại trong `pending/` gây lặp vô tận.
  - Vấp Guard Hook trong lúc Worker chạy ngầm: vẫn ghi nhận 100% vào `D:/Taadaa/logs/guard_scan_audit.jsonl` và được watchdog `farm-gate-compliance-6h-report` tổng hợp sau mỗi 6h.
