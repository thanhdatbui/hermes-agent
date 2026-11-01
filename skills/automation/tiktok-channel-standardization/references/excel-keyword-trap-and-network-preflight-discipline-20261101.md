# Kỷ Luật Đối Soát Niche Chân Lý & Preflight Kiểm Tra Mạng Trước Mọi Thao Tác

## 1. Bài Học Cốt Lõi: CẤM Tin Mù Quáng Vào Cột Keyword Trong Excel (The Excel Keyword Trap)
- **Hiện tượng:** Trong các file Excel quản lý farm (ví dụ `Tik5.xlsx` cụm Admin), cột `Keyword Video` thường xuyên bị người tạo file gán nhãn nhầm/mặc định (ví dụ ghi là `Xe` hoặc `Anime`).
- **Sai lầm kinh điển của Agent:** 
  - Đọc nhãn Excel thấy chữ `Xe`, sau đó nhìn thumbnail video bị thiên kiến xác nhận (Confirmation Bias), tự tưởng tượng ra góc quay cabin xe hơi, đường cao tốc để cãi lại User.
  - Trong khi thực tế nội dung video thật 100% là cảnh câu cá, sông nước dã ngoại.
- **KỶ LUẬT THÉP:**
  - **Video thực tế đã đăng trên kênh và video trong kho nguồn là MỎ NEO CHÂN LÝ (Ground Truth) DUY NHẤT.**
  - CẤM TUYỆT ĐỐI lấy thông tin cột Keyword trong Excel để suy diễn hoặc cãi lại User.
  - Khi User hỏi kênh thuộc ngách nào: Bắt buộc cắt zoom trực tiếp các thumbnail video thật ra xem bằng mắt (VLM / Browser Vision) trước khi phát ngôn.

## 2. Invariant Preflight Kiểm Tra Mạng Bắt Buộc Trước Mọi Script UI (Fail-Closed Network Guard)
- **Nguyên nhân sự cố:**
  - Khi máy Android bị rớt proxy hoặc Wi-Fi dính dấu chấm than `!` (chưa thông ra Internet), nếu runner thao tác UI (nhập tên, lưu bio) sẽ bị TikTok báo lỗi `Không thể lưu` và có nguy cơ làm app treo/checkpoint.
- **Giải pháp O(1) không chế lại bánh xe:**
  - Trong `automation_core.preflight` đã có sẵn hàm `require_android_vpn(adb, required=True, interface='wlan0', verify_live_ip=True)`.
  - Bắt buộc chèn kiểm tra ở ngay đầu hàm `_execute_rename_inner()` hoặc hàm thực thi chính của mọi script thao tác thiết bị:
    ```python
    from automation_core.adb import AdbClient
    from automation_core.preflight import require_android_vpn

    adb_client = AdbClient(host="192.168.110.119" if MACHINE_ID >= 200 else None, port=5037, serial=SERIAL)
    require_android_vpn(adb_client, required=True, interface="wlan0", verify_live_ip=True)
    ```
  - **Cơ chế Fail-Closed:** Nếu proxy timeout hoặc Wi-Fi dính `!` (không lấy được Public IPv4 qua proxy), tiến trình dừng ngay lập tức tại giây đầu tiên (`exit code 2`), không mở app, không gõ phím mù quáng.

## 3. Kỷ Luật Trích Xuất Avatar Khung Hình Rộng (Wide-View / Full-Body Invariant)
- **Phản hồi của User:** "Ảnh nào view to hơn đi chứ toàn bị mất 1 phần người trong ảnh".
- **Yêu cầu kỹ thuật khi cắt avatar người trong video dã ngoại/câu cá:**
  - Cắt quá sát khuôn mặt (tight crop) trong các video hoạt động ngoài trời sẽ làm mất vóc dáng, mất bối cảnh và gây cảm giác bị lẹm cụt người.
  - Bắt buộc chuẩn bị ít nhất các phương án có góc nhìn rộng (wide view): thấy trọn vẹn toàn thân hoặc nửa thân trên kèm cử chỉ hành động (ngồi câu cá, đứng vung cần, ngắm cảnh bên bờ hồ) để User lựa chọn.
