# Phone Farm Emergency Shutdown (Power Outage / Mất Điện)

## Mục đích & Nguy cơ khi mất điện
- Khi nguồn điện lưới bị cắt đột ngột hoặc UPS cảnh báo sắp hết dung lượng, nếu rút điện hoặc tắt công tắc nguồn Box Phone ngay lập tức, bộ nhớ flash (UFS/eMMC) của các thiết bị Android dễ bị hỏng hệ thống tập tin (corrupted filesystem, bootloop, treo logo).
- Cần gửi lệnh tắt mềm `reboot -p` qua ADB để hệ điều hành Android thực hiện unmount phân vùng dữ liệu và ghi xả bộ nhớ đệm (cache flush) an toàn.

## Kiến trúc công cụ cấp cứu
1. **Python Script (`shutdown_farm_emergency.py`)**:
   - Vị trí: `D:\OneDrive\Command all project\shutdown_farm_emergency.py`
   - Dùng `ThreadPoolExecutor(max_workers=40)` để phát lệnh song song đến toàn bộ đàn máy (80+ máy trong 2-4 giây).
   - Lệnh ADB: `adb -s <serial> shell reboot -p` với `timeout=8`.
   - Lưu ý xử lý ngoại lệ: Rất nhiều thiết bị ngắt kết nối USB ngay khi nhận tín hiệu shutdown, dẫn đến `TimeoutExpired` hoặc ngắt pipe đột ngột — cần coi đây là tắt thành công (`success`).
   - Tự động dò tìm ADB binary (`shutil.which('adb')` hoặc fallback đường dẫn XiaoWei `C:\Program Files (x86)\xiaowei\tools\adb.exe`).

2. **Batch Launcher & Dual-Fallback (`TAT_FARM_KHAN_CAP.bat`)**:
   - Vị trí: Đặt tại `D:\OneDrive\Command all project\`, đồng bộ sang `D:\OneDrive\TAT_FARM_KHAN_CAP.bat` và Desktop `C:\Users\Kibe\Desktop\TAT_FARM_KHAN_CAP.bat`.
   - Cơ chế:
     - Ưu tiên gọi script Python để xử lý đa luồng có báo cáo chi tiết.
     - **Dự phòng (Fallback)**: Nếu Python chưa cài hoặc lỗi môi trường, batch file tự động duyệt qua `adb devices` bằng vòng lặp `for /f` và bắn `start /b %ADB_EXE% -s <serial> shell reboot -p` ngầm để không cần phụ thuộc bất kỳ runtime nào.

## Quy trình 3 bước thao tác chuẩn khi mất điện
1. **Bấm chạy `TAT_FARM_KHAN_CAP.bat` trên Desktop hoặc OneDrive**.
2. **Đợi 5 - 10 giây** để điện thoại hoàn tất flush cache và tắt hẳn màn hình/ngắt kết nối USB.
3. **Gạt công tắc nguồn cứng Box Phone** (ngắt nguồn điện nuôi các máy) và tiến hành tắt máy tính điều khiển / tắt UPS.
