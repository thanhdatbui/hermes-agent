# Windows Junction Sync & Zero-Truncation Closeout Discipline

## 1. Bài học chống dừng sớm & cấm Clarify khi Closeout < 85
- Khi `closeout_gate.py` trả về điểm < 85 (REJECTED): TUYỆT ĐỐI CẤM dừng lại viết báo cáo thanh minh "code đã an toàn trên máy" hoặc dùng công cụ `clarify` để hỏi User "nên làm gì tiếp".
- Hành vi dừng lại khi chưa đạt 85 bị User coi là trốn việc, bỏ cuộc và gây phẫn nộ nghiêm trọng.
- Coordinator phải chủ động đọc kỹ từng Finding trong Sol Scorecard (`logic_correctness`, `test_evidence`, `telemetry_observability`, `farm_safety_regression`, `code_architecture`), bám đuổi sửa code và bổ sung test cho đến khi đạt `APPROVED (>= 85/100)`.

## 2. Cô lập Scope & Chống Diff Truncation
- **Nguyên nhân diff truncation:** Khi repo có staged files lớn từ các phiên trước hoặc file watchdog hàng nghìn dòng, diff tổng thể vượt ngưỡng 60KB bị cắt ngắn (`[... diff truncated due to size limit ...]`). Sol Auditor sẽ trừ điểm nặng vì không thể audit toàn bộ code.
- **Cách xử lý chuẩn:**
  1. Unstage sạch các file tồn đọng của phiên trước: `git reset HEAD`.
  2. Chỉ stage đúng các file thuộc phạm vi phiên hiện tại: `git add <target_files>`.
  3. Khi chạy Closeout Gate, truyền chính xác danh sách file qua `--files <target_files>` để khớp 100% với staged diff.
  4. Diff nhỏ gọn (< 10-15KB) đảm bảo Sol đọc trọn vẹn 100% dòng code và test, không bị truncation.

## 3. Tiêu chuẩn Production-Grade cho Windows Junction (`mklink /J`)
Khi refactor cơ chế copy/robocopy sang Windows Directory Junction để làm Single Source of Truth:
1. **Fail-Closed khi Source thiếu:** Ném ngoại lệ `throw "Plugin source directory not found: ..."` ngay từ đầu, cấm silent skip.
2. **Xác thực 2 lớp ReparsePoint & LinkType:**
   - Kiểm tra `[bool]($Existing.Attributes -band [System.IO.FileAttributes]::ReparsePoint)`.
   - Kiểm tra `$Existing.LinkType -eq 'Junction'`.
   - Ném lỗi nếu target là thư mục thường hoặc symlink không rõ nguồn gốc.
3. **So sánh Resolved Path tuyệt đối:**
   - `Resolve-Path` cho cả target hiện có và source mong đợi. Nếu trỏ sai nguồn, ném lỗi và cấm tự ý xóa.
4. **Chống Filesystem Churn & TOCTOU:**
   - Nếu junction đã tồn tại và trỏ đúng nguồn: **GIỮ NGUYÊN**, chỉ tăng `$SyncStats.unchanged++`. TUYỆT ĐỐI CẤM `rmdir` rồi `mklink` lại vì tạo khoảng trống TOCTOU và tăng rủi ro lỗi filesystem không cần thiết.
   - Chỉ tạo mới `mklink /J` khi junction chưa tồn tại (`$SyncStats.created++`).
5. **Kiểm tra `$LASTEXITCODE`:** Bắt buộc kiểm tra `$LASTEXITCODE -ne 0` ngay sau mọi lệnh gọi `cmd.exe /d /c mklink` và throw khi thất bại.
6. **Structured Telemetry bắt buộc:**
   - Khởi tạo `$SyncStats = @{ total = 0; created = 0; unchanged = 0 }`.
   - Cuối script in ra JSON nén phục vụ quan sát vận hành:
     `Write-Host "Plugin sync telemetry: $($SyncStats | ConvertTo-Json -Compress)" -ForegroundColor Green`

## 4. Bộ Test Acceptance hoàn chỉnh cho Setup Script
Trong file test tương ứng (ví dụ `test_setup_admin_junction.py`), bắt buộc có đủ:
1. Contract kiểm tra `mklink /J` và không còn `robocopy`.
2. Fail-closed khi source missing (`throw`).
3. Xác thực `ReparsePoint` và `LinkType -eq 'Junction'`.
4. Xác thực giữ nguyên junction hợp lệ (`$SyncStats.unchanged++`).
5. Kiểm tra JSON telemetry parse được với đầy đủ keys `total`, `created`, `unchanged`.
6. Runtime test mô phỏng thực tế trên NTFS Windows (`mklink /J` và `rmdir` đa plugin trong `tempfile.TemporaryDirectory`).
