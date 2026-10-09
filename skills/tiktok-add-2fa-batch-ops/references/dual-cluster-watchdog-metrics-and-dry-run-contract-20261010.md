# Quy Chuẩn Điều Phối Dual-Cluster Watchdog & Khế Ước Dry-Run (2026-10-10)

Đúc kết từ phiên xử lý sự cố `night-tiktok-2fa-watchdog` (job_id: `2029d4224662`) và quy trình khắc phục Closeout Gate.

---

## 1. Cạm bẫy UnboundLocalError trong tổng hợp số liệu đa cụm
- **Hiện tượng**: Runner hoàn thành thành công cả 2 cụm Kibe (Máy 1-80) và Admin (Máy 201-280 qua SSH), nhưng watchdog script kết thúc với exit code 1 do:
  ```
  UnboundLocalError: cannot access local variable 'suc' where it is not associated with a value
  ```
- **Nguyên nhân**:
  - Khi phân tách output đa cụm (`if "=== CLUSTER ADMIN" in out:`), kịch bản tính riêng `k_res` và `a_res` để in báo cáo nhưng quên gán biến gộp `suc` và `fail` (chỉ gán ở nhánh `else:` đơn cụm).
  - Bước lưu trạng thái `save_state(today_str, {"success_count": suc, "failed_count": fail})` cố truy cập `suc` dẫn đến văng traceback ngay tại dòng cuối cùng của `main()`.
- **Quy tắc bắt buộc**:
  - Khi script watchdog hỗ trợ đa cụm, mọi biến lưu trữ state hoặc alert metadata (`suc`, `fail`, `skip`) BẮT BUỘC phải được khởi tạo hoặc gán tổng hợp tường minh ở tất cả các nhánh rẽ:
    ```python
    if "=== CLUSTER ADMIN" in out:
        k_res = parse_summary_counts(kibe_text)
        a_res = parse_summary_counts(admin_text)
        suc = k_res["success"] + a_res["success"]
        fail = k_res["failed"] + a_res["failed"]
    else:
        res = parse_summary_counts(out)
        suc, fail = res["success"], res["failed"]
    ```

---

## 2. Khế ước Dry-Run phản ánh đúng môi trường đa cụm
- **Vấn đề**: Hàm `run_night_batch(dry_run=True)` cũ trả về chuỗi phẳng:
  `"TOTAL=40 SUCCESS=40 FAILED=0 (dry-run Kibe + Admin)"`
  Chuỗi này không chứa header `=== CLUSTER ADMIN`, khiến lệnh kiểm tra `--dry-run` nhảy vào nhánh `else:` và không bao giờ phủ được nhánh code đa cụm thực tế.
- **Quy chuẩn**:
  - Output mock của `--dry-run` BẮT BUỘC phải mô phỏng đầy đủ cấu trúc phân tách cụm:
    ```python
    if dry_run:
        return 0, (
            "=== CLUSTER KIBE (MÁY 1-80) ===\nTOTAL=40 SUCCESS=40 FAILED=0\n"
            "=== CLUSTER ADMIN (MÁY 201-280) ===\nTOTAL=40 SUCCESS=40 FAILED=0"
        )
    ```
  - Unit test TDD phải mock output chứa cả 2 cụm để bảo vệ invariant: `main()` không bao giờ văng ngoại lệ dù kết quả rẽ nhánh nào.

---

## 3. Thực thi an toàn qua SSH OpenSSH Windows (Admin Farm)
- Mọi lời gọi remote sang cụm Admin qua SSH Windows PowerShell bắt buộc tuân thủ giao thức Base64 `EncodedCommand`:
  ```python
  import base64
  ps_script = (
      "$env:PYTHONIOENCODING = 'utf-8'\n"
      "$env:PYTHONUTF8 = '1'\n"
      "Set-Location 'D:/Taadaa/tiktok-add-bao-mat-f2a'\n"
      "$wb = 'D:\\OneDrive\\TaadaaData\\admin\\taikhoan_dat_v2_updated .xlsx'\n"
      "& 'D:\\Taadaa\\python-envs\\automation\\Scripts\\python.exe' python_runner/run_batch_live_2fa.py "
      "--workbook-path $wb --workbook-sheet 'Tài Khoản' --max-workers 40 --live\n"
  )
  b64_ps = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
  cmd_admin = ["ssh", "-o", "ConnectTimeout=10", "admin-farm", f"powershell -NoProfile -EncodedCommand {b64_ps}"]
  ```
- Tuyệt đối không dùng chuỗi lệnh thô `-Command "..."` để tránh bị shell quote stripping làm vỡ đường dẫn có khoảng trắng và lỗi Unicode tên sheet tiếng Việt.

---

## 4. Chuẩn hóa Hằng Số Mã Thoát (Return Code Contract) & Observability
- **Bẫy Reviewer Closeout Gate**: Reviewer sẽ trừ điểm nghiêm trọng nếu watchdog so khớp mã thoát dạng số ma thuật (magic numbers như `code in (0, 4)`) mà không có giải trình hoặc định nghĩa rõ ràng.
- **Chuẩn hóa Hằng số**:
  ```python
  EXIT_SUCCESS = 0
  EXIT_SAFE_SKIP = 4  # Tất cả target được bỏ qua an toàn (đã có 2FA hoặc bận lock hợp lệ)
  ACCEPTABLE_RETURN_CODES = (EXIT_SUCCESS, EXIT_SAFE_SKIP)
  ```
- **Telemetry & State Persistence**:
  - Thay thế in trần stderr bằng module `logging` chuẩn.
  - Khi lưu state JSON tại `save_state`, bắt buộc bổ sung trường `failure_reason` khi mã lỗi khác acceptable, và phân lập chi tiết trạng thái từng cụm (`farms: {kibe: ..., admin: ...}`).

---

## 5. Kinh Nghiệm Vận Hành Sol Repair Trong Closeout Gate
- Khi Closeout Gate bị `REJECTED` (Strike 1 hoặc 2), chạy `sol_repair.py` bắt buộc chỉ định `--model review` (hoặc `chatgpt-web/gpt-5.6-sol-high`) để tránh timeout streaming của model mặc định `gpt-web-sol`.
- Nếu đề xuất của Sol Repair vượt quá ngân sách O(1) (`numstat > 30 dòng` hoặc refactor lan man), bắt buộc kích hoạt nhánh **Fallback Worker** (`delegate_task`) theo đúng `HERMES_SUBAGENT_RULES.md` với contract thu hẹp, tuyệt đối không tự áp dụng patch quá lớn trong session chính.
