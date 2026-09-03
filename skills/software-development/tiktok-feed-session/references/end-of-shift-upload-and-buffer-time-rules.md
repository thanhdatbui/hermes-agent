# Đánh giá Đăng Video Đồng Loạt Cuối Ca & Quy tắc Buffer Time Giữa Các Ca (2026-08-25)

## 1. Đánh giá Đăng Video Đồng Loạt (Cuối Phiên 3)
- **Thuật toán & Trust Score:** Rất tốt cho tài khoản vì mô phỏng đúng hành vi người dùng thật: Lướt feed, tương tác, xem video (Phiên 1, 2, đầu Phiên 3) rồi mới đăng video ở cuối ca.
- **Tần suất chuẩn:** Mỗi tài khoản đăng 1 video/ngày vào khung giờ cố định của ca nuôi đó, trải đều qua 3 ca (Sáng - Chiều - Tối).
- **Kiểm soát kỹ thuật Farm:**
  - Không bắn lệnh upload đồng thời cùng 1 giây: Lệnh kết thúc phiên 3 tự nhiên có độ lệch 5–15 phút giữa các máy.
  - Khi chạy batch upload độc lập, script bắt buộc duy trì tối đa 16 máy song song và stagger 2–8s để không làm nghẽn bus ADB và băng thông proxy/VPN.

## 2. Quy tắc Buffer Time Giữa Các Ca (Chống Xung Đột Device Lock)
- **Thời gian đệm tối thiểu:** Giữa thời điểm kết thúc đăng video của ca trước và giờ bắt đầu của ca sau phải cách nhau tối thiểu **30–45 phút**.
- **Nếu cách < 30 phút hoặc sắp đến giờ Cron ca sau:**
  - **CẤM CHẠY BÙ UPLOAD:** Không được kích hoạt batch upload bù khi chuẩn bị đến giờ cron của ca tiếp theo.
  - **Hậu quả nếu chạy đè:** 
    1. Tranh chấp Device Lock: Máy upload giữ lock `tiktok-upload`, cron ca sau (Feed) sẽ bị chặn `SKIPPED_LOCKED` và bỏ lỡ phiên nuôi đầu tiên.
    2. Loạn Account Session: Ca trước đang switch/giữ nick của Row N (vd Row 2), ca sau lại mở nick của Row M (vd Row 1) gây lỗi nhận diện tài khoản (`profile account mismatch`).
  - **Quy tắc:** Thỉnh thoảng 1 nick lỡ nhịp không đăng video 1 ngày hoàn toàn không ảnh hưởng đến độ trust; ưu tiên giữ sạch phiên chạy của ca tiếp theo đúng giờ.
