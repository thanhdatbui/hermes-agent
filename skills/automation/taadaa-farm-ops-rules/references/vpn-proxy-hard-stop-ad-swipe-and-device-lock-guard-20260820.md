# Quy Chuẩn Hard-Stop Khi Lỗi VPN/Proxy, Vuốt Lên Bỏ Qua Quảng Cáo & Tuân Thủ Khóa Thiết Bị Liên Tiến Trình (20/08)

## 1. QUY TẮC SỐNG CÒN: Lỗi Hạ Tầng VPN / Proxy ➔ DỪNG HẲN MÁY, CẤM LƯỚT TIẾP LỘ IP
- **Hiện tượng**: ViChanger báo lỗi `GET_IP failed`, proxy dead/unreachable, hoặc `tun0` down.
- **Nguyên tắc**: 
  - Mất kết nối VPN đồng nghĩa máy đang sử dụng IP thật trực tiếp của mạng farm.
  - Mọi hành động mở TikTok, lướt feed hay gửi lệnh ADB thao tác app lúc này đều làm lộ IP thật và dẫn đến chết dàn tài khoản hàng loạt.
  - **Bắt buộc**: Dừng ngay lập tức toàn bộ tiến trình trên máy, TUYỆT ĐỐI CẤM auto-resume hay thử lướt tiếp khi chưa có VPN an toàn.

## 2. QUY TẮC XỬ LÝ QUẢNG CÁO (SPONSORED / OVERLAY) & POPUP LẠ
- **Nguyên tắc xử lý**:
  - Gặp video quảng cáo dạng Sponsored, phiếu khảo sát, CTA ("Tìm hiểu thêm", "Xem ngay", "Mua ngay") hoặc overlay: **Ưu tiên hàng đầu là VUỐT LÊN (Swipe Up)** như thao tác lướt video bình thường của người dùng thật.
  - Nút "Đóng" (X) hoặc "Hủy" chỉ đóng vai trò là **fallback phụ** khi thao tác vuốt không giải phóng được màn hình.

## 3. QUY TẮC VUỐT RETRY 2 LẦN KHI KẸT MÀN HÌNH KHÔNG NHẬN DIỆN ĐƯỢC
- **Nguyên tắc**:
  - Khi script gặp màn hình lạ chưa có trong allowlist hoặc classifier chưa nhận diện được, script BẮT BUỘC thực hiện **vuốt lên retry tối đa 2 lần** (`_swipe_recovery_on_stuck`).
  - Nếu sau 2 lần vuốt mà máy trở lại Feed (FYP/Following/Friends) ➔ Ghi nhận thành công và tiếp tục phiên nuôi bình thường.
  - Chỉ khi sau 2 lần vuốt vẫn kẹt cứng thì mới chuyển sang trạng thái manual review / giữ hiện trường gửi alert.

## 4. QUY TẮC TUÂN THỦ KHÓA THIẾT BỊ LIÊN TIẾN TRÌNH (CROSS-PROJECT DEVICE LOCK)
- **Nguyên tắc**:
  - Trước khi AI Auto-Recovery can thiệp vào bất kỳ thiết bị nào, BẮT BUỘC gọi `inspect_device_lock(machine)`.
  - Nếu thiết bị đang bị giữ lock bởi tiến trình khác (botmail, hotmail, reg gmail, reg tiktok...) ở trạng thái `running`, `queued`, `recovery`, `failed_locked`:
    ➔ **AI Auto-Recovery BẮT BUỘC BỎ QUA VÀ DỪNG NGAY**, tuyệt đối không gửi bất kỳ lệnh ADB nào can thiệp tranh chấp tài nguyên thiết bị.
