# PowerShell Log Probe PathNotFound & Unbounded Grep Timeout Pitfall

## 1. Sự cố: `PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand` (Case 2026-09-06)

### A. Triệu chứng
Chuỗi pipeline ban đêm (`run_night_chain_pipeline.py`) chạy Phase 1 (Reg Gmail) thất bại với exit code 1 hoặc 2:
```text
Phase 1 (Reg Gmail) thất bại (exit_code=1): + FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand
```

### B. Nguyên nhân gốc rễ
1. Trong script launcher PowerShell (`run_parallel.ps1`), cấu hình `$ErrorActionPreference = 'Stop'` được bật để dừng khi có lỗi nghiêm trọng.
2. Hàm đọc log `Get-RunResultFromLog`:
   ```powershell
   if (Test-Path -LiteralPath $LogPath) {
       $content = Get-Content -LiteralPath $LogPath
   ```
3. Khi tiến trình con (`cmd.exe /c python gmail_reg_v10.py ... > logFile`) kết thúc đột ngột, file log chưa kịp flush, bị khoá bởi Windows I/O, hoặc có race condition giữa `Test-Path` và `Get-Content`:
   - `Get-Content` ném ra ngoại lệ terminating `ItemNotFoundException` / `PathNotFound`.
   - Do `$ErrorActionPreference = 'Stop'`, toàn bộ script dừng ngay lập tức và trả về exit code lỗi.
   - Hàm `parse_summary_line` của pipeline quét stdout/stderr từ dưới lên và bắt trúng dòng `+ FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand`.

### C. Giải pháp chuẩn hoá (Fail-Safe Log Reading)
Luôn bọc `Get-Content` trong khối `try/catch` với `-ErrorAction Stop`, kết hợp kiểm tra rỗng và dùng biến cờ `$hasLog` để phân biệt chính xác giữa log trống và log không tồn tại:
```powershell
    $content = @()
    $hasLog = $false
    if (![string]::IsNullOrWhiteSpace($LogPath)) {
        try {
            if (Test-Path -LiteralPath $LogPath -PathType Leaf) {
                $content = @(Get-Content -LiteralPath $LogPath -ErrorAction Stop)
                $hasLog = $true
            }
        } catch {
            $content = @()
            $hasLog = $false
        }
    }
```
Khi đó, nếu file bị xóa giữa chừng hoặc lỗi I/O, ngoại lệ được tóm gọn, `$hasLog = $false` và runner tự động rẽ nhánh sang `Missing log, exit code $ExitCode` mà không bao giờ văng terminating exception.

---

## 2. Cạm bẫy Speculative Hardcoded Log Path trong Pipeline Caller

### A. Triệu chứng
Trong caller `run_night_chain_pipeline.py`:
```python
_send_night_chain_alert("Phase 1 (Reg Gmail)", gmail_code, parse_summary_line(gmail_out, "Gmail"), str(GMAIL_REPO_DIR / "logs" / "reg.log"))
```
File `D:/Taadaa/register gmail/logs/reg.log` thực tế **không hề tồn tại** (log thật được lưu theo thư mục timestamp `D:\CodexRuntime\codex_gmail_debug-register-gmail\logs_parallel_<timestamp>/`).

### B. Hậu quả
- Báo cáo cảnh báo Telegram gửi link log chết.
- Worker subagent nhận chỉ thị vào tìm file `logs/reg.log` không có thật, lãng phí turns tìm kiếm và phân tích lan man.

### C. Quy tắc & Giải pháp chuẩn hoá
1. **Tìm kiếm động 2 lớp (Dynamic Resolver):**
   - **Lớp 1 (Từ output):** Quét regex tìm `RUN_DIR:\s*([^\r\n]+)` hoặc `Log dir:\s*([^\r\n]+)` từ output của batch launcher. Nếu thư mục tồn tại, ưu tiên lấy file `summary.txt` hoặc chính thư mục đó.
   - **Lớp 2 (Từ runtime root):** Quét `Path(os.environ.get("GMAIL_RUNTIME_ROOT", r"D:\CodexRuntime\codex_gmail_debug-register-gmail")).glob("logs_parallel_*")`, sắp xếp theo `st_mtime` giảm dần để lấy log mới nhất.
   - **Lớp 3 (Fallback):** Nếu không tìm thấy, fallback về thư mục repo hoặc để trống `log_p=""` để alert system tự lấy log mặc định của cron.
2. **CẤM:** Tuyệt đối không hardcode đường dẫn file log giả định không tồn tại.

---

## 3. Cạm bẫy Unbounded Grep gây Timeout 900s

### A. Triệu chứng
Khi tìm kiếm chuỗi code trong repo Taadaa:
```bash
grep -rn "Get-Content" "/d/Taadaa/Tiktok_Reg"
grep -rn "Get-Content" "/d/Taadaa/register gmail"
```
Lệnh bị treo và dính `[Command timed out after 900s]` (15 phút), làm kiệt quệ thời gian của phiên và chạm giới hạn lượt lặp.

### B. Nguyên nhân
Các thư mục repo trên máy farm chứa các folder cực lớn: `.git`, `node_modules`, `python-envs`, thư mục dump video/ảnh, `runtime/`. Quét đệ quy toàn bộ thư mục gốc mà không giới hạn loại file sẽ duyệt hàng triệu byte.

### C. Quy tắc tìm kiếm an toàn (O(1) & Narrow Scoped)
1. **Luôn có filter file:** Thêm `--include="*.ps1"` hoặc `--include="*.py"` khi dùng `grep`.
2. **Không quét từ root:** Chỉ quét thư mục con cụ thể: `scripts/`, `tests/`.
3. **Ưu tiên O(1):** Nếu đã biết script chạy chính (`run_all.ps1`, `run_parallel.ps1`), dùng `read_file` hoặc `grep -n "<chuỗi>" "<file_đích>"`.
