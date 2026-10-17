# Bẫy Đổi Header Excel Nhưng Quên Sửa Consumer & Cơ Chế Fallback Đảo Lộn Slot Toàn Farm (`sync-safe-workbook.py` & `upload_preflight.py`)

## 1. Dấu Hiệu & Triệu Chứng Lỗi
- **Ca Đăng Video (Upload)**: Toàn bộ máy farm đồng loạt bị skip đăng video với lý do:
  `{"status": "skipped", "reason": "missing_video_folder", "workbook": "TikN.xlsx"}`.
- **Ca Nuôi Feed (Feed Swipe / Preflight)**: Hàng loạt máy bị báo lỗi:
  `profile username still mismatched after switch: expected=X, actual=Y`.
  Kiểm tra trên máy thật thì máy đang giữ đúng nick của Tik đó, nhưng file `taikhoan_run_safe.xlsx` lại ghi nhận nick của slot khác (bị đảo lộn slot 7 và 8, hoặc 1 và 2).
- **Hiện tượng "Sửa xong một lúc sau lại bị đảo lộn lại"**: Người vận hành sửa tay trên `taikhoan_run_safe.xlsx` thì chạy được một lúc, nhưng ngay khi cronjob `taikhoan-run-safe-sync` kích hoạt (chu kỳ 5 phút), nó lại tự động sinh đè file cũ và đảo lộn slot tiếp.

## 2. Gốc Rễ Sự Cố (Root Cause Analysis - 17/10/2026)
Sự cố bắt nguồn từ việc ở session trước, Agent thực hiện "Chuẩn hóa header" trên các file Excel để phân biệt rõ giữa thư mục render đích và video nguồn cào:
- File `Tik1.xlsx` .. `Tik8.xlsx`: đổi cột 4 thành `Folder Video (Render Dich)` và cột 5 thành `Video Goc (Nguon Cao)`.
- File Master `taikhoan_dat_v2_updated .xlsx`: đổi cột 2 thành `Folder Video (Slot 1-640)`.

**Cạm bẫy chí mạng**: Chỉ đổi tên cột trên Excel nhưng **KHÔNG rà soát toàn bộ các consumer scripts** đang đọc các cột này:
1. **Trong `upload_preflight.py` (`read_machine_row_from_tik_workbook`)**:
   - Code cũ so khớp exact string:
     `folder_idx = next((i for i, h in enumerate(headers) if h in ("folder video", "video folder", "tik")), None)`
   - Khi header là `'Folder Video (Render Dich)'`, chuỗi lowercase `'folder video (render dich)'` so sánh `in` trả về `False` $\rightarrow$ `folder_idx = None` $\rightarrow$ `folder_video = ""` $\rightarrow$ toàn bộ farm Kibe bị skip upload.
2. **Trong `sync-safe-workbook.py` (`_header_index`)**:
   - Code cũ so khớp exact string:
     `folder_col = _header_index(source_sheet, ("folder video", "folder", "thu muc"))`
   - Khi header là `'Folder Video (Slot 1-640)'`, `folder_col` trả về `None`.

## 3. Cơ Chế Fallback Nguy Hiểm: Tự Động Xáo Trộn Slot Theo Thứ Tự Dòng
Khi `folder_col is None`, script `sync-safe-workbook.py` mất công thức toán học phân bổ slot:
$$\text{target\_slot} = (\text{Folder} - 1) \pmod 8$$
Thay vì ném exception hoặc dừng lại cảnh báo, script rơi vào nhánh fallback ngầm:
- Nó duyệt từng dòng của máy trong file Master DAT và nhét lần lượt vào Slot 1, Slot 2... Slot 8 theo **thứ tự dòng xuất hiện trên sheet**.
- Trong file Master DAT, qua nhiều đợt reg nick và sửa đổi qua thời gian, thứ tự dòng vật lý của một số máy không theo thứ tự Folder 1 đến 8 (ví dụ M76 dòng Folder 608 nằm ở dòng 7, còn dòng Folder 602 nằm ở dòng 8).
- **Hậu quả**: Slot 8 bị gán nhầm thành nick Slot 2 (`anhhuong5185`), còn nick Slot 8 thật (`duonghoailan1999`) bị đẩy lên Slot 7. Toàn bộ các máy có dòng xáo trộn bị đảo lộn slot trên `taikhoan_run_safe.xlsx`, gây lỗi mismatch diện rộng khi ca nuôi chạy.

## 4. Kỷ Luật & Quy Tắc Bất Biến (Invariant Rules)

### Quy tắc 1: Bộ Lọc Header Mở Rộng Toàn Diện (Expanded Aliases)
Mọi consumer script đọc file Excel Master hoặc Tik*.xlsx BẮT BUỘC dùng danh sách alias bao quát toàn bộ các biến thể cũ và mới:
```python
# Cho Folder Video (Render Đích / Slot 1-640):
("folder video slot 1 640", "folder video (render dich)", "folder video", "folder", "thu muc", "render dich")

# Cho Video Gốc (Nguồn Cào):
("video goc (nguon cao)", "video goc", "video gốc", "nguon cao", "nguồn cào")
```

### Quy tắc 2: CẤM Fallback Bốc Mù Theo Thứ Tự Dòng
Trong các script đồng bộ workbook (`sync-safe-workbook.py`, `hermes_taikhoan_sync_cron.py`):
- TUYỆT ĐỐI CẤM fallback tự động điền tuần tự Slot 1..8 khi không tìm thấy cột Folder.
- BẮT BUỘC fail-closed:
  ```python
  if not folder_col:
      raise RuntimeError(f"source workbook missing required Folder Video column in {source.name}; refusing silent row-order fallback")
  ```

### Quy tắc 3: Quy Trình Đối Soát 3 Tầng Toàn Diện Sau Khi Sửa Code / Sync
Trước khi kết luận hệ thống an toàn, BẮT BUỘC chạy script đối soát chéo 3 tầng:
1. **Tầng 1 (Toán học & Invariant)**: Chạy `excel_preflight_validator.py --excel-dir <path> --check-all` trên cả Kibe và Admin (phải đạt PASS 100%, 0 FAIL, 0 WARN).
2. **Tầng 2 (Đối soát 1:1 Khớp Nick)**: Kiểm tra 1:1 giữa Master DAT $\leftrightarrow$ Tik1..Tik8 $\leftrightarrow$ `taikhoan_run_safe.xlsx` (640/640 slot Kibe và 628/628 slot Admin phải trùng khớp username $100\%$).
3. **Tầng 3 (Đối soát Database)**: Chạy `sync_farm_account_info.py` và kiểm tra bảng `farm_account_info` trong `tiktok_tracker.db` khớp 1:1 với các file Excel.

### Quy tắc 4: Khóa Bằng Unit Test Hồi Quy (Regression Tests)
Mọi thay đổi liên quan đến đọc Header hoặc phân bổ Slot BẮT BUỘC phải đi kèm unit test kiểm tra:
- Khớp cả header cũ (`Folder Video`) và header mới (`Folder Video (Slot 1-640)`, `Folder Video (Render Dich)`).
- Đảm bảo khi các dòng trong test workbook bị đảo lộn thứ tự (dòng slot 8 đứng trước dòng slot 1), output safe workbook vẫn đưa nick vào đúng slot 1 và slot 8 theo công thức Folder.
