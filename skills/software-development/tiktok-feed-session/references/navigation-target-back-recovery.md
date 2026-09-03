# Navigation Target Recovery (Back on Missing XML Target)

## Vấn đề
Trong phiên lướt feed (`feed_swipe_smoke` / `multi_machine_feed_session`), quá trình tương tác có thể vô tình click chạm vào avatar/tên creator, sticker, liên kết hoặc landing page mở ra màn hình **External Profile / Webview / Chi tiết**.
Khi chuyển sang bước điều hướng kế tiếp hoặc đối soát hồ sơ (`verify_profile`, chuyển tab `profile`, `home`), thanh bottom/top tab không tồn tại trên XML hiện tại -> gây lỗi `navigation target <name> not found in XML` và dừng phiên sớm.

## Cơ chế xử lý chuẩn (`calibrate_screens.py`)
Tại hàm `tap_navigation_target`:
- Khi lần tìm target đầu tiên qua XML trả về `point is None` (không thấy node UI):
- Kích hoạt recovery:
  1. Gửi lệnh `KEYCODE_BACK` (phím 4) qua ADB shell: `input keyevent 4`.
  2. Nghỉ `1.0s` chờ UI ổn định.
  3. Re-capture XML mới và tìm lại node UI của target.
  4. Nếu tìm thấy, thực hiện tap bình thường và log trạng thái `navigation_target_not_found_back_recovery: success`.
- Đảm bảo tuân thủ nguyên tắc XML-first và tự động hồi phục khi máy bị lạc trang.
