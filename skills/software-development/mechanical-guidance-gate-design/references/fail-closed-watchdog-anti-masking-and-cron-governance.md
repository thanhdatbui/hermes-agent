# Fail-Closed Watchdog Anti-Silent-Masking & Universal Cron Governance

## 1. Bối Cảnh & Nguy Cơ "Im Lặng Giả Tạo" (False-Negative Masking)
Khi áp dụng nguyên tắc **"Vi phạm mới bắn ra, không vi phạm thì im lặng"** (*Silent on Nominal, Loud on Anomaly*) để chống bão tin nhắn rác (Alert Fatigue), hệ thống đối mặt với một tử huyệt kiến trúc:
> **Rủi ro Vi phạm ngầm:** Vi phạm thực sự xảy ra trên Farm, nhưng watchdog bị mù hoặc drop dòng log do lỗi parse, dẫn đến kết luận nhầm là `PASS` / `NO_EVIDENCE` và im lặng tuyệt đối, Operator hoàn toàn mất dấu sự cố.

## 2. 4 Chốt Chặn Triệt Tiêu Vi Phạm Ngầm Trong Watchdog

### 2.1. Fail-Closed Timestamp Check (Chống Rớt Log Dị Dạng)
- **Điểm yếu cũ:** Hàm `in_window(line, cutoff)` trả về `False` khi không parse được định dạng timestamp $\to$ Bỏ qua hoàn toàn dòng đó.
- **Chuẩn cơ học bắt buộc:** Nếu một dòng log khớp pattern nghi vấn vi phạm (`BLOCK_SUSPECT_RE = r'"action":\s*"block"|\b(?:DENY|REJECTED|BLOCKED|QUARANTINE|ABORT)\b'`), nhưng `parse_line_timestamp()` trả về `None`, hàm BẮT BUỘC đối chiếu với thời gian sửa đổi gần nhất của file (`file_mtime`).
- Nếu `file_mtime >= cutoff` $\to$ Bắt buộc coi dòng đó nằm trong cửa sổ thời gian (`return True`), cấm vứt bỏ.

### 2.2. Unclassified Catch-All Gate (Chống Lệch Regex / Bỏ Quên Hook Mới)
- Mọi dòng log chứa tín hiệu chặn mà không khớp với bất kỳ Gate định danh nào (G1..G10) sẽ tự động bị gom vào nhóm `[Unclassified] <rule_id/snippet>`.
- Sự xuất hiện của bất kỳ bản ghi unclassified nào sẽ lập tức ép trạng thái `overall = "FAIL"`, kích hoạt báo cáo alert về Telegram ngay lập tức.

### 2.3. Audit Persistence Tránh "Chặn Câm" (No-Silent-Block in Hooks)
- 100% các hàm `_block()` hoặc `deny()` trong pre-tool hooks (`guard_device_bulkhead.py`, `guard_pytest_scope.py`, `guard_model_drift.py`, `guard_closeout_discipline.py`) bắt buộc ghi JSON có cấu trúc vào file `runtime/audit_logs/guard_scan_audit.jsonl` trước khi thoát.
- Bọc ghi log với try/except an toàn, đảm bảo nếu file audit tạm thời bị khóa thì hook vẫn chặn được và có fallback, không gây crash engine.

### 2.4. 24H Daily Heartbeat (Dead-Man's Switch)
- **Quy tắc:**
  - Trong các tick 6h thông thường (06:00, 12:00, 18:00 UTC): Nếu 0 vi phạm $\to$ Im lặng 100% (stdout rỗng, không gửi tin).
  - Duy nhất tại tick 00:00 UTC (07:00 sáng VN): Dù 0 vi phạm, hệ thống BẮT BUỘC phát 1 bản tin Heartbeat ngắn gọn 3 dòng:
    ```text
    🛡️ *[FARM GATE COMPLIANCE — 24H HEARTBEAT]* ✅
    ⏰ Chu kỳ 24h: 2026-10-24 00:00:00 UTC -> 2026-10-25 00:00:00 UTC
    📁 Đối soát: 15 log files (1871 dòng) — 0 vi phạm.
    ℹ️ Hệ thống 10 Gate cơ giới hóa và Hook Guard đang vận hành bình thường.
    ```
- Giúp Operator xác nhận kênh truyền và daemon scheduler vẫn đang sống khỏe, phân biệt rạch ròi giữa "Bình an vô sự" và "Hệ thống chết lâm sàng".

---

## 3. Quy Chuẩn Áp Dụng Cho Toàn Bộ Cron Reports Trên Farm

Mọi cronjob báo cáo định kỳ cấu hình `no_agent: true` trên Farm Taadaa bắt buộc phải tuân thủ chuẩn Watchdog Công Nghiệp:

| Cronjob Name | Trạng Thái Bình Thường (Nominal) | Điều Kiện Bắn Báo Động (Anomaly) |
| :--- | :--- | :--- |
| `farm-gate-compliance-6h-report` | 0 vi phạm $\to$ Im lặng (trừ nhịp 00:00 Heartbeat) | Có bất kỳ Gate nào FAIL hoặc có unclassified block |
| `daily-stale-upload-accounts-watchdog` | 100% acc đăng video đúng tiến độ $\to$ Im lặng | Có tài khoản kẹt/đóng băng > 24h không lên video |
| `farm-render-download-watchdog` | Hàng đợi render/download chạy đều $\to$ Im lặng | Hàng đợi tắc > 1h hoặc Admin full đĩa |
| `gpm-gmail-nurture-6h-report` | State machine nuôi luân chuyển đều $\to$ Im lặng | Profile checkpoint, kẹt captcha, proxy die |
| `onedrive-multicloud-sync-watchdog` | Hash cloud khớp 100% $\to$ Im lặng | Lệch file giữa OneDrive vs GDrive hoặc token hết hạn |

### Quy tắc triển khai trong script:
1. Tính toán logic nghiệp vụ và lọc danh sách bất thường (`anomalies`).
2. Nếu `len(anomalies) == 0`: Không gọi `print()`, thoát `sys.exit(0)` với stdout rỗng.
3. Nếu `len(anomalies) > 0`: Format bảng Markdown chi tiết đúng lỗi cần xử lý và `print()` ra stdout để scheduler tự động forward về Telegram.
4. Nếu script phát sinh exception không xử lý được: Cho phép crash (`sys.exit(1)`) để Hermes kích hoạt cơ chế báo động sự cố hỏng watchdog.
