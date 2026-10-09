# Post-Noon Chain Watchdog Triage & Verification Patterns

## Ngữ cảnh & Kiến trúc Chuỗi Sau Ca Trưa
Chuỗi tự động chạy sau ca trưa: `post_noon_chain_watchdog.py` (Cron `7d32d8c1907e`, khung giờ 14:30 - 17:30) điều phối tuần tự 2 Phase:
1. **Phase 1: Reg Gmail** (`run_all.ps1` -> `run_parallel.ps1` -> `gmail_reg_v10.py`, concurrency 15–40 máy)
2. **Phase 2: TikTok Add 2FA** (`run_batch_live_2fa.py` -> `run_capture_phase_b.py`, concurrency tối đa 40 máy)

---

## 1. Triệu Chứng False Reporting: "Tổng máy: 0, Success (0), Fail (0)" Dù Chạy Thật & Thành Công
- **Hiện tượng**: Watchdog chạy 20 - 30 phút, Telegram nhận báo cáo:
  ```text
  [BÁO CÁO CHUỖI SAU CA TRƯA] Reg Gmail -> Add 2FA TikTok
  - Thời gian: 15:06 -> 15:28 (22 phút)
  - Phase 1 (Reg Gmail - Code 1): Tổng máy: 0, Success (0), Fail (0)
  - Phase 2 (Add 2FA TikTok - Code 4): Tổng máy: 0, Success (0), Fail (0)
  ```
- **Thực tế ngầm**:
  - Phase 1: 15 máy chạy thật, 13 máy SUCCESS (M7, M8, M9, M10, M17, M23, M28, M42, M44, M48, M55, M64, M68), ghi nhận đầy đủ vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
  - Phase 2: 40 máy target chạy thật, Row 139 (M18) bật 2FA thành công và ghi mã Secret vào `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`.

---

## 2. Phân Tích 3 Root Cause Gây Lệch Báo Cáo & Khóa Oan Idempotency

### Nguyên nhân 1: Lệch Schema Regex Output của Subprocess
- Trong `post_noon_chain_watchdog.py`, hàm bóc tách:
  ```python
  def parse_summary_counts(output: str) -> tuple[int, int, int]:
      m = re.search(r"TOTAL=(\d+)\s+SUCCESS=(\d+)\s+FAILED=(\d+)", output)
      if m:
          return int(m.group(1)), int(m.group(2)), int(m.group(3))
      succs = len(re.findall(r"Machine\s+\d+.*(?:SUCCESS|OK)", output))
      fails = len(re.findall(r"Machine\s+\d+.*(?:FAIL|FAILED|ERROR)", output))
      return succs + fails, succs, fails
  ```
- **Lỗi Phase 1 (Reg Gmail - `run_parallel.ps1`)**:
  - `run_parallel.ps1` in chuỗi `TOTAL=...` qua `Write-Host`. Trong PowerShell 5.1 khi gọi từ Python `subprocess.run(capture_output=True)` không pipe rõ ràng hoặc bị warning/merge output cắt ngang, chuỗi `TOTAL=` có thể không xuất hiện trên `proc.stdout`.
- **Lỗi Phase 2 (TikTok 2FA - `run_batch_live_2fa.py`) — Lệch 100%**:
  - `run_batch_live_2fa.py` in bảng qua hàm `_print_results()`:
    `{item.machine} | {item.source_row} | {item.username_masked} | {item.status} | {item.reason or '-'}`
  - Format dòng thật: `18 | 139 | user*** | success | -`
  - **Không hề có chữ `TOTAL=`**, **không có chữ `Machine`**, và `status` in chữ thường (`success`, `failed`, `skipped`).
  - Regex watchdog bắt buộc chữ hoa `(?:SUCCESS|OK)` và tiền tố `Machine\s+\d+` nên **trượt 100%**, luôn trả về `(0, 0, 0)`.

### Nguyên nhân 2: Exit Code Non-Zero Do Cơ Chế Fail-Closed
- `run_parallel.ps1`: Có dòng cuối `if ($fail -gt 0) { exit 1 }`. Chỉ cần 1–2 máy fail (như M03 kẹt provider, M69 lỗi tạo acc), toàn bộ script trả **Exit Code 1** dù 13 máy khác thành công.
- `run_batch_live_2fa.py`: Có dòng cuối `return 0 if all(item.status in ("success", "skipped") for item in results) else 4`. Nếu có bất kỳ máy nào `failed`, script trả **Exit Code 4**.
- Watchdog in `Code 1` và `Code 4` khiến người vận hành tưởng toàn bộ chuỗi bị sập.

### Nguyên nhân 3: Bẫy Khóa Idempotency Khi Exit Code != 0
- Trong `post_noon_chain_watchdog.py`:
  ```python
  save_state(today_str, {"gmail_code": g_code, "2fa_code": t2fa_code})
  ```
- Hàm lưu `last_success_date = today_str` được gọi vô điều kiện, không phân biệt code 0 hay non-zero. Khi watchdog chạy lại ở tick sau, `already_ran_today()` trả về `True` ➔ ngắt không cho chạy bù hay báo cáo lại.

---

## 3. Quy Trình Khai Thác Chân Lý O(1) (Không Quét Đĩa)

Khi watchdog báo `Tổng máy: 0`, Coordinator KHÔNG được kết luận farm không chạy. Phải audit O(1) qua các nguồn sự thật (Ground Truth):

1. **Audit Phase 1 (Reg Gmail)**:
   - Thư mục runtime: `D:\CodexRuntime\codex_gmail_debug-register-gmail\`
   - Tìm thư mục log mới nhất: `logs_parallel_<yyyyMMdd_HHmmss>`
   - Đọc trực tiếp file JSON kết quả:
     `logs_parallel_<ts>\summary.json`
     File này chứa cấu trúc JSON chuẩn:
     ```json
     {
       "summaryRows": [...],
       "successCount": 13,
       "failedCount": 2
     }
     ```
   - Đối soát file Excel đích: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (kiểm tra timestamp sửa đổi).

2. **Audit Phase 2 (TikTok 2FA)**:
   - Thư mục backup: `C:\Users\Kibe\AppData\Local\codex_gmail_debug-tiktok-add-bao-mat-f2a\workbook-backups\`
   - Kiểm tra file backup mới nhất vừa tạo trong khung giờ chạy:
     `taikhoan_dat_v2_updated .<timestamp>.backup.xlsx`
   - So sánh diff giữa backup và workbook hiện tại (`D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`) tại sheet `Tài Khoản`:
     Nếu có row có cột E (2FA) chuyển từ `None` sang chuỗi Base32 (32 ký tự) ➔ đó là tài khoản đã add 2FA thành công thật.
   - Thư mục launch plan: `C:\Users\Kibe\AppData\Local\codex_gmail_debug-tiktok-add-bao-mat-f2a\lock-scope-audit-<run_id>.json` xác nhận danh sách máy đã target.

---

## 4. Chuẩn Hóa Patch Contract Cho Watchdog Parser (`post_noon_chain_watchdog.py`)

1. **Bóc tách Phase 1 từ `summary.json`**:
   - Thay vì parse regex từ stdout PowerShell, đọc trực tiếp file `summary.json` trong `logs_parallel_*` mới nhất sinh ra trong vòng 60 phút qua.
   - Lấy chính xác `summaryRows.Count`, `successCount`, `failedCount`.
2. **Bóc tách Phase 2 từ bảng output của `run_batch_live_2fa.py`**:
   - Thêm parser đọc các dòng table:
     ```python
     for line in t2fa_out.splitlines():
         parts = [p.strip() for p in line.split("|")]
         if len(parts) >= 4 and parts[0].isdigit():
             status = parts[3].lower()
             if status == "success":
                 succs += 1
             elif status == "failed":
                 fails += 1
     ```
3. **Idempotency an toàn**:
   - Chỉ lưu `last_success_date` khi có ít nhất một phase có success > 0 hoặc cả 2 phase đều exit code 0.
   - Khi `gmail_code != 0` hoặc `2fa_code != 0`, báo rõ số máy thành công kèm cảnh báo `(Exit code != 0: một số máy gặp lỗi cần audit)`.
