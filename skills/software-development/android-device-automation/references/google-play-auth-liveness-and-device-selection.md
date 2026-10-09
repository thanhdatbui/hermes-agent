# Google Play Store Auth Liveness & App Installation Preflight trên Samsung S7 Farm

## 1. Hiện Tượng & Cạm Bẫy `dumpsys account`
- Khi kiểm tra thiết bị qua lệnh `adb shell dumpsys account`, máy có thể liệt kê nhiều tài khoản Google (`type: com.google`).
- **Tuy nhiên:** Sự tồn tại của tài khoản trong `dumpsys account` **không đồng nghĩa** với việc Google Play Store (CH Play) đang trong trạng thái đăng nhập hợp lệ.
- Trên thực tế, nhiều máy Samsung Galaxy S7 (Android 8.0) sau các đợt reg batch hoặc ngâm máy bị hết hạn token xác thực (token revoked / expired / session out). Khi mở Google Play Store qua intent `market://details?id=...` hoặc `com.android.vending`, ứng dụng bị chặn ngay bởi màn hình cảnh báo:
  > *"Cần xác thực. Bạn phải đăng nhập vào Tài khoản Google."* (kèm nút *"Thử lại"* và game mini *"Khinh khí cầu"*).

## 2. Quy Trình Probe Liveness Google Play Store O(1)
Trước khi cài đặt bất kỳ ứng dụng mới hoặc chạy thử nghiệm cần CH Play:
1. **Mở Intent cửa hàng:**
   ```bash
   adb -s <SERIAL> shell am start -n com.android.vending/com.google.android.finsky.activities.MainActivity -a android.intent.action.VIEW -d "market://details?id=<PACKAGE_ID>"
   ```
2. **Chờ 2-3s và chụp screencap:**
   ```bash
   adb -s <SERIAL> shell screencap -p /sdcard/ps_check.png && adb -s <SERIAL> pull /sdcard/ps_check.png ./ps_check.png
   ```
3. **Đọc text qua WinRT OCR:**
   - Nếu OCR phát hiện: `"can xac thuc"` / `"cần xác thực"` / `"authentication is required"`:
     -> Máy đang bị out session Google Play. **Tuyệt đối không tap mù** hay cố gắng bấm Thử lại. Chuyển ngay sang máy tiếp theo trong pool.
   - Nếu OCR phát hiện các tab chính: `"Bảng xếp hạng"`, `"Trò chơi"`, `"Đề xuất"`, hoặc nút xanh `"Cài đặt"` (`"Install"`):
     -> Máy có phiên Google Play Store hoàn toàn sống và sẵn sàng tải ứng dụng.

## 3. Tương Thích Ứng Dụng Mới (Ví Dụ Thực Tế: Phygitals trên S7)
- Nhiều ứng dụng Web3/Fintech hiện đại trên Google Play vẫn hỗ trợ Android 8.0 (API 26).
- Ví dụ kiểm chứng thực tế: App **Phygitals: Rip TCG Packs** (`com.phygitals.mobile` - Phygitals Inc, 57 MB, 18+) hiển thị đầy đủ nút **"Cài đặt"** trên Samsung Galaxy S7 (SM-G930F, Android 8.0), chứng minh không bị chặn bởi minSdk trên thiết bị này.
