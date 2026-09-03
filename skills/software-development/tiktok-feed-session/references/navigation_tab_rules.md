# Quy tắc điều hướng top tab trong Feed Session (Friends / Following / For You)

## 1. Không tìm thấy tab (Friends / Following) trong XML
- Khi script nuôi acc phân bổ đổi feed (`next_feed_type`), nếu target (ví dụ: tab "Bạn bè" / `friends`) không tìm thấy element trên UI/XML (`navigation target friends not found in XML`):
  - **Hành vi chuẩn**: Bỏ qua việc đổi tab, giữ nguyên tab hiện tại (`current_feed_type` hoặc fallback về `for-you`) và tiếp tục vòng lặp vuốt cho đủ số lượng video yêu cầu của phiên.
  - **CẤM**: Không được ngắt phiên / trả về failure làm dừng phiên (`DỪNG PHIÊN`).
