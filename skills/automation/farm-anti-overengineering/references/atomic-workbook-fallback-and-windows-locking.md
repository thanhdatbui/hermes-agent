# Atomic Workbook Fallback & Windows File Locking Pitfalls

> Tài liệu tổng hợp từ đợt review code kiến trúc độc lập (Claude CLI) ngày 05/09/2026 cho sự cố `[WORKBOOK_UPDATE_FAILED]` trên `Tiktok-video`.

## 1. Bối cảnh & Vấn đề
Trong các consumer repo (`Tiktok-video`, `tiktok-follow`, `Tiktok_Reg`):
- Tiến trình ghi nhận STT video hoặc trạng thái tài khoản vào workbook chung (`tik3.xlsx`, `taikhoan_run_safe.xlsx`) chạy song song 16 – 20 máy cùng lúc.
- Chuẩn farm là sử dụng `from automation_core.workbook import atomic_workbook_update`.
- Tuy nhiên, trong một số sub-environment / venv (như `venv-core024`), việc lệch `sys.path` hoặc thiếu package có thể gây crash:
  ```text
  ModuleNotFoundError: No module named 'automation_core.workbook'
  ```
- Khi triển khai fallback 2 lớp trong consumer repo, nếu không cẩn thận sẽ tạo ra các lỗ hổng nghiêm trọng phá hỏng tính toàn vẹn của workbook.

---

## 2. 5 Cạm Bẫy (Pitfalls) Khi Viết Fallback Atomic Workbook

### Pitfall 1: Bỏ qua File Locking (`lock_timeout`)
- **Triệu chứng:** Fallback nhận tham số `lock_timeout=30` nhưng không thực hiện cơ chế khóa file, hoặc hết timeout (`acquired=False`) vẫn tiếp tục ghi mà không raise.
- **Hậu quả:** Khi 16-20 runner cùng upload xong và cùng ghi vào `tik3.xlsx`, các tiến trình ghi đè lẫn nhau (race condition) $\rightarrow$ workbook bị mất dòng hoặc corrupt file ZIP/Excel.
- **Giải pháp:** Fallback bắt buộc phải có khóa độc quyền (Atomic Exclusive Lock) với deadline và enforce `raise TimeoutError`:
  ```python
  lock_file = p.with_suffix(p.suffix + ".lock")
  deadline = time.monotonic() + (lock_timeout or 30)
  acquired = False
  fd = None
  while time.monotonic() < deadline:
      # Phá stale lock nếu process cũ crash (> 2x timeout)
      if lock_file.exists():
          try:
              if time.time() - lock_file.stat().st_mtime > (lock_timeout or 30) * 2:
                  lock_file.unlink()
          except OSError:
              pass
      try:
          fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
          acquired = True
          break
      except FileExistsError:
          time.sleep(0.2)
      except Exception:
          break
  if not acquired:
      raise TimeoutError(f"Could not acquire workbook lock on {p} within {lock_timeout}s")
  ```

### Pitfall 1b: Stale / Orphaned Lock File Làm Treo Toàn Bộ Runner Sau
- **Triệu chứng:** Process trước bị force-kill hoặc mất điện trước `finally`, file `.lock` bị kẹt trên đĩa.
- **Giải pháp:** Kiểm tra TTL `time.time() - lock_file.stat().st_mtime > (lock_timeout or 30) * 2` trước khi thử acquire để chủ động dọn lock mồ côi.

### Pitfall 2: `Path.replace()` Văng `PermissionError` trên Windows
- **Triệu chứng:** `temp_path.replace(p)` ném lỗi `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`.
- **Nguyên nhân:** Trên Windows, `os.replace()` **không hoàn toàn atomic** nếu file đích đang được mở đọc bởi Excel hoặc tiến trình khác.
- **Giải pháp:** Bọc retry loop với backoff:
  ```python
  replaced = False
  for attempt in range(5):
      try:
          temp_path.replace(p)
          replaced = True
          break
      except PermissionError:
          time.sleep(0.5)
  if not replaced:
      temp_path.replace(p)
  ```

### Pitfall 3: Lỗi Hợp Đồng Callback (`update_cb`) Falsy
- **Triệu chứng:** Viết `if update_cb(temp_path): temp_path.replace(p)`.
- **Hậu quả:** Rất nhiều hàm sửa Excel thực hiện in-place modification và không `return True` (trả về `None`). Câu lệnh `if` coi `None` là False $\rightarrow$ bỏ qua bước replace $\rightarrow$ dữ liệu bị mất âm thầm (silent data loss).
- **Giải pháp:** Kiểm tra hợp đồng rõ ràng:
  ```python
  cb_res = update_cb(temp_path)
  if cb_res is True or cb_res is None:
      # Thực hiện replace
  ```

### Pitfall 4: Hardcode Đường Dẫn `D:/Taadaa/automation-core/src`
- **Triệu chứng:** Hardcode cứng ký tự ổ đĩa `D:`. Khi chạy test ở CI/CD, máy khác, hoặc thư mục làm việc phụ sẽ fail âm thầm.
- **Giải pháp:** Dynamic resolve qua 3 tầng:
  ```python
  env_ac = os.environ.get("AUTOMATION_CORE_SRC")
  candidate_paths = [
      Path(env_ac) if env_ac else None,
      Path(__file__).resolve().parents[3] / "automation-core" / "src",
      Path("D:/Taadaa/automation-core/src"),
  ]
  for cand in candidate_paths:
      if cand and cand.is_dir() and str(cand) not in sys.path:
          sys.path.insert(0, str(cand))
  ```

### Pitfall 5: SyntaxError F-string Lồng Dấu Ngoặc Kép (Python < 3.12)
- **Triệu chứng:** `f".bak-{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}"` gây SyntaxError trên Python 3.11.
- **Giải pháp:** Tách việc định dạng timestamp ra biến riêng trước khi đưa vào f-string:
  ```python
  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  backup_file = p.with_suffix(p.suffix + f".bak-{ts}")
  ```
