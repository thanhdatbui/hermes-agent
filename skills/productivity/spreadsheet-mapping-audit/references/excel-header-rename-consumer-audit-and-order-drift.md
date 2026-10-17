# Kỷ Luật Chuẩn Hoá Header Excel & Chống Lệch Thứ Tự Dòng (Order Drift)

## 1. Bối Cảnh & Nguy Cơ Chí Mạng (Sự Cố 17/10/2026)
- **Hiện tượng**: Farm liên tục báo lỗi đảo lộn dữ liệu, lệch slot tài khoản (`profile username still mismatched after switch` trên 12–13 máy MikroTik) và toàn bộ Farm Kibe bị bỏ qua đăng video (`skipped: missing_video_folder`).
- **Nguyên nhân kép bắt nguồn từ việc đổi Header nhưng bỏ quên Consumer Scripts**:
  1. Trong session chuẩn hóa trước đó, các file Excel được đổi tên cột để phân biệt rõ:
     - `Tik1..Tik8.xlsx`: `Folder Video` ➔ `Folder Video (Render Dich)`
     - `taikhoan_dat_v2_updated .xlsx`: `Folder Video` ➔ `Folder Video (Slot 1-640)`
  2. Nhưng các consumer script Python đang đọc các file này lại dùng bộ so sánh cứng:
     - `upload_preflight.py`: `if h in ("folder video", "video folder", "tik")` ➔ Không khớp chuỗi mới ➔ `folder_idx = None` ➔ Toàn bộ máy farm bị skip đăng video!
     - `sync-safe-workbook.py`: `("folder video", "folder", "thu muc")` ➔ Không khớp chuỗi mới ➔ `folder_col = None`!
  3. **Cạm bẫy Fallback mù quáng (Blind Sequential Row Fallback Trap)**:
     - Khi `folder_col = None`, script không dùng công thức toán `(Folder - 1) % 8` để xếp slot 1..8, mà rơi vào nhánh fallback ngây thơ: *cứ thấy dòng nào xuất hiện trước thì nhét vào Slot 1, Slot 2... Slot 8*.
     - Với các máy có dòng trong Master DAT bị lưu lộn xộn (như M76, M77, M78, M79 có dòng Folder 608 nằm trước Folder 602), slot 7 và slot 8 bị đảo ngược vị trí.
     - Mỗi khi Cronjob `taikhoan_sync_cron` chạy nền, nó lại tự động ghi đè file `taikhoan_run_safe.xlsx` bằng dữ liệu đảo lộn slot, phá hủy mọi nỗ lực sửa tay của người vận hành!

---

## 2. Invariant Bắt Buộc Khi Đổi Tên / Chuẩn Hoá Header Excel

### Rule 1: CẤM Đổi Header Trên Excel Khi Chưa Rà Soát Toàn Bộ Consumer Scripts
Trước khi đổi bất kỳ tiêu đề cột nào trên file Excel (Master DAT, Tik1..Tik8, PROXY, Gmail), BẮT BUỘC phải rà soát tất cả các repo tiêu thụ dữ liệu:
- `D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py`
- `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/upload_preflight.py`
- `D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-tik-workbooks.py`
- `D:/Taadaa/tools/excel_preflight_validator.py`
- `D:/Taadaa/tools/sync_farm_account_info.py`

### Rule 2: Chuẩn Hoá Bộ Nhận Diện Cột (Expanded Alias Matching)
Mọi hàm tìm cột BẮT BUỘC dùng danh sách alias bao quát cả tên cũ và tên mới, chuẩn hóa NFKD bỏ dấu và ký tự đặc biệt:
```python
folder_col = _header_index(
    source_sheet,
    ("folder video slot 1 640", "folder video", "folder", "thu muc", "render dich"),
)
```
Đối với tìm kiếm bằng substring (`any(k in h for k in ...)`), phải đảm bảo không bắt nhầm sang cột khác (ví dụ: phân biệt rõ `render dich` là Folder Video Cột 4 vs `nguon cao` là Video Gốc Cột 5).

### Rule 3: CẤM Fallback Mù Quáng Khi Thiếu Cột Khóa (No Blind Fallback)
Khi một cột quan trọng cấu thành slot (như Folder Video) bị thiếu hoặc `None`:
- **TUYỆT ĐỐI CẤM** tự ý fallback nhét tuần tự dòng vào slot theo thứ tự vật lý của Excel.
- Script phải raise `RuntimeError("source workbook missing required Folder Video column")` để dừng tiến trình, không được phép âm thầm sinh ra file runtime sai lệch rồi ghi đè lên hệ thống.

---

## 3. Quy Trình Đối Soát Toàn Diện 1.280 Slot (Fleet-Wide Audit Checklist)

Khi có nghi ngờ hoặc sau khi chỉnh sửa dữ liệu Excel, BẮT BUỘC chạy kiểm toán đủ 5 tầng:
1. **Tầng 1 (Công thức toán học độc bản)**:
   - Chạy `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/<cluster> --check-all`
   - Xác nhận: Folder Video khớp `(M - 1) * 8 + slot`, Video Gốc khớp `(slot - 1) * 80 + M`.
2. **Tầng 2 (Đối soát Master DAT $\leftrightarrow$ Tik1..Tik8)**:
   - Khớp 1:1 từng slot giữa Master DAT và 8 file Tik con (Kibe đủ 640/640, Admin đủ 628/628).
3. **Tầng 3 (Đối soát Tik1..Tik8 $\leftrightarrow$ `taikhoan_run_safe.xlsx`)**:
   - Khớp 1:1 danh sách username tại mỗi slot (1..8) của 80 máy.
4. **Tầng 4 (Số lượng video đã đăng `posted_count`)**:
   - Đối soát cột `Video Đã Đăng` giữa Tik con và `taikhoan_run_safe.xlsx` để cron sync cập nhật đồng bộ.
5. **Tầng 5 (CSDL SQLite `tiktok_tracker.db`)**:
   - Chạy `python D:/Taadaa/tools/sync_farm_account_info.py` để cập nhật bảng `farm_account_info`, bảo đảm Dashboard `:1905` phản ánh chính xác 1:1 với Excel.
