# Opportunistic Upload Timeout Budget Alignment & Deadman Recovery Pattern

## 1. Sự cố: `hard outer watchdog deadline expired` khi bật Opportunistic Upload
### Hiện tượng
- Farm alert: `[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG`
- Signature: `❌ script-blocker:hard outer watchdog deadline expired`
- Tỷ lệ: 8–15% toàn batch (ví dụ Ca trưa Row 4 dính 8/80 máy: M7, M28, M29, M48, M53, M60, M73, M79).
- Log chi tiết: Máy hoàn thành 100% lướt feed (19–21 swipes, verify matched) sau 14–18 phút. Sau đó bước vào hook `upload-hook` (`scripts.tiktok_workflow`), chạy đến phút 27–31 thì bị outer watchdog kill và đánh dấu `failed`.

### Root Cause
Lệch logic giữa **thực thi upload hook** và **tính toán watchdog hard budget**:
- Luồng hook (`_run_upload_hook`): Chấp nhận upload nếu `session_index == 2` HOẶC `_allow_upload_hook == True` (cơ chế Opportunistic Upload cho phép Phiên 1 đăng video nếu chưa đạt hạn ngạch shift).
- Luồng tính toán (`_worker_hard_timeout_seconds`): Chỉ kiểm tra `upload_eligible = _effective_session_index(config) == 2`, **bỏ quên `_allow_upload_hook`**.
- Hậu quả: Phiên 1 chỉ được cấp budget feed + follow + 300s buffer (~26 phút), không có `upload_budget` (2700s). Khi upload video kéo dài, watchdog cưỡng chế ngắt máy.

### Pattern Khắc Phục Chuẩn
1. Tại `_worker_hard_timeout_seconds`:
   ```python
   upload_eligible = (_effective_session_index(config) == 2) or bool(config.get("_allow_upload_hook", False))
   ```
2. Bổ sung Observability/Telemetry log ngay sau khi tính `worker_hard_timeout`:
   ```python
   _upload_allowed = (_effective_session_index(ctx.config) == 2) or bool(ctx.config.get("_allow_upload_hook", False))
   ctx.logger.log(
       device_id="batch",
       account="all",
       step="multi-machine-feed-session/watchdog_budget",
       action="budget_calculated",
       result="success",
       extra={
           "worker_hard_timeout_seconds": worker_hard_timeout,
           "upload_eligible": _upload_allowed,
           "session_index": _effective_session_index(ctx.config),
       },
   )
   ```

---

## 2. Quy trình "Gọi Sol Plan" & Closeout Gate Chuẩn
Khi user yêu cầu **"Gọi Sol plan"** hoặc khi cần lập kế hoạch xử lý sự cố farm:
1. **Dùng công cụ Sol Planner chuyên biệt:**
   ```bash
   python D:/Taadaa/tools/sol_planner.py \
     --goal "<Mục tiêu xử lý lỗi>" \
     --file "<File target>" \
     --flow-name "<tên-flow>"
   ```
   Script sẽ tự động gọi OmniRoute `:20129` model `chatgpt-web/gpt-5.6-sol-high` (hoặc fallback), trả về JSON cấu trúc: diagnosis, tasks (T1..Tn), patch contracts với anchor $c==1$.

2. **Chạy Sol Review Scorecard trước khi closeout:**
   ```bash
   python D:/Taadaa/tools/closeout_gate.py --repo "<path_repo>" --base HEAD --skip-test --verbose
   ```
   Ngưỡng thông qua: `Overall Score >= 85/100` (`VERDICT: APPROVED`).

---

## 3. Quy tắc Deadman Switch (Progress Supervisor Deadman Switch)
- **Cơ chế:** Khi session thực hiện quá nhiều thao tác thăm dò (read/search/grep/terminal) liên tục trong >15 phút mà không có bất kỳ State Change nào (không patch code, không compile, không chạy test), Deadman Switch sẽ đóng băng toàn bộ tool calls để chống "Agent Insanity Loop".
- **Hành động đúng của Coordinator:**
  1. KHÔNG tiếp tục gõ lệnh thăm dò hoặc cố xoá file rác mù quáng.
  2. Báo cáo ngay cho User hiện trạng, nguyên nhân gốc rễ và đề xuất Patch Contract đóng duy nhất ($c==1$).
  3. Thực hiện ngay 1 thao tác State Change hợp lệ (`patch` file code cần sửa hoặc chạy compile/test) để hệ thống tự động giải phóng Deadman Switch.
