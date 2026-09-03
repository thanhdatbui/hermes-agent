# Avatar Upload Flow Optimization & Reboot Proxy Bypass (2026-09-03)

## 1. Phân biệt `ACCOUNT_MISSING` với "Tạo/Up avatar sai"
- **Hiện tượng:** User thấy nick trên máy chưa có avatar hoặc profile trống và nghi ngờ: *"acc này tạo ra bị sai hay sao up ava sai luôn r"*.
- **Quy trình triage:**
  1. Kiểm tra file avatar gốc: `D:\video goc\<video gốc>\avatar.jpg` và `D:\TIKTOK-videonuoinick\<Folder>\avatar.jpg`. Nếu cả hai file đều tồn tại, kích thước 512x512 JPEG hợp lệ thì **avatar không bị sai**.
  2. Kiểm tra log batch trước đó (`machine-<N>.out.log`): Tìm dòng lỗi cuối. Nếu kết thúc tại `ACCOUNT_SWITCHER_FAILED: ACCOUNT_MISSING`, nguyên nhân thực sự là nick chưa được đăng nhập / chưa có trong switcher TikTok của máy, khiến workflow dừng sớm trước khi tới `ENSURE_AVATAR`.

## 2. Tối ưu hóa thứ tự nạp Media trong `ENSURE_AVATAR` (`AVATAR_UPLOAD_MENU_MISSING`)
- **Vấn đề:** Thiết kế cũ mở menu "Thay đổi ảnh" trước rồi mới tiến hành xóa cache, push avatar và gọi `refresh_media_library` (~30-40s). Trong lúc đó, bottom sheet trên TikTok bị timeout hoặc đóng lại do broadcast MediaScanner, dẫn đến lỗi `AVATAR_UPLOAD_MENU_MISSING: Không tìm thấy Tải ảnh lên`.
- **Giải pháp:**
  - Thực hiện dọn rác, push file `/sdcard/Pictures/av_...jpg`, touch file và refresh MediaStore **TRƯỚC** khi chạm vào `Thay đổi ảnh` / avatar circle `(540, 400)`.
  - Khi menu mở ra, chạm ngay vào `Tải ảnh lên` / `Thư viện` / `g9u`.
  - Nếu menu bị trôi, tự động tap lại avatar circle `(540, 400)` để re-open bottom sheet.

## 3. Gộp Polling đa Selector cho nút Tiếp trong Picker (`AVATAR_SELECTION_FAILED`)
- **Vấn đề:** Khi gọi `_wait_for_element` tuần tự 6 lần cho từng selector (`o_9`, `Tiếp (1)`, `wrj`, `Tiếp`, `Next`, `Lưu và đăng`) với `timeout=60` mỗi lần:
  - Tổng thời gian chờ lên đến 360 giây (6 phút), dump UI liên tục làm quá tải daemon ATX trên Samsung S7 và gây nghẽn toàn batch.
  - Một số build TikTok dùng resource-id `xip`, `rts`, `sca` hoặc nút tại tọa độ `(924, 1842)`.
- **Giải pháp:**
  - Gộp tất cả selector vào một vòng lặp polling duy nhất 25s (`deadline = time.time() + 25.0`), mỗi tick chỉ dump UI 1 lần và quét toàn bộ danh sách `("o_9", "xip", "wrj", "rts", "qii", "rou", "sca")` cùng các text biến thể.
  - Bổ sung fallback tap tọa độ `(924, 1842)` khi màn hình chọn ảnh vẫn còn hiển thị.

## 4. Gỡ bỏ Gate Proxy Watcher khi Soft Reboot trên Farm Wi-Fi Router Proxy
- **Vấn đề:** Trong `state_machine.py`, hàm `restore_proxy_after_reboot` vẫn gọi `wait_for_proxy_ready` và `require_android_vpn(adb, required=True)`, gây lỗi `proxy readiness timed out` khi máy thực hiện soft reboot recovery.
- **Giải pháp:** Khi farm chạy qua Wi-Fi Router Proxy (MikroTik / Singbox), `proxy_handoff` là `None`, bypass hoàn toàn việc chờ proxy-watcher và kiểm tra VPN `tun0` để máy tiếp tục workflow.
