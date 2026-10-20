# Antigravity Pool Timeout & Multi-Worker Timeout Governance

## 1. Hiện tượng & Triệu chứng lỗi (Failure Symptoms)
- Khi điều phối Worker qua Antigravity CLI (`python D:/Taadaa/tools/ag_cli.py fix ...`) hoặc `dispatch_worker.py`:
  - Tiến trình chạy ngầm dường như bị "treo" (hang), không phản hồi kết quả sau nhiều phút.
  - Kiểm tra `pool_state.json` thấy hàng loạt hoặc toàn bộ 22 profiles (`acc_01` .. `acc_22`) rơi vào trạng thái:
    `"Status: COOLDOWN (1200s còn lại) [TimeoutExpired (180s)]"`.
  - Toàn bộ pool bị tê liệt (exhausted) do tất cả profiles đều bị phạt cooldown.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lỗi áp đè Timeout cứng (Timeout Override Trap)**:
   - Các công cụ dispatch (`dispatch_worker.py`, `claude_worker.py`, `haiku_worker.py`) trước đây hardcode cờ mặc định `--timeout 180` (3 phút).
   - Khi điều phối sang `ag_cli.py fix` (vốn đã được benchmark cấu hình default là 1200s–1500s), caller lại truyền cứng `--timeout 180`.
2. **Không phải lỗi do file hay mạng**:
   - Log nội bộ `~/.gemini/antigravity-cli/cli.log` cho thấy mô hình Gemini Code Assist đang suy luận và stream token bình thường (`streamGenerateContent`).
   - Việc suy luận trong codebase lớn, nhiều ngữ cảnh cần thời gian xử lý nhiều hơn 3 phút.
3. **Phản ứng dây chuyền Cooldown Cascade**:
   - Khi đúng 180s, `subprocess.communicate(timeout=args.timeout)` ném `TimeoutExpired`.
   - `ag_cli.py` kích hoạt `taskkill` và tự động đánh dấu profile đó vi phạm, phạt `set_profile_cooldown(name, duration=1200, reason="TimeoutExpired (180s)")`.
   - Cơ chế failover chuyển sang profile tiếp theo, profile tiếp theo lại bị ngắt ở 180s và bị phạt tiếp, dẫn đến cascade khóa toàn bộ 22 profile trong pool.

## 3. Quy chuẩn cấu hình Timeout chuẩn toàn Farm (Golden Standards)
Tất cả các worker, dispatcher và script cầu nối trên hệ thống Taadaa BẮT BUỘC tuân thủ mức trần timeout sau:
- **`dispatch_worker.py`**: `--timeout` mặc định là **`1200`** giây (20 phút).
- **`claude_worker.py`**: `default_timeout` của mọi role (`worker`, `planner`, `reviewer`) là **`1200`** giây (20 phút).
- **`haiku_worker.py`**: `DEFAULT_TIMEOUT` là **`1200`** giây (20 phút).
- **`sol_worker.py`**: `DEFAULT_TIMEOUT_PER_TURN` là **`300`** giây (5 phút/turn).
- **`ag_cli.py`**: `ask` là **`1200`** giây, `fix` là **`1500`** giây (25 phút).

## 4. Quy trình Cứu hộ khi Pool bị đóng băng (Recovery Procedure)
Khi pool Antigravity bị phạt cooldown hàng loạt do timeout cũ:
1. Mở file `D:/Taadaa/agy_profiles/pool_state.json`.
2. Đặt lại tất cả các profile:
   - `cooldown_until`: `0`
   - `cooldown_seconds`: `0`
   - `reason`: `""`
   - `quota_hits`: `0`
3. Kiểm tra lại trạng thái bằng lệnh:
   ```bash
   python D:/Taadaa/tools/ag_cli.py pool-status
   ```
   Xác nhận toàn bộ 22/22 profiles hiển thị `Status: READY`.
