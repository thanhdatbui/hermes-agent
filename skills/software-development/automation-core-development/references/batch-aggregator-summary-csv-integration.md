# Batch Aggregator & summary.csv Integration Pattern

## 1. Kiến Trúc Dual-Threshold Systemic Failure Detection

`automation_core.batch_aggregator` dùng cơ chế ngưỡng kép để lọc báo động:
- **Tỷ lệ lỗi (min_rate)**: $\ge 10\%$ (mặc định)
- **Số lượng máy lỗi (min_count)**: $\ge 3$ máy (mặc định)

### Quy tắc cảnh báo & Silent Skip:
- **Systemic Failure (`should_alert = True`)**: Thỏa mãn ĐỒNG THỜI cả hai điều kiện `rate >= min_rate` VÀ `count >= min_count`. Kích hoạt Telegram Farm Alert kèm ảnh snapshot đại diện và canary test directive.
- **Sporadic Failure (`should_alert = False`)**: Khi số lỗi nhỏ lẻ (dưới 10% hoặc dưới 3 máy), batch aggregator ghi nhận trạng thái **"Silent Skip - Fleet safe"** và TUYỆT ĐỐI KHÔNG gửi Telegram alert để tránh spam / alarm fatigue cho người vận hành.

---

## 2. Quy Cách Parse `summary.csv` từ PowerShell Runners

Các runner PowerShell (như `Tiktok-video/run_tiktok_upload_batch.ps1`) xuất `summary.csv` qua lệnh:
```powershell
$results | Sort-Object Machine | Export-Csv -LiteralPath $summaryPath -NoTypeInformation -Encoding UTF8
```

### Các cột dữ liệu chuẩn:
- `Machine`: Số thứ tự hoặc serial (ví dụ: `8`, `14`, `m8`, `DEV-01`). Khi nạp vào `MachineResult`, nếu là chuỗi số thuần (`machine_val.isdigit()`), chuẩn hóa thành `f"m{machine_val}"` để khớp chữ ký `_RE_SERIAL_TAADAA`.
- `Status`: Chuỗi trạng thái (`"THÀNH CÔNG"`, `"LỖI"`, `"SKIPPED_LOCKED"`, `"LOGIN_RECOVERY_BLOCKED"`).
- `Verified`: Chuỗi boolean (`"True"`, `"False"`).
- `Reason`: Mô tả nguyên nhân lỗi (ví dụ: `"DEVICE_LOCK_FAILED: device lock active"`, `"upload_subprocess_nonzero (exit 2)"`).
- `ExitCode`: Mã thoát tiến trình con (`"0"`, `"1"`, `"2"`, `"3"`).
- `Report`: Đường dẫn tới file JSON report (ví dụ: `...\runs\<id>\report.json`).

### Logic suy luận trạng thái máy:
- **Thành công (`succeeded = True`)**: `Verified.lower() in ("true", "1")` VÀ `ExitCode in ("0", "")` VÀ `Status.upper() not in ("LỖI", "FAILED", "ERROR", "SKIPPED_LOCKED")`.
- **Thất bại (`succeeded = False`)**: Trích xuất `error_type` và `error_message` từ file `Report` JSON nếu tồn tại; nếu không có file `Report`, bóc tách tiền tố từ `Reason` (ví dụ `DEVICE_LOCK_FAILED: ...` $\rightarrow$ `error_type="DEVICE_LOCK_FAILED"`).
- **Snapshot Media**: Tìm kiếm ảnh hiện trường từ trường `snapshot_png` / `screenshot_path` trong `report.json` hoặc thư mục con `screenshots/` của phiên chạy.

---

## 3. Hook Không Chặn (Non-Blocking) Vào PowerShell Runner

Chèn hook ngay sau khi xuất `$summaryPath`, bọc trong khối `try/catch` để không làm gián đoạn mã thoát và báo cáo của runner:

```powershell
$summaryPath = Join-Path $batchDir "summary.csv"
$results | Sort-Object Machine | Export-Csv -LiteralPath $summaryPath -NoTypeInformation -Encoding UTF8

try {
    Write-Host "Đang tổng hợp lỗi batch và đánh giá ngưỡng cảnh báo..."
    $aggregatorCmd = if ($python -and (Test-Path -LiteralPath $python)) { $python } else { "python" }
    & $aggregatorCmd -m automation_core.batch_aggregator "$summaryPath" --telegram
} catch {
    Write-Warning "Không thể chạy batch_aggregator: $_"
}
```

---

## 4. Tích Hợp Telegram Farm Alert (`automation_core.alerts`)

- Gửi ảnh hiện trường bằng `_send_telegram_photo` (giới hạn caption 1024 ký tự qua `_safe_truncate_html`), fallback sang `_send_telegram_text` nếu ảnh upload lỗi hoặc không có ảnh.
- Kiểm tra `_is_test_environment()`: Trong môi trường pytest (`PYTEST_CURRENT_TEST` hoặc `AUTOMATION_CORE_TEST_MODE`), tắt toàn bộ network call tới Telegram để đảm bảo unit tests chạy offline và cách ly tuyệt đối.

---

## 5. Cạm Bẫy Tra Cứu File Trên Windows Farm (`D:\Taadaa`)

- **CẤM DÙNG `find /d/Taadaa -name ...`**: Thư mục `D:\Taadaa` chứa hàng trăm GB video, deep learning models (`.pt`), node_modules và artifacts. Lệnh find đệ quy toàn ổ sẽ gây treo terminal 15 phút (900s timeout) làm cạn kiệt budget lượt gọi tool.
- **Quy tắc**: Chỉ dùng `search_files` hoặc `ls` giới hạn đúng thư mục con của repo mục tiêu (ví dụ `/d/Taadaa/Tiktok-video/runs`).
