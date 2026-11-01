# Bài Học Thực Chiến Chuẩn Hoá Kênh: Ground Truth Video vs Bẫy Nhãn Excel & Quy Trình Proposal Canvas

## 1. Cạm Bẫy Nhãn Bảng Tính vs Mỏ Neo Chân Lý (Excel Anchor Bias)
- **Hiện tượng sự cố:**
  - Khi tra cứu toạ độ kênh (ví dụ máy 223, slot Tik 5), cột Keyword trong `Tik5.xlsx` ghi nhãn `Xe` và bộ hashtag `#xe #xevietnam...`.
  - Coordinator nhìn thấy nhãn `Xe`, khi soi lướt thumbnail bị thiên kiến xác nhận (Confirmation Bias), tự suy diễn khung cảnh hồ nước/bờ cỏ thành "cabin xe, đường cao tốc, an toàn giao thông" và cãi lại User khi User hỏi *"Cái video cắn đề xuất là đi câu cá mà? Xe clmm à"*.
- **Quy tắc bất biến (Invariant):**
  - Cột Keyword trong Excel do người lập bảng gán ngẫu nhiên hoặc điền sai lúc reg nick hàng loạt.
  - **NỘI DUNG VIDEO ĐÃ ĐĂNG VÀ KHO VIDEO THỰC TẾ LÀ MỎ NEO CHÂN LÝ (GROUND TRUTH) DUY NHẤT.**
  - Tuyệt đối cấm lấy nhãn trong file Excel để cãi lại User hoặc để suy diễn chủ đề kênh.
  - Khi User hỏi vặn về niche, **BẮT BUỘC kiểm tra trực tiếp kho video nguồn (`D:/TIKTOK-videonuoinick-admin/<F_vid>` hoặc `D:/video goc/<F_src>`)** thay vì đọc cột Keyword trong Excel.

## 2. Kỷ Luật Xuất Bản Proposal Canvas Trước Khi Nạp Avatar (Anti-Premature-Push)
- **Hiện tượng sự cố:**
  - Coordinator tự ý cắt 1 ảnh ưng ý (PA 1), đẩy thẳng vào máy thật và chạy runner nạp avatar mà **chưa gửi Bảng Proposal Canvas 4 phương án cho User duyệt**.
  - Bị User bắt lỗi gay gắt: *"mày đã cắt ava cho tao chọn đâu?"*.
- **Quy trình chuẩn hoá bắt buộc:**
  1. Cắt 4 phương án avatar vuông $512 \times 512$ từ các clip khác nhau trong kho hoặc trên kênh.
  2. Ghép thành Bảng Proposal Canvas 4 ô tròn viền xanh lá (PA 1, PA 2, PA 3, PA 4) kèm nhãn mô tả góc chụp.
  3. Dùng `browser_navigate` và `browser_vision` soi mắt kiểm tra cả 4 ô tròn (sạch chữ 100%, rõ nét, cân đối).
  4. Đăng ký receipt `create_vision_receipt` và gửi thẻ `MEDIA:<path_canvas>` lên khung chat cho User chọn.
  5. **CHỈ ĐƯỢC PHÉP nạp avatar vào thiết bị KHI VÀ CHỈ KHI User đã phản hồi chọn cụ thể phương án (ví dụ "PA 1", "chọn cái 2", "lấy 3").**

## 3. Tích Hợp Cơ Chế Network Preflight Fail-Closed O(1)
- **Vấn đề:**
  - Các script thao tác profile standalone (`do_rename_canonical_runner.py`) trước đây không check mạng mà chỉ check ADB. Khi máy bị chết proxy hoặc Wi-Fi dính dấu chấm than `!`, script vẫn bấm mở app, gõ text dẫn đến TikTok nảy lỗi `Không thể lưu`.
- **Giải pháp O(1) đã kiểm chứng:**
  - Sử dụng hàm có sẵn trong `automation_core.preflight` thay vì chế lại bánh xe:
    ```python
    from automation_core.adb import AdbClient
    from automation_core.preflight import require_android_vpn

    adb_client = AdbClient(host="192.168.110.119" if MACHINE_ID >= 200 else None, port=5037, serial=SERIAL)
    require_android_vpn(adb_client, required=True, interface="wlan0", verify_live_ip=True)
    ```
  - Khi proxy chết / Wi-Fi dính dấu `!`, hàm lập tức ném ngoại lệ và dừng script ngay giây đầu tiên (`return 2`), bảo vệ tài khoản an toàn tuyệt đối.
