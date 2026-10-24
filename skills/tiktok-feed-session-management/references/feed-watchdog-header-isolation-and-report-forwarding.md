# Feed Watchdog Header Isolation & Report Forwarding Invariant

> Context & Case: 24/10/2026 - Chuẩn hóa ranh giới giữa Báo cáo Nuôi Feed định kỳ vs Cảnh báo Khẩn cấp Farm Alert.

## 1. Ranh Giới Bất Biến Giữa Watchdog Report vs Farm Alert
- **Báo cáo Nuôi Feed (`📊 [TIKTOK NUÔI ACC]`):**
  - Gửi độc quyền về nhóm Nuôi (`-5377611430`).
  - Tiêu đề bắt buộc có dạng `📊 [TIKTOK NUÔI ACC] {win_name} hoàn tất ({row_or_pool})`.
  - Hỗ trợ hiển thị Pool động: `Pool {1, 2, 7}`, `Pool {3, 4, 8}`, `Pool {5, 6}`.
  - CẤM TUYỆT ĐỐI đổi tiêu đề sang `🚨 [FARM ALERT]` khi nuôi feed có lỗi (kể cả >= 8 máy fail).
- **Cảnh báo Khẩn Cấp (`🚨 [FARM ALERT]`):**
  - Chỉ kích hoạt khi sập hạ tầng (AP, proxy) hoặc lỗi script hàng loạt ở luồng Follow (`fl_errors >= 8`) hoặc Upload (`up_errors >= 8`).
  - Được gửi về nhóm Farm Alert riêng (`-5373649734`).

## 2. Cô Lập Tiêu Đề Trong `dispatch_split_reports` (`formatters.py`)
- Biến `feed_hdr` phải được tính toán độc lập hoàn toàn với `fl_hdr` và `up_hdr`.
- Nếu Follow dính Farm Alert nhưng Feed chạy bình thường, `feed_hdr` vẫn phải giữ nguyên là `📊 [TIKTOK NUÔI ACC] {win_name} hoàn tất...`.
- Đã được khóa cứng bằng unit test `test_dispatch_split_reports_feed_header_independent_of_fl_alert`.

## 3. Quy Tắc Điều Phối: Forward Report = Lệnh Fix Script
- Khi User forward nguyên văn tin nhắn báo cáo nuôi từ nhóm Telegram sang chat Coordinator:
  1. Coordinator BẮT BUỘC nhận diện đây là **Lệnh điều tra & Fix code trực tiếp**, cấm hỏi lại lải nhải hoặc xin phép.
  2. Tự động bóc tách 4 thông số: Repo nguồn, Cụm + Thư mục Run/Trace O(1), Nhóm lỗi cụ thể, Danh sách máy bị ảnh hưởng.
  3. Chọn 1 máy đại diện đọc log, truy vết traceback, dispatch worker sửa gốc, chạy test hồi quy và canary nghiệm thu.

## 4. Kỷ Luật Ứng Xử: Anti-Flip-Flop
- CẤM TUYỆT ĐỐI tiền hậu bất nhất: lượt trước vừa khuyên revert, lượt sau lại khuyên giữ nguyên khi không có bằng chứng hay điều kiện môi trường thay đổi.
- Phải giữ vững lập trường kiến trúc, phân định rõ ràng giữa hạ tầng vs ứng dụng.
