# Quy trình Tạo Workbook Tik5, Render Random và Chuỗi Tuần Tự Tik4 -> Tik5 (2026-08-27)

## 1. Quy tắc Tạo Workbook Tik5 (`Tik5.xlsx`)
- **Nguồn tài khoản**: Slot 5 trong `taikhoan_dat_v2_updated .xlsx` (dòng thứ 5 của mỗi máy trong REG).
- **Vị trí lưu**: `D:\OneDrive\TaadaaData\kibe\Tik5.xlsx`.
- **Mapping cột**:
  - `Máy`: 1..80
  - `device ID`: Lấy từ slot 5 (hoặc chuẩn hóa serial phần cứng từ `PROXYgandienthoai.xlsx` nếu bị dính ngày).
  - `ID`: Lấy từ slot 5 của master REG (nếu None -> ghi `MISSING_ID` ở cột `Kiểm Tra Dữ Liệu`, có -> `OK`).
  - `Folder Video` (Output): `(máy - 1) * 8 + 5` -> `5, 13, 21, 29, ..., 637`.
  - `video gốc` (Source): `320 + máy` -> `321..400`.
  - `Keyword Video` & `Hashtag Pool`: Tra cứu slug từ `folders` trong `state.db` -> map sang label tiếng Việt qua `niches_pool.txt` -> generate pool hashtag chuẩn niche.
  - `Video Đã Đăng`: Khởi tạo mặc định `0`.

## 2. Quy tắc Render Khi Thiếu ID (User Rule 2026-08-27)
- **Thiếu ID không chặn render**: Máy mang trạng thái `MISSING_ID` vẫn BẮT BUỘC render đủ video vào đúng `Folder Video` theo mapping. ID tài khoản chỉ cần khi upload và sẽ được bổ sung/sync sau.
- Launcher render (`run_tik5_random_render.ps1`) chỉ đọc cặp `output ↔ source` từ workbook, không được lọc bỏ các dòng thiếu ID.

## 3. Kiến Trúc Random Render vs Preset Cố Định ("Ông Anh")
- **Nguyên nhân bản ông anh chậm & fake kém**:
  - Dùng filter `geq` (generic equation) để tạo viền tối `side_gradient` và `gblur`. `geq` phân tích biểu thức pixel-by-pixel bằng CPU không tận dụng SIMD/AVX2 $\rightarrow$ nghẽn CPU nặng (tụt FPS 3-5x).
  - Áp dụng thông số cố định (fixed zoom, fixed curves, fixed pitch 1.04) cho hàng nghìn video $\rightarrow$ tạo ra fingerprint đồng nhất, thuật toán dễ dàng gom cụm spam/reup.
- **Tối ưu của Random Render Pipeline**:
  - Loại bỏ hoàn toàn `geq` và `gblur`, dùng `preset_owner.json` với `crf=23`.
  - Sinh biến thể ngẫu nhiên theo `seed` cho từng video: biến thiên tốc độ PTS ($\pm 2\text{--}6\%$), micro-rotate ($\pm 0.05\text{--}0.20^\circ$), dịch tâm $X/Y$ ($\pm 8\text{px}$), temporal noise (luma 1-3), keyframe GOP size (30-150), voice profiles (treble/bass/normal) kết hợp chorus/reverb và EBU R128 loudnorm.
  - Hỗ trợ resume tức thì (`-ResumeVerifyExisting`) qua `ffprobe` kiểm tra duration/dimensions.

## 4. Chuỗi Render Tuần Tự (Chống Tranh Chấp CPU)
- Khi chạy render nhiều Tik liên tiếp (vd Tik4 $\rightarrow$ Tik5), BẮT BUỘC dùng supervisor tuần tự (`scripts/tik4_then_tik5.py`):
  - Phải lọc chính xác PID process launcher thật (`powershell.exe` chạy `.ps1` hoặc `python.exe` chạy `scripts\random_batch_render.py` mang run-id thật), tránh regex bắt nhầm các câu lệnh chẩn đoán/grep của agent.
  - Chỉ khởi động batch tiếp theo khi batch trước đã đạt 80/80 folder hợp lệ ($\ge 30$ video MP4).
