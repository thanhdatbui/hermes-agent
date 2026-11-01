# Kỷ Luật Đối Soát Định Danh Cụm Máy: Admin (M200+) vs Kibe (M<200)

## 1. Bối Cảnh & Nguy Cơ Nhầm Lẫn
- Hệ thống Taadaa Farm phân chia máy thành 2 cụm độc lập:
  - **Cụm Kibe Local:** Máy 1 đến 80 (`M < 200`). Quản lý qua file Excel tại `D:/OneDrive/TaadaaData/kibe/Tik<Slot>.xlsx` và `taikhoan_run_safe.xlsx`.
  - **Cụm Admin Remote:** Máy 201 đến 280 (`M >= 200`). Quản lý qua file Excel tại `D:/OneDrive/TaadaaData/admin/Tik<Slot>.xlsx`.
- **Nguy cơ nhầm lẫn số học:**
  - Máy $200 + N$ (ví dụ: Máy 223) và Máy $N$ (ví dụ: Máy 23) có thể bị nhầm lẫn khi tra cứu bằng mắt hoặc regex lỏng lẻo nếu không chú ý prefix `2xx`.
  - Dễ gây hoài nghi ("Có lộn máy admin với kibe không?") nếu Coordinator không báo cáo minh bạch toạ độ và bằng chứng đối soát.

## 2. Quy Trình Đối Soát O(1) Tuyệt Đối
Trước khi trả lời hoặc thực thi chuẩn hoá, bắt buộc chạy kiểm chứng đối soát 3 chiều:
1. **Tra cứu CSDL Farm:**
   ```bash
   python D:/Taadaa/tools/lookup_channel.py -u <username> --json
   ```
   Kiểm tra trường `"host"` (`"admin"` hay `"kibe"`), `"machine"` (ví dụ: `223`), `"tik_workbook"` (`Tik5.xlsx`).

2. **Xác thực trực tiếp trong Excel của cả 2 cụm:**
   - Đọc trực tiếp dòng chứa username trong `D:/OneDrive/TaadaaData/admin/Tik<Slot>.xlsx` và đối chiếu với `D:/OneDrive/TaadaaData/kibe/Tik<Slot>.xlsx`.
   - Xác nhận rõ ràng: Nick nằm ở dòng máy nào, serial thiết bị nào.

3. **Kiểm tra trạng thái thiết bị (Inspect Machine):**
   - Với máy $N$ (Kibe): `python D:/Taadaa/tools/inspect_machine.py <N>`
   - Với máy $200+N$ (Admin): `python D:/Taadaa/tools/inspect_machine.py <200+N>`
   - Đảm bảo thiết bị thật online đúng serial và ADB host (`localhost:5037` vs `192.168.110.119:5037`).

## 3. Kỷ Luật Báo Cáo Phản Hồi
Khi trả lời User về máy thuộc cụm Admin ($M \ge 200$):
- Luôn ghi rõ: **`Máy <M> (Admin Remote)`** thay vì chỉ ghi cộc lốc số máy.
- Trình bày rõ bằng chứng đối soát ở cả 2 file `admin/Tik<Slot>.xlsx` và `kibe/Tik<Slot>.xlsx` để dập tắt ngay sự nghi ngờ lệch cụm.
