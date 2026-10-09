# Quy Tắc Vận Hành S7 & Pipeline GPM - OAuth OmniRoute (Kibe Farm)

## 1. Cơ Chế Gỡ Cuốn Chiếu Acc Trên S7 (S7 Rolling Cleanup Preflight)
- **Ngưỡng trần tối đa**: **5 tài khoản Google / 1 máy Samsung S7**.
  - Không giữ quá 5 acc để tránh tràn RAM 4GB, giật lag máy và dính cờ thiết bị (Device Farm Abuse).
  - Không giữ ít hơn (như 2-3 acc) để tận dụng thời gian ngâm tài khoản (Account Aging) lên tới 40-50 ngày trước khi gỡ.
- **Thời điểm kích hoạt**: Bước Preflight Check ngay trước khi bắt đầu bất kỳ batch reg Gmail nào.
- **Điều kiện kiểm tra để gỡ (3 Safety Gates)**:
  - Nếu máy đã đạt trần 5 acc -> Quét tìm acc cũ nhất trên máy (dựa vào ngày reg / ngày đưa lên GPM).
  - Phải thỏa mãn đồng thời 3 Gate:
    1. **Gate 1**: Đã kích hoạt 2FA Google Authenticator (có Secret Key 32 ký tự lưu trong Excel).
    2. **Gate 2**: Đã nạp thành công OAuth Antigravity vào OmniRoute (đã có Refresh Token).
    3. **Gate 3**: Đã ngâm trên GPM Profile tối thiểu **>= 30 ngày**.
  - Nếu thỏa mãn: Dùng lệnh hệ thống ADB trên điện thoại gỡ DUY NHẤT 1 acc cũ nhất đó.
- **CẤM TUYỆT ĐỐI**:
  - Không gỡ qua web `myaccount.google.com/device-activity` trên máy tính (nguyên nhân gây cờ 7 ngày `rrk=77`).
  - Không gỡ dồn dập nhiều acc cùng lúc (tối đa 1 acc / 1 chu kỳ reg).

## 2. Quy Trình Hot-Session Hook: Nạp OAuth OmniRoute Ngay Lập Tức
- **Nguyên tắc**: Login GPM -> Bật 2FA -> **Nạp OAuth OmniRoute NGAY LẬP TỨC** trong cùng profile.
- **Lợi ích**: Tận dụng cookie phiên đăng nhập "nóng" (Active Session). Mở link OAuth Antigravity trong session vừa login thì Google chỉ hiện bảng chọn tài khoản và nút "Cho phép" (Allow), 1 click là lấy được token mà không bị hỏi mật khẩu hay checkpoint.
- **Nếu để chờ**: Cookie nguội, proxy đổi IP sẽ bắt đăng nhập lại từ đầu và tăng nguy cơ gặp reCAPTCHA/challenge.

## 3. Xử Lý Checkpoint SMS (`challenge/iap`)
- **Bản chất**: Tài khoản KHÔNG bị die/disabled. Tài khoản vẫn đang LIVE bình thường trên điện thoại Samsung S7.
- **Xử lý**:
  - Xóa profile rác trên GPM ngay lập tức (`/api/v3/profiles/delete/{id}`) để giải phóng port.
  - Ghi chú trạng thái `CHECKPOINT` vào Excel và status JSON.
  - **Để ngâm hoàn toàn (Cool-down) 3 - 7 ngày**: CẤM bật profile nuôi trong thời gian chờ (tránh làm tăng Suspicious Score).
  - Sau thời gian ngâm và xoay IP, Google thường tự động hạ cấp checkpoint từ đòi SMS sang gửi thông báo xác nhận trên máy S7.

## 4. Bảo Vệ Tên Combo & Model Routing OmniRoute
- **BẤT BIẾN**: Tên combo trên OmniRoute (ví dụ `ag-gemini-pool-3`) là BẤT BIẾN 100%. Tuyệt đối không được đổi tên combo vì sẽ làm crash toàn bộ model routing của các agent.
- **Targets**: Các tài khoản mới thêm vào được đánh nhãn con (`pool-19`, `pool-20`, `pool-30`...) và nối tiếp vào ĐUÔI của combo làm tầng dự phòng/tràn tải.
- **Gán Proxy 1:1**: Luôn gán đúng cổng proxy vật lý tương ứng của máy cho connection ID và sync-models sau khi exchange token thành công.
