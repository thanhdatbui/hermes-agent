# Chẩn đoán: "Có hình mà sao ghi device offline" (Cross-Shift Screencap vs ADB Disconnect)

## 1. Bản chất hiện tượng
Khi người vận hành (operator) thắc mắc: *"Có hình mà sao ghi device offline?"* kèm ảnh chụp màn hình máy có banner đỏ `[MAY N] - HH:MM:SS DD/MM`:
- **Không phải script chụp được ảnh rồi báo lỗi offline ngay lập tức.**
- **Đây là sự chênh lệch thời gian giữa hai Ca/Row chạy khác nhau (Cross-shift / Cross-row mismatch).**

## 2. Cơ chế sinh ảnh và phát sinh lỗi
1. **Thời điểm sinh ảnh (Thành công ở Phiên trước):**
   - Ví dụ: Máy chạy Row 1 (nick A) lúc `01:37:29 06/09`.
   - Phiên hoàn tất thành công, module `PIL` vẽ banner đỏ `[MAY 80] - 01:37:29 06/09` đè lên ảnh chụp màn hình nghiệm thu (`D:\Taadaa\m80_verified_banner.png` hoặc trong `artifacts/`).
2. **Thời điểm báo lỗi (Offline ở Phiên sau):**
   - Ví dụ: Cron khởi động Row 2 (nick B) lúc `07:34:51 06/09` (cách gần 6 tiếng).
   - Bước `Preflight ADB / VPN` kiểm tra serial máy (`adb -s <serial> get-state`).
   - Nếu trong thời gian nghỉ giữa 2 ca, máy bị lỏng cáp USB, lỗi hub sạc, hoặc pin sập nguồn, ADB daemon trả về:
     `device offline or ADB/USB disconnected: adb.exe: device '<serial>' not found`
   - Runner lập tức fast-fail ở preflight, ghi lock `blocked` trong `recovery_lock_handoff.json` và claim alert Telegram tại `alert-claims/<date>-row<N>/machine_<ID>.claimed`.
3. **Vì sao người dùng nhìn thấy ảnh?**
   - Khi operator kiểm tra hoặc bot gửi ảnh chứng minh máy gần nhất, ảnh hiển thị là ảnh lưu của phiên thành công trước đó (Row 1), trong khi lỗi offline thuộc về phiên hiện tại (Row 2).

## 3. Quy trình điều tra O(1) chuẩn (Cấm quét đĩa / Cấm grep -r)
1. **Đọc timestamp trên banner đỏ của ảnh:**
   - Ví dụ: `[MAY 80] - 01:37:29 06/09` -> Chụp lúc 01:37 sáng.
2. **Đọc thời gian và stop_reason trong summary.txt của phiên lỗi hiện tại:**
   - Thư mục: `D:\Taadaa\runtime\kibe\live\<date>\<run_folder>\machines\machine_<N>\<run_id>\summary.txt`.
   - So sánh `start_time` (ví dụ `07:34:51`) với timestamp trên banner (cách nhau nhiều giờ).
3. **Kiểm tra trạng thái ADB vật lý tức thời:**
   - Chạy `adb -s <serial> get-state` hoặc `python D:/Taadaa/tools/inspect_machine.py <N>`.
   - Nếu trả về `device '<serial>' not found` và `adb devices` thiếu serial: xác nhận máy mất kết nối phần cứng.
4. **Kiểm tra file handoff lock:**
   - Đọc `machines/machine_<N>/<run_id>/recovery_lock_handoff.json`:
     `final_status: "blocked"`, `lock_status: "blocked"`.

## 4. Mẫu phản hồi chuẩn cho Operator / User
> *"Ảnh có banner đỏ `[MAY <N>] - <HH:MM:SS> <DD/MM>` là ảnh nghiệm thu thành công của **Row <X>** từ lúc **<HH:MM>** khi máy còn online bình thường.*
>
> *Đến **<HH:MM>** phiên chạy **Row <Y>**, máy <N> đã bị mất kết nối ADB (`device not found`). Hiện tại `adb devices` không nhận diện được serial `<serial>`. Sự cố do phần cứng (lỏng cáp sạc USB / ngắt cổng hub / hết pin), vui lòng kiểm tra cắm lại máy ngoài dàn."*
