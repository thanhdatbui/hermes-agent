# Samsung Galaxy S7 (Korean ROM) Wi-Fi Onboarding & UI Diagnostic Patterns

## 1. Bối cảnh & Đặc thù thiết bị
- Thiết bị Samsung SM-G930 series tại Taadaa farm chủ yếu là máy xách tay Hàn Quốc (chạy ROM nguyên bản tiếng Hàn `ko-KR`).
- Máy **không có quyền root** (`su: not found`), do đó không thể trích xuất mật khẩu đã lưu từ `/data/misc/wifi/WifiConfigStore.xml`.
- Mọi thao tác kết nối Wi-Fi cho máy mới xuất kho (onboarding) phải thực hiện qua UI Settings hoặc gửi broadcast nếu có agent hỗ trợ.

## 2. Quy trình kết nối Wi-Fi chuẩn qua UI Settings Samsung (Korean UI)
1. **Mở cài đặt Wi-Fi**:
   - `adb shell am start -a android.settings.WIFI_SETTINGS`
2. **Mã nhận diện các thành phần UI trong `com.android.settings`**:
   - Danh sách mạng: `com.android.settings:id/twlist` (`SemExpandableListView`).
   - Tên mạng (SSID): Item có `android:id/title` chứa tên SSID (ví dụ `kibe 1`).
   - Dialog kết nối:
     - Header tiêu đề: `android:id/alertTitle` hiển thị đúng SSID.
     - Ô nhập mật khẩu: `com.android.settings:id/password` (`android.widget.EditText`).
       - **Lưu ý bẫy `(변경 없음)`**: Nếu mạng đã được lưu cấu hình trước đó nhưng sai pass, text trong ô sẽ hiển thị placeholder `(변경 없음)` (No change). Cần tap vào ô và xóa ký tự cũ (`keyevent 67`) trước khi nhập pass mới.
     - Checkbox hiển thị mật khẩu: `com.android.settings:id/show_password` (Text: `비밀번호 표시`).
       - **Bắt buộc tap bật checkbox này**: Khi bật, nội dung trong EditText sẽ lộ rõ trong XML dump, cho phép verify chính xác ký tự đã gõ trước khi bấm Kết nối (loại trừ 100% khả năng gõ thiếu/sai do ADB).
     - Nút Kết nối: `android:id/button1` (Text: `연결`).
     - Nút Hủy: `android:id/button2` (Text: `취소`).

## 3. Chẩn đoán kết nối & Từ điển trạng thái UI tiếng Hàn
- **Kiểm tra trạng thái tầng thấp qua dumpsys**:
  ```bash
  adb -s <SERIAL> shell dumpsys wifi | grep -i mWifiInfo
  ```
  - `Supplicant state: COMPLETED` -> Đã kết nối thành công, kèm RSSI và Link speed.
  - `Supplicant state: FOUR_WAY_HANDSHAKE` rồi chuyển sang `DISCONNECTED` -> Xác thực thất bại (sai pass, AP từ chối, hoặc MAC filtering).

- **Từ điển trạng thái trên UI Samsung (`android:id/summary`)**:
  - `연결 중…` -> Đang kết nối (Connecting...).
  - `인증 오류 발생` -> Lỗi xác thực phát sinh (Authentication error).
  - `비밀번호를 잘못 입력했습니다.` (`com.android.settings:id/wifi_password_error_text`) -> Mật khẩu nhập không đúng.
  - `연결됨` -> Đã kết nối thành công (Connected).

## 4. Kỷ luật Fail-Fast khi gặp lỗi xác thực (Anti-Spam Discipline)
- Khi nhập đúng mật khẩu (đã verify qua ô `show_password`) nhưng UI báo `인증 오류 발생` hoặc dumpsys rơi vào `FOUR_WAY_HANDSHAKE -> DISCONNECTED` quá 2 lần:
  1. Dừng thao tác ngay lập tức, không lặp lại vòng lặp gõ/tap mù quáng làm tốn iterations.
  2. Đối chiếu nhanh với một máy live khác trong farm xem máy đó có đang kết nối ổn định với cùng BSSID hay không:
     ```bash
     adb -s <OTHER_SERIAL> shell dumpsys wifi | grep -i mWifiInfo
     ```
  3. Báo cáo cụ thể cho operator: Máy bị từ chối ở handshake nào, trạng thái UI thực tế, kèm đề xuất kiểm tra mật khẩu thực tế hoặc bộ lọc MAC / DHCP trên Access Point.
