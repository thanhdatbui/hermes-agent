# Batch Aggregator & Consumer Hook Contract

## 1. Mục Đích & Kiến Trúc
Hệ thống `automation_core.batch_aggregator` dùng để phát hiện lỗi hệ thống (systemic failure) và cảnh báo P0 tức thì khi chạy batch trên fleet thiết bị Android (TikTok feed, Gmail reg, Hotmail reg...).

Module chính: `automation-core/src/automation_core/batch_aggregator.py`
Entrypoint CLI: `python -m automation_core.batch_aggregator <path-to-dir-or-file> [--telegram] [--min-rate R] [--min-count C]`

---

## 2. Các Layout Dữ Liệu Hỗ Trợ
`load_results_from_run_dir` và `parse_results_from_file` hỗ trợ 3 layout dữ liệu chuẩn từ các consumer runners:

1. **Layout 1 (Root manifest với `multi_machine_summary`):**
   - File `<run_dir>/run_manifest.json` chứa key `multi_machine_summary`: danh sách dict các máy (`machine`/`serial`, `final_status`/`status`, `blocker_type`/`error_type`, `stop_reason`/`reason`/`error_message`, `artifact_root`).
   - Tự động trích xuất snapshot PNG/XML trong `artifact_root` nếu có.

2. **Layout 2 (`machines/<serial>/` đa cấp kèm fallback):**
   - Thư mục `<run_dir>/machines/<serial>/run_manifest.json`.
   - Hỗ trợ cả 2 cấp thư mục lồng nhau (`machines/<serial>/<subrun>/run_manifest.json`).
   - Nếu `error_message` rỗng, tự động đọc fallback từ `summary.txt` cùng cấp tìm dòng `stop_reason:` hoặc `reason:`.

3. **Layout 3 (Subdir runner manifest):**
   - Bất kỳ thư mục con `<run_dir>/<job_dir>/run_manifest.json`.

---

## 3. Quy Tắc P0 Auth/Login Alert (Bypass Ngưỡng Systemic)
Thông thường, `evaluate_batch` chỉ cảnh báo khi lỗi đạt ngưỡng kép:
`rate >= min_rate` (mặc định 10%) VÀ `count >= min_count` (mặc định 3).

**Ngoại lệ P0 bắt buộc:**
- Các lỗi liên quan đến phiên đăng nhập / văng tài khoản / checkpoint phải được cảnh báo NGAY LẬP TỨC mà không phụ thuộc vào ngưỡng count hay rate.
- Danh sách từ khóa kích hoạt P0:
  `AUTH_CRITICAL_KEYWORDS = ("login", "account screen", "verification", "checkpoint", "auth", "văng", "identity")`
- Nếu phát hiện bất kỳ máy nào dính lỗi chứa từ khóa trên:
  - Bật `should_alert = True`.
  - Format mục `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]` trong tin nhắn Telegram liệt kê danh sách serial và lý do lỗi.

---

## 4. Chuẩn Hook Vào PowerShell Consumer Runners

### A. TikTok Feed Session (`run-feed-session.ps1`)
Sau khi lệnh python kết thúc, resolve `$targetBatchDir` an toàn từ `$artifactRootPath` thay vì chỉ dựa vào biến `$runDir` đơn lẻ:
```powershell
$targetBatchDir = $null
if ($runDir -and (Test-Path $runDir)) {
    $targetBatchDir = $runDir
} elseif ($artifactRootPath -and (Test-Path $artifactRootPath)) {
    if (Test-Path (Join-Path $artifactRootPath "run_manifest.json")) {
        $targetBatchDir = $artifactRootPath
    } else {
        $subDirs = Get-ChildItem -LiteralPath $artifactRootPath -Directory | Sort-Object LastWriteTime -Descending
        if ($subDirs) {
            $targetBatchDir = $subDirs[0].FullName
        }
    }
}

if ($targetBatchDir) {
    try {
        & $Python -m automation_core.batch_aggregator "$targetBatchDir" --telegram
    } catch {
        Write-Warning "batch_aggregator hook error: $_"
    }
}
```

### B. Parallel Batch Runner (`register gmail/run_parallel.ps1`)
Sau khi in Merge Summary và ghi file `$summaryJson`:
```powershell
if (Test-Path $summaryJson) {
    try {
        Write-Host "Evaluating batch aggregation alerts..."
        & $Python -m automation_core.batch_aggregator "$summaryJson" --telegram
    } catch {
        Write-Warning "batch_aggregator hook error: $_"
    }
}
```

---

## 5. Pitfall Quy Trình Thực Thi Cho Coding Agent
- **Không đọc thừa thãi trước patch đã có hợp đồng**: Khi nhận được hợp đồng patch mã nguồn gồm đầy đủ `old_string` và `new_string`, gọi tool `patch` trực tiếp. Việc gọi `read_file` liên tiếp để khảo sát lại từng đoạn sẽ đốt sạch ngân sách tool iterations trước khi kịp chạy pytest.
- **Xác minh pytest trước khi kết thúc**: Sau khi patch xong các module lõi và test cases, luôn chạy:
  `pytest tests/test_batch_aggregator.py -v`
  để bảo đảm 100% tests pass.
