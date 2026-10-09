# PowerShell NativeCommandError Leakage & Batch Summary Parsing

## 1. Bối cảnh & Sự cố thực tế (Incident 09/09/2026)
- **Cảnh báo nhận được:**
  ```text
  🚨 [FARM ALERT: LỖI SCRIPT / PIPELINE]
  • Quy trình / Script: Chuỗi Ban Đêm Reg & 2FA (night-chain-reg-pipeline / run_night_chain_pipeline.py)
  • Chi tiết lỗi: Phase 1 (Reg Gmail) thất bại (exit_code=1): + FullyQualifiedErrorId : NativeCommandError
  ```
- **Thực tế hiện trường O(1):**
  - Batch Reg Gmail chạy trên 15 máy farm: 3 máy thành công (đã merge vào Excel), 12 máy fail do proxy timeout / captcha / phone verify (hao hụt tự nhiên).
  - Kết quả đã ghi đủ vào `summary.txt` và `summary.json`.
  - Tiến trình hoàn toàn không bị crash hay văng exception, nhưng hệ thống lại réo còi báo động "LỖI SCRIPT / PIPELINE".

---

## 2. Chuỗi nguyên nhân gốc rễ (Chain of Causes)

### A. PowerShell 5.1 stderr wrapper (`NativeCommandError`)
- Trong Windows PowerShell 5.1, khi script chạy dưới `$ErrorActionPreference = 'Stop'` hoặc khi gọi tiến trình con native:
  - Bất kỳ luồng ghi nào vào stderr từ executable con (kể cả warning lành tính, python logging hay exit code non-zero) đều bị PowerShell chuyển thành `System.Management.Automation.RemoteException`.
  - Chuỗi text in ra console chứa:
    ```text
    powershell.exe : ...
        + CategoryInfo          : NotSpecified: (...:String) [], RemoteException
        + FullyQualifiedErrorId : NativeCommandError
    ```
- Khi `run_all.ps1` gọi `powershell @parallelArgs` (spawn process lồng), lỗi stderr này bị leak thẳng ra ngoài cho process cha (`run_night_chain_pipeline.py`).

### B. Exit Code của Batch Runner (`if ($fail -gt 0) { exit 1 }`)
- `run_parallel.ps1` kết thúc bằng:
  ```powershell
  Release-QueuedReservations
  if ($fail -gt 0) {
      exit 1
  }
  ```
- Việc trả về 1 khi có ít nhất 1 máy fail là bình thường với CLI độc lập, nhưng đối với pipeline xâu chuỗi nhiều pha, nếu chỉ nhìn vào exit code để phân định "sập script" thì mọi batch có hao hụt đều bị quy kết là crash.

### C. Cơ chế parse summary ngây thơ (Naive Reverse Scanning)
- `parse_summary_line` quét từ cuối chuỗi ngược lên tìm `failure_markers` chứa `"Error"`, `"FAILED"`.
- Vì dòng `+ FullyQualifiedErrorId : NativeCommandError` có chữ `Error` và nằm ở cuối stderr, hàm lập tức chọn dòng này làm lý do lỗi thay vì tìm summary thật sự.
- Trong khi đó, dòng summary của runner dùng `KET QUA: OK=...` lại không nằm trong danh sách `summary_markers`.

---

## 3. Quy chuẩn bất biến cho Pipeline & Runner

### Quy tắc 1: Phân định rạch ròi "Script Crash" vs "Batch Execution Result"
- `send_farm_script_alert` (Cảnh báo đỏ LỖI SCRIPT / PIPELINE) **CHỈ ĐƯỢC KÍCH HOẠT KHI**:
  1. Script văng unhandled exception / traceback.
  2. Script không tồn tại hoặc sai đường dẫn preflight.
  3. Quá thời gian timeout (90m) bị force kill.
  4. Script kết thúc nhưng **KHÔNG TẠO ĐƯỢC** `summary.json` / `summary.txt` (chứng tỏ bị chết giữa chừng).
  5. Bước merge kết quả vào dữ liệu trung tâm thất bại (`BLOCKED: merge success results that bai`).
- Khi batch đã chạy xong, tạo `summary.json` có `total > 0` và merge thành công:
  - Tỷ lệ fail từng máy là **Hao hụt vận hành (Operational Failure)**, đã có `automation_core.batch_aggregator` xử lý theo Fleet Error Budget và xuất hiện trong báo cáo tổng kết cuối chuỗi.
  - **TUYỆT ĐỐI CẤM** gọi `_send_night_chain_alert` / `send_farm_script_alert` khi batch đã hoàn tất.

### Quy tắc 2: Lọc bỏ rác PowerShell trong Error Parser
Khi viết hàm bóc tách lỗi từ output CLI trên Windows, **BẮT BUỘC** bỏ qua các dòng boilerplate của PowerShell:
```python
POWERSHELL_NOISE = (
    "NativeCommandError",
    "CategoryInfo",
    "FullyQualifiedErrorId",
    "RemoteException",
    "+ CategoryInfo",
    "+ FullyQualifiedErrorId",
    "+ ~~~",
    "At line:",
)
```
Nếu một dòng chứa bất kỳ token nào ở trên, tuyệt đối không chọn làm error summary.

### Quy tắc 3: Gọi Script con trong PowerShell cùng Session
Tránh spawn tiến trình `powershell.exe` lồng nhau không cần thiết trong cùng môi trường. Ưu tiên:
```powershell
& (Join-Path $scriptRoot 'run_parallel.ps1') @parallelParams
```
thay vì `powershell @parallelArgs`.

### Quy tắc 4: Xuất chuẩn Summary Markers ra Stdout
Mọi runner PowerShell khi in kết quả bắt buộc phải ghi rõ các marker chuẩn ra `Write-Host`:
```powershell
Write-Host "RUN_DIR: $logDir"
Write-Host "TOTAL=$($summaryRows.Count) SUCCESS=$successCount FAILED=$failedCount SKIP_DEVICE_LOCKED=$skipDeviceLockedCount PENDING_VERIFY=$pendingVerifyCount PHONE_VERIFY=$phoneCount ACCOUNT_CREATION_ERROR=$accountCreationErrorCount FAILED_OTHER=$failedOtherCount"
Write-Host "KET QUA: OK=$ok | SKIP_DEVICE_LOCKED=$skipLocked | FAILED=$fail"
```
Giúp các script wrapper cha hoặc regex parser nhận diện ngay lập tức ở độ phức tạp $O(1)$.
