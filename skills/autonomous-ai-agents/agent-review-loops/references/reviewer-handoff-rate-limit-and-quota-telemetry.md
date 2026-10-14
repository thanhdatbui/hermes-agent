# Reviewer Handoff 429 Failover & Desktop Quota Telemetry (15/10/2026)

## 1. Bẫy Deadlock tại Strike 3 Reviewer Handoff
Theo quy định Closeout Gate:
- Strike 1 & Strike 2: `sol_repair.py` (Sol High qua OmniRoute :20129) độc quyền tạo bản vá O(1) đầu tiên.
- Strike 3: Khi cùng một `scope_hash` bị từ chối 3 lần liên tiếp, hệ thống kích hoạt **3-Strike Reviewer Hand-off**.
  - Khóa tệp `D:/Taadaa/runtime/handoff_locks/HANDOFF_LOCK_<scope_hash>.json`.
  - Toàn bộ Coordinator, Worker, và Sol Repair dừng phỏng đoán, nhường quyền sửa cho Reviewer CLI (`claude-sonnet-5-5`).

### Tử huyệt thực tế:
Khi gọi Claude CLI (`claude -p`), tài khoản Claude Pro có thể chạm trần cửa sổ trượt 5 giờ (`HTTP 429: You've hit your session limit · resets X:XX`).
Nếu không có cơ chế thoát hiểm, phiên làm việc sẽ rơi vào trạng thái bế tắc (Deadlock):
- Sol Repair bị khóa vì đã qua Strike 3.
- Coordinator không được phép sửa tự do.
- Claude CLI bị Anthropic chặn 429.

### Giải pháp khắc phục (Failover to Antigravity Pool):
Khi Claude CLI trả về exit code khác 0 kèm thông điệp `hit your session limit` hoặc lỗi `HTTP 429`:
1. Ngay lập tức ghi nhận audit event `claude_limit_hit_detected`.
2. Kích hoạt fallback khẩn cấp sang **Antigravity CLI** (`python D:/Taadaa/tools/ag_cli.py fix <task>` trên pool 7 tài khoản Pro xoay vòng LRU qua Proxy 4G).
3. Đảm bảo toàn bộ tham số `--file`, `--workdir`, `--timeout` được chuyển tiếp đầy đủ.

## 2. Nguồn đo lường Quota thực tế trên Windows
- Lệnh `claude auth status --text` **KHÔNG** trả về `% quota` còn lại.
- Nguồn số liệu duy nhất chính xác 100% từ server Anthropic là file cơ sở dữ liệu của Claude Desktop App:
  `C:\Users\Kibe\AppData\Roaming\Claude\plan-usage-history.json`
  Mỗi mẫu gồm:
  - `fh`: % đã dùng trong cửa sổ 5 giờ (ngưỡng an toàn: < 85%).
  - `sd`: % đã dùng trong 7 ngày (ngưỡng an toàn: < 90%).
  - `t`: timestamp mili-giây.

### Quy tắc Fail-Closed khi kiểm tra Quota:
- Nếu file không tồn tại, lỗi cú pháp JSON, hoặc mẫu mới nhất đã cũ quá 24 giờ (`is_stale = True`), hoặc giá trị là `NaN`:
  Bắt buộc áp dụng cơ chế **Fail-Closed**: Không cho phép gọi mù quáng Claude Pro mà tự động chuyển hướng task sang `ag_cli.py fix` để bảo vệ tài khoản không bị lockout.

## 3. Tắt vĩnh viễn Advisor ngầm (`advisorModel: 'off'`)
Trong `C:\Users\Kibe\.claude\settings.json`:
- Cấu hình `"advisorModel": "off"` là bắt buộc.
- Nếu để `"advisorModel": "sonnet"`, mỗi task code khó Claude CLI sẽ tự động kích hoạt thêm 1 tiến trình Sonnet Advisor ngầm, ngốn thêm 13.000 - 30.000 tokens và làm chậm thời gian phản hồi từ 10s lên >60s, đốt cạn quota 5h chỉ sau vài task.

## 4. Kỷ luật tối cao khi kết thúc phiên (Closeout Gate Invariant)
- **CẤM TUYỆT ĐỐI** tuyên bố phiên làm việc "kết thúc trọn vẹn" hoặc báo DONE khi `closeout_gate.py` chưa trả về `APPROVED (score >= 85)` và exit code 0.
- Báo DONE khi chưa đủ điểm là vi phạm kỷ luật nặng nhất.
- Khi dính Strike 3 và Claude CLI bị 429 mà chưa giải quyết được: Bắt buộc báo cáo đúng trạng thái **BLOCKED kèm bằng chứng thực tế** (bằng chứng log `429`, file `HANDOFF_LOCK`, và scorecard hiện tại). Không bao giờ làm đẹp báo cáo.
