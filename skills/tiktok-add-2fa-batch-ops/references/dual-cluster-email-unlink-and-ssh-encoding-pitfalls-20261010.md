# Dual-Cluster 2FA Pitfalls: TikTok v46+ Email Unlink Block & SSH CLI Encoding (10/10/2026)

## 1. TikTok v46+ Email Unlink Block & `EMAIL_DISABLE_NOT_STABLE`

### Hiện tượng
- Chạy batch 2FA trên Farm Admin (hoặc máy chưa đồng bộ patch) báo: `Hoàn tất 0 | Lỗi 20`.
- Thư mục journals tích lũy nhiều file `.dpapi` (ví dụ 21 file) nhưng workbook Excel hoàn toàn không được ghi nhận 2FA mới.
- Các worker đều vượt qua bước submit OTP thành công, nhưng fail ngay sau đó và rollback/exit `failed`.

### Nguyên nhân gốc rễ
- Trên TikTok app v46+ (cụm Admin v46.6.3, Kibe v47.0.3), hệ thống TikTok chặn hoàn toàn thao tác gỡ/xóa Email đối với các tài khoản không liên kết Số điện thoại (SĐT).
- Hàm `_disable_email_and_confirm_stable` trong `live_phase_b_adapter.py` cố gắng bấm "Email" -> "Xóa" -> "Xác nhận", nhưng popup xóa bị chặn hoặc giao diện không cho phép gỡ email, dẫn đến timeout `EMAIL_DISABLE_NOT_STABLE`.
- Trên Kibe lúc đầu vá tạm thời:
  ```python
  # BỎ BƯỚC GỠ EMAIL: TikTok v46+ chặn xóa email với tài khoản không có SĐT.
  return
  ```
- **Bản vá chuẩn hóa Closeout Gate (APPROVED 86đ):**
  Không được dùng `return` cụt ngủn (bị Sol Auditor reject vì phá vỡ luồng chuẩn khi gặp account cho phép gỡ email). Thay vào đó, giữ nguyên quy trình thử gỡ email nhưng bọc bắt `LiveAdapterError`:
  ```python
  if _method_checked(current, "Email") is True:
      try:
          self._tap_value("Email", prefix=True)
          self._tap_value("Xóa")
          self._tap_value("Xác nhận")
          self._wait_stable(lambda xml: _method_checked(xml, "Email") is False, "EMAIL_DISABLE_NOT_STABLE")
      except LiveAdapterError as exc:
          # TikTok v46+ chặn gỡ email khi nick chưa có SĐT: ghi nhận telemetry và bảo toàn 2FA
          if self.diagnostic_root is not None:
              try:
                  self.diagnostic_root.mkdir(parents=True, exist_ok=True)
                  with (self.diagnostic_root / "phase_b_events.jsonl").open("a", encoding="utf-8") as fp:
                      fp.write(json.dumps({"event": "EMAIL_REMOVE_SKIPPED", "reason": str(exc)}, ensure_ascii=False) + "\n")
              except OSError:
                  pass
  ```
  Nhờ đó: Nếu TikTok cho phép gỡ -> gỡ sạch. Nếu TikTok chặn -> ghi nhận telemetry sự kiện và tiếp tục hoàn tất 2FA, không bị crash dở dang.
- Tuy nhiên, patch này chưa được commit và deploy sang repo `D:/Taadaa/tiktok-add-bao-mat-f2a` trên máy Admin (`admin-farm`). Đồng thời, file trên Admin còn bị lỗi bảng mã tiếng Việt (Mojibake: `Xóa` biến thành `XA3a`, `Xác nhận` biến thành `XA-c nh-n`), khiến adapter văng lỗi 100%.

### Quy tắc bất biến
- BẮT BUỘC giữ Email khi bật 2FA trên TikTok v46+: chỉ bật Authenticator App và lưu mật khẩu, KHÔNG được cố gỡ Email.
- Mọi bản sửa logic adapter trong `tiktok-add-bao-mat-f2a` BẮT BUỘC phải đồng bộ cả 2 cụm Kibe (1-80) và Admin (201-280) trước khi kích hoạt batch runner.

---

## 2. Lỗi Transcode Bảng Mã CLI Qua SSH PowerShell (`--workbook-sheet`) & Cơ Chế `resolve_sheet`

### Hiện tượng
- Gọi remote batch qua SSH PowerShell với EncodedCommand:
  `powershell -NoProfile -EncodedCommand ...`
  khi truyền tham số có dấu tiếng Việt như `--workbook-sheet 'Tài Khoản'`.
- Tham số khi vào Python trên máy đích bị biến dạng thành `--workbook-sheet 'Ti Kho?n'` do PowerShell chuyển đổi tham số sang OEM ANSI code page (CP1252/CP1258).
- Gây lỗi `WorkbookError("SOURCE_SHEET_MISSING")` hoặc `KeyError: 'Worksheet Ti Kho?n does not exist.'`.

### Giải pháp chuẩn hóa (2 Tầng Phòng Vệ)
1. **Tầng Watchdog / Runner**:
   - Trong `run_batch_live_2fa.py`, biến `DEFAULT_SHEET = "Tài Khoản"` đã được hardcode chuẩn UTF-8 bên trong mã nguồn Python.
   - Khi watchdog gọi qua SSH PowerShell, **KHÔNG truyền cờ `--workbook-sheet`** nếu đang dùng sheet mặc định, để Python tự load hằng số nội tại mà không qua lớp CLI parsing của Windows PowerShell.

2. **Tầng Adapter Workbook (`core/workbook.py`) — Resilient Sheet Lookup**:
   - Thêm hàm `resolve_sheet(wb, requested_sheet)` tự động nhận diện mềm dẻo:
     ```python
     def resolve_sheet(wb: openpyxl.Workbook, requested_sheet: str):
         if requested_sheet in wb.sheetnames:
             return wb[requested_sheet]
         import unicodedata, re
         def _strip(s: str) -> str:
             return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").casefold().strip()
         norm_req = _strip(requested_sheet)
         for name in wb.sheetnames:
             if _strip(name) == norm_req:
                 return wb[name]
         norm_letters = re.sub(r"[^a-z]", "", norm_req)
         for name in wb.sheetnames:
             name_letters = re.sub(r"[^a-z]", "", _strip(name))
             # Thắt chặt heuristic: bắt buộc cùng ký tự đầu 't', đuôi 'n', chứa 'kho', và chênh lệch độ dài <= 2
             if name_letters == norm_letters or (
                 name_letters.startswith("t") and norm_letters.startswith("t")
                 and name_letters.endswith("n") and norm_letters.endswith("n")
                 and "kho" in name_letters and "kho" in norm_letters
                 and abs(len(name_letters) - len(norm_letters)) <= 2
             ):
                 return wb[name]
         raise WorkbookError("SOURCE_SHEET_MISSING")
     ```
   - Thay thế toàn bộ các điểm truy cập `wb[target.source_sheet]` trong các hàm nghiệp vụ (`inspect_target`, `password_is_blank`, `read_pass_value`, `read_email_value`, `update`, `verify`) thành `resolve_sheet(wb, target.source_sheet)`.
   - Kết quả: Kể cả khi CLI bị lỗi transcode thành `'Ti Kho?n'`, hàm vẫn nhận diện chính xác sheet `'Tài Khoản'`.

---

## 3. Lỗi Đếm Trùng (Double Counting) Số Lượng Skip Trong Watchdog

### Hiện tượng
- Báo cáo watchdog hiển thị số lượng bỏ qua gấp đôi thực tế (ví dụ: `Bỏ qua 120` trong khi cụm Admin chỉ có 80 máy và tối đa 60-70 targets).

### Nguyên nhân
- Script `run_batch_live_2fa.py` in 2 bảng kết quả:
  1. `_print_results(results)`: in toàn bộ danh sách kết quả (bao gồm cả các dòng `skipped`).
  2. `if skipped: _print_results(skipped, title="Skip do device lock hoặc preflight")`: in lại riêng các dòng `skipped`.
- Regex của watchdog:
  `re.findall(r"^\s*(\d+)\s*\|\s*(\d+)\s*\|\s*[^|]+\|\s*(\w+)", output, re.M)`
  quét toàn bộ stdout và khớp cả 2 bảng, khiến mỗi target skip bị cộng 2 lần.

### Giải pháp
- Khi parse bảng output của `run_batch_live_2fa.py`, chỉ parse phần kết quả đầu tiên trước tiêu đề `Skip do device lock`:
  ```python
  table_section = output
  if "Skip do device lock" in output:
      table_section = output.split("Skip do device lock")[0]
  table_rows = re.findall(r"^\s*(\d+)\s*\|\s*(\d+)\s*\|\s*[^|]+\|\s*(\w+)", table_section, re.M)
  ```

---

## 4. Quy Trình Đồng Bộ & Nghiệm Thu Mã Nguồn Sang Farm Admin

Khi sửa code trong `tiktok-add-bao-mat-f2a` trên máy Kibe, BẮT BUỘC thực hiện nghiệm thu theo 3 bước:
1. **Chạy Unit Test Trên Kibe**:
   ```bash
   python -m unittest discover -s "D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner" -p "test_workbook.py"
   python -m unittest discover -s "D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner" -p "test_run_batch_live_2fa.py"
   python -m unittest discover -s "D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner" -p "test_live_phase_b_adapter.py"
   ```
2. **Đồng Bộ Sang Admin-PC Qua SCP**:
   ```bash
   scp -o ConnectTimeout=10 \
     "D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/core/workbook.py" \
     "D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/core/live_phase_b_adapter.py" \
     "D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/run_batch_live_2fa.py" \
     admin-farm:"D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/"
   ```
3. **Chạy Unit Test & Dry-Run Trực Tiếp Trên Admin-PC**:
   ```bash
   ssh admin-farm "powershell -Command \"& 'D:\Taadaa\python-envs\automation\Scripts\python.exe' -m unittest discover -s 'D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner' -p 'test_workbook.py'\""
   ssh admin-farm "powershell -Command \"& 'D:\Taadaa\python-envs\automation\Scripts\python.exe' D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/run_batch_live_2fa.py --workbook-path 'D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx' --limit 5\""
   ```
