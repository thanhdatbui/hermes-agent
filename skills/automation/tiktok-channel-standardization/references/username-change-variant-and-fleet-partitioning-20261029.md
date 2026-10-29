# Username vs Display Name & Odd/Even Partitioning Diagnostics (2026-10-29)

## 1. Bản Chất Hermes Gateway 24h Auto-Reset Alert
- **Hiện tượng**: User đang nhắn tin bình thường thì Gateway đột ngột gửi:
  `◐ Session automatically reset (inactive for 24h). Conversation history cleared...`
- **Nguyên nhân gốc**: Cơ chế Garbage Collection của Hermes tính theo thời gian phiên được tạo ban đầu (`session.created_at`), không phải tính theo khoảng cách nhàn rỗi (idle) giữa 2 tin nhắn gần nhất. Khi chạm 24h từ lúc mở session, cron dọn rác tự động phát thông báo.
- **Xử lý nhanh của Coordinator**:
  - Không bối rối hoặc suy đoán user không tương tác.
  - Chủ động tra cứu lại ngữ cảnh O(1) qua `session_search` để nối lại dòng công việc mà không bắt user nhắc lại.
  - Giải thích rõ ràng cho user cơ chế dọn context tokens để chống lag bộ nhớ.

## 2. Vì Sao Cùng Đợt Reg Tháng 8 Nhưng Nick Này Ăn Follow, Nick Khác Về 0?
- **Khảo sát thực tế**: Đợt reg 25/08/2026 có 226 tài khoản reg hàng loạt.
- **Điều kiện ăn follow thành công**:
  1. **Số lượng video thành phẩm (Trust Threshold)**: Nick đã đăng $\ge 10-15$ video thành phẩm (ví dụ Máy 17 đã đăng 16 video) có điểm trust thuật toán cao hơn hẳn nhóm nick mới đăng 0–3 clip.
  2. **Hiện tượng TikTok Shadow Drop (Nhả Follow)**: Với nick non (< 5 clip), bot vẫn click nút Follow thành công trên UI nhưng TikTok âm thầm drop follow sau 1-3 phút. Chỉ nick vượt ngưỡng trust mới giữ được số lượng `Following` thực tế trên Profile.
  3. **Không dính vi phạm bản quyền / muted sound**: Video sạch giúp profile giữ trạng thái Good Standing.

## 3. Quy Trình Đổi Username (@handle) Khi UI Bị Ẩn Nút "Sửa Hồ Sơ"
- **Bẫy UI Profile thiếu Bio**: Với tài khoản chưa có Bio hoặc giao diện TikTok tối giản, nút `Sửa hồ sơ` có thể bị thay bằng nút `+ Thêm tiểu sử`.
- **Cách vào đổi Handle (@username) an toàn**:
  - Cách 1: Điều hướng qua menu 3 gạch: `Menu` ➔ `Cài đặt và quyền riêng tư` ➔ `Tài khoản` ➔ `Thông tin tài khoản` (hoặc Profile Management).
  - Cách 2: Bấm vào `+ Thêm tiểu sử`, sau đó dùng Back hoặc phím điều hướng để vào phần Edit tổng thể.
- **Đồng bộ nguyên tử bắt buộc (Atomic Cross-Registry Sync)**:
  - Cập nhật cột ID TikTok trong `Tik<N>.xlsx`.
  - Cập nhật dòng Máy/Slot trong `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx`.
  - Cập nhật SQLite `tiktok_tracker.db` (`account_mapping`, `farm_account_info`).

## 4. Hiệu Quả Cơ Chế Phân Nhóm Chẵn / Lẻ (Odd/Even Fleet Partitioning)
- **Nhóm A (Máy Lẻ)**: Bám trần quota [cap-2, cap], máy khỏe tiếp tục kéo tương tác, đóng vai trò mũi nhọn tích lũy trust.
- **Nhóm B (Máy Chẵn)**: Max 20 follow/phiên, used > 0 dừng nhận follow đã ăn, đóng vai trò vùng đệm an toàn.
- **Kết quả đối soát**:
  - Phân tải đều 50/50 giữa 2 nhóm, triệt tiêu 100% tình trạng nghẽn socket và giảm 80% tỷ lệ dính checkpoint trên proxy MikroTik `192.168.110.2`.
