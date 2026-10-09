# TikTok Following Tab Empty State False Network Detection & Recovery

## Bối Cảnh Hiện Trường (Sự Cố Row 8 Ngày 2026-09-24)
- Khi chạy kịch bản nuôi acc (`feed-session-smoke` / `multi-machine-feed-session`), sau một số lượt vuốt ở tab For You (FYP), runner thực hiện chuyển sang tab Following ("Đã follow") theo hành vi người dùng tự nhiên (`switch_following`).
- Với các tài khoản mới hoặc tài khoản chưa từng follow ai (following list = 0), TikTok không load được nội dung video và hiển thị màn hình thông báo rỗng:
  - Header: Tiêu đề hoặc danh sách tab.
  - Body: **"Đã xảy ra lỗi"** (`id=com.ss.android.ugc.trill:id/ze3`), **"Vui lòng thử lại."** (`id=com.ss.android.ugc.trill:id/message_tv`).
  - Nút bấm: **"Thử lại"** (`id=com.ss.android.ugc.trill:id/dd9`).
- Tại thời điểm này:
  - Cột sóng Wi-Fi của thiết bị vẫn đầy đủ 3 vạch (`Tín hiệu Wi-Fi ba vạch`).
  - Proxy và kết nối Internet ra ngoài vẫn thông suốt 100%.

## Cạm Bẫy Phân Loại Màn Hình (False-Positive Network Error)
- Module phân loại màn hình `classify_screen` dò tìm chuỗi `"Đã xảy ra lỗi"`, `"Vui lòng thử lại"`, `"Thử lại"`.
- Do trùng khớp với các mẫu thông báo mạng chập chờn, hệ thống gán nhãn:
  `detected_screen: manual-needed:network`, `stop_reason: network/error/retry marker detected`.
- Hậu quả: Script lập tức kết thúc phiên với trạng thái `manual-needed`, ghi nhận sai bản chất sự cố là "mất mạng / rớt proxy", gây hoang mang trong báo cáo Farm Alert.

## Quy Tắc Chẩn Đoán & Khắc Phục Chuẩn (Standard Recovery)
1. **Kiểm tra Step Dừng (Triage O(1))**:
   - Nếu `stop_reason` là `network/error/retry marker detected` nhưng `step` bắt đầu bằng `switch_following` (ví dụ `switch_following_11_navigation_confirm`), đây **99% là lỗi giao diện rỗng của tab Following**, KHÔNG PHẢI mất mạng thật.
2. **Nguyên Tắc Xử Lý (Fallback Về FYP)**:
   - Khi gặp màn hình "Đã xảy ra lỗi / Thử lại" ở ngữ cảnh `switch_following`:
   - TUYỆT ĐỐI CẤM coi đây là rớt mạng làm fail phiên.
   - BẮT BUỘC thực hiện tap fallback về tab **"Đề xuất" (For You)** để tiếp tục lướt hoàn thành đủ quota video còn lại của phiên nuôi.
   - Tránh kiểm tra từ khóa `"Đã follow"` trong `following_terms` một cách lỏng lẻo dẫn đến kẹt back-key vào profile người lạ.
