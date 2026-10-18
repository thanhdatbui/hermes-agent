# Antigravity CLI (`ag_cli.py`) Dispatch & Flag Traps

## 1. Subcommand Argument Schema
In `D:/Taadaa/tools/ag_cli.py`:
- `ask` parser: accepts `--prompt`, `--file`, `--model`, `--workdir`, `--timeout`, and `--profile`.
- `fix` parser: accepts `--prompt`, `--file`, `--model`, `--workdir`, and `--timeout`. **Does NOT accept `--profile`.**

### Error Manifestation
```bash
python D:/Taadaa/tools/ag_cli.py fix --profile acc_01 "Tạo file..."
# Output:
# usage: ag_cli.py [-h] {ask,fix,models,pool-status,init-profile} ...
# ag_cli.py: error: unrecognized arguments: --profile
```

### Correct Pattern
When fixing or scaffolding code, omit `--profile`:
```bash
python D:/Taadaa/tools/ag_cli.py fix --workdir "D:/Taadaa/site ban hang clone" --timeout 240 "<focused_task>"
```
The pool scheduler automatically selects the best profile via LRU while respecting `.profile.lock` leases and cooldown states.

## 2. Multi-File Module Scaffolding Timeout
Attempting to scaffold an entire 5-file module (e.g. SQLite DB, evaluator, sync adapter, FastMCP server, and full test suite) in a single turn triggers exit code 124 (timeout > 180s).
- **Rule**: Decompose into bite-sized 1-2 file deliveries.
- Phase 1: Storage engine (`db.py`) + Domain Evaluator (`evaluator.py`).
- Phase 2: FastMCP server (`server.py`) + Sync adapter (`sync_adapter.py`).
- Phase 3: Pytest test suite (`tests/test_mcp_server.py`).
- Always run long CLI tasks via `terminal(background=True, notify_on_complete=True)` with timeout $\ge 240\text{s}$.

## 3. `DEFAULT_MODEL` Invariant: `gemini-3.8-flash-medium` vs `high` Trap
- **User Preference Invariant**: Antigravity CLI (`ag_cli.py`) BẮT BUỘC đặt mặc định là `gemini-3.8-flash-medium`.
- **Cạm bẫy `high`**: Thiết lập `gemini-3.8-flash-high` kích hoạt Deep Think quá sâu. Với các task sinh code hoặc phân tích module lớn, model stream ra >15,000–20,000 ký tự qua proxy 4G mất từ 105s đến 140s, dễ dàng làm nổ tung các ngưỡng timeout 60s/120s.
- **Quy tắc**: Giữ `DEFAULT_MODEL = "gemini-3.8-flash-medium"`. Mức `high` chỉ dùng khi có yêu cầu tường minh cho bài toán toán học / giải tích / kiến trúc đặc biệt.

## 4. Bảng Quy Chuẩn Timeout Toàn Hệ Thống Cho Bộ Cầu Nối AI
Tránh các mốc timeout "nghẽn cổ chai" (60s / 120s) khi gọi AI sinh code:
- `D:/Taadaa/tools/ag_cli.py ask`: Tối thiểu **300s (5 phút)**.
- `D:/Taadaa/tools/ag_cli.py fix`: Tối thiểu **600s (10 phút)** (cần thời gian đọc file, AST rewrite và self-test).
- `D:/Taadaa/tools/dispatch_worker.py`: Tối thiểu **180s (3 phút)** per worker.
- `D:/Taadaa/tools/haiku_worker.py`: Tối thiểu **180s (3 phút)**.
- `D:/Taadaa/benchmark_arena/gemini_argon_server.py`: `STOP_TIMEOUT_S = 300s`, `REQUEST_TIMEOUT_S = 360s`.

## 5. Cạm Bẫy Deadlock LRU Khi Bị Timeout Trong `ag_cli.py`
- **Hiện tượng**: Một tài khoản bị timeout do proxy lag, nhưng ở mọi lần gọi sau hệ thống lại tiếp tục bốc trúng tài khoản đó khiến toàn bộ tiến trình kẹt cứng liên hoàn.
- **Căn nguyên**: LRU chọn profile có `last_used` nhỏ nhất (hoặc = 0). Khi `subprocess.TimeoutExpired` xảy ra, nếu script thoát hoặc ném exception mà không ghi nhận `last_used` và không set cooldown, profile đó vẫn giữ `last_used = 0` và tiếp tục đứng đầu danh sách ưu tiên.
- **Khắc phục chuẩn**:
  ```python
  except subprocess.TimeoutExpired:
      set_profile_cooldown(name, duration=300, reason=f"TimeoutExpired ({args.timeout}s)")
      record_profile_usage(name)
      continue  # Rotate ngay sang profile sẵn sàng tiếp theo trong pool
  ```

## 6. Bẫy Suy Đoán Vội Vàng Về Nguồn Gốc Profile (False Shared-Account Claim)
- **Sai lầm nhận thức**: Nhìn thấy cờ `--copy-current` trong lệnh khởi tạo mẫu của `ag_cli.py` rồi vội vàng quy chụp toàn bộ các profile dùng chung 1 tài khoản OAuth.
- **Quy tắc thực địa (Evidence-First)**: Bắt buộc đọc trực tiếp `google_accounts.json` và `oauth_creds.json` tại từng thư mục `D:/Taadaa/agy_profiles/<name>/.gemini/` để kiểm tra email và tiền tố refresh token trước khi đưa ra bất kỳ kết luận nào về cấu hình tài khoản.

