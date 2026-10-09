# Triage "Nick chưa up video / nghi sót video": Quy trình điều tra O(1) & Slot Phân bổ

## 1. Bản chất & Nguyên nhân gốc
Khi người dùng thắc mắc: "Sao nãy bảo up hết all nick rồi giờ lòi ra nick này chưa up?", có 2 nguyên nhân phổ biến nhất:
1. **Hiểu lầm về phạm vi (Scope Misunderstanding):** Đợt upload trước chỉ chạy cho một số Row/Slot nhất định (ví dụ Row 1 - Row 4 đã chạy đủ $\ge 1$ video/nick), trong khi nick được hỏi nằm ở Row sau (Row 5 - Row 8) chưa từng được kích hoạt batch upload.
2. **Nhầm lẫn số máy trên UI Remote Management:** Phần mềm quản lý máy ảo/box (như Xiaowei / VIP Emulator) hiển thị nhiều máy cùng lúc. Cửa sổ con đang active (zoom to) có thể là Máy X (ví dụ M73), trong khi menu context hoặc máy đang chọn ở nền lại là Máy Y (ví dụ M43).

## 2. Quy trình điều tra O(1) chuẩn (Coordinator)
- **Bước 1: Trích xuất username từ ảnh:**
  Đọc chính xác username trên màn hình Profile (ví dụ `@leminhloc0523`, lưu ý OCR có thể đọc nhầm chữ 'l' thành 'i' như `ieminhloc`).
- **Bước 2: Tra cứu nhanh trong `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx`:**
  - Không quét đĩa rộng, chỉ mở trực tiếp file Excel nguồn.
  - Xác định STT máy thật (`Máy`), Serial (`Device ID`) và Row/Slot (1..8) của nick.
  - Công thức tính Slot: `Slot = ((STT - 1) % 8) + 1` hoặc đối chiếu trực tiếp với danh sách 8 account của máy.
- **Bước 3: Kiểm tra trạng thái đăng video theo từng Workbook (`Tik1.xlsx` -> `Tik6.xlsx`):**
  - Mở workbook `TikN.xlsx` tương ứng với Slot của nick đó.
  - Kiểm tra cột `Video Đã Đăng` của toàn bộ Row:
    + Nếu toàn bộ Row $N$ có `Video Đã Đăng = 0`: Xác nhận đợt batch upload trước chưa chạy tới Row này, không phải lỗi sót lẻ tẻ.
    + Nếu Row $N$ đã có nhiều nick $> 0$ mà riêng nick này $= 0$: Kiểm tra folder video (`D:\TIKTOK-videonuoinick\<Folder>`) và file log run để xác định lỗi cụ thể.
- **Bước 4: Báo cáo rõ ràng:**
  - Tách bạch rõ: Nick thuộc Máy nào, Slot mấy, Folder mấy.
  - Thống kê tiến độ theo Row của toàn farm (Row 1..4 đã xong bao nhiêu, Row 5..8 trạng thái thế nào).
  - Tránh tranh cãi cảm tính, đưa số liệu kiểm chứng từ file Excel và folder trên đĩa.
