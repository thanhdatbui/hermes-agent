# Post-Auth Bio Screen & ADB Hang Recovery (2026-09-27)

## 1. Màn hình "Tiểu sử" (Bio screen) sau khi Login TikTok
- **Dấu hiệu nhận diện**:
  - Text: "Tiểu sử", "Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào."
  - Nút action: "Hủy" ở góc trên trái `[24,72][167,204]`, tâm `(95, 138)`. Hoặc "Lưu" ở góc trên phải `[922,72][1056,204]`.
- **Cơ chế xử lý trong `handle_post_auth_screens`**:
  - Không coi đây là unknown screen để tránh lặp vô hạn tới khi timeout 600s.
  - Bắt buộc tap `Hủy` hoặc `Bỏ qua` (fallback coord `(95, 138)`). Sau khi hủy, TikTok sẽ vào thẳng Profile hoặc Feed.

## 2. Xử lý ADB Daemon Deadlock / Hang
- **Dấu hiệu**:
  - Lệnh `python D:/Taadaa/tools/inspect_machine.py <N>` bị timeout 10.0s ở bước `shell getprop` hoặc `shell dumpsys`.
  - Worker chạy script ADB bị treo im lặng, không có stdout mới.
- **Hành động khắc phục dứt điểm**:
  1. Kiểm tra tiến trình: `ps -W | grep adb`
  2. Diệt tận gốc tiến trình treo: `taskkill -F -IM adb.exe`
  3. Khởi động lại daemon sạch: `adb start-server`
  4. Ping kiểm tra lại thiết bị: `python D:/Taadaa/tools/inspect_machine.py <N>`

## 3. Kỷ luật An toàn: Cấm Quét Đĩa Diện Rộng (Invariant Bất Di Bất Dịch)
- Tuyệt đối cấm chạy `grep -rn`, `find`, `os.walk`, `glob(recursive=True)` trên toàn bộ cây thư mục `D:/Taadaa` hoặc trong repo.
- Quét qua `.pytest-basetemp-*` sẽ bị lỗi Windows `Permission denied` và khiến terminal bị đóng băng 600s.
- Mọi thao tác truy xuất log, artifact, dump XML phải thực hiện theo đường dẫn O(1) cụ thể theo date/timestamp.
