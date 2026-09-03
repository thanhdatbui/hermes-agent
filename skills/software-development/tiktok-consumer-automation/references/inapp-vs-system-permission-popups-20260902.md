# In-App TikTok Permission Modals vs Android System Permission Dialogs (Case 75)

## 1. Phân loại hai dạng Dialog xin quyền
1. **System Permission Dialog (`packageinstaller`):**
   - Package: `com.google.android.packageinstaller`, `com.android.packageinstaller`, `com.android.permissioncontroller`.
   - Xuất hiện khi Android OS hỏi quyền trực tiếp (Ví dụ: truy cập danh bạ, vị trí, bộ nhớ).
   - Được xử lý tập trung qua `SYSTEM_PERMISSION_PACKAGES` trong navigation calibration (`calibrate_screens.py`).
2. **In-App TikTok Modal (`com.ss.android.ugc.trill`):**
   - Dialog nội bộ do TikTok hiển thị (ví dụ: *"Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị."* kèm nút *"Không cho phép"* | *"Mở cài đặt"*).
   - Package giữ nguyên là `com.ss.android.ugc.trill`.
   - **Bắt buộc đăng ký trong `BENIGN_POPUP_REGISTRY`** (`flows/benign_popup_registry.py`) để các luồng Feed / Swipe Recovery tự động phát hiện và bấm *"Không cho phép"* / *"Don't allow"*, tránh bị nhận nhầm thành `manual-needed:loading` hoặc kẹt ở `swipe recovery (2 swipes) still stuck`.

## 2. Quy tắc Điều tra Alert Máy N
- Khi nhận cảnh báo `[MÁY N]`: CẤM quét tìm kiếm đệ quy toàn bộ thư mục `.ai-runs` hay `runtime`.
- Luôn tra cứu trực tiếp số máy $N$ ra `serial` thiết bị từ file workbook mapping (`Tik1.xlsx`) hoặc file config (`config-machine-N.yaml`), sau đó chạy lệnh ADB trực tiếp lên serial để kiểm tra hiện trường.
