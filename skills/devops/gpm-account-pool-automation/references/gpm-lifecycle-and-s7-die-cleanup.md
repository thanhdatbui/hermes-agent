# Quy trình đồng bộ vòng đời GPM & Dọn Gmail DIE trên thiết bị S7

## 1. Đồng bộ Profile GPM (gpm-lifecycle-sync)
- **CẤM XÓA PROFILE GPM KHI GMAIL DIE (QUY TẮC BẢO TOÀN TÀI SẢN)**:
  - **TUYỆT ĐỐI KHÔNG XÓA PROFILE GPM**: Không được bật hay thiết kế logic tự động xóa profile GPMLogin khi Gmail gắn kèm bị `DIE`, `BAN`, hoặc `SUSPENDED`.
  - **Lý do**: Profile GPM thường đã được verify số điện thoại tốn tiền (5sim / SMS OTP), liên kết dịch vụ trả phí (OpenAI / Codex / API pool), hoặc lưu session / token quan trọng. Xóa profile GPM sẽ làm mất trắng tài khoản và chi phí đã đầu tư.
  - Profile GPM cho dù Gmail die vẫn phải giữ nguyên trên hệ thống để tái sử dụng, giữ token OpenAI/Codex hoặc audit.
- **Tạo Profile LIVE mới**:
  - Quét các tài khoản `LIVE` chưa có profile trong `profile_data.db`.
  - Lấy proxy chuẩn từ `PROXYgandienthoai.xlsx` theo số máy (`mid`).
  - Gọi API `POST /api/v3/profiles/create` với tên chuẩn: `{mid:02d} - {email} - {port}` và `group_id = 1`.

## 2. Dọn dẹp Gmail DIE trên thiết bị S7 (S7 Rolling Cleanup)
- **Vấn đề**: HĐH Android trên S7 giới hạn 4-5 tài khoản Google. Gmail DIE không dọn sẽ kẹt slot và gây popup Google Play Services liên tục.
- **Điểm rơi cuốn chiếu tối ưu**:
  1. **07:15 - 08:15**: Ngay sau cron `daily-manual-stock-checklive` (07:00) và TRƯỚC KHI chạy bật 2FA Gmail (`post-morning-gmail-2fa-watchdog` 08:30).
  2. **13:30 - 14:30**: TRƯỚC chuỗi Reg Gmail chiều (`post-noon-chain-watchdog` 14:30) để nhả slot cho việc tạo acc mới.
- **Kỷ luật an toàn thiết bị (3 Tầng Guard)**:
  - **Tầng 1**: Bắt buộc kiểm tra `is_feed_runner_active()` -> né toàn bộ ca nuôi feed.
  - **Tầng 2**: Kiểm tra manifest buffer: cách ca nuôi tiếp theo ít nhất 45 phút (`MIN_IDLE_BUFFER_MIN = 45`).
  - **Tầng 3**: Kẹp khóa độc quyền bằng `automation_core.device_lock`:
    ```python
    from automation_core.device_lock import acquire_device_lock
    with acquire_device_lock(machine=str(machine_id), serial=serial, project="gpm-cleanup"):
        # Mở Cài đặt -> Đồng bộ tài khoản -> Xóa tài khoản Google DIE
    ```
  - **Non-blocking bypass**: Nếu máy A đang bị giữ lock, lập tức bỏ qua máy A để dọn máy B/C đang rảnh; tick sau quay lại cuốn chiếu.
