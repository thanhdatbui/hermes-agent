# Artifacts Extraction vs Post-Shift Sleeping Phones & Cross-Session De-duplication

## 1. Bản chất cốt lõi: Post-Shift Sleeping Phones
- Khi ca chạy (Feed, Follow, Upload) kết thúc, điện thoại Android tự động tắt màn hình về chế độ ngủ (Screen OFF/Dozing) hoặc nhả về màn hình chính (LauncherActivity).
- **CẤM TUYỆT ĐỐI** gọi live ADB commands (`adb exec-out screencap`, `atx-agent dumpUI`, `uiautomator dump`) vào các máy đã kết thúc ca. Thao tác này sẽ chỉ chụp được màn hình đen xì hoặc màn hình Home vô nghĩa, làm sai lệch Telemetry (Gate 0 fail giả hoặc Planner bị ảo giác).
- **Giải pháp chuẩn:** Khi phát sinh sự cố sau ca chạy, BẮT BUỘC trích xuất dữ liệu trực tiếp từ **Run Artifacts** trong thư mục ca chạy (`runtime/.../machines/machine_<ID>/...` và CodexRuntime `runs/...`):
  * **Ảnh sự cố thật:** Bốc các file chụp đúng thời điểm lỗi như `*-before.png`, `*failure*.png`, `*recaptured*.png`, hoặc `artifacts/**/screen.png`.
  * **Cấu trúc UI XML:** Bốc `popup_before.xml`, `ui.xml` được lưu trước đó.
  * **Log & Stack trace:** Đọc tail 100-150 dòng `execution.log` hoặc `summary.txt`, trích xuất `reason`, `stop_reason`.
  * **Gate 0 Score:** Khi sự cố có `atx_status == 'run_artifact'` hoặc có log/stack trace xác thực từ ca chạy, hệ thống công nhận Telemetry đạt chuẩn Cổng 0 (`score = 2`), không được ép buộc XML dump sống.

## 2. Kỷ luật Rà soát Trùng lặp Xuyên Session (Cross-Session De-duplication)
- **Triệu chứng:** Nhận được trigger từ cronjob cũ hoặc báo cáo sự cố (ví dụ `incident-auto-heal-dispatcher` báo thất bại từ các ca trước).
- **Bẫy điều phối:** Coordinator vội vàng nhảy vào điều tra, sửa code, lặp lại toàn bộ các bước mà một session trước đó đã sửa xong, kiểm thử và chốt phiên.
- **Kỷ luật bắt buộc trước khi động thủ:**
  1. Khi nhận alert/trigger liên quan đến một module nền tảng, **BẮT BUỘC** gọi `session_search` rà soát lịch sử gần nhất xem có session nào đã nhận diện, vá lỗi hoặc chốt phiên cho vấn đề này chưa.
  2. Kiểm tra `git log -n 5 --oneline` để xác thực xem commit sửa lỗi tương ứng đã nằm trên HEAD hay chưa.
  3. Nếu vấn đề đã được giải quyết trọn vẹn ở session trước, đối soát trạng thái hiện tại và báo cáo ngay kết quả DONE kèm bằng chứng commit/test, tuyệt đối không re-dispatch Worker hay sửa đè code gây xung đột.
