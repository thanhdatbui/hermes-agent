# Quy chuẩn Tắt màn hình & Chống nung nhiệt Mainboard S7 Farm

## 1. Bản chất phần cứng Box Farm (Main không màn hình thật)
- Dàn máy farm là mainboard rời cắm trong box, không có màn hình AMOLED vật lý (không sợ burn-in).
- Tuy nhiên, nếu để màn hình hiển thị liên tục (hoặc stream lên PC qua tool view):
  - Chip Exynos và SurfaceFlinger liên tục render frame 60 FPS.
  - SoC và IC nguồn (PMIC) bị nung nóng liên tục (nhiệt độ tăng 3°C - 7°C trong không gian box hẹp).
  - Nguy cơ: Hở chân chip BGA (rụng RAM/CPU), chai tụ nguồn và lão hóa chip nhớ eMMC/UFS.

## 2. Các cạm bẫy khi tắt màn hình qua ADB (Pitfalls)
1. **Cạm bẫy `input keyevent 26` (Nút Nguồn):**
   - Keyevent 26 là lệnh **Toggle** (Bật <-> Tắt). Nếu máy đang ở trạng thái chập chờn hoặc đang ngủ, gửi 26 sẽ **bật màn hình dậy**.
   - **Chuẩn hóa:** BẮT BUỘC dùng `input keyevent 223` (`KEYCODE_SLEEP`) để ép ngủ bắt buộc 1 chiều.
2. **Cạm bẫy `stay_on_while_plugged_in = 7` (Developer Options):**
   - Nếu setting này còn mang giá trị `7` (hoặc `3`, `1`), Android PowerManager coi nguồn USB cắm từ box là tín hiệu cưỡng chế sáng vĩnh viễn. Bộ đếm `screen_off_timeout` sẽ **bị đóng băng không đếm ngược**.
   - **Chuẩn hóa:** BẮT BUỘC gán `settings put global stay_on_while_plugged_in 0` và `svc power stayon false`.
3. **Cạm bẫy Always On Display (AOD) trên Samsung S7:**
   - Khi tắt màn hình, S7 chuyển sang chế độ Dozing chạy `com.samsung.android.app.aodservice` để hiển thị đồng hồ ngầm khiến tool view PC (Xiaowei, Scrcpy) vẫn bắt khung hình.
   - **Chuẩn hóa:** BẮT BUỘC gán `settings put system aod_mode 0`.
4. **Cạm bẫy chuỗi lệnh Shell Android:**
   - Dùng dấu `;` dễ bị ngắt giữa chừng nếu lệnh trước fail nhẹ hoặc delay.
   - **Chuẩn hóa:** Nối lệnh nguyên tử bằng `&&`.

## 3. Lệnh chuẩn thiết lập 10 phút tự tắt màn hình an toàn (Fail-Safe)
Đặt thời gian chờ 10 phút (`600000` ms) để trong khi bot chạy (nếu lag, dump XML chậm, mạng giật) màn hình không bị tắt phụt làm miss click, nhưng khi xong task hoặc idle lâu sẽ tự tắt hoàn toàn:

```bash
settings put global stay_on_while_plugged_in 0 && \
svc power stayon false && \
settings put system aod_mode 0 && \
settings put system screen_off_timeout 600000 && \
input keyevent 223
```

## 4. Kiểm chứng trạng thái Display Power
Kiểm tra máy đã ngủ thực sự chưa qua:
```bash
dumpsys power | grep -E "Display Power:|mWakefulness="
```
- `mWakefulness=Asleep` hoặc `Dozing`
- `Display Power: state=OFF`
