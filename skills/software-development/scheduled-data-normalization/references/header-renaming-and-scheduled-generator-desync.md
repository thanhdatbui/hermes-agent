# Header Renaming & Scheduled Generator Desync Pitfall (Bẫy Đổi Header Excel Gây Lệch Generator Định Kỳ)

## 1. Bản Chất Vấn Đề
Khi thực hiện chuẩn hóa dữ liệu hoặc cấu trúc file Excel (ví dụ đổi tên cột để phân biệt mục đích sử dụng):
- Header trong file nguồn (`taikhoan_dat_v2_updated .xlsx`) được đổi: `Folder Video` $\rightarrow$ `Folder Video (Slot 1-640)`.
- Header trong các file phân bổ (`Tik1..Tik8.xlsx`) được đổi: `Folder Video` $\rightarrow$ `Folder Video (Render Dich)`.

Nếu các script generator tự động (`sync-safe-workbook.py`) và consumer runner (`upload_preflight.py`) sử dụng phép so sánh cứng (exact string / exact tuple matching) để tìm chỉ mục cột:
- Script không nhận diện được tên cột mới $\rightarrow$ trả về `col_idx = None`.
- **Hệ quả đối với Consumer**: Thiếu trường thông tin bắt buộc $\rightarrow$ toàn bộ tác vụ bị skip (ví dụ `upload_preflight` skip toàn farm vì `missing_video_folder`).
- **Hệ quả đối với Scheduled Generator (Nguy hiểm nhất)**:
  * Khi `folder_col = None`, generator mất công thức tính slot dựa theo ID thư mục: $\text{Slot} = (\text{Folder} - 1) \pmod 8 + 1$.
  * Generator rơi vào cơ chế fallback tuần tự: bốc các dòng từ trên xuống dưới trong sheet nguồn gán lần lượt vào Slot 1..8.
  * Với các máy có dòng lưu không theo thứ tự slot vật lý trong sheet nguồn (như M76, M77, M78...), thứ tự 8 slot bị xáo trộn hoàn toàn (Slot 8 thành Slot 7, Slot 2 thành Slot 8).
  * Định kỳ mỗi 5 phút, cronjob (như `taikhoan-run-safe-sync`) kích hoạt và **âm thầm ghi đè file runtime (`taikhoan_run_safe.xlsx`) bằng dữ liệu đảo lộn**, khiến việc sửa tay trên file runtime lập tức bị xóa sạch sau vài phút.

## 2. Quy Tắc Bắt Buộc (Invariant Rules)

### Invariant 1: Multi-Alias Substring Matching
Mọi generator hoặc consumer đọc header từ file Excel không bao giờ được dùng exact match hẹp. BẮT BUỘC dùng danh sách alias bao quát toàn bộ các phiên bản schema cũ và mới:
```python
folder_col = _header_index(
    source_sheet,
    ("folder video slot 1 640", "folder video", "folder", "thu muc", "render dich"),
)
```

### Invariant 2: Fail-Closed On Missing Mapping Columns
Khi generator phụ thuộc vào một cột để phân bổ slot/phân loại dữ liệu (như cột Folder để chia slot 1..8), nếu không tìm thấy cột đó (`folder_col is None`):
- **CẤM TUYỆT ĐỐI** fallback sang bốc dòng tuần tự hoặc suy diễn ngầm làm xáo trộn dữ liệu.
- Phải lập tức ném ngoại lệ rõ ràng (`RuntimeError("Missing required folder column for slot calculation")`) để ngăn chặn việc ghi đè file runtime bằng dữ liệu rác.

### Invariant 3: Đồng Bộ Test Suite Trước Khi Đổi Schema
Trước khi đổi bất kỳ header nào trên file Excel vận hành, BẮT BUỘC:
1. Rà soát toàn bộ các consumer scripts trong repo đọc cột đó.
2. Cập nhật unit test để kiểm chứng việc parse thành công cả schema cũ lẫn schema mới.
3. Chạy test suite xác nhận 100% pass trước khi triển khai file Excel mới vào môi trường production.
