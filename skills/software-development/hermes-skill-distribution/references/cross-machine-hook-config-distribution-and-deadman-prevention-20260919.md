# Cross-Machine Config & Hook Distribution Architecture (Kibe ↔ Admin)

## 1. Bản chất sự cố Deadman Lockout (19/09/2026)
- **Triệu chứng**: Agent bên máy Admin bị đóng băng hoàn toàn, mọi tool call (`terminal`, `read_file`, `delegate_task`, `clarify`) đều bị trả về lỗi:
  `[HARD GATE #0 - PROGRESS SUPERVISOR DEADMAN SWITCH] TIẾN TRÌNH BỊ ĐÓNG BĂNG!`
- **Nguyên nhân cốt lõi**:
  1. Hook `guard_progress_supervisor.py` cài ở `pre_tool_call` không có matcher, tự động đếm số lần gọi công cụ không sửa file (`action_count > 8` và `elapsed > 15m`).
  2. Coordinator làm đúng vai trò (chỉ inspect O(1), đọc log, đối soát Excel) nên không gọi `write_file`/`patch` trong session cha. Hook ngộ nhận agent bị loop/chết não và tự động kích hoạt "suicide lock", khóa luôn cả `delegate_task` khiến Coordinator không thể dispatch worker để sửa code hay giải phóng.
  3. Khi phát hiện và fix trên Kibe, kỹ sư chỉ sửa cục bộ trong `%LOCALAPPDATA%\hermes`, bỏ quên 2 kênh phân phối mẫu. Khi Admin sync, file cũ bị kéo sang và tái diễn sự cố.

## 2. Quy chuẩn Đồng bộ 4 Vị trí (Quad-Location Parity)
Khi thêm, sửa hoặc gỡ bỏ bất kỳ hook / cấu hình nào trên hệ thống phân tán Kibe ↔ Admin, BẮT BUỘC phải áp dụng đồng thời trên cả 4 điểm:

| STT | Điểm phân phối | Đường dẫn | Mục đích |
|---|---|---|---|
| 1 | Runtime Local (Kibe) | `%LOCALAPPDATA%\hermes\` | Môi trường chạy thực tế của máy Kibe |
| 2 | Tools Farm Repository | `D:\Taadaa\tools\hooks\` | Kho mã nguồn các hook dùng chung |
| 3 | Git Deploy Template | `D:\Taadaa\Hermes\deploy\hermes-home\` | Bản mẫu kéo qua `sync-from-kibe.ps1` (git `fork main`) |
| 4 | OneDrive Shared Sync | `D:\OneDrive\Taadaa_Sync_Shared\hermes-sync\` | Bản mẫu kéo qua `apply_sync_admin.py` |

## 2.1 Danh mục hiện vật BẮT BUỘC trong mỗi chu kỳ đồng bộ
1. **Các file Hook Python**: Tất cả các file trong `D:\Taadaa\tools\hooks\*.py`. Chú ý KHÔNG hardcode username (dùng `Path.home()` / `LOCALAPPDATA`).
2. **Cấu hình `config.yaml`**: Đồng bộ sang Deploy template và OneDrive shared sync.
3. **Danh sách cấp phép `shell-hooks-allowlist.json`**: Hermes kiểm tra xác thực hook dựa trên hash/tên file trong allowlist. Nếu thiếu file này trên máy Admin, toàn bộ shell hook mới sẽ bị chặn thực thi hoặc đòi tương tác terminal người dùng.
4. **Kho kỹ năng `skills/`**: Đồng bộ additive từ `%LOCALAPPDATA%\hermes\skills\` sang kho chia sẻ.
5. **Cập nhật script tiếp nhận (`apply_sync_admin.py`)**: Đảm bảo script giải nén/copy hook vào cả `%LOCALAPPDATA%\hermes\hooks\` VÀ `D:\Taadaa\tools\hooks\`, đồng thời chép `shell-hooks-allowlist.json` vào `%LOCALAPPDATA%\hermes\` và `~/.hermes\`.

## 3. Quy tắc Thiết kế Hook An toàn (Safety Invariants)
1. **Tuyệt đối cấm Pre-tool Hook không Matcher chặn đứng Coordinator**:
   Mọi hook tại `pre_tool_call` phải khai báo rõ `matcher` (ví dụ `terminal`, `read_file`). Không bao giờ đặt hook chặn toàn diện không matcher nếu không có điều kiện bypass rõ ràng cho vai trò Coordinator.
2. **Out-of-Band Stall Detection thay vì In-Band Suicide Lock**:
   Việc phát hiện session bị treo hoặc chạy quá lâu phải do các watchdog giám sát tiến trình ngoài luồng (`hermes_stale_watchdog.py`) đảm nhiệm, gửi thông báo cảnh báo về Telegram thay vì tự ý ngắt quyền gọi công cụ của session tương tác.
3. **Cứu hộ nhanh máy vệ tinh bị khóa**:
   Khi máy vệ tinh (Admin) bị dính lock do hook giám sát:
   ```powershell
   # Gỡ bỏ hook và xóa state file ngay lập tức
   Set-Content -Path "$env:LOCALAPPDATA\hermes\hooks\guard_progress_supervisor.py" -Value "import sys`nsys.exit(0)" -Encoding utf8
   Remove-Item -Path "$env:LOCALAPPDATA\hermes\cache\progress_supervisor*" -Force -ErrorAction SilentlyContinue
   ```

## 4. Hook Review & Model Drift Protection (`guard_model_drift.py`)
- **Vai trò**: Intercept tại `pre_tool_call` (matcher: `terminal`), chặn các cờ `--model` cấm (`sol-pro`, `sol-instant`) khi gọi `closeout_gate.py`, bảo toàn pool reviewer chuẩn `review` (Sol-High 16 accounts).
- **Tính tương thích Test Suite**: Khi tinh chỉnh thông báo lỗi trong `closeout_gate.py`, bắt buộc giữ cụm từ `is NOT allowed` trong thông báo `[Gate] FATAL: Model '...' is NOT allowed! Matches forbidden pattern: ...` để pass toàn bộ unit tests trong `tests/test_closeout_gate_scorecard.py`.

