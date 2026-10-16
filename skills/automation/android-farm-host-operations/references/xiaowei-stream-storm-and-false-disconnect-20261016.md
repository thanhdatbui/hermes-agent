# XiaoWei Stream Storm & False Disconnect on USB 2.0 EHCI (16/10/2026)

## 1. Hiện Tượng & Triệu Chứng
- Người dùng mở phần mềm chiếu màn hình **Tiểu Vi / Phóng Vệ / 牧卫 / 极卫 (`xiaowei.exe`)** khi farm đang trong ca nuôi (Feed session, Follow runner, GPM-Browser).
- Trên giao diện xuất hiện hàng loạt ô màu cam (20–30 máy, ví dụ M09, 10, 13, 14, 18, 19, 28, 29, 30, 38, 42, 44, 45, 48, 49, 50, 51, 59, 60, 62, 63, 65, 67, 68, 71, 73...):
  > *"Điện thoại đã ngắt kết nối, vui lòng kiểm tra."* (kèm icon chấm hỏi xoay vòng màu cam).
- Người dùng hoang mang tưởng farm bị sập hub, đứt cáp hoặc văng hàng loạt điện thoại.

## 2. Bản Chất Kỹ Thuật (Root Cause)
1. **Bão Khởi Tạo Stream (`start_iter` Storm) Trên Bus USB 2.0 EHCI:**
   - Khi vừa khởi động (`MainWindowHandle` hiển thị), `xiaowei.exe` bắn đồng loạt 80 lệnh socket ADB để cài đặt minicap/reverse port và khởi tạo luồng stream (`start_iter`).
   - Lúc này băng thông USB 2.0 (trần 35–40 MB/s) đang bị chiếm dụng bởi automation scripts (screencap, am start, dump window).
   - Socket bắt tay của Tiểu Vi bị timeout đệm:
     * `ERROR [xiaowei::android::client_center] ...: 执行端口:5037 adb_heart 命令错误1: ... (os error 10060)`
     * `ERROR [xiaowei::android::client_center] ...: <serial> start_iter 超时: deadline has elapsed`
2. **Ảo Giác "Văng Máy" Trong Giao Diện Tiểu Vi:**
   - Khi `start_iter` gặp timeout, cơ chế nội bộ của Tiểu Vi không retry nhẹ nhàng mà lập tức chuyển trạng thái hiển thị của slot đó thành "Điện thoại đã ngắt kết nối".
   - **Thực tế phần cứng và ADB server:** 77/80 máy vẫn giữ nguyên trạng thái `device` trên cổng 5037, sạc bình thường, app TikTok và script vẫn đang chạy ngầm trong máy điện thoại.
3. **Va Chạm Kép Với ADB Port 5038:**
   - Tiểu Vi tự khởi động thêm tiến trình `adb.exe -P 5038` làm rẽ nhánh 1 vài thiết bị cá biệt sang port 5038, khiến socket port 5037 của Tiểu Vi báo `device not found` cho những máy đó.

## 3. Quy Trình Chẩn Đoán O(1) Cho Coordinator
1. **Kiểm tra ADB thật sự:**
   - Dùng socket thuần kiểm đếm port 5037: nếu số lượng thiết bị đạt 75–78 máy `device`, khẳng định ngay thiết bị không hề bị văng.
   - Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` kiểm tra ngẫu nhiên 2–3 máy bị báo cam: xác nhận pin, model, screen awake/sleep và focus activity.
2. **Kiểm tra thời điểm khởi động của XiaoWei:**
   - So sánh thời gian tạo tiến trình `xiaowei.exe` với thời điểm phát sinh lỗi trong `C:\Program Files (x86)\xiaowei\logs\app_rCURRENT.log`.
   - Nếu thấy hàng loạt dòng `start_iter 超时: deadline has elapsed` ngay trong 1–2 phút sau khi app mở: 100% là hiện tượng nghẽn stream khởi tạo ban đầu, không phải lỗi máy vật lý.
3. **Xử lý dứt điểm:**
   - Giải thích rõ cho người dùng để an tâm (máy đang chạy bình thường, không rút cáp/reboot).
   - Khuyên tắt Tiểu Vi trong lúc ca nuôi đang chạy để trả lại toàn bộ băng thông USB 2.0 cho runner.
   - Bắn lệnh `adb -P 5038 kill-server` nếu phát hiện có tiến trình ADB 5038 mồ côi tranh chấp cổng.
