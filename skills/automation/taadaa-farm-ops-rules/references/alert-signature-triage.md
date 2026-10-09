# Batch Alert Signature & Error Triage Reference

## 1. Nguyên Tắc Phân Tích Lỗi Khi Nhận Alert (Anti-Defensive Reporting)
Khi nhận Batch Alert chứa signature lỗi cụ thể (ví dụ: `detector-miss:network/error/retry marker detected`):
1. **Giải thích trực tiếp ý nghĩa của Signature ngay từ đầu:**
   - Signature đó tương ứng với mã lỗi nào trong code?
   - Chuỗi text / marker nào trên màn hình đã kích hoạt lỗi này?
   - Tại sao script lại dừng phiên khi gặp lỗi đó? (ví dụ: script dừng chủ động để bảo vệ nick, tránh quẹt mù khi video không nạp được nội dung).
2. **CẤM báo cáo kiểu lảng tránh / phòng thủ:**
   - CẤM vội vàng kết luận "tất cả máy đều bình thường, proxy live" mà không giải thích lỗi hệ thống vừa cảnh báo.
   - Luôn đặt câu hỏi: "Cảnh báo này nói về lỗi gì, tại sao nó xuất hiện lúc chạy batch?".

## 2. Danh Mục Các Signature Blocker Thường Gặp (Feed / Multi-Machine)
- `detector-miss:network/error/retry marker detected`:
  - Mã nội bộ: `manual-needed:network` (trong `core/classifier.py` và `core/safety.py`).
  - Kích hoạt bởi: Màn hình TikTok chứa text "Thử lại", "Lỗi mạng", "Không có kết nối Internet", "Try again", "Retry".
  - Hành động recovery tự động của script: Thử sleep 2s, tìm popup dismiss, thử force-stop app rồi khởi động lại 1 lần. Nếu màn hình vẫn kẹt -> Dừng phiên với stop_reason `network/error/retry marker detected`.
- `manual-needed-popup`: Xuất hiện popup ngoài dự kiến chưa có handler dismiss.
- `login-gms-verification`: Màn hình vướng login, account picker hoặc Google/GMS verification.
- `capture-invalid`: Lỗi chụp màn hình ADB hoặc UI dump không hợp lệ.
- `focus-device-issue`: App bị văng khỏi foreground hoặc mất kết nối ADB / device lock.
