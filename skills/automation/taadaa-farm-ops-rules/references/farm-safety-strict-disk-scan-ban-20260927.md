# Farm Safety: Cấm Tuyệt Đối Quét Ổ Đĩa Diện Rộng (Disk Scan Invariant)

## Quy tắc bất di bất dịch
**CẤM TUYỆT ĐỐI** Coordinator và Worker tự ý chạy:
- `grep -rn`
- `find`
- `os.walk`
- `glob(..., recursive=True)`
- `search_files` (quét toàn bộ ổ D:/Taadaa)
hoặc bất kỳ lệnh tìm kiếm đệ quy diện rộng nào trên toàn bộ `D:/Taadaa` (kể cả `.ai-runs/`, `runtime/`), TRỪ KHI có lệnh đích danh từ User.

## Lý do kỹ thuật
1. Ổ `D:/Taadaa` chứa hàng triệu file: các thư mục virtualenv (`python-envs/`), thư mục test tạm với phân quyền hạn chế (`.pytest-basetemp-*`), các đợt lưu runtime XML/screenshots cũ (`.ai-runs/`, `runtime/`).
2. Quét đệ quy diện rộng dẫn tới:
   - Gặp lỗi *Permission denied* gây treo terminal.
   - Timeout 600s của shell/terminal, làm sập quy trình điều phối.
   - Gây nghẽn IO ổ đĩa, làm gián đoạn các batch nuôi acc / upload video đang chạy song song trên farm.

## Cách tiếp cận đúng (O(1) Access)
1. Chỉ inspect đúng file/đường dẫn cụ thể đã biết trước (dựa trên tên file, serial máy, timestamp log).
2. Khi tìm artifact hoặc log của máy `N`, dùng các công cụ chuyên dụng O(1) có sẵn như:
   - `python D:/Taadaa/tools/inspect_machine.py <N>`
   - Đọc trực tiếp file log theo ngày: `D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/.../machines/machine_<N>/...`
3. Tuyệt đối không dùng lệnh tìm kiếm mò mẫm khi chưa khoanh vùng chính xác đường dẫn.
