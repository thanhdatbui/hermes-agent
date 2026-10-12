# Bẫy Lỗ Hổng Sequence (Sequence Hole Trap) & Kỷ Luật Nghiêm Ngặt Quota Min 45 Clip

## 1. Kỷ Luật Bất Biến: Cấm Hạ Chuẩn Dưới 45 Clip (User Invariant 2026-10-12)
- **Lời răn đe của User**: *"Tao nhớ yêu cầu rõ ràng phải đủ 45. Folder thiếu thì tìm đúng kênh đó cào thêm vào"*.
- **Quy tắc ứng xử**:
  - Khi thấy folder thành phẩm hoặc kho gốc thiếu clip (ví dụ 40/45 clip khiến Watchdog báo `🟡 79/80`), **CẤM TUYỆT ĐỐI viện cớ hoặc gợi ý người dùng hạ chuẩn xuống min 30 hay min 40 clip để làm đẹp báo cáo**.
  - Chuẩn $\ge 45$ clip là trần tối thiểu bất biến của toàn Farm (cả Kibe và Admin).
  - Hành động bắt buộc: Đối soát đúng kênh của folder đó, nếu thiếu nguồn thì cào thêm đúng kênh đó vào thư mục nguồn ($F_{src}$), nếu nguồn đã đủ ($\ge 45$) thì kích hoạt worker render bù đúng các clip còn thiếu.

## 2. Bẫy Ngộ Nhận Giữa Max Sequence Index và File Count (Sequence Hole Trap)
- **Hiện tượng**:
  - Một folder render (ví dụ `D:\TIKTOK-videonuoinick\63`) có file `45.mp4` và người kiểm tra/script nhìn lướt qua tưởng đã đủ 45 clip.
  - Tuy nhiên, Watchdog đếm thực tế `len([f for f in ... if f.endswith('.mp4')])` chỉ ra **40 clip**, dẫn đến cảnh báo `🟡 Tik7: 79/80 folder (≥45 clip) [98.8%]`.
- **Nguyên nhân cốt lõi**:
  - Trong quá khứ, các file `19.mp4, 20.mp4, 21.mp4, 23.mp4, 28.mp4` bị lỗi (như slide ảnh nhạc 0-byte) nên bị xóa đi.
  - Khi script render bù (`render_kibe_under45.py`) chạy ở lượt tiếp theo, logic chọn clip hoặc renderer incremental check file hiện có (thấy file `39.mp4` tồn tại nên chỉ render tiếp từ `40.mp4` đến `45.mp4`).
  - Hậu quả: Thư mục có các số `1..18, 22, 24..27, 29..45` (tổng đúng 40 file, khuyết 5 lỗ hổng). File có tên `45.mp4` nhưng số lượng thực tế chỉ là 40!
- **Kỷ luật kiểm tra 2 lớp (Two-Layer Sequence Verification)**:
  1. **Lớp 1 - Đếm số lượng thực tế**: `count = len([f for f in folder.glob("*.mp4")]) >= 45`.
  2. **Lớp 2 - Kiểm tra liên tục không lỗ hổng**:
     ```python
     seq_nums = {int(f.stem) for f in folder.glob("*.mp4") if f.stem.isdigit()}
     expected = set(range(1, len(seq_nums) + 1))
     holes = expected - seq_nums
     if holes:
         # Có lỗ hổng sequence: Bắt buộc lấp đầy các số bị khuyết
     ```

## 3. Đối Soát Chuẩn Giữa Output Folder ($F_{out}$) và True Source ($F_{src}$) Trên Kibe
- **Quy tắc phân định**:
  $$F_{out} = (\text{Máy} - 1) \times 8 + \text{Slot}$$
  $$F_{src} = (\text{Slot} - 1) \times 80 + \text{Máy}$$
  - Ví dụ Máy 8 ca Slot 7 (Tik7): $F_{out} = 63$, nhưng $F_{src} = (7-1) \times 80 + 8 = 488$.
- **Bẫy kiểm tra nhầm thư mục nguồn**:
  - Không được nhầm tưởng thư mục nguồn của Output 63 là `D:\video goc\63`.
  - Nguồn chân lý thực tế nằm ở `D:\video goc\488` (chủ đề Câu chuyện, 57 clip MP4 có sẵn).
  - Khi lấp lỗ hổng cho Output 63, chỉ cần lấy các video từ Source 488 render bù vào đúng các số `19, 20, 21, 23, 28` hoặc render nối tiếp từ `46..50.mp4`.
