# Raw Video Gốc vs Render Nuôi Avatar Extraction & Post-Run Excel Reconciliation (2026-10-10)

## Context & Operator Directive
Khi chuẩn hóa avatar cho tài khoản farm, Operator chấn chỉnh dứt khoát:
> **"Lấy từ video gốc ấy đừng lấy từ render"**

## 1. Căn nguyên: Tại sao cắt avatar từ kho Render (`TIKTOK-videonuoinick`) luôn thất bại Visual QA?
Khi video được tải về từ nguồn, file gốc lưu tại `D:\video goc\<raw_folder>` ở độ phân giải gốc (ví dụ 576x1024 hoặc 576x828), màu sắc tự nhiên, chưa dính bất kỳ hiệu ứng nhân tạo nào.

Tuy nhiên, khi qua pipeline render để tạo video nuôi nick sang `D:\TIKTOK-videonuoinick\<render_folder>` (1080x1920):
1. **Ép tỉ lệ khung hình 9:16:** Các video gốc ngang hoặc tỉ lệ 1:1.4 (như 576x828) bị phóng to (zoom in) và cắt xén mạnh mép trên/dưới để vừa 1080x1920. Điều này làm đỉnh đầu (hair apex) hoặc cằm của nhân vật bị chạm sát mép khung hình $\to$ Khi cắt crop vuông/tròn sẽ mất hoàn toàn khoảng thở (0% headroom).
2. **Áp hiệu ứng Dark Vignette:** Pipeline render thường phủ lớp gradient tối (vignette) ở đỉnh và đáy video để làm nổi bật phụ đề hoặc tránh bản quyền. Khi bốc frame từ video render, vùng trán và tóc luôn bị ám vệt đen nhân tạo, bị Vision API chấm FAIL (Điểm $\le 4.5/10$).
3. **Bộ lọc màu & Làm mịn da (Beauty LUT):** Render áp bộ lọc màu và làm mịn da gắt làm bệt chi tiết lông mi, con ngươi và texture da tự nhiên.

## 2. Quy trình Trích xuất Chuẩn 100% từ Video Gốc
1. **Xác định đúng thư mục Video Gốc thực tế:**
   - Kiểm tra `video gốc` trong workbook `Tik<N>.xlsx` hoặc tính toán theo công thức mapping ca/máy: `(Tik-1)*80 + Máy`.
   - Trong case Máy 26 Tik 1: `Folder Video = 201`, nhưng thư mục chứa 49 video gốc thô chưa qua render là `D:\video goc\26`.
2. **Trích xuất từ file video gốc nguyên bản:**
   - Đọc trực tiếp từ `D:\video goc\<raw_folder>\<vnum>.mp4` (ví dụ `38.mp4` tại 4.5s).
   - Độ phân giải gốc 576x1024, không dính vignette render, không dính CapCut watermark hay phụ đề.
   - Thẩm định qua Vision API: Đạt điểm xuất sắc **9.1/10 (PASS)** (mắt mở to, bắt sáng tự nhiên, viền tóc rõ nét, màu áo polo đen tương phản đẹp).
3. **Đồng bộ hóa 3 đầu kho:**
   Sau khi tạo file vuông 512x512 chất lượng cao (JPEG quality 95-96, ghi nguyên tử `.tmp.jpg` $\to$ `.replace()`):
   - `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg` (để runner upload bốc)
   - `D:\video goc\<Folder Video>\avatar.jpg`
   - `D:\video goc\<video_goc>\avatar.jpg`

## 3. Bẫy Phiên bản `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION` trên Kibe Local
- Trong môi trường `D:\CodexRuntime\tiktok-video\venv-core024`, metadata version là `0.4.44`.
- **CẤM** gán `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION=0.4.45` trên trạm Kibe local. Điều này khiến `run_tiktok_upload_batch.ps1` văng lỗi:
  `automation-core version mismatch: expected=0.4.45; actual=0.4.44`
- Bắt buộc đặt: `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION=0.4.44`.

## 4. Bẫy Post-Run Excel Reversion của `run_post.py`
- Khi `run_post.py` kết thúc pha `ENSURE_AVATAR`, nó tự động mở `Tik<N>.xlsx` và cập nhật cột `Avatar = OK`.
- Nếu trước đó Coordinator đã sửa `Keyword Video` và `Hashtag Pool` trong file Excel, việc `run_post.py` lưu workbook có thể revert các cột khác về giá trị cũ từ bộ nhớ cache/snapshot nếu không đồng bộ.
- **Quy tắc bắt buộc:** Ngay sau khi runner báo hoàn tất, Coordinator BẮT BUỘC đọc lại dòng tài khoản trong `Tik<N>.xlsx`, kiểm tra lại các cột:
  * Col 5 (`video gốc`)
  * Col 6 (`Keyword Video`)
  * Col 7 (`Hashtag Pool`)
  * Col 10 (`Avatar`)
  Nếu bị lệch nhãn (ví dụ `Thư viện` thay vì `Gái xinh VN`), phải ghi đè cập nhật lại ngay lập tức và lưu file.
