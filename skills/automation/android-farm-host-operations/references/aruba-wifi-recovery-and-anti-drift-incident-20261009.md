# Bài Học Khắc Phục Sự Cố Wi-Fi Farm & Phục Hồi An Toàn (09/10/2026)

## 1. TAI NẠN LỆCH SUBNET & RỦI RO LỘ IP DO FALLBACK TỰ Ý
- **Hiện tượng**: Khi 1 máy (M7) mất kết nối Wi-Fi chính, Coordinator tự ý thử nghiệm fallback sang SSID vãng lai/ngoài quy hoạch (`Dat`).
- **Hậu quả nghiêm trọng**:
  1. SSID lạ cấp dải IP `192.168.10.x` (thay vì dải chuẩn Farm `192.168.110.x`).
  2. Toàn bộ routing tới router MikroTik (`192.168.110.2`) và container proxy (`200xx`) bị đứt gãy (`Network is unreachable`).
  3. Vi phạm nguyên tắc bảo mật: Tiềm ẩn nguy cơ lộ IP Direct FPT nếu script preflight gặp lỗ hổng.
- **Quy tắc đúc kết**:
  + **CẤM TUYỆT ĐỐI** tự tiện cho máy nhảy sang SSID ngoài quy hoạch hoặc viết code fallback tự động sang SSID ngoài.
  + **CỐ ĐỊNH QUY HOẠCH 40 MÁY/AP**:
    * M01–M40: `kibe 1` (pass `23102025` - AP .253)
    * M41–M80: `kibe 2` (pass `19051995` - AP .252)
    * M201–M240: `admin 1` (pass `19051995` - AP .251)
    * M241–M280: `admin 2` (pass `19051995` - AP .250)
  + **CẤM DỒN TẢI SANG AP KHÁC**: Không tự ý gán máy cụm 1 sang AP cụm 2 để tránh làm quá tải 40 máy/AP của Aruba gây rớt mạng hàng loạt.

---

## 2. BẪY CHUỖI CỦA LỆNH ADB-JOIN-WIFI TRÊN SHELL ANDROID
- **Hiện tượng**: Chạy lệnh qua shell ADB:
  ```bash
  am start -n com.steinwurf.adbjoinwifi/.MainActivity -e ssid 'kibe 1' -e password_type WPA -e password '23102025'
  ```
  Android intent shell cắt chuỗi tại dấu cách, khiến app chỉ nhận `ssid = "kibe"`. Kết quả là hàng loạt máy kết nối vào SSID rác tên `kibe`, không có số 1, dẫn đến mất Wi-Fi toàn cụm!
- **Giải pháp chuẩn xác**:
  BẮT BUỘC dùng cờ `--es` (explicit string) và escape dấu ngoặc kép chuẩn:
  ```bash
  am start -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "kibe 1" --es password_type WPA --es password "23102025"
  ```

---

## 3. SỰ CỐ ROGUE DHCP TRÊN MASTER ARUBA VIRTUAL CONTROLLER
- **Hiện tượng**: Một số máy khi kết nối Wi-Fi lại nhận IP `192.168.10.x` thay vì `192.168.110.x`.
- **Nguyên nhân**: Trên Master AP (`192.168.110.251`), tồn tại một pool DHCP nội bộ cũ (`ip dhcp kibe_dhcp subnet 192.168.10.0/24`). Khi AP con reboot hoặc máy gửi DHCP Discover, AP Aruba trả IP nhanh hơn MikroTik và cấp sai subnet.
- **Cách xử lý**:
  Truy cập SSH vào AP Master:
  ```text
  conf t
  no ip dhcp kibe_dhcp
  end
  commit apply
  ```
  Để MikroTik (`192.168.110.2`) là DHCP Server duy nhất cấp dải `192.168.110.x`.

---

## 4. QUY TRÌNH PHỤC HỒI WI-FI 2 CẤP AN TOÀN
Khi phát hiện máy mất kết nối Wi-Fi / wlan0 không có IP:
1. **Cấp 1 (Radio Toggle nhẹ)**:
   ```bash
   adb -s <serial> shell svc wifi disable
   sleep 1
   adb -s <serial> shell svc wifi enable
   sleep 3
   ```
2. **Cấp 2 (Bẻ khóa blocklist bằng adb-join-wifi)**:
   Nếu máy dính cờ `ASSOCIATION_REJECTION` (do AP từ chối handshake cũ), gọi `adb-join-wifi` ép handshake lại đúng SSID quy hoạch:
   ```bash
   adb -s <serial> shell 'am force-stop com.steinwurf.adbjoinwifi && am start -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "<SSID_CHUAN>" --es password_type WPA --es password "<PASS_CHUAN>"'
   sleep 4
   adb -s <serial> shell input keyevent 3
   ```
3. **Nếu cả 2 cấp thất bại**:
   **DỪNG LẠI NGAY LẬP TỨC**. Giữ nguyên hiện trường, ghi log cảnh báo ra watchdog. **CẤM TUYỆT ĐỐI GÁN BỪA MẠNG KHÁC HOẶC DỒN SANG AP KHÁC ĐỂ CHỮA CHÁY**.

---

## 5. BẪY PROFILE WI-FI TỒN LƯU TRONG WIFICONFIGSTORE & ANDROID AUTO-ROAM
- **Nguyên nhân máy tự ý nhảy sang SSID lạ**: Khi máy từng kết nối vào SSID khác (dù chỉ thử nghiệm 1 lần), Android framework ghi profile đó vào `WifiConfigStore.xml` với `priority = 100`.
- Mỗi khi AP chính bị drop hoặc watchdog chạy radio toggle (`svc wifi disable` -> `enable`), OS Android tự động quét và roam sang bất kỳ mạng nào có sẵn trong danh sách đã lưu nếu tín hiệu tốt hơn.
- **Hậu quả**: Chỉ gỡ code fallback trong Python là KHÔNG ĐỦ; trên điện thoại vẫn còn profile nên máy vẫn tự nhảy ngầm.
- **Cách triệt tiêu**: Phải chạy batch re-join đúng SSID quy hoạch qua `adb-join-wifi` (bật cờ `disableOthers=true` trong `enableNetwork`) để vô hiệu hóa profile lạ trên toàn bộ dàn máy.

---

## 6. BẪY BINDER TRÊN SAMSUNG KOREAN ROM (SM-G930S) & QUY TRÌNH ADB-JOIN-WIFI
- Lệnh binder `service call wifi 14 i32 <netId>` (removeNetwork) bị từ chối trên ROM Samsung SKT do thiếu quyền: `Neither user 2000 nor current process has android.permission.CHANGE_WIFI_STATE`.
- **Cơ chế gọi adb-join-wifi chuẩn xác**:
  1. `adb shell am force-stop com.steinwurf.adbjoinwifi && adb shell pkill -f steinwurf` (bắt buộc vì `MainActivity` không có `onNewIntent`).
  2. Bọc nháy đơn hoặc dùng `--es` quanh SSID chứa khoảng trắng: `am start -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid '<SSID>' --es password_type WPA --es password '<PASS>'`.

---

## 7. KỶ LUẬT THỰC THI BATCH 20 WORKERS & CADENCE BÁO CÁO
- Với quy mô 80–160 máy, chạy tuần tự hoặc ít worker (<=8) sẽ làm tắc nghẽn farm kéo dài hơn 1 tiếng.
- BẮT BUỘC dùng `ThreadPoolExecutor(max_workers=20)` cùng `with_device_lock`: 154 máy hoàn tất trong < 60 giây.
- Kỷ luật phản hồi: Báo cáo số liệu thực tế ngay lập tức kèm tỷ lệ máy đạt chuẩn / lỗi để người vận hành nắm bắt hiện trường.

