# Incident Auto-Heal Dispatcher & Dual-Cluster Telemetry Invariants

> Context: Closed-loop autonomous incident recovery (`incident-auto-heal-dispatcher`, `cron_incident_auto_heal.py`, `incident_auto_harness.py`, `incident_emitter.py`).

## 1. Nguyên nhân gốc rễ Gate 0 Telemetry Blocked (Blind Telemetry Failure)
- **Triệu chứng:** Hàng loạt vé sự cố bị kẹt tại Cổng 0 với trạng thái `BLOCKED_PENDING_TELEMETRY` (`xml_dump: null`, `screenshot: null`).
- **Nguyên nhân gốc:** Watchdog báo lỗi theo số thứ tự máy (vd: `machine_id="48"`). Lệnh ADB chạy `adb -s 48 exec-out screencap` bị fail vì `48` không phải là Hardware Serial ADB.
- **Quy tắc giải quyết:**
  1. Trong `incident_emitter.py`, hàm `resolve_serial_and_args(serial, machine_id)` bắt buộc gọi `inspect_machine.get_serial_for_machine(int(machine_id))` để tra cứu Serial thật từ `PROXYgandienthoai.xlsx`.
  2. Với cụm Admin Remote (`machine_id >= 200`), lệnh ADB bắt buộc thêm cờ kết nối socket: `[tool, '-H', '192.168.110.119', '-P', '5037', '-s', target]`.
  3. Chỉ khi lấy đủ ảnh screenshot (>0 byte) và XML dump UI thật qua ADB thì vé mới đủ điều kiện vào Cổng 1 (Planner).

## 2. Kỷ luật Anti-Spam Telegram trong Batch Dispatcher
- **Anti-Pattern:** Bắn thông báo Telegram riêng lẻ cho từng vé bị `BLOCKED` hoặc `FAILED` bên trong vòng lặp duyệt hàng đợi `pending/`. Khi có nhiều vé tồn đọng, hệ thống sẽ xả liên thanh hàng chục tin nhắn rác làm ngập nhóm chat.
- **Quy chuẩn thực thi:**
  1. `IncidentAutoHarness.notify()` CHỈ gửi tin chi tiết khi trạng thái là `SUCCESS_MERGED` (đã pass đủ 6 cổng, canary máy thật thành công và Closeout Reviewer chấm >= 85 điểm).
  2. Mọi trạng thái thất bại khác (`BLOCKED_PENDING_TELEMETRY`, `PLANNER_FAILED`, `WORKER_FAILED`, `CANARY_BLOCKED`, `CLOSEOUT_REJECTED`) được cách ly sang thư mục `D:/Taadaa/runtime/incidents/blocked/` trong im lặng.
  3. Dispatcher chỉ in 1 dòng tóm tắt tổng số vé `resolved` và `failed` ra console/stdout sau khi duyệt xong toàn bộ hàng đợi.

## 3. Kiến trúc 6 Cổng & Khuyến nghị Thẩm định Claude
- **Cổng 0 (Telemetry):** Bắt buộc ảnh screenshot và XML dump thật; kết hợp WinRT OCR đọc text trên WebView/Canvas mà accessibility XML không lấy được.
- **Cổng 1 (Planner):** Gọi Sonnet/Sol phân tích stack trace và telemetry, sinh Patch Contract O(1).
- **Cổng 2 (Worker):** Tuân thủ nghiêm ngặt bậc thang Sol (Free) -> Agy CLI -> Haiku. Sửa phạm vi hẹp <= 30 dòng.
- **Cổng 3 (Regression):** GuardGate quét chống vi phạm Invariant.
- **Cổng 4 (Canary):** Test trên điện thoại thật. BẮT BUỘC tôn trọng Device Lock của ca nuôi: Canary có mức ưu tiên thấp hơn ca nuôi đang chạy, không cướp lock làm zombie máy.
- **Cổng 5 (Closeout):** Focused test + Sol Reviewer (:20129) chấm >= 85/100 mới cho phép merge.
- **Escalation Storm Alert:** Khi phát hiện số vé `blocked/` tăng bất thường (≥3 vé trong 30 phút do sự cố hạ tầng như rớt socket ADB server Admin), hệ thống phải bắn 1 cảnh báo tổng hợp về Nhóm Farm Alert để Operator xử lý hạ tầng, tránh im lặng hoàn toàn.
