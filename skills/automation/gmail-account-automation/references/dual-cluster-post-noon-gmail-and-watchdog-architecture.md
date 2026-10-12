# Dual-Cluster Post-Noon Chain Architecture (Kibe & Admin Farm Reg Gmail)

**Ngày chốt:** 2026-10-12  
**Chỉ thị từ Operator:** Gọi luôn Farm Admin cho luồng Reg Gmail sau ca trưa song hành cùng Farm Kibe.

---

## 1. Kiến Trúc Điều Phối Song Hành 2 Cụm Farm

### Bối cảnh trước đây:
- Phase 2 (Add 2FA TikTok) đã hỗ trợ phân phối kép: chạy local trên Kibe và gọi từ xa sang `admin-farm` qua SSH.
- Phase 1 (Reg Gmail) trước đây chỉ gọi cục bộ trên máy Kibe (`D:/Taadaa/register gmail/run_all.ps1`), bỏ trống 80 máy Farm Admin (Máy 201-280).

### Thiết kế điều phối chuẩn hóa (`post_noon_chain_watchdog.py`):
1. **Cluster Kibe (Máy 1 - 80):**
   - Chạy trực tiếp `powershell.exe -File run_all.ps1`.
   - Sử dụng inventory mặc định `taikhoan_run_safe.xlsx` và workbook `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
   - Đầu ra log mang tiền tố: `=== CLUSTER KIBE (MÁY 1-80) ===`.
2. **Cluster Admin (Máy 201 - 280):**
   - Kích hoạt qua SSH `ssh -o ConnectTimeout=10 admin-farm` với PowerShell `EncodedCommand` (Base64 UTF-16LE).
   - Thiết lập môi trường độc lập cho Farm Admin:
     ```powershell
     $env:PYTHONIOENCODING = 'utf-8'
     $env:PYTHONUTF8 = '1'
     Set-Location 'D:/Taadaa/register gmail'
     $env:PROXY_DIENTHOAI_PATH = 'D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx'
     $env:GMAIL_EXCEL_FILE = 'D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx'
     $env:PYTHONPATH = 'D:/Taadaa/register gmail;D:/Taadaa/automation-core/src'
     $env:GMAIL_REG_PYTHON_EXE = 'D:\Taadaa\python-envs\automation\Scripts\python.exe'
     & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ./run_all.ps1
     ```
   - Đầu ra log mang tiền tố: `=== CLUSTER ADMIN (MÁY 201-280) ===`.

---

## 2. Quy Ước Phân Loại Lỗi & Exit Codes (Disambiguation Contract)

Reviewer và Sol Auditor yêu cầu phân biệt rõ ràng giữa lỗi thiết bị trong batch và lỗi sập runner/mạng:

* **Exit Code 0:** Toàn bộ máy trong batch hoàn tất thành công.
* **Exit Code 1 (Batch Execution with failures):** Batch chạy được nhưng có thiết bị thất bại (do Google đòi SĐT `phone_verify`, lỗi provider UI hoặc thiết bị offline). Nếu `g_tot > 0`, watchdog vẫn coi là lượt chạy hợp lệ của batch.
* **Exit Code 2 (Runner Crash / Infrastructure Failure):**
  - Bắt nguồn từ ngoại lệ Python, lệnh `subprocess.run` timeout, hoặc lỗi kết nối SSH tới `admin-farm`.
  - Format thông điệp chuẩn hóa:
    `RUNNER_ERROR|<CLUSTER>|<ExceptionType>: <Details>`
    (Ví dụ: `RUNNER_ERROR|ADMIN|TimeoutExpired: ssh timeout`).
  - Khi một cluster gặp Exit Code 2: Watchdog ghi nhận trạng thái `failed` vào state để phục vụ retry ở chu kỳ tiếp theo, nhưng **KHÔNG** làm gián đoạn việc tổng kết của cluster còn lại hoặc Phase 2 (TikTok 2FA).

---

## 3. Correlation ID & Structured Observability (`WATCHDOG_EVENT`)

Nhằm phục vụ truy vết ở quy mô 160 máy không bị phụ thuộc hoàn toàn vào parse text log:
1. **`run_id`:** Mỗi chu kỳ watchdog sinh một mã định danh duy nhất (12 hex chars, ví dụ `a1b2c3d4e5f6`). `run_id` được in vào header báo cáo Telegram và lưu xuyên suốt trong `post_noon_chain_state.json`.
2. **Structured Log (`WATCHDOG_EVENT`):**
   Ghi ra `stderr` dưới dạng JSON có cấu trúc:
   ```json
   WATCHDOG_EVENT {"ts": "2026-10-12T19:30:00+07:00", "run_id": "a1b2c3d4e5f6", "event": "cluster_runner_error", "cluster": "ADMIN", "error": "TimeoutExpired"}
   ```

---

## 4. Báo Cáo Đối Xứng Chuẩn Hóa Trên Telegram

Khớp marker cluster linh hoạt bằng regex `re.search(r"===\s*CLUSTER\s+ADMIN\b", output, re.I)` để tránh gãy khi định dạng khoảng trắng thay đổi:

```text
[BÁO CÁO CHUỖI SAU CA TRƯA] [LANE ALL (GMAIL + TIKTOK 2FA)]
- Thời gian: 15:45 -> 16:40 (55 phút)
- Mã chạy (run_id): 7e372d8054aa

- Phase 1 (Reg Gmail - Code 0):
  • Farm Kibe (Máy 1-80): Hoàn tất 5 máy | Bỏ qua 0 | Lỗi 10
  • Farm Admin (Máy 201-280): Hoàn tất 6 máy | Bỏ qua 0 | Lỗi 9

- Phase 2 (Add 2FA TikTok - Code 4):
  • Farm Kibe (Máy 1-80): Hoàn tất 12 máy | Bỏ qua 10 | Lỗi 52
  • Farm Admin (Máy 201-280): Hoàn tất 8 máy | Bỏ qua 51 | Lỗi 21
```
