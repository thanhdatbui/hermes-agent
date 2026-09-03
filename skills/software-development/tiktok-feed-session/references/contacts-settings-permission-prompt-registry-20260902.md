# In-App Contacts Settings Permission Prompt Registry & Triage (Case 75, Máy 52)

## 1. Hiện tượng & Bối cảnh
- **Máy gặp lỗi:** Máy 52 (`ce0418243a6250430c`), tài khoản `santowycbvq`.
- **Dấu hiệu:** `multi-machine-feed-session` dừng phiên với thông báo:
  `Lý do: TikTok startup/loading screen detected; swipe recovery (2 swipes) still stuck`
  Trạng thái: `GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`.
- **UI thực tế:** Xuất hiện popup nội bộ của TikTok (`com.ss.android.ugc.trill`):
  *"Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị"* (hoặc *"To connect with people you know on TikTok, allow access to your contacts in device settings"*).
  Nút bấm: `Không cho phép` (hoặc `Don't allow`) và `Mở cài đặt` (`Open settings`).

## 2. Phân biệt System Dialog vs In-App Dialog
- **System Dialog (Case 71, M72):** Package `com.google.android.packageinstaller` / `com.android.permissioncontroller`. Xử lý trong `flows/calibrate_screens.py` (`tap_navigation_target`) bằng `SYSTEM_PERMISSION_PACKAGES` và `dismiss_tiktok_popups`.
- **In-App TikTok Dialog (Case 75, M52):** Package vẫn là `com.ss.android.ugc.trill`. Khi feed swipe recovery chạy, runner gọi `find_matching_handler` trong `benign_popup_registry.py`.

## 3. Quy tắc Triệt để
1. **Đăng ký Registry:** Bắt buộc có entry trong `BENIGN_POPUP_REGISTRY`:
   ```python
   register_popup_handler(
       RegistryEntry(
           "contacts_settings_permission_prompt",
           91,
           _detect_contacts_settings_permission,
           _dismiss_contacts_settings_permission,
           True,
           "manual",
       )
   )
   ```
2. **Detector (`_detect_contacts_settings_permission`):**
   - Quét các markers text/desc:
     - `"Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị"`
     - `"truy cập vào danh bạ của bạn trong mục cài đặt thiết bị"`
     - `"cho phép truy cập vào danh bạ của bạn trong mục cài đặt"`
     - `"To connect with people you know on TikTok, allow access to your contacts in device settings"`
     - `"allow access to your contacts in device settings"`
3. **Dismisser (`_dismiss_contacts_settings_permission`):**
   - Tìm nút từ chối: `"không cho phép"`, `"don't allow"`, `"deny"`, `"từ chối"`, `"hủy"`, `"cancel"`.
   - Tính tọa độ trung tâm và bấm (`_perform_click_target`).
   - Fallback phím Back (`send_device_back_key`) nếu không tìm thấy tọa độ.
4. **Quy tắc Triage khi nhận Alert [MÁY N]:**
   - **Tuyệt đối CẤM:** Không dùng `find`, `grep`, `search_files` quét đệ quy thư mục `.ai-runs/` hoặc `runtime/`.
   - **Đúng quy trình:** Tra thẳng serial qua `Tik1.xlsx` / `kibe.yaml` -> kết nối trực tiếp thiết bị qua ADB để lấy UI XML / screencap.
