# Incident-to-Guard Automation & 8-Gate Compliance Monitoring

## 1. Cơ Chế Liên Tục Nạp Case Mới (Incident-to-Guard Pipeline)
Trước đây, mỗi lần xuất hiện sự cố mới trên Farm (như Case 161 popup, Case 162 USB, Case 300s timeout), việc thêm case vào GuardGate phải sửa tay 3 file (`predicates.py`, `rules.json`, `runner.py`). Điều này dẫn tới:
- Sót case sau khi fix xong sự cố -> session sau Agent khác lại vào sửa ngược phá hoại tiếp.
- Lỗi Rule Shadowing: Khai báo nhiều rule cùng match `(code_edit, commit)` khiến rule sau bị che khuất.

### Giải pháp thống nhất 3 bên (Claude Sonnet, Sol Reviewer, Hermes Coordinator):
1. **Generic Declarative Predicates:** Thay vì viết hàm Python rời rạc cho từng case, chuẩn hóa 4 khuôn mẫu đọc thẳng `params`:
   - `numeric_floor`: Ép biến $\ge \text{min\_value}$ (chống hạ timeout).
   - `numeric_ceiling`: Ép biến $\le \text{max\_value}$ (chống tăng limit follow/retry).
   - `prohibited_pattern`: Cấm regex vi phạm (chống lách ASCII không dấu, cấm adb tap bừa).
   - `required_pattern`: Bắt buộc regex an toàn (ép cứng `CREATE_NO_WINDOW`, `Hidden`).
2. **Công cụ tự động hóa `add_rule.py`:**
   - Nhận cấu hình JSON + 2 test vector bắt buộc (1 diff vi phạm -> DENY, 1 diff chuẩn -> ALLOW).
   - Chạy kiểm định GuardEngine trong RAM; PASS 100% mới ghi đè nguyên tử (atomic `_atomic_write_json` qua tempfile + `os.replace`).
   - Cấm Agent dùng `add_rule.py` để nới lỏng (Allow/Exempt) — tool chỉ cho phép siết (Deny).
3. **Chốt chặn tại Closeout Gate:** Khi phiên làm việc xử lý xong một sự cố hệ thống, Closeout Gate bắt buộc phải có bước kiểm tra nạp Invariant Rule bảo vệ tương ứng thì mới cấp Token hoàn tất phiên.

---

## 2. Bản Đồ 8 Gate Cơ Giới Hóa & Giám Sát Đối Soát 6H

Toàn bộ các Gate trên Farm đều đã được cơ giới hóa bằng code/hook và ghi log tự động:
1. **Visual Evidence Gate (`guard_media_vision_gate.py`):** Log `runtime/audit_logs/vision_receipts.jsonl`. Ép buộc ảnh `MEDIA:` phải có chữ ký HMAC-SHA256 qua WinRT OCR / Browser Vision < 300s.
2. **Planning Gate (`dispatch_planner.py`):** Log `logs/dispatch_planner.jsonl` & `runtime/sol_plans/`. Ép buộc task kiến trúc phải qua Claude Sonnet CLI hoặc Sol Planner trước khi code.
3. **Worker Dispatch Gate (`dispatch_worker.py`):** Log `logs/dispatch.jsonl` & `runtime/audit_logs/dispatch_audit.jsonl`. Khóa sàn timeout worker $\ge 300\text{s}$, bắt sống lỗi `files_modified == 0`.
4. **Invariant GuardGate (`guardgate/runner.py`):** Log `tools/guardgate/ledger.jsonl`. Quét AST diff tại Step 2.5, auto-quarantine stash và trả Action Mandate O(1).
5. **Closeout Reviewer Gate (`closeout_gate.py`):** Log `logs/gate_audit.jsonl`. Độc quyền Sol Reviewer chấm điểm $\ge 85$ hoặc Grace Band 80-84.
6. **Safe Push Guard (`safe_push.py` & `.git/hooks/pre-push`):** Log `logs/safe_push_audit.jsonl`. Chặn push remote nếu thiếu Closeout Approved hoặc thiếu Canary máy thật.
7. **Anti-Disk Scan Guard (`guard_broad_grep.py`):** Log `runtime/audit_logs/guard_scan_audit.jsonl`. Chặn đứng `os.walk`, `grep -r`, `find` khi nhận Farm Alert.
8. **Cronjob Console Window Guard (`guard_cronjob_safety.py`):** Log `runtime/audit_logs/console_block_audit.jsonl`. Ép cứng `CREATE_NO_WINDOW (0x08000000)`, cấm pop console cướp focus.

### Watchdog Giám Sát Tuân Thủ (`gate_compliance_watchdog.py`):
- Chạy định kỳ 6h (`0 */6 * * *`) với `no_agent: true` (zero token).
- Quét 8 file log trong 6h gần nhất, tính tỷ lệ tuân thủ và bắn báo cáo trực tiếp về Telegram Farm Alert (`-5373649734`).
- **Telegram Delivery Robustness (Chống Lỗi HTTP 400 Bad Request):** Báo cáo giám sát chứa nhiều hằng số kỹ thuật mang dấu gạch dưới (`NO_EVIDENCE`, `STATUS_OK`). Hàm phát tán Telegram bắt buộc phải bọc xử lý lỗi: nếu gửi bằng `parse_mode="Markdown"` bị từ chối (HTTP 400), phải tự động fallback gửi ngay bằng Plaintext (`parse_mode=None`) để không làm mất tin nhắn cảnh báo.
- **Hermes Cron Execution Path & Dual-Sync Requirement:** Khi đăng ký cronjob `no_agent: true`, runner của Hermes tìm script trong `%LOCALAPPDATA%\hermes\scripts\<script>`, trong khi hook bảo mật (`guard_cronjob_safety.py`) lại kiểm tra đối chiếu tại `cwd / script`. Cần bảo đảm script được đồng bộ đồng thời qua `cron_sync_watchdog.py` sang cả `scripts/` và thư mục gốc của runtime.
- **Universal UTC Timezone Normalization:** Audit log toàn Farm (`gate_audit.jsonl`, `vision_receipts.jsonl`) lưu chuẩn UTC (`timestamp_utc`). Watchdog bắt buộc tính `now = datetime.now(timezone.utc)` và chuẩn hóa mọi timestamp trong log sang offset-aware UTC. So sánh datetime naive hoặc tính theo giờ địa phương (UTC+7) sẽ lệch 7 tiếng, gây ra hiện tượng `NO_EVIDENCE` giả mạo.

---

## 3. Chống Bypass Cơ Chế "Cấm Khóc Lóc" (Tri-Party Triệt Tiêu Bại Liệt)
- **Cấm khóc lóc cảm xúc:** Hook tiền trạm chặn đứng text than phiền ("em xin lỗi/em hứa"), chỉ cho phép xuất theo cấu trúc kỹ thuật `[FAULT-CONFIRMED]`.
- **Cấm khóc lóc quan liêu:** Không cho phép tự tạo ticket JSON rồi đứng im. Mọi lệnh DENY phải đi kèm `REQUIRED_ACTION_O1` copy-paste chạy ngay.
- **Auto-quarantine chặt chẽ:** Chỉ stash file vi phạm (`git stash push --keep-index -- <path>`), cấm Agent gọi `stash pop/drop/clear` để lách luật.
- **Strike 3 Guidance Update:** Bộ đếm strike do Hook ghi ra ledger ngoài tầm model. Agent dùng `update_guidance.py` với mã băm SHA256 bảo vệ enforcement, nạp bài học mới xong bắt buộc phải BẺ LÁI (PIVOT) sang task khác trong queue, cấm đứng im.
