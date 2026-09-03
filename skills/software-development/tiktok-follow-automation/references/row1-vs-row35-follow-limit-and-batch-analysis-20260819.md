# Phân Tích Thực Nghiệm: Tỉ Lệ Nhả Follow & Giới Hạn Tích Lũy Theo Phiên (19/08/2026)

## 1. Bản Chất Hiện Tượng Nhả Follow (Pull-to-Refresh Released)
- **Cơ chế xác nhận nhả follow:** Sau khi tap nút Follow, runner thực hiện kéo từ trên xuống (Pull-to-refresh, $y_1=35\%h \rightarrow y_2=80\%h$) và chờ $\ge 3.5s$ để tải lại trang Profile. Nếu nút chuyển ngược từ "Đã follow" / "Nhắn tin" về lại nút "Follow" đỏ $\rightarrow$ Ghi nhận `FOLLOW_FAILED` và dừng ngay session.

## 2. Đối Chiếu Thực Nghiệm: Nick Đã Đăng Video (Row 1) vs Nick 0 Video (Row 3, Row 5)
Trích xuất từ dữ liệu chạy thực tế ngày 19/08/2026 trên 64 máy farm:

| Nhóm Tài Khoản | Trạng Thái Video | Kết Quả Thực Tế | Tỉ Lệ Nhả Follow |
| :--- | :--- | :--- | :--- |
| **Row 1 (Đã đăng 8–15 video)** | Có Trust Score | **Follow được 4–8 người/phiên mượt mà** ở các phiên đầu (húp >280 follows). Chỉ bị limit ở các phiên cuối ca. | ~60% (chỉ dính khi chạm trần tích lũy ngày) |
| **Row 3 & Row 5 (0 video - Chưa đăng)** | Chưa có Trust Score | **Bị nhả ngay từ lượt follow đầu tiên (followed = 0)**. Nút vừa bấm xong vuốt refresh là bật đỏ lại ngay lập tức. | **100% (nhả ngay lập tức)** |

### Kết luận quan trọng:
1. **Nick chưa đăng video (0 video):** Bị thuật toán TikTok phân loại vào nhóm tài khoản rác/bot clone $\rightarrow$ **CẤM chạy follow trên nick 0 video**. Phải nuôi feed và đăng tối thiểu 1–2 video trước khi cho đi follow.
2. **Nick đã có video (Row 1):** Được cấp hạn mức trust nhất định, cho phép follow thành công 10–15 người mỗi ngày.

## 3. Quy Luật Limit: Hạn Mức Tích Lũy Trong Ngày (Daily Rolling Limit)
Dữ liệu diễn biến của Row 1 qua 6 phiên sáng ngày 19/08:
- **Phiên 06:00:** 14 máy OK (64 follow) | **0 máy nhả**.
- **Phiên 06:45:** 23 máy OK (119 follow) | **1 máy nhả**.
- **Phiên 07:45:** 13 máy OK (57 follow) | **1 máy nhả**.
- **Phiên 08:30:** 10 máy OK (44 follow) | **0 máy nhả**.
- **Phiên 09:45:** **CHẠM TRẦN TÍCH LŨY! 15 máy bị nhả follow hàng loạt.**
- **Phiên 10:45:** **Tiếp tục 9 máy bị nhả follow.**

👉 **Quy luật:** TikTok **KHÔNG tính limit riêng cho từng phiên** mà tính **cộng dồn theo ngày (Daily Rolling Limit)**. Khi một nick trong buổi sáng đã follow đạt ngưỡng 12–20 người qua 3–4 batch chạy bù, TikTok tự động kích hoạt cờ rate-limit và nhả toàn bộ các lượt follow tiếp theo trong ngày.

## 4. Quy Tắc Vận Hành Chuẩn
1. **Số phiên follow cho mỗi nick:** Mỗi nick chỉ được tham gia tối đa **1–2 phiên follow/ngày** (mục tiêu 5–8 follow/ngày).
2. **Sau khi hoàn thành chỉ tiêu follow:** Các batch nuôi sau trong ngày của máy đó chỉ chạy thuần túy **kịch bản Feed (lướt video, thả tim)**, không gọi follow hook nữa để bảo vệ an toàn cho nick.
3. **Khi dính `FOLLOW_FAILED`:**
   - Dừng follow ngay lập tức.
   - Ghi nhận cooldown riêng theo từng nick (`follow_state_<máy>_row_<index>.json`).
   - Tự động đóng app TikTok, xóa Recent Apps và đưa máy về màn hình chính (Home).
