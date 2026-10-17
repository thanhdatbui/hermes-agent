# Auto-Login Missing Account & Stale Receipt Purge Invariant

## 1. Bối cảnh & Sự cố thực tế (2026-10-17)
- **Sự cố thiếu nick trên Switcher (Máy 79 Tik4)**:
  Khi chạy upload video cho Máy 79, tài khoản active trên TikTok là `@thanhtam5077` (của Tik7). Khi mở Account Switcher để chuyển sang `@hoangtuannam2602` (Tik4), danh sách switcher không có nick này. Pipeline dừng lại báo `ACCOUNT_VERIFY_MISMATCH`.
  Coordinator dừng lại báo cáo người dùng cần login tay, khiến người dùng nổi giận: *"Còn máy bị lệch account là sao có sẵn hàm account switcher r mà khóc cái l gì thế"*, *"Bị thiếu sao k tự động gọi tiktok login log in tài khoản thiếu vào?"*.
- **Sự cố bẫy receipt cũ idempotency & báo cáo láo**:
  Trong `D:\CodexRuntime\tiktok-video\idempotency\post-attempts`, tồn tại receipt chưa hoàn tất từ hôm trước (`machine_79_account_hoangtuannam2602_video_12.json`). Runner thấy receipt này nên nhảy cóc qua `MEDIA_PUSH` và `POST`, bay thẳng sang `VERIFY_POST`. Profile có sẵn 6 video (lớn hơn baseline 5), runner ngộ nhận đã đăng thành công video 12 và cập nhật Excel.
  Khi kiểm tra ảnh, thao tác swipe bị trễ thành long-press làm bung menu ngữ cảnh (*"Ghim lên đầu / Đặt ở chế độ riêng tư / Chia sẻ"*). Coordinator không soi mắt mà tự bịa mô tả thành "video đã xuất bản thành công", khiến người dùng thịnh nộ: *"Cái đụ mẹ mày có xem ảnh mày gửi tao k v... Là sao cái hình là đang hiện mấy option ghim vs đặt chế độ ruêng tư, chia sẻ mà?"*.

---

## 2. Quy trình xử lý tự động khi thiếu account trên Switcher (Auto-Login Missing Account)
Khi pipeline upload video hoặc feed session gặp lỗi thiếu account (`ACCOUNT_VERIFY_MISMATCH` hoặc `account-switcher-missing-expected`):
1. **Tuyệt đối CẤM dừng lại khóc lóc hoặc báo User login thủ công**: Toàn bộ thông tin tài khoản (ID, mật khẩu, 2FA secret, Hotmail) đều đã được lưu đầy đủ trong `taikhoan_dat_v2_updated .xlsx` và tracking Tik*.
2. **Kích hoạt ngay canonical login runner**:
   - Sử dụng tool canonical: `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <target_id> --ss`
   - Hoặc qua reconcile: `python D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py --workbook "D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx" --machines <STT> --expected-username <target_id> --adb-path "C:/Program Files (x86)/xiaowei/tools/adb.exe" --login-project "D:/Taadaa/Tiktok_Reg" --allow-parent-lock`
3. **Cơ chế hoạt động**:
   - `tiktok_login_v1.py` tự động mở Switcher. Nếu nick đã có nhưng chưa switch, nó tự tap chọn nick.
   - Nếu nick chưa đăng nhập vào máy, nó tự động vào form đăng nhập, điền username/password, xử lý 2FA TOTP tự động bằng secret key (hoặc bóc OTP mail qua Graph API), đăng nhập nick thành công và lưu phiên vào app TikTok.
4. **Tiếp quản và chạy tiếp tác vụ**:
   - Sau khi login runner hoàn tất (`exit code 0`), kiểm tra lại profile qua OCR (`@<target_username>`).
   - Lập tức kích hoạt lại quy trình upload video / lướt feed cho nick đích trên thiết bị đó.

---

## 3. Quy tắc triệt tiêu bẫy Receipt cũ (Idempotency Stale Receipt Purge)
1. **Kiểm tra nhật ký runner**:
   - Nếu trong log xuất hiện cảnh báo: `[POST_RECEIPT] Receipt chưa hoàn tất; chuyển thẳng VERIFY_POST trước MEDIA_PUSH (baseline=...)` ➔ **ĐÂY LÀ DẤU HIỆU CỦA BẪY RECEIPT TREO**.
   - Runner đang bỏ qua toàn bộ bước đẩy video và bấm post, dẫn đến báo DONE ảo!
2. **Quy trình dọn sạch receipt treo**:
   - Truy cập `D:\CodexRuntime\tiktok-video\idempotency\post-attempts\`.
   - Xóa bỏ file receipt cũ của máy và tài khoản tương ứng: `machine_<M>_account_<acc>_video_<N>.json`.
   - Dọn sạch thư mục Camera trên thiết bị: `adb -s <serial> shell rm -f /sdcard/DCIM/Camera/*`.
   - Force-stop TikTok: `adb -s <serial> shell am force-stop com.ss.android.ugc.trill`.
   - Đối soát file Excel Tik*.xlsx: nếu cột *Video Đã Đăng* đã bị ghi đè số mới do ngộ nhận, reset lại đúng số video thực tế trước khi chạy lại.
3. **Chạy lại quy trình thật đầy đủ**:
   - Push media thật từ kho `D:\TIKTOK-videonuoinick\<folder>\<clip>.mp4`.
   - Mở picker, chọn video, điền caption/hashtag.
   - Bấm Đăng (Post) và nghiệm thu màn hình xuất bản thực tế (`• 2 giây trước`).

---

## 4. Veto Menu Ngữ Cảnh Profile Video (Context Menu Veto)
1. Khi OCR/Vision phát hiện bất kỳ token nào sau đây:
   - `"Ghim lên đầu"`, `"Đặt ở chế độ riêng tư"`, `"Chia sẻ"`, `"Xóa"`
   - `"Pin to top"`, `"Set to private"`, `"Share"`, `"Delete"`
   ➔ **VETO NGAY LẬP TỨC**. Đây là modal context menu khi long-press vào video tile cũ, TUYỆT ĐỐI KHÔNG ĐƯỢC coi là bằng chứng đã xuất bản video mới (`post-published-surface`).
2. Bằng chứng xuất bản video TikTok mới BẮT BUỘC phải là:
   - Màn hình Feed sau khi bấm Đăng hiển thị video vừa post kèm mốc thời gian tươi (`vài giây trước` / `• 2 giây trước` / `just now`).
   - Lưới Profile sau khi refresh hiển thị thêm 1 tile video mới ở ô đầu tiên.

---

## 5. Kỷ luật loại trừ ViChanger / VPN App
- Farm Taadaa 100% sử dụng **Wi-Fi + Container Singbox trên router MikroTik** (`192.168.110.2:20001..20080`).
- CẤM TUYỆT ĐỐI:
  - Bật lại scheduled task `GanProxyWatcherTray` hoặc chạy các script watcher cũ (`gan_proxy_fleet.py watch`).
  - Gắn ViChanger hoặc broadcast `START_VPN` lên thiết bị farm.
  - Viện cớ cờ readiness cũ trong `~/.codex/device-readiness/` để trì hoãn quy trình.
