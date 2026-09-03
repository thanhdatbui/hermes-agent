# Samsung S7 RTC Clock Loss, Wi-Fi Zone Mismatch & Idempotency Fingerprint Recovery (2026-09-03)

## 1. Samsung S7 RTC Clock Loss / 2016 Date Bug & SSL Handshake Collapse

### Hiện tượng & Triệu chứng:
* Máy farm sau khi sập nguồn hoặc cạn pin bị mất pin lưu RTC $\rightarrow$ đồng hồ hệ thống bị reset về năm **2016** (ví dụ: `Sat Jan 2 02:03:34 2016`).
* **Android Network Status**: Biểu tượng Wi-Fi trên status bar báo `Tín hiệu Wi-Fi đủ.,Không có Internet.` (do Android Captive Portal check qua HTTPS bị fail SSL handshake).
* **TikTok App**: Màn hình Trang chủ hiện `Đã xảy ra lỗi` / `Thử lại sau`.
* **Account Switcher**: Khi gọi `select_exact_account`, bottom-sheet mở lên bấm vào account mục tiêu thì sheet đóng lại nhưng profile vẫn giữ nguyên account cũ (do request API đổi tài khoản của TikTok thất bại âm thầm vì lỗi SSL `ERR_CERT_DATE_INVALID`) $\rightarrow$ Runner fail tại `ACCOUNT_READY` với lỗi `ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account`.

### Cơ chế & Cách khắc phục trên Android không Root:
1. Non-root shell ADB không thể gõ `date` trực tiếp (`cannot set date: Operation not permitted`), và `service call alarm 2` bị từ chối do thiếu `android.permission.SET_TIME`.
2. Trên mạng Farm có proxy chặn cổng UDP 123 (NTP), bật `auto_time` không tự đồng bộ được qua internet trực tiếp.
3. **Quy trình đồng bộ chuẩn qua Settings UI**:
   * Mở giao diện ngày giờ: `adb -s <serial> shell am start -a android.settings.DATE_SETTINGS`
   * Tắt switch `Thời gian tự động` (`android:id/switch_widget` -> TẮT).
   * Mở `Cài đặt ngày` (`android:id/title` text 'Cài đặt ngày') -> Chỉnh con lăn Năm (`2026`), Tháng, Ngày về đúng hiện tại -> bấm `H.TẤT`.
   * Mở `Cài đặt thời gian` -> Chỉnh con lăn Giờ, Phút về giờ hiện tại -> bấm `H.TẤT`.
   * Gán lại proxy chuẩn: `python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_adb.py --machines <N>`.
   * Relaunch TikTok: `am force-stop com.ss.android.ugc.trill` -> mở lại app -> feed tải bình thường, switch account hoạt động 100%.

---

## 2. Aruba Instant Zone Isolation & Wi-Fi AUTHENTICATION_FAILURE

### Quy tắc phân bổ AP Zone toàn Farm Kibe (80 Máy):
* **Máy 01–40**: Bắt buộc kết nối SSID `kibe 1` (Aruba AP 1 / Zone 1).
* **Máy 41–80**: Bắt buộc kết nối SSID `kibe 2` (Aruba AP 2 / Zone 2).
* **Mật khẩu Wi-Fi toàn farm**: `19051995`.

### Triệu chứng lệch Profile Wi-Fi:
* Nếu máy thuộc dải 41–80 (ví dụ M66) cố kết nối vào `kibe 1`, Aruba AP sẽ từ chối xác thực (`level2FailureCode=AUTHENTICATION_FAILURE` / `reason=WRONG_KEY`).
* Giao diện Android báo `Đã xảy ra lỗi xác thực` và interface `wlan0` rơi về trạng thái `NO-CARRIER` / `state DORMANT`.

### Cách xử lý:
1. Mở `android.settings.WIFI_SETTINGS`.
2. Nếu đang lưu `kibe 1` sai: bấm vào `kibe 1` -> chọn `QUÊN` (Forget).
3. Cuộn danh sách tìm `kibe 2` (hoặc bấm `Thêm mạng`), nhập mật khẩu `19051995` -> bấm `KẾT NỐI`.
4. Sau khi `wlan0` nhận IP `192.168.110.x`, chạy `python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_adb.py --machines <N>`.

---

## 3. Idempotency Media Fingerprint Unresolved Reservation Recovery

### Nguyên nhân:
* Khi runner upload video bị gián đoạn (timeout, killed, ngắt điện giữa chừng) trong các state `MEDIA_PUSH` hoặc `VIDEO_PICK`, tiến trình đã kịp ghi nhận reservation vào ledger: `D:/CodexRuntime/tiktok-video/idempotency/media-fingerprints/<key>.json` với `"status": "reserved"`.
* Lượt chạy canary hoặc retry tiếp theo sẽ bị chặn đứng tại state `RESOLVE_NEXT_VIDEO` với lỗi:
  `[MEDIA_FINGERPRINT] [MEDIA_FINGERPRINT_PENDING] Exact media SHA-256 has unresolved ledger status=reserved` -> chuyển sang `MANUAL_REVIEW`.

### Cách xử lý an toàn:
* Kiểm tra file trong `D:/CodexRuntime/tiktok-video/idempotency/media-fingerprints/`.
* Tìm file JSON có `machine == <N>` và `status == "reserved"`.
* Nếu xác nhận video tương ứng chưa từng đăng/verify thành công trên profile TikTok, xóa file reservation cũ để lượt chạy mới thực hiện reserve và upload lại từ đầu.
