# Rerun Safety & Platform Block Discipline (Script Errors vs Anti-Bot Blocks)

## 1. Phân Biệt Tuyệt Đối Giữa Lỗi Script vs Lỗi Nền Tảng Chặn

Khi vận hành hệ thống farm Android (đăng ký Gmail, đăng ký TikTok, login, nuôi acc):

### Nhóm A: Lỗi Code / Script Logic (ĐƯỢC PHÉP CHẠY LẠI SAU KHI SỬA CODE)
- **Định nghĩa:** Lỗi phát sinh do script tự động hóa chưa xử lý đúng tình huống UI, format dữ liệu, hoặc cú pháp lệnh ADB.
- **Ví dụ cụ thể:**
  1. Chuỗi Họ/Tên nhiều từ có khoảng trắng bị lệnh `adb shell input text` phân tách đối số gây lỗi `Invalid arguments for command: text` và bỏ trống input field.
  2. Chưa có vòng lặp retry đổi username khi Google báo trùng (`Username bị taken`).
  3. Stale marker trong cache kiểm tra readiness khiến script tưởng nhầm proxy bị treo.
  4. Selector UI chưa cập nhật theo phiên bản app mới.
- **Quy trình xử lý:**
  - Sửa mã nguồn trong codebase / automation-core.
  - Viết unit test cô lập xác minh logic.
  - Chạy Live Canary trên 1 máy kiểm chứng thành công.
  - Sau khi kiểm chứng thành công mới được kích hoạt chạy lại cho các máy bị ảnh hưởng bởi lỗi script này.

---

### Nhóm B: Lỗi Nền Tảng Chặn / Anti-Bot (TUYỆT ĐỐI CẤM TỰ Ý CHẠY LẠI)
- **Định nghĩa:** Lỗi do Google, TikTok hoặc dịch vụ máy chủ chủ động chặn yêu cầu tạo tài khoản / đăng nhập dựa trên tín hiệu phát hiện bot, blacklist dải IP proxy, hoặc fingerprint thiết bị.
- **Ví dụ cụ thể:**
  1. **Google bắt xác minh số điện thoại (`PHONE_VERIFY`):** Google yêu cầu nhập SĐT nhận OTP để tiếp tục đăng ký.
  2. **Google từ chối tạo tài khoản (`ACCOUNT_CREATION_ERROR`):** Thông báo *"Không thể tạo tài khoản Google"* sau bước nhập mật khẩu do IP/thiết bị bị rate-limit.
  3. **TikTok CAPTCHA cứng / Device Banned:** TikTok chặn đăng ký ngay từ màn đầu.
- **Quy tắc vận hành nghiêm ngặt:**
  - **CẤM TỰ Ý CHẠY LẠI:** Tuyệt đối không tự kích hoạt chạy lại hoặc đề xuất chạy lại các máy này trong cùng phiên/dải IP.
  - **Lý do:** Cố tình spam chạy lại khi đã bị nền tảng gắn cờ sẽ làm nát dải IP proxy, làm bẩn fingerprint của máy và tăng nguy cơ bị ban hàng loạt (cascading ban).
  - **Hành động đúng:** Ghi nhận lỗi và phân loại rõ ràng (ví dụ: `PHONE_VERIFY`, `ACCOUNT_CREATION_ERROR`), cách ly máy và để máy nghỉ cooldown (thay proxy / chờ qua ca khác).

---

## 2. Quy Chuẩn Báo Cáo Batch Rerun
Khi báo cáo kết quả chạy lại hoặc tóm tắt batch:
- Chỉ báo cáo ngắn gọn theo cấu trúc: `Mục đích → Kết quả (Success / Fail + Mã lỗi) → Blocker`.
- Tách bạch rõ:
  - Máy thành công (`SUCCESS`).
  - Máy dừng do chính sách nền tảng (`PHONE_VERIFY`, `ACCOUNT_CREATION_ERROR`) $\rightarrow$ Khẳng định không chạy lại.
  - Máy bị lỗi phần cứng/mất kết nối vật lý (cáp USB/ADB).
