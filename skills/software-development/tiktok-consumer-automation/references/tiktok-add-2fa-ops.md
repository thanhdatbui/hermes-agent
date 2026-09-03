# TikTok Add 2FA (Security) Automation Reference

Quy chuẩn và lưu ý khi vận hành add 2FA (Xác minh 2 bước) cho farm TikTok (repo `D:\Taadaa\tiktok-add-bao-mat-f2a`).

## 1. Cơ chế Target & Filter Ưu tiên
- **Workbook chính:** `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (Sheet: `Tài Khoản`).
- **Proxy mapping:** `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`.
- **Dải máy farm:** Hỗ trợ 1-80 (`_machine` validation).
- **Tiêu chí acc cổ (Row 1 & Row 2):**
  - Cột `Máy` từ 1-80.
  - Cột `ID` có giá trị username hợp lệ.
  - Cột `2FA` còn trống (chưa bật 2FA).
  - Slot 1 hoặc Slot 2 tương ứng với 2 dòng đầu tiên của mỗi máy trong sheet `Tài Khoản`.

## 2. Quy trình Preflight & Lock Safety
- **Lock-first:** Phải acquire central device lock (`acquire_device_lock`) trước khi thực hiện bất kỳ thao tác ADB/UI nào trên thiết bị. Giữ nguyên lock trong suốt quá trình chạy.
- **VPN Preflight:** `require_android_vpn(client, required=True)` kiểm tra `tun0`, proxy IP live qua ViChanger trước khi vào TikTok.
- **ATX Session Capture:** Đảm bảo `atx-agent` (port 7912) hoạt động, dump UI qua ATX session.

## 3. Quy tắc xử lý khi dừng/lỗi
- Nếu gặp lỗi navigation/switcher (ví dụ `ACCOUNT_SWITCH_ANCHOR_AMBIGUOUS` khi TikTok đang ở Feed thay vì Profile):
  1. Chụp ảnh screencap màn hình thật (`adb exec-out screencap -p`).
  2. Gửi ảnh dạng `MEDIA:<absolute_path>` ở dòng riêng (không bọc markdown).
  3. Giữ nguyên lock và hiện trường màn hình, dừng lại xin ý kiến user, tuyệt đối không tự ý tap mò hoặc tắt lock.
