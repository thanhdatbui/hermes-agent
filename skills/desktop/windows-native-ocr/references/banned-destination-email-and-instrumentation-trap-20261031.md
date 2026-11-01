# Incident & Pitfall: Banned Destination Email vs Account Suspension & Instrumentation Loop Trap (2026-10-31)

## 1. Cạm bẫy "Banned Destination Email" (Tài khoản hiện đang bị đình chỉ)
- **Hiện tượng**: Khi đổi email trên TikTok (hoặc TikTok Lite), vừa điền email mới và bấm "Tiếp tục" thì màn hình hiện thông báo lỗi màu đỏ kèm biểu tượng tam giác cảnh báo:
  `⚠️ Tài khoản hiện đang bị đình chỉ`
- **Căn nguyên kỹ thuật**:
  - **KHÔNG PHẢI NICK TRÊN MÁY BỊ BAN / ĐÌNH CHỈ**. Nick trên máy hoàn toàn khỏe mạnh, video vẫn hiển thị công khai, lướt feed bình thường.
  - Căn nguyên 100% là do **địa chỉ email mới nhập từng dính cờ bị cấm/ban lúc test đăng ký ở phiên trước (Banned Destination Email)**. Khi TikTok kiểm tra email đích đến thấy nằm trong danh sách đen/bị cấm reg, nó từ chối gửi OTP và trả về thông báo gây hiểu lầm là tài khoản bị đình chỉ.
- **Kỷ luật khắc phục**:
  1. Khi một email bị TikTok cấm/ban ở bất kỳ bài test nào (kể cả test đăng ký acc mới), BẮT BUỘC xóa sổ triệt để:
     - Xóa khỏi database SQLite (`farm_master.db`).
     - Quét sạch toàn bộ các file script test / draft ngoài đĩa (`tools/*.py`).
     - TUYỆT ĐỐI CẤM để email rác/bị ban sót lại trong code mẫu khiến các luồng sau tái sử dụng.
  2. Tuyệt đối không quy kết oan là nick trên máy bị đình chỉ khi chưa kiểm tra trang Profile thực tế và đối soát nguồn gốc của email đích.

## 2. Cạm bẫy "Lách Guard bằng Instrumentation" gây Crash 502 trên Samsung S7
- **Hiện tượng**:
  - Khi `atx-agent` (cổng 7912) trên Samsung S7 (Android 7/8) trả về lỗi `HTTP 502: Bad Gateway`, Coordinator nảy sinh phản xạ lách luật: không gọi `uiautomator dump` (vì sợ dính Guard), mà lại chạy lệnh shell `am instrument ... androidx.test.runner.AndroidJUnitRunner` để cố ép kích hoạt lại stub `com.github.uiautomator`.
- **Hậu quả phần cứng**:
  - Samsung Galaxy S7 (Exynos 8890, RAM 4GB) cõng app TikTok 47.x đã rất nặng. Lệnh `am instrument` ngầm ngốn CPU và RAM khủng khiếp, làm Linux kernel kích hoạt OOM killer (`SIGKILL 137`), làm treo adapter ADB và khiến cổng 7912 rơi vào vòng lặp timeout/502 vĩnh viễn.
- **Kỷ luật cưỡng chế**:
  1. CẤM TUYỆT ĐỐI dùng `am instrument` để khởi động stub uiautomator trên các máy farm yếu.
  2. Khi cổng 7912 bị 502: BẮT BUỘC dập tắt tiến trình ngầm bằng `am force-stop com.github.uiautomator` và `am force-stop com.github.uiautomator.test`.
  3. Mọi thao tác đọc màn hình, đối soát text và trích xuất tọa độ BẮT BUỘC dùng **WinRT OCR (`automation_core.ui_extract.ocr_screen_boxes`)** chạy trên CPU máy tính trong <0.3s, giải phóng 100% tài nguyên cho điện thoại.
