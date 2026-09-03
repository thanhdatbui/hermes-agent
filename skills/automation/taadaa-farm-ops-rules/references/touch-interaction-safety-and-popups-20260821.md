# Quy Tắc Điều Khiển Giao Diện & Tương Tác Cảm Ứng Phone Farm (21/08/2026)

## 1. Nút Camera (+) Ở Đáy Màn Hình TikTok
- **Vị trí**: Nằm chính giữa Bottom Navigation Bar `[432, 1794][648, 1920]` (tâm ~540, 1857).
- **Nguy cơ**: Lệnh swipe kéo từ cận đáy hoặc tap fallback `(540, 1700~1800)` khi máy trễ cảm ứng sẽ kích hoạt nhầm nút (+), làm bật giao diện Camera/Quay video và kẹt máy.
- **Quy chuẩn**:
  - Tọa độ vuốt an toàn: Bắt đầu từ Y <= 1600 (ví dụ: `input swipe 540 1600 540 400 300` hoặc `450 1540 450 620 500`).
  - TUYỆT ĐỐI CẤM swipe bắt đầu tại Y > 1600 (như `540 1800 ...`) hoặc tap fallback mù tại tọa độ cận đáy X=540.
  - Khi dính màn hình Camera: Dùng `dismiss_camera_creation_screen` (gửi phím BACK hoặc tap nút X góc trên trái [95, 90]) để thoát về Feed ngay lập tức.

## 2. Xử Lý Popup "Follow bạn bè của bạn"
- Khi gặp modal danh sách gợi ý bạn bè / follow lại:
  - **Hành động bắt buộc**: Quét và bấm toàn bộ các nút **"Follow lại" / "Follow back"** để tăng tương tác và follow chéo tự nhiên cho tài khoản.
  - **Sau khi bấm**: Đóng modal bằng nút "X" (hoặc phím BACK) để trả máy về luồng lướt Feed bình thường.

## 3. Quy Tắc Xử Lý Quảng Cáo & Popup Không Xác Định
- **Quảng cáo (Ad overlay / Sponsored card / Khảo sát quảng cáo)**: Ưu tiên vuốt lên (swipe up) để lướt qua video tiếp theo. Nút "Đóng" chỉ là fallback khi vuốt 2 lần không qua. CẤM bấm vào nút CTA (Tìm hiểu thêm, Mua ngay).
- **Màn hình lạ / không rõ**: Thử vuốt lên (swipe recovery) tối đa 2 lần trước khi kết luận kẹt màn hình và gửi alert giữ hiện trường.
