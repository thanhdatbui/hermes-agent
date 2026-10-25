# Silent-When-Clean Watchdog Pattern & 10-Gate Full-Spectrum Observability

## 1. Bối Cảnh & Vấn Đề
- Khi hệ thống cơ giới hóa mở rộng lên 10 Gate và 13 chốt chặn, việc báo cáo định kỳ 6h (`farm-gate-compliance-6h-report`) nếu không có bộ lọc thông minh sẽ gặp 2 vấn đề lớn:
  1. **Spam Tin Nhắn (Alert Fatigue):** Khi farm hoạt động hoàn hảo 0 lỗi, watchdog vẫn bắn tin `🛡️ Không phát sinh vi phạm (12 files đối soát)` mỗi 6 tiếng, làm loãng kênh Farm Alert.
  2. **Rác Dữ Liệu Trong Báo Cáo:** Khi có lỗi, báo cáo lại in ra toàn bộ 10 gate, trong đó có 6-7 gate mang trạng thái `⚪ NO_EVIDENCE (hợp lệ: 0, vi phạm: 0)` hoặc `✅ PASS`, khiến Operator phải cuộn mỏi tay mới tìm thấy gate đang hỏng.
  3. **Chốt Chặn Chặn Trong Bóng Tối:** 4 hook (`guard_device_bulkhead.py`, `guard_pytest_scope.py`, `guard_model_drift.py`, `guard_closeout_discipline.py`) chặn vi phạm nhưng chỉ in JSON ra stdout cho Hermes mà không ghi log ra file, dẫn đến việc watchdog 6h hoàn toàn "mù" với các vi phạm này.

## 2. Kiến Trúc Chuẩn Hóa 3 Tầng ("Vi Phạm Mới Bắn Ra, Không Vi Phạm Thì Im Lặng")

### Tầng 1: Full-Spectrum Hook Audit Logging
- 100% các pre-tool hooks khi kích hoạt `_block()` hoặc `_log_and_exit()` BẮT BUỘC ghi bản ghi có cấu trúc (`timestamp`, `rule_id`, `guidance`, `required_action`, `message`) vào `D:/Taadaa/runtime/audit_logs/guard_scan_audit.jsonl`.
- Bổ sung 2 nguồn log chuyên sâu vào watchdog 6h:
  * **G9 Android Proxy Guard:** Giám sát `runtime/audit_logs/proxy_guard_audit.jsonl` (bắt chặn gán IP/domain ngoài làm proxy).
  * **G10 Claude Quota Gate:** Giám sát `logs/claude_quota_audit.jsonl` (bắt các lần ngắt gọi Claude CLI do chạm trần 5h/tuần).

### Tầng 2: Silent-When-Clean Delivery Semantics
- Khi hàm `evaluate()` đối soát 6h qua và tính toán `total_violations == 0` (và không có `remediation_hits`):
  * Hàm `render_markdown(report)` trả về chuỗi rỗng: `""`.
  * Hàm `main()` kiểm tra `if not text.strip(): return 0` và thoát ngay với stdout rỗng.
  * Nhờ cờ `no_agent: true` của cronjob Hermes: stdout rỗng đồng nghĩa với **SILENT**, scheduler không gửi bất kỳ tin nhắn nào về Telegram, giữ kênh Farm Alert hoàn toàn yên tĩnh khi hệ thống xanh sạch.

### Tầng 3: Violation-Only Gate Rollup (Gọt Bỏ Gate 0 Vi Phạm)
- Khi có vi phạm (`total_violations > 0`):
  * Lọc danh sách: `failing_gates = [g for g in gates if g["fail_hits"] > 0 or g.get("remediation_hits", 0) > 0]`.
  * Header báo cáo đổi thành: `📋 *Chi tiết Gate Có Vi Phạm:*`.
  * Chỉ hiển thị các gate đang fail (kèm số lần vi phạm và số lần remediation).
  * Ẩn sạch 100% các gate `NO_EVIDENCE` hoặc `PASS (vi phạm: 0)` để Operator thấy ngay tiêu điểm cần can thiệp.
  * Đi kèm bảng xếp hạng `Top Quy Tắc Bị Chặn Nhiều Nhất` để nạp guidance O(1).
