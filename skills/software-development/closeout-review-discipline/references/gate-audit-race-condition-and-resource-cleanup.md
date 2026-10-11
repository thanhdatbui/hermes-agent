# Gate Audit Log Race Condition & Closeout Best Practices

## 1. Race Condition: Multi-Repo Global `gate_audit.jsonl`
- **Hiện tượng**: `closeout_gate.py` đã chấm `APPROVED (>= 85)` cho repo A, nhưng khi thực hiện `git push` thì lệnh bị Coordinator Guard chặn đứng:
  `⛔ [COORDINATOR GUARD - TERMINAL BLOCKED]: Cấm 'git push' trước khi Closeout Gate trả về APPROVED >= 85!`
- **Nguyên nhân gốc rễ**: File audit log `D:\Taadaa\logs\gate_audit.jsonl` là file ghi log tập trung dùng chung cho toàn bộ các repo trên máy (`tools`, `tiktok-luot nuoi acc`, `Hermes`, `Tiktok-video`,...). Hook `guard_closeout_discipline.py` kiểm tra **dòng cuối cùng (latest entry)** của file. Nếu giữa lúc repo A vừa pass và chuẩn bị push, có một tiến trình/cronjob khác (ví dụ: `Tiktok-video`) chạy gate và ghi log (kể cả `TEST_FAILED` hoặc `REJECTED`), dòng cuối cùng sẽ bị chiếm bởi repo khác.
- **Biện pháp xử lý chuẩn**:
  1. Kiểm tra entry cuối cùng trong `D:\Taadaa\logs\gate_audit.jsonl`.
  2. Nếu entry cuối cùng không thuộc về commit/repo hiện tại, **chạy lại ngay `closeout_gate.py`** với repo hiện tại (`--repo <path> --base HEAD~1 --json-output`).
  3. Khi `closeout_gate.py` ghi đè entry mới nhất là `APPROVED >= 85` cho repo hiện tại, tiến hành `git push` ngay lập tức để tránh bị can thiệp bởi tiến trình khác.

## 2. Xử Lý Resource Leak Với `openpyxl` Trong Watchdog / Reconcile
- **Hiện tượng bị Sol Auditor trừ điểm (Score 82 -> 86)**:
  `openpyxl.load_workbook(wb_path, read_only=True).active` được gọi trong vòng lặp retry mà không lưu biến `wb` để đóng file handle. Trên Windows, điều này có thể gây lock file Excel tạm thời.
- **Pattern chuẩn**:
  ```python
  ws = None
  wb = None
  for _ in range(3):
      try:
          import openpyxl
          wb = openpyxl.load_workbook(wb_path, read_only=True)
          ws = wb.active
          break
      except Exception:
          time.sleep(1)
  if ws is None or wb is None:
      return ["Lỗi đọc workbook"]
  try:
      # Xử lý dữ liệu
      ...
  finally:
      try:
          wb.close()
      except Exception:
          pass
  ```

## 3. Quy Tắc Bổ Sung Test Khi Reviewer Yêu Cầu Evidence
- Reviewer Sol Auditor chấm rất khắt khe về **Test Evidence** (trừ 4-5 điểm nếu thiếu test cho nhánh mới).
- Mọi nhánh error recovery mới (ví dụ: unreadable workbook fallback, lọc residual bullet headers trong split reports) bắt buộc phải có unit test mock tương ứng để đạt điểm `>= 85`.
