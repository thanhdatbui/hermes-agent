# Quy Tắc Kho Mail & Onboarding Sau Reg TikTok (2026-08-23)

## 1. Kho Mail Live (`gmail_clean_v2.xlsx`)
- `gmail_clean_v2.xlsx` là **kho mail live** của user.
- **Tuyệt đối KHÔNG xóa mail** khỏi `gmail_clean_v2.xlsx` chỉ vì mail đó đã đăng ký TikTok xong.
- Chỉ xóa hoặc chuyển mail sang quarantine khi chạy quy trình **check-live** phát hiện mail thực sự die / mất khỏi máy VÀ chưa gắn với ID TikTok nào trong file tracking.

## 2. Tracking ID TikTok (`taikhoan_dat_v2_updated .xlsx`)
- Khi đăng ký TikTok thành công bằng email nào (cột F `GMAIL`), **bắt buộc phải ghi ID TikTok cùng hàng với mail đó**.
- Không được để việc cập nhật / đổi email sau này làm mất liên kết mail gốc đã dùng để reg.

## 3. Đặt Tên / Biệt Danh Sau Khi Reg (Màn hình "Tên")
- Màn hình form đổi tên hiển thị `Tên` / `Bạn chỉ có thể đổi tên một lần mỗi 7 ngày.` / `Thêm tên bạn mong muốn`.
- Đây là bước đặt biệt danh cho nick sau khi đăng ký xong.
- Quy tắc: Có thể lấy đại 1 tên bất kỳ (hoặc sinh từ tiền tố email/username) điền vào -> Lưu -> Xác nhận đặt biệt danh để hoàn tất profile.

## 4. Tương Tác Giữa Device Lock & Cron Nuôi Acc
- Cron nuôi acc (`hermes_cron_runner`) tự động kiểm tra `C:\Users\Kibe\.codex\device-locks`.
- Khi máy bị lock do đang chạy batch reg, cron nuôi sẽ ghi nhận `SKIPPED_DEVICE_LOCKED` và **bỏ qua duy nhất phiên nuôi đó**, không xung đột hay can thiệp vào máy.
- Giải phóng device lock ngay sau khi reg xong để máy tiếp tục các phiên nuôi tiếp theo trong ngày.
