# Gate Observability, Telemetry & Compliance Watchdog (Chống Chặn Thầm Lặng)

## 1. Bối Cảnh Sự Cố & Nỗi Đau Vận Hành
Khi hệ thống phone farm phát triển nhiều tầng gate cơ học (GuardGate Invariants, Closeout Gate, Pre-push Hook, Media Vision Gate, Dispatch Floor Gate, Vietnamese Accent Validator), các vi phạm và lần chặn thường diễn ra phân tán trong các file JSONL âm thầm (`ledger.jsonl`, `gate_audit.jsonl`, `dispatch.jsonl`, `safe_push_audit.jsonl`).
- **Nỗi đau Operator:** Agent vi phạm hoặc bị chặn liên tục (ví dụ: ngày 24/10/2026 có tới 21 lần Closeout Gate REJECTED, 26 lần worker timeout) nhưng Operator không hề hay biết cho đến khi tình cờ vào kiểm tra tay ("lâu lâu mới nhớ phát hiện ra").
- **Hậu quả:** Các lỗi lặp đi lặp lại âm thầm đốt token, nghẽn tài nguyên worker hoặc tiềm ẩn nguy cơ agent tìm cách lách luật mà không được phát hiện kịp thời.

## 2. Kiến Trúc Giám Sát Tuân Thủ 3 Tầng (Tri-Tier Observability)

### Tầng 1: Real-Time Ping Khi Gate Bị Trigger DENY / Strike
- Mỗi khi bất kỳ gate nào kích hoạt trạng thái `DENY`, `REJECTED`, hoặc `STRIKE-3-GUIDANCE-GAP`, gate BẮT BUỘC phải phát một telemetry ping tức thì về kênh giám sát (Telegram Farm Alert hoặc webhook).
- **Format chuẩn O(1) cho Telemetry Ping:**
  ```text
  🛑 [GATE INTERCEPT / VIOLATION]
  • Gate: <gate_name> (<rule_id>)
  • Target Repo/File: <repo_path> / <file_name>
  • Vi phạm: <1-line violation reason>
  • Action Mandate đã cấp: <REQUIRED_ACTION_O1 command>
  • Strike Count: <strike_count>/3 (Trạng thái Auto-Quarantine: OK/NA)
  ```
- **Nguyên tắc:** Ping ngắn gọn, có cấu trúc, không spam tin nhắn hội thoại chính, gửi trực tiếp về kênh alert chuyên trách.

### Tầng 2: Watchdog Đối Soát & Báo Cáo Định Kỳ (6h/24h Rollup)
- Đăng ký cronjob định kỳ (theo ca 6h hoặc tổng kết 24h) tổng hợp từ 4 nguồn log phân tán:
  1. `D:/Taadaa/tools/guardgate/ledger.jsonl` (Invariant rule decisions)
  2. `D:/Taadaa/logs/gate_audit.jsonl` (Closeout review verdicts & scores)
  3. `D:/Taadaa/logs/safe_push_audit.jsonl` (Pre-push hook intercepts)
  4. `D:/Taadaa/logs/dispatch.jsonl` (Worker execution categories: TIMEOUT, QUOTA, NO_DIFF)
- **Nội dung Scorecard Báo Cáo:**
  - Tổng số lần thẩm định Closeout (tỷ lệ APPROVED vs REJECTED).
  - Số lần Pre-push hook chặn thành công các commit vi phạm.
  - Thống kê phân loại worker fail (Timeout, Quota, No-diff).
  - Danh sách Top 3 Gate / Invariant bị vi phạm nhiều nhất để Operator kịp thời bổ sung Guidance hoặc vá lỗi hệ thống.
  - Tỷ lệ tự phục hồi O(1) (Agent có chạy lệnh phục hồi và pass ở turn kế tiếp hay không).

### Tầng 3: Công Cụ Tra Cứu Tức Thì O(1) (`gate_audit_summary.py`)
- Cung cấp script chuyên dụng đọc nhanh đuôi các file JSONL với thời gian thực thi `< 1s`:
  `python D:/Taadaa/tools/gate_audit_summary.py [--since 24h|6h|ca] [--json]`
- Hỗ trợ Operator tra cứu nhanh qua Telegram slash command `/gate_status` mà không cần SSH hay đọc log thủ công.
