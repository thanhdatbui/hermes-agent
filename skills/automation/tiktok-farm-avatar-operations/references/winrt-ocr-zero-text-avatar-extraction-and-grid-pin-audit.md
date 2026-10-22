# WinRT OCR Zero-Text Avatar Extraction & TikTok Profile Grid View Audit

## 1. Zero-Text Avatar Extraction Pipeline (WinRT OCR)
Khi trích xuất avatar từ kho video gốc (`D:/video goc/<id>/` hoặc `D:/TIKTOK-videonuoinick/<id>/`):
- Không chọn thủ công bằng mắt trên 1 frame duy nhất vì dễ dính text watermark mờ, phụ đề viền đáy hoặc logo nhà sản xuất.
- **Quy trình chuẩn tự động hóa:**
  1. Dùng `cv2.VideoCapture` duyệt qua nhiều mốc thời gian của video (ví dụ: `1.0s`, `2.5s`, `4.0s`).
  2. Crop khung hình vuông tại tâm (`cx, cy = w//2, h//2`, kích thước `dim = min(h, w)`), resize chuẩn về `512x512` bằng nội suy `INTER_LANCZOS4`.
  3. Gọi hàm `winrt_ocr` từ `D:/Taadaa/tools/winrt_ocr_util.py` (hoặc chạy script `D:/Taadaa/tools/run_winrt_ocr.py <path>`).
     * **Lưu ý Windows Path:** Bắt buộc truyền đường dẫn tuyệt đối với dấu gạch chéo ngược `\` hoặc raw string chuẩn Windows (ví dụ: `r"D:\Taadaa\..."`), nếu dùng gạch chéo xuôi `/` trong PowerShell WinRT API có thể gây lỗi `Invalid pointer` / `InvokeMethodOnNull`.
  4. Lọc lấy frame có kết quả OCR text hoàn toàn rỗng: `len(txt.strip()) == 0` (0 text detected).
  5. Trước khi đính kèm `MEDIA:`, Coordinator BẮT BUỘC gọi `browser_vision` để soi mắt kiểm tra:
     - Xác nhận đúng chủ thể phù hợp với Niche (ví dụ: đồ chơi, nhiếp ảnh, đời sống).
     - Bố cục vuông vức, rõ nét, không bị lẹm góc, không dính logo viền.
  6. Áp dụng đồng bộ: Copy ảnh `avatar.jpg` vào cả thư mục nguồn `D:/video goc/<id>/` và thư mục render `D:/TIKTOK-videonuoinick/<id>/`.
  7. Khóa cờ bảo vệ: Tạo file rỗng `.manual_avatar_locked` và `.manual_hashtag_locked` trong cả 2 thư mục để tránh bị cronjob tự động ghi đè.

## 2. Quy Tắc Audit Lưới Video (Grid View) Trên Hồ Sơ TikTok — Chống Bỏ Sót Top View
- **Hiện tượng lỗi mắt nhắm mắt mở:** Khi quan sát giao diện hồ sơ bằng mắt hoặc crop ảnh thumbnail, nếu chỉ nhìn lướt qua hàng đầu tiên (3 video đầu), rất dễ bỏ sót các video nghìn view hoặc top view khủng (như clip 8.853 view) nằm ở các hàng bên dưới.
- **Quy tắc bất biến:**
  - TUYỆT ĐỐI KHÔNG kết luận top view của kênh chỉ qua ảnh chụp màn hình cục bộ hoặc nhìn lướt hàng đầu.
  - Bắt buộc dùng `capture_atx_session_ui(dev)` dump toàn bộ cây UI XML của hồ sơ.
  - Dùng hàm `parse_profile_tiles(xml)` trong `D:/Taadaa/tools/pin_top_videos.py` để bóc tách toàn bộ các ô video.
  - Tự động chuẩn hóa chuỗi view: xử lý số có dấu chấm (`8.853`), dấu phẩy (`17,8K`), chữ `M` thành số nguyên (`int`).
  - Sắp xếp giảm dần: `tiles.sort(key=lambda x: x["views"], reverse=True)` để lấy chính xác video có lượt view cao nhất (`cands[0]`).
  - Script `pin_top_videos.py` đã tích hợp sẵn cơ chế **Auto-swap**: Nếu kênh đã đạt tối đa 3 video ghim (`--max-pins 3`), script tự so sánh và tháo video đã ghim có view thấp nhất ra để ghim video mới có view cao hơn lên đầu.

## 3. Khắc Phục Lỗi ATX-Agent Dump Trên Thiết Bị S7 (Port 7912)
- Endpoint `http://127.0.0.1:7912/dumpUI` KHÔNG tồn tại trên daemon `atx-agent` (trả về lỗi HTTP 404 Page Not Found).
- Cơ chế đọc UI XML duy nhất hoạt động chuẩn xác là gọi qua `capture_atx_session_ui(dev)` từ `automation_core.persistent_ui` (sử dụng session endpoint `/session/<pid>:com.github.uiautomator/jsonrpc/0` với method `dumpWindowHierarchy`).
- Nếu thiết bị trả về `EMPTY_HIERARCHY` hoặc `atx-agent` bị kẹt:
  1. Kiểm tra màn hình máy có đang BẬT hay không (`dumpsys power | grep "Display Power"`). Nếu tắt phải bật màn hình và mở đúng app TikTok.
  2. Gọi `reset_atx_agent(dev)` để restart daemon và uiautomator stub.
  3. Gọi lại `capture_atx_session_ui(dev)` để nhận UI XML sạch.
