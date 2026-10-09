# Kỷ Luật Khóa 2 Chiều Giữa Add 2FA Và Các Script Khác Trên Farm (21/09/2026)

## 1. Sự cố xung đột giữa Add 2FA và Test Reg
- Khi tiến trình Add 2FA (`tiktok-add-bao-mat-f2a`) đang giữ máy và điều hướng trong màn hình Authenticator App hoặc popup đổi mật khẩu, Coordinator hoặc các script khác (như `social_reg_v1.py`) nếu chạy mà không check lock chuẩn sẽ nhận định nhầm là máy bị kẹt và tự ý `force-stop` + `input keyevent 3`.
- Hành động này làm đứt gãy hoàn toàn luồng lấy Secret Key và rotate pass của nick trên máy đó.

## 2. Invariant vận hành bảo vệ tiến trình Add 2FA
1. **Tiến trình Add 2FA luôn sở hữu `machine_<N>.lock.json`**:
   - Add 2FA tạo lock `user_authorized=True` tại `~/.codex/device-locks/`.
   - Các script khác khi chạy bắt buộc phải kiểm tra và skip ngay lập tức nếu thấy file lock này tồn tại với PID còn sống.
2. **Quyền hạn `force-stop`**:
   - Chỉ có tiến trình sở hữu lock mới được phép `force-stop` TikTok trên máy đó để reset app.
   - Cấm mọi lệnh ADB can thiệp từ bên ngoài khi máy đang trong ca 2FA.
3. **Cơ chế Reaper 1h tự động dọn dẹp**:
   - Nếu tiến trình 2FA bị crash hoặc treo quá 1 giờ (3600s), script `reap-dead-owner-locks.py` sẽ tự động chuyển lock vào thư mục cách ly và dọn dẹp app về Home.
   - Không cần và cấm Coordinator tự ý can thiệp giải phóng lock thay cho Reaper.
