# Case 75: In-App TikTok Contacts Permission Settings Prompt Registry Dismissal (02/09/2026)

## 1. Bối Cảnh Sự Cố & Triệu Chứng (Máy 52)
- **Thiết bị:** Máy 52 (serial `ce0418243a6250430c`), tài khoản `santowycbvq`.
- **Triệu chứng lỗi:** Dừng phiên `multi-machine-feed-session` với thông báo:
  `TikTok startup/loading screen detected; swipe recovery (2 swipes) still stuck`
  Trạng thái: `GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`.
- **Hiện trường:** Trên màn hình video feed xuất hiện dialog nội bộ của app TikTok:
  *"Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị"*
  Nút bấm: `Không cho phép` | `Mở cài đặt`.

## 2. Nguyên Nhân Cốt Lõi (Root Cause)
1. **Dialog nội bộ của app TikTok:** Đây là dialog trong package `com.ss.android.ugc.trill`, không phải dialog xin quyền hệ thống Android (`packageinstaller`).
2. **Thiếu Registry Handler:** Khi rơi vào `swipe_recovery_on_stuck` (`feed_swipe_smoke.py`), runner gọi `find_matching_handler` trong `benign_popup_registry.py`. Trước đó `BENIGN_POPUP_REGISTRY` chưa có handler cho `contacts_settings_permission_prompt`.
3. **Fail-Closed:** Runner không tìm thấy handler phù hợp để bấm `Không cho phép`, sau 2 lần vuốt không thoát được dialog và dừng phiên giữ hiện trường.

## 3. Giải Pháp Kỹ Thuật (Case Fix)
1. **Trong `benign_popup_registry.py` (`tiktok-luot nuoi acc`):**
   - Bổ sung `_detect_contacts_settings_permission`: nhận diện text tiếng Việt và tiếng Anh (`"Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị"`, `"truy cập vào danh bạ của bạn trong mục cài đặt thiết bị"`, `"cho phép truy cập vào danh bạ của bạn trong mục cài đặt"`, `"To connect with people you know on TikTok, allow access to your contacts in device settings"`, `"allow access to your contacts in device settings"`).
   - Bổ sung `_dismiss_contacts_settings_permission`: quét tìm các nhãn từ chối (`"Không cho phép"`, `"Don't allow"`, `"Deny"`, `"Từ chối"`, `"Hủy"`, `"Cancel"`), tính center bounds và tap. Fallback gửi phím Back an toàn.
   - Đăng ký vào `BENIGN_POPUP_REGISTRY` với Priority 91:
     `register_popup_handler(RegistryEntry("contacts_settings_permission_prompt", 91, _detect_contacts_settings_permission, _dismiss_contacts_settings_permission, True, "manual"))`
2. **Trong `automation_core.tiktok.benign_popup` (`automation-core`):**
   - Nâng cấp `detect_contacts_settings_permission_dialog`: mở rộng bộ nhãn từ chối và markers, loại bỏ việc bị chặn nhầm bởi text nhạy cảm xuất hiện ở video nền.
3. **Unit Tests:**
   - 10 unit tests trong `test_benign_popup_registry.py` (122 passed).
   - Test trong `test_tiktok_benign_popup.py` (729 passed).

## 4. Quy Tắc Tiếp Nhận Alert [MÁY N] (Anti-Disk-Scan Invariant)
- **TUYỆT ĐỐI CẤM:** Quét `find`, `grep`, `search_files`, `ls` đệ quy trong thư mục `.ai-runs` hoặc `runtime` khi nhận alert có số máy.
- **QUY TRÌNH CHUẨN:**
  1. Tra cứu trực tiếp serial qua `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` (dòng tương ứng với số máy).
  2. Dùng ADB với serial đó (`adb -s <serial> ...`) để kiểm tra `dumpsys window` / capture màn hình live.
  3. Dispatch worker thực thi sửa code & unit test, coordinator giữ vai trò review & chốt phiên 6 Gate.
