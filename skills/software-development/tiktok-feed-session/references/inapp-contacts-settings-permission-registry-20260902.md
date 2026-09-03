# In-App Contacts Settings Permission Dialog vs System Permission Dialog & Direct Alert Triage (Case 75, Machine 52)

## 1. Phân biệt System Permission Dialog vs In-App TikTok Permission Modal
- **System Permission Dialog (Case 71, Máy 72):**
  - Package: `com.google.android.packageinstaller`, `com.android.packageinstaller`, `com.android.permissioncontroller`.
  - Kích hoạt khi điều hướng tab/quyền cấp hệ điều hành Android.
  - Xử lý qua: `SYSTEM_PERMISSION_PACKAGES` trong `calibrate_screens.py` -> gọi `dismiss_tiktok_popups`.
- **In-App TikTok Permission Modal (Case 75, Máy 52):**
  - Package: `com.ss.android.ugc.trill` (thuộc chính TikTok).
  - Nội dung text: *"Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị."* (hoặc bản tiếng Anh: *"To connect with people you know on TikTok, allow access to your contacts in device settings"*).
  - Các nút hành động: `Không cho phép` (Don't allow) | `Mở cài đặt` (Open settings).
  - Xuất hiện trực tiếp trong Feed / Startup.

## 2. Cơ chế xử lý & Đăng ký Registry bắt buộc
- Khi Feed gặp modal này và vào `swipe_recovery_on_stuck` (`feed_swipe_smoke.py`), cơ chế hồi phục gọi `find_matching_handler` trong `flows.benign_popup_registry`.
- Nếu handler chưa được đăng ký trong `BENIGN_POPUP_REGISTRY`, `find_matching_handler` trả về `None`, dẫn đến swipe recovery bất lực và fail-closed với lỗi:
  `TikTok startup/loading screen detected; swipe recovery (2 swipes) still stuck` hoặc `unknown TikTok state; swipe recovery (2 swipes) still stuck`.
- **Giải pháp chuẩn:**
  1. Đăng ký `contacts_settings_permission_dialog` (hoặc `contacts_permission_prompt`) vào `BENIGN_POPUP_REGISTRY` với priority phù hợp (khoảng 85).
  2. Detector: Bắt các cụm từ khóa *"cho phép truy cập vào danh bạ"*, *"kết nối với những người bạn biết"*, *"cài đặt thiết bị"*, *"access your contacts"*.
  3. Dismisser: Tìm và tap chính xác vào element có text *"Không cho phép"* / *"Don't allow"* / *"Từ chối"* để dismiss popup an toàn và trả về Feed.

## 3. Quy tắc Triage Alert [MÁY N]
- **Tuyệt đối CẤM:** Quét / grep / find đệ quy toàn bộ thư mục `.ai-runs` hay `runtime`.
- **Quy trình chuẩn:**
  1. Tra cứu số máy $N$ ra `serial` trực tiếp từ file workbook (`D:\OneDrive\TaadaaData\kibe\Tik1.xlsx`) hoặc config (`D:\CodexRuntime\tiktok-video\config-machine-N.yaml` / `kibe.yaml`).
  2. Kiểm tra focus và trạng thái hiện trường bằng lệnh adb trực tiếp (`adb -s <serial> shell dumpsys window` hoặc chụp màn hình `screencap -p`).
  3. Định vị nguyên nhân và dispatch worker sửa mã theo đúng Coordinator pattern.
