# PowerShell NativeCommandError Artifact & Chained Batch Pipeline Alert Suppression

## 1. Hiện tượng & Sự cố thực tế (Incident 09/09/2026)
- **Cảnh báo nhận được:**
  ```text
  🚨 [FARM ALERT: LỖI SCRIPT / PIPELINE]
  • Quy trình / Script: Chuỗi Ban Đêm Reg & 2FA (night-chain-reg-pipeline / run_night_chain_pipeline.py)
  • Chi tiết lỗi: Phase 1 (Reg Gmail) thất bại (exit_code=1): + FullyQualifiedErrorId : NativeCommandError
  ```
- **Hiện trường thực tế:**
  - Batch Reg Gmail chạy trên 15 máy: 3 máy thành công (đã merge tài khoản vào Excel `gmail_clean_v2.xlsx`), 12 máy thất bại do proxy timeout / recaptcha / phone verify.
  - File `summary.txt` và `summary.json` đã được tạo đầy đủ. `batch_aggregator` đã được gọi.
  - Tuy nhiên, `run_night_chain_pipeline.py` vẫn kích hoạt cảnh báo đỏ sập pipeline/script lên Telegram.

---

## 2. Phân tích nguyên nhân gốc rễ (3 tầng bẫy)

1. **Bẫy Exit Code 1 trên Batch Runner (`run_parallel.ps1`):**
   - Script chạy batch kết thúc bằng:
     ```powershell
     if ($fail -gt 0) { exit 1 }
     ```
   - Trong vận hành phone farm, batch nhiều máy luôn có tỷ lệ hao hụt tự nhiên ($fail > 0$). Việc trả về exit code 1 là quy ước CLI cục bộ nhưng khiến script cha hiểu nhầm là crash toàn bộ.

2. **Bẫy PowerShell 5.1 Nested Process & `NativeCommandError` (`run_all.ps1`):**
   - `run_all.ps1` gọi launcher con bằng child process:
     ```powershell
     powershell @parallelArgs
     if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
     ```
   - Trên Windows PowerShell 5.1, khi một tiến trình native con trả về non-zero exit code hoặc ghi stderr (kể cả warning vô hại), PowerShell tự động bọc stderr lại thành `System.Management.Automation.RemoteException` và in ra khối text:
     ```text
     powershell.exe : ...
         + CategoryInfo          : NotSpecified: (...:String) [], RemoteException
         + FullyQualifiedErrorId : NativeCommandError
     ```

3. **Bẫy Quét Summary & Regex Parser (`run_night_chain_pipeline.py`):**
   - `parse_summary_line(output)` chỉ quét stdout tìm `summary_markers` (`TOTAL=`, `SUCCESS=`). Do `run_parallel.ps1` chỉ in `KET QUA: OK=...` ra stdout mà không in `TOTAL=`, parser không tìm thấy marker.
   - Khi fallthrough sang `failure_markers` (`"FAILED"`, `"ERROR"`, `"TIMEOUT"`), từ `"Error"` trong `"NativeCommandError"` khớp điều kiện, khiến parser chọn nhầm dòng rác của PowerShell làm thông điệp lỗi chính.
   - Hàm `main()` kiểm tra `if gmail_code != 0:` lập tức kích hoạt `_send_night_chain_alert` (`send_farm_script_alert`), ngộ nhận hao hụt máy là sập script.

---

## 3. Quy chuẩn khắc phục bất biến

1. **Không bọc Nested `powershell.exe` trong launcher cha:**
   - Trong launcher PowerShell (`run_all.ps1`), gọi trực tiếp script con trong cùng phiên bằng toán tử gọi lệnh (`& $scriptPath @params`) hoặc hashtable splatting, tránh spawn tiến trình `powershell.exe` con sinh `NativeCommandError`.

2. **Chuẩn hóa Summary Line ra stdout:**
   - Mọi batch runner PowerShell khi hoàn tất bắt buộc in ra console:
     ```powershell
     Write-Host "TOTAL=$($summaryRows.Count) SUCCESS=$successCount FAILED=$failedCount ..."
     Write-Host "RUN_DIR: $logDir"
     ```
     để tiến trình cha parse O(1) mà không cần quét đĩa.

3. **Lọc sạch PowerShell Noise trong Parser:**
   - Parser output phải chủ động bỏ qua các dòng rác chẩn đoán của PowerShell trước khi tìm error marker:
     ```python
     ps_noise = (
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

4. **Phân biệt Lỗi Script / Pipeline vs Kết quả Vận hành Batch:**
   - Script điều phối pipeline đa pha (`run_night_chain_pipeline.py`) chỉ được kích hoạt `send_farm_script_alert` khi script thực sự bị crash, timeout hoặc không sinh được summary (preflight block, syntax error).
   - Nếu `parse_gmail_details()` trả về `total > 0` và summary đã được sinh ra: batch đã hoàn tất chu trình. Tỷ lệ lỗi được quản lý bởi `automation_core.batch_aggregator` theo Fleet Error Budget (ngưỡng >=10-15%, >=3 máy) và tổng hợp tại báo cáo cuối phiên, TUYỆT ĐỐI không bắn alert lỗi script giữa chừng.
