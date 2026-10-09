# Excel Sync Performance & Machine Serial Invariant Rules (2026-09-24)

## 1. Openpyxl `read_only=True` Streaming vs Random Access Bottleneck

### Hiện tượng
Script `generate_cron_source_config.py` hoặc các tool đọc workbook an toàn bị treo 60s - 90s, gây timeout cron `hermes_taikhoan_sync_cron.py` (exit code 124).

### Nguyên nhân
Khi mở workbook ở chế độ stream `openpyxl.load_workbook(path, read_only=True)`:
- Thư viện `openpyxl` không nạp toàn bộ DOM XML vào RAM.
- Nếu truy cập ngẫu nhiên qua `ws.cell(row, col)` trong vòng lặp `for r in range(...)`: Mỗi lần gọi `ws.cell()`, openpyxl phải rewind và parse lại luồng XML từ đầu file tới hàng cần đọc!
- Với file 640 dòng x 4 cột = 2.560 lần tua lại XML -> Thời gian chạy tăng từ 0.3s lên 60-90s.

### Quy tắc chuẩn hóa (BẮT BUỘC)
Trong chế độ `read_only=True`, TUYỆT ĐỐI KHÔNG dùng `ws.cell(row, col)`. Bắt buộc duyệt tuần tự 1 lần duy nhất bằng `ws.iter_rows(values_only=True)`:
```python
# CHUẨN: O(N) streaming 1 lượt duy nhất (< 0.5s)
for row in ws.iter_rows(min_row=2, values_only=True):
    if not row or row[0] is None:
        continue
    m_val = row[0]
    dev_val = str(row[1] or "").strip() if len(row) > 1 else ""
    id_val = row[2] if len(row) > 2 else None
    vids_val = row[3] if len(row) > 3 else None
```

---

## 2. Invariant: Đồng nhất Hardware Serial trên 8 Slot của Mỗi Máy

### Hiện tượng
Cron sync báo lỗi:
`CRON_SOURCE_SYNC_EXC: MAPPING_CONFLICT`
khi gọi `generate_config_from_safe_workbook()`.

### Nguyên nhân
- Trong `python_runner.hermes_cron.source_config.SourceConfig._validate_machine_serials`:
  Mỗi máy (`machine_id`) chỉ được phép map với ĐÚNG 1 serial phần cứng duy nhất:
  ```python
  if prior_serial is not None and prior_serial != account.serial:
      raise ValueError(ReasonCode.MAPPING_CONFLICT.value)
  ```
- Khi sửa/swap tài khoản trong `taikhoan_dat_v2_updated .xlsx` (ví dụ: đổi nick ở Row 76 / Folder 75 của Máy 10), nếu chỉ copy thông tin tài khoản mà quên đồng bộ cột Serial (Cột 10 / J) với 7 slot còn lại của Máy 10, máy sẽ mang 2 serial khác nhau (`988627464e374e3234` vs `ce051605a41be20803`).
- Khi sinh `SourceConfig`, validator phát hiện conflict và hủy toàn bộ quá trình sync để bảo vệ farm.

### Quy tắc sửa
1. Đối soát toàn bộ các dòng của máy bị lỗi:
   ```python
   # Kiểm tra xem máy có bị lệch serial giữa các slot không
   serials_per_machine = {}
   for r in ws.iter_rows(min_row=2, values_only=True):
       m, s = r[0], r[9]
       serials_per_machine.setdefault(m, set()).add(s)
   # Tìm máy có len(serials) > 1
   ```
2. Đồng bộ cột 10 (Serial) trên toàn bộ 8 dòng của máy đó về đúng 1 serial phần cứng duy nhất đang cắm trên farm.

---

## 3. Quy trình gỡ lỗi Duplicate Accounts khi Preflight Validator chặn

### Hiện tượng
`excel_preflight_validator.py` báo:
`[FAIL] tik3.xlsx: dòng X, cột 3, máy Y - Trùng lặp tài khoản 'ABC': xuất hiện tại tik3.xlsx (slot 3, máy Y) và Tik2.xlsx (dòng X, slot 2, máy Y)`

### Quy trình đối soát & Fix an toàn
1. **Truy vấn DB `tiktok_tracker.db` và lịch sử session**:
   - Kiểm tra email ở slot bị trùng (ví dụ `thachnha1103199810@gmail.com`).
   - Tìm kiếm snapshot trên TikTok Web / DB để lấy đúng username chính chủ đã reg của email đó (ví dụ: `tranvantrang9810`).
   - Nếu email đó chưa từng reg TikTok (trả về statusCode 10221 / not found): slot đó phải là `None` (trống), không được copy paste nick của slot khác vào.
2. **Cập nhật đồng thời cả 2 nguồn**:
   - Sửa ô ID trong `taikhoan_dat_v2_updated .xlsx` (Sheet 'Tài Khoản').
   - Sửa ô ID tương ứng trong `TikN.xlsx` (Sheet 'TaiKhoan').
3. **Chạy lại Preflight Validator**:
   ```bash
   python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/kibe --exit-on-error
   ```
   Bắt buộc kết quả ra `[RESULT] PASS 100%` mới cho phép sync tiếp sang runtime.
