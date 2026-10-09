# Windows Directory Junction Deployment & Closeout Anti-Surrender Lessons

## 1. Anti-Surrender & Anti-Clarify Discipline under Closeout Gate

- **User Correction Incident**: Khi điểm Reviewer đạt 78–84/100 (cận kề ngưỡng 85/100), Agent tuyệt đối **KHÔNG ĐƯỢC** xuất báo cáo "BÁO CÁO HIỆN TRẠNG / BLOCKED" hoành tráng để thanh minh, và **CẤM** gọi `clarify` để hỏi user "có nên tiếp tục hay dừng chốt phiên".
- **Hành vi đúng**:
  1. Trích xuất trực tiếp các finding kỹ thuật còn thiếu từ Reviewer scorecard.
  2. Không bao giờ phát ngôn "code an toàn/không có rủi ro" khi chưa có `APPROVED >= 85`.
  3. Bám đuổi sửa code/test và re-run gate tự động trong thầm lặng cho đến khi đạt điểm.

## 2. Scope Staging Containment & Diff Anti-Bloat

- Khi repo có staged files từ các session/tác vụ trước đó, `closeout_gate.py` với `--files` sẽ văng lỗi `staged files != --files targets`.
- **Cách xử lý**:
  - Unstage các file ngoài scope (`git reset HEAD -- <unrelated_paths>`).
  - Stage đúng và duy nhất các file thuộc scope phiên hiện tại (`--files <file1> <file2>`).
  - Giữ diff tinh gọn (thường < 15KB) để tránh bị cắt xén (diff truncation penalty) từ reviewer.

## 3. Windows Directory Junction (`mklink /J`) Production Safety Contract

Khi chuyển đổi việc copy/đồng bộ plugin/tool sang Windows Directory Junction:
- **Missing Source**: Bắt buộc fail-closed throw ngay (`if (-not (Test-Path -LiteralPath $Src -PathType Container)) { throw ... }`).
- **Destination Validation**:
  - Kiểm tra cả `[bool]($Existing.Attributes -band [System.IO.FileAttributes]::ReparsePoint)` lẫn `$Existing.LinkType -eq 'Junction'`.
  - So sánh `Resolve-Path` của junction target hiện hữu với resolved source path.
  - **Preserve Existing Valid Junction**: Nếu junction đã tồn tại và trỏ đúng nguồn, **GIỮ NGUYÊN** (`$SyncStats.unchanged++`). Tuyệt đối không xóa bằng `rmdir` rồi tạo lại để tránh TOCTOU window và filesystem churn.
- **Error Checking**: Bắt buộc kiểm tra `if ($LASTEXITCODE -ne 0) { throw ... }` sau mỗi lệnh `cmd.exe /c mklink /J` hoặc `rmdir`.
- **Structured Telemetry**:
  - Thu thập thống kê thực thi (`total`, `created`, `unchanged`).
  - Xuất telemetry JSON nén: `Write-Host "Plugin sync telemetry: $($SyncStats | ConvertTo-Json -Compress)" -ForegroundColor Green`.
- **Test Evidence**:
  - Không viết "synthetic telemetry" trong test (tự ghi JSONL giả lập không liên quan implementation).
  - Viết offline contract tests kiểm tra đầy đủ các nhánh throw/validation.
  - Viết runtime test thực tế trên Windows sử dụng `tempfile.TemporaryDirectory` để chứng minh `mklink /J` liên kết 2 chiều và `rmdir` junction không xóa source.
