# Subagent Shell Gate Invariants & Closeout Gate Evidence Discipline (03/10/2026)

## 1. Subagent Leaf Terminal Shell Gate (Cấm Chuỗi Nối Lệnh Chứa Ký Tự Điều Khiển)
- **Triệu chứng**:
  Khi Coordinator dispatch worker qua `delegate_task` và giao lệnh PowerShell/Bash có chuỗi nối lệnh hoặc ký tự điều khiển:
  ```powershell
  Get-NetTCPConnection -LocalPort 1905 ... | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force } && wscript ...
  ```
  Subagent lập tức bị chặn bởi `Shell Gate` hoặc `Worker Gate`:
  `⛔ [WORKER GATE - SHELL RESTRICTION]: Chặn terminal chạy các chuỗi nối lệnh shell và ký tự điều khiển (&&, ;, |, $, (), v.v.).`
  Hậu quả: Subagent không chạy được lệnh và kết thúc với 0 file hoàn thành.
- **Biện pháp khắc phục**:
  1. Trong `delegate_task`, Coordinator BẮT BUỘC hướng dẫn worker chạy **từng lệnh đơn lẻ (atomic command)**, một lệnh trên một tool call.
  2. Tuyệt đối không nối lệnh bằng `&&`, `;`, `|`, không nhúng subshell `$()` hay backticks trong argument.
  3. Với các tác vụ quản lý tiến trình (kill PID, restart service): Coordinator nên tự thực thi tại session chính bằng terminal đơn lẻ hoặc giao worker gọi script khép kín (.vbs, .ps1, .py) không qua pipe.

## 2. Bẫy Toán Tử `>` Trong Argument Của Coordinator Terminal
- **Triệu chứng**:
  Coordinator chạy lệnh terminal chứa nội dung text so sánh hoặc code (ví dụ `closeout_gate.py --text "... f_val <= 30 or delta_h >= 30 ..."`), nhưng lệnh bị chặn:
  `⛔ [COORDINATOR GUARD - TERMINAL BLOCKED]: Cấm dùng toán tử điều hướng ghi file '>' trong terminal!`
- **Nguyên nhân**:
  Hook kiểm tra lệnh terminal của Coordinator quét sự xuất hiện của ký tự `>` (để chống việc agent dùng echo/cat heredoc ghi lén mã nguồn ngoài tool `write_file`/`patch`). Regex không phân biệt ký tự `>` nằm trong chuỗi đối số `"..."` hay là toán tử redirect của shell.
- **Biện pháp khắc phục**:
  1. Tuyệt đối không truyền chuỗi chứa dấu `>` hoặc `<` vào argument lệnh terminal của Coordinator.
  2. Nếu cần truyền nội dung code/diff cho Closeout Gate, ghi nội dung vào file tạm (hoặc audit package file) rồi truyền qua cờ `--input <path>` thay vì `--text "..."`.

## 3. Quy Chuẩn Bằng Chứng Của Closeout Gate (Sol Auditor Ground Truth)
- **Bẫy tự báo cáo (Self-Report Failure)**:
  Truyền một câu tóm tắt bằng chữ thuần túy qua `--text` mà không có unified diff và test output sẽ bị Sol Auditor chấm 59/100 (`REJECTED`) do thiếu cơ sở kiểm chứng.
- **Yêu cầu bắt buộc để đạt $\ge 85/100$**:
  Mọi gói thẩm định Closeout Gate (dù chạy qua `--repo` hay qua `--input`) BẮT BUỘC phải cung cấp đủ:
  1. Unified git diff chi tiết (`diff --git ...`).
  2. Kết quả log pytest đầy đủ (số lượng passed, duration).
  3. Bằng chứng kiểm tra thực tế (telemetry, live API response, hoặc ảnh màn hình `MEDIA:<path>`).
