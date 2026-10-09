# Quy định giao tiếp và trình bày báo cáo chốt phiên (Anti-Clutter Protocol)

## 1. Nguyên tắc chống xả rác kỹ thuật (Anti-Clutter & Clean Chat)
- **Tuyệt đối cấm xả raw output**: Không được để các thông báo tiến trình nền (`[Background process finished with exit code...]`), stdout/stderr thô, JSON điểm số dài ngoằng hoặc lỗi bash trực tiếp xuất hiện trên màn hình chat Telegram của User.
- **Tắt thông báo nền máy móc**: Luôn đảm bảo `display.background_process_notifications` là `off` hoặc `none` khi chạy các lệnh kiểm tra tự động nền.
- **Không spam các vòng lặp sửa lỗi trung gian**: Khi Closeout Gate trả về điểm chưa đạt (Score < 85 hoặc REJECTED), Coordinator và Worker phải tự động lặp sửa bài trong âm thầm, KHÔNG bắn các lỗi trung gian ra chat làm hoang mang User.

## 2. Chuẩn mực báo cáo chốt phiên
Khi chốt phiên hoàn tất, chỉ gửi **1 báo cáo tổng kết duy nhất** bằng tiếng Việt chuẩn mực:
- **Tiêu đề & Trạng thái**: Đã chốt phiên thành công (APPROVED) với điểm số (ví dụ: 85/100).
- **Nội dung thực hiện**: 2-3 gạch đầu dòng tóm tắt các tính năng/sửa đổi cốt lõi đã hoàn thành.
- **Bằng chứng xác thực**: Số lượng test đã passed và commit SHA đã push lên remote.
- **Ngôn ngữ**: Trình bày rành mạch, ngắn gọn, dùng ngôn từ dễ hiểu, tránh thuật ngữ nội bộ của LLM/máy móc.
