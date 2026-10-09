# Thiết lập máy phụ Admin (200+) & Cấp quyền mua Hotmail tự động

## 1. Khởi tạo dữ liệu Admin chống TARGET_INVENTORY_EMPTY (2026-09-04)
- Khi thiết lập máy phụ Admin (dải 200–999), file `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx` ban đầu nếu rỗng (chỉ có header) sẽ khiến bộ quét `_detect_clean.py` fail-closed với lỗi `TARGET_INVENTORY_EMPTY`.
- **Cách xử lý chuẩn:**
  - Trích xuất danh sách thiết bị từ `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx` (80 máy từ 201 đến 280) và populate vào sheet `Accounts` của `taikhoan_run_safe.xlsx`.
  - Cấu trúc cột: `['May', 'Device ID', 'ID', 'Video Đã Đăng']` với `ID=None`, `Video Đã Đăng=0`.

## 2. Cấp quyền mua Hotmail tự động cho máy phụ (2026-09-04)
- Máy Admin không có quyền truy cập trực tiếp web mua hay vốn nạp riêng; mọi tài khoản mua qua BoxTaiKhoan API.
- **Thông số BoxTaiKhoan API:**
  - Auth API Key: `a0ed850f635d5c7042e89f68b41476bb` (cấu hình qua biến môi trường `BOXTAIKHOAN_API_KEY`).
  - Kiểm tra số dư / Profile: `GET https://boxtaikhoan.com/api/profile.php?api_key=<key>` trả về `status: success`, `username` và `money`.
  - Endpoint mua tự động: `POST https://boxtaikhoan.com/ajaxs/client/product.php` (id 60 - Hotmail OAuth2 393đ).
  - Tham số Form POST: `action=buyProduct`, `id=60`, `variant_id=0`, `amount=1`, `coupon=''`, `api_key=<key>`, `user_input='{}'`.
  - Headers bắt buộc: `User-Agent`, `X-Requested-With: XMLHttpRequest`, `Content-Type: application/x-www-form-urlencoded`.
  - Format trả về: `mail|pass|refresh_token|client_id`. Khi mua số lượng lớn, BẮT BUỘC gọi API mua lẻ từng acc (`amount=1`) qua vòng lặp để nhận trực tiếp mảng `data` JSON đầy đủ 450–525 ký tự token.
  - Microsoft Graph Token Verification: Gọi `POST https://login.microsoftonline.com/consumers/oauth2/v2.0/token` (`grant_type=refresh_token`, `client_id`, `refresh_token`, `scope=https://graph.microsoft.com/.default offline_access`), kiểm tra HTTP 200 và có `access_token` mới ghi nhận hợp lệ 100%.
- **Vị trí đồng bộ Tool:**
  - Tool CLI `buy_hotmail.py` được đồng bộ sang `D:\Taadaa\tools\` (thông qua OneDrive NTFS junction `%ONEDRIVE_SHARED%\tools` -> `D:\Taadaa\tools`) và các repo (`Hotmail\tools\`, `AI-Tools\tools\`).
  - Máy Admin chỉ cần chạy lệnh `python D:/Taadaa/tools/buy_hotmail.py --append-admin <N>` để tự động mua, xác thực Microsoft Graph Token và nạp thẳng vào `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx`.

## 3. Pitfalls cài đặt môi trường trên Admin (`link_shared_to_admin.bat`)
- **Escape ký tự trong Batch:**
  - Tránh để `\tools` bị dính ký tự Tab `\t` làm sai lệnh rmdir/mklink.
  - Tránh để `\admin.yaml` bị nuốt mất `\a` thành `dmin.yaml` làm sai biến hệ thống `TAADAA_HOST_CONFIG`.
- **Runtime directory:**
  - Bắt buộc có lệnh `if not exist "D:\Taadaa\runtime\admin" mkdir "D:\Taadaa\runtime\admin"` vì runtime root không được chia sẻ qua OneDrive mà phải tạo cục bộ trên từng host.

## 4. Quy tắc bảo toàn tên file dữ liệu trên Host phụ Admin (CẤM ĐỔI TÊN) (2026-09-05)
- **Vấn đề:** Các tên file dữ liệu do lịch sử Codex đặt tên khá lộn xộn (`gmail_clean_v2.xlsx`, `taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx` có dấu cách). Người vận hành có thể muốn đổi tên cho gọn hoặc đúng nghĩa hơn trên máy Admin.
- **Quy tắc bắt buộc:** **TUYỆT ĐỐI CẤM ĐỔI TÊN** các file này trên Admin hay bất kỳ host phụ nào.
- **Lý do kỹ thuật:**
  1. Hơn 10 repo trong farm (`Tiktok_Reg`, `Hotmail`, `tiktok-video`, `tiktok-follow`, `automation-core`, `taadaa_host.py`...) đều hardcode/reference mặc định theo đúng các tên file này.
  2. Việc phân tách dữ liệu 2 máy đã được giải quyết triệt để và an toàn 100% bằng đường dẫn thư mục cha:
     - Kibe: `D:\OneDrive\TaadaaData\kibe\`
     - Admin: `D:\OneDrive\TaadaaData\admin\`
  3. Đổi tên riêng trên Admin sẽ phá vỡ tính tương thích chéo (`portable`), gây crash `FileNotFoundError` toàn bộ runners khi Admin kéo code về.

## 5. Cài đặt bộ APK tự động cho Farm (`install_farm_apks.py`) (2026-09-05)
- **Kho APK nguồn trên OneDrive:** `D:\OneDrive\apk-bank\`
  - Outlook: `D:\OneDrive\apk-bank\com_microsoft_office_outlook\` (`com.microsoft.office.outlook`)
  - ViChanger: `D:\OneDrive\apk-bank\vn_vichanger_app\base.apk` (`vn.vichanger.app`)
  - TikTok (Split APK 50 file): `D:\OneDrive\apk-bank\com_ss_android_ugc_trill\` (`com.ss.android.ugc.trill`)
- **Tool tự động hóa:** `D:\Taadaa\tools\install_farm_apks.py` (đồng bộ qua OneDrive Junction và repo `AI-Tools\tools\`).
- **Cơ chế hoạt động:**
  - Tự động nhận diện đường dẫn ADB (`xiaowei` hoặc PATH).
  - Pre-check kiểm tra gói cài (`pm path`), tự động skip các app đã có (`[SKIP_INSTALLED]`) để tiết kiệm thời gian, dùng `--force` khi cần cài đè.
  - Hỗ trợ cài cho 1 máy (`--stt 201` hoặc `--device <serial>`), hoặc cài song song đa luồng cho toàn bộ máy đang cắm cáp (`--all`).
  - Hỗ trợ `install-multiple -r` cho bộ Split APK TikTok.

## 6. Pitfall STT 201+ bị chặn trong `social_reg_v1.py` (2026-09-05)
- **Vấn đề:** Trong `social_reg_v1.py`, mảng `ACCOUNTS` chỉ hardcode dải máy STT 1..80 của Kibe. Khi máy Admin chạy `social_reg_v1.py 201 --ss`, script tìm trong `ACCOUNTS` không thấy nên thoát ngay với thông báo `Không có STT 201`.
- **Giải pháp chuẩn:** Khi `acc` không tìm thấy trong `ACCOUNTS`, script BẮT BUỘC fallback động:
  - Tra cứu `resolve_machine_device(stt, TARGET_INVENTORY_WORKBOOK)` từ `taikhoan_run_safe.xlsx` của Admin để lấy device serial ADB thật.
  - Tự động tạo `acc = {"stt": stt, "device": resolved_device, "email": preferred_email or "", "pass": ""}` để luồng reg tiếp tục bình thường cho toàn bộ dải máy 200+.
