# PowerShell Runner Dot-Source Guard & Chained Pipeline Safety

## 1. Sự cố thực tế (Incident 06/09/2026)
- **Hiện tượng:** Lúc 05:30 sáng, một subagent khi kiểm chứng hàm `Get-RunResultFromLog` trong PowerShell đã thực thi lệnh dot-source:
  ```powershell
  . 'D:\Taadaa\register gmail\run_parallel.ps1'
  ```
- **Hậu quả:** File `run_parallel.ps1` không có guard chặn dot-sourcing. Khi được nạp bằng toán tử `.`, PowerShell lập tức thực thi toàn bộ code ở top-level và khởi động một batch chạy thật (`gmail_reg_v10.py`) trên 17 máy farm cùng lúc, gây xung đột thiết bị ngay trước ca nuôi acc 06:00.
- **Biện pháp khẩn cấp đã áp dụng:** Dùng `cmd.exe /c "taskkill /F /T /PID <parent_pid>"` để ngắt sạch toàn bộ cây tiến trình PowerShell cha và các process Python/CMD con trước khi rạng sáng.

---

## 2. Quy chuẩn bất biến cho script PowerShell Runner (Dot-Source Guard)

Mọi file script PowerShell đóng vai trò Runner, Launcher hoặc Batch Orchestrator (`run_parallel.ps1`, `run_all.ps1`, `run-feed-session.ps1`...) **BẮT BUỘC** phải có guard kiểm tra ngữ cảnh thực thi:

### Cách 1: Early Return khi dot-sourced (Khuyên dùng cho script hiện hữu)
Đặt ngay sau các khai báo `function`:
```powershell
# Chống kích hoạt chạy batch khi script được dot-source để test hàm
if ($MyInvocation.InvocationName -eq '.') {
    return
}
```

### Cách 2: Main Wrapper Pattern
Đóng gói toàn bộ luồng chạy chính vào `function Main` và chỉ gọi khi script được thực thi độc lập:
```powershell
function Main {
    param($ScriptArgs)
    # Toàn bộ logic chạy batch ở đây
}

if ($MyInvocation.InvocationName -ne '.') {
    Main $args
}
```

---

## 3. Cấm kỵ đối với Agent / Worker khi viết kiểm thử PowerShell

1. **CẤM dot-source trực tiếp file runner nếu chưa kiểm tra file có guard:**
   - Trước khi gõ `. 'path/to/runner.ps1'`, bắt buộc phải đọc file xem có `if ($MyInvocation.InvocationName -eq '.')` hay không.
   - Nếu script chưa có guard, **CẤM dot-source**. Hãy trích xuất function cần test ra script kiểm thử cô lập hoặc bổ sung guard vào script trước.
2. **Ưu tiên kiểm thử qua Python native hoặc script test độc lập:**
   - Hạn chế tối đa việc load cả môi trường PowerShell production chỉ để kiểm tra định dạng chuỗi hay regex.

---

## 4. Chained Pipeline Prerequisites (Chuỗi ban đêm & Pipeline đa pha)

Trong các pipeline xâu chuỗi nhiều pha (như `run_night_chain_pipeline.py`: Reg Gmail -> Reg TikTok -> Add 2FA):

1. **Module Top-Level Resolution Fail-Closed:**
   - Các repo consumer như `tiktok-add-bao-mat-f2a` gọi `resolve_proxy_mapping_path()` ngay tại top-level import.
   - Khi chạy qua subprocess từ pipeline cha, bắt buộc phải kế thừa hoặc inject đầy đủ `TAADAA_HOST_CONFIG` và `AUTOMATION_PROXY_MAPPING` vào `env` của subprocess. Thiếu biến này sẽ gây `ConsumerPreflightError` sập script ngay tại dòng `import`.
2. **Ràng buộc phụ thuộc dữ liệu giữa các pha (Data Dependency Gating):**
   - Phase 2 (Reg TikTok bằng Gmail) chỉ được phép nạp danh sách máy mà Phase 1 (Reg Gmail) đã xác nhận `SUCCESS` và tài khoản đã tồn tại trong ứng dụng Gmail trên máy.
   - Tuyệt đối không nạp máy đã fail ở Phase 1 vào Phase 2, tránh gây lãng phí 15-20 phút chờ OTP không bao giờ về (`account list chua thay ...@gmail.com`).

---

## 5. Bẫy NativeCommandError Khi Gọi Child PowerShell (Case 145 — 09/09/2026)

### Hiện tượng
`run_all.ps1` gọi `run_parallel.ps1` qua tiến trình con:
```powershell
powershell @parallelArgs   # <- NGUY HIỂM
```
Khi child trả về non-zero exit code (vì có máy fail trong batch) hoặc ghi bất kỳ gì ra stderr, PowerShell 5.1 của host bọc thông điệp đó thành một `ErrorRecord` và in:
```
+ FullyQualifiedErrorId : NativeCommandError
    + CategoryInfo          : NotSpecified: (...) [], RemoteException
```
Những dòng này bị `subprocess.run(capture_output=True)` của Python pipeline cha thu về trong `stderr`, gây nhiễu log parser.

### Fix chuẩn: In-Session Splatting (không spawn child PS)
```powershell
# THAY THẾ: dùng hashtable splatting, gọi trong session hiện tại
$parallelParams = @{ maxWorkers = $maxWorkers }
if ($cooldownDays -gt 0) { $parallelParams['cooldownDays'] = $cooldownDays }
# ... thêm các tham số khác ...

$parallelScript = Join-Path $scriptRoot 'run_parallel.ps1'
& $parallelScript @parallelParams
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```
`& script @hashtable` chạy trong cùng process PowerShell, không tạo child process mới, nên không có `NativeCommandError` bọc lỗi.

### Bộ lọc rác diagnostic khi parse output PowerShell từ Python
Khi `subprocess.run()` capture output của script PowerShell, bắt buộc lọc bỏ các dòng rác chẩn đoán trước khi scan tìm lỗi thật:
```python
PS_NOISE_MARKERS = (
    "NativeCommandError",
    "CategoryInfo",
    "FullyQualifiedErrorId",
    "RemoteException",
    "+ CategoryInfo",
    "+ FullyQualifiedErrorId",
    "+ ~~~",
    "At line:",
)

def is_ps_noise(line: str) -> bool:
    return any(noise in line for noise in PS_NOISE_MARKERS)

# Dùng trong failure scan:
for line in reversed(lines):
    if is_ps_noise(line):
        continue
    if any(marker.casefold() in line.casefold() for marker in failure_markers):
        return line
```

---

## 6. Chặn Farm Alert Giả: Phân Biệt Batch Attrition vs. Script Crash (Case 145)

### Anti-Pattern nguy hiểm
```python
# SAI: cứ exit_code != 0 là alert lỗi script/pipeline
if gmail_code != 0:
    _send_night_chain_alert("Phase 1 (Reg Gmail)", gmail_code, ...)
```
Batch runner như `run_parallel.ps1` trả về `exit 1` khi có bất kỳ máy nào fail (`if ($fail -gt 0) { exit 1 }`). Đây là hao hụt tự nhiên của đàn máy — batch vẫn chạy đầy đủ và ghi nhận kết quả từng máy.

### Pattern đúng: kiểm tra summary trước khi alert
```python
if gmail_code != 0:
    gmail_details = parse_gmail_details(gmail_out)
    gmail_log_p = find_latest_gmail_log_path(gmail_out)
    # Nếu batch hoàn tất và ghi nhận kết quả (total > 0),
    # batch_aggregator đã xử lý theo fleet error budget — không alert crash
    if not (isinstance(gmail_details, dict) and int(gmail_details.get("total", 0) or 0) > 0):
        _send_night_chain_alert("Phase 1 (Reg Gmail)", gmail_code,
                                parse_summary_line(gmail_out, "Gmail"), gmail_log_p)
```

### Nguyên tắc tổng quát
- `exit_code != 0` + `summary có total > 0` = **Batch hoàn tất, có hao hụt tự nhiên** → im lặng, để fleet error budget & `batch_aggregator` xử lý.
- `exit_code != 0` + `summary không tạo được / total = 0` = **Script thực sự crash** → mới alert lỗi script/pipeline.

### Metrics chuẩn để expose từ runner (cho parser pha sau)
Runner PowerShell BẮT BUỘC in ra stdout các dòng có định dạng parseable:
```powershell
Write-Host "KET QUA: OK=$ok | SKIP_DEVICE_LOCKED=$skipLocked | FAILED=$fail"
Write-Host "TOTAL=$($summaryRows.Count) SUCCESS=$successCount FAILED=$failedCount SKIP_DEVICE_LOCKED=$skipDeviceLockedCount PENDING_VERIFY=$pendingVerifyCount PHONE_VERIFY=$phoneCount ACCOUNT_CREATION_ERROR=$accountCreationErrorCount FAILED_OTHER=$failedOtherCount"
Write-Host "RUN_DIR: $logDir"
```
Python parser dùng regex `r"TOTAL=\d+"` và `r"RUN_DIR:\s*([^\r\n]+)"` để extract O(1), không cần quét toàn bộ log.
