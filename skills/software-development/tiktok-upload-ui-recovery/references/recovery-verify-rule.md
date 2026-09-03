# Recovery: kiểm tra màn thật trước khi sửa (user rule 2026-08-09)

Áp dụng cho MỌI công việc **recovery** (sửa lỗi UI, sửa handler, sửa rule, retry máy fail)
trên farm. User yêu cầu: *"luôn kiểm tra màn thật trc khi sửa thay vì tin artifact — làm tới đâu
kiểm tra màn + handle tới đó"*.

## 1. Check màn thật TRƯỚC khi sửa

- Capture screencap ảnh + UI dump **live** của ĐÚNG máy/serial tại thời điểm hiện tại:
  ```bash
  adb -s <serial> exec-out screencap -p > screen.png
  adb -s <serial> shell uiautomator dump /sdcard/ui.xml && adb -s <serial> shell cat /sdcard/ui.xml
  # hoặc XML live qua atx (curl port-forward 7912) nếu dump shell treo
  ```
- **KHÔNG tin artifact cũ**: log cũ, XML dump cũ, screenshot/report/summary của session trước
  KHÔNG phải bằng chứng trạng thái hiện tại của máy. Máy có thể đã đổi màn hình, popup mới,
  app bị force-stop, pin chết...
- Kết luận trạng thái UI (popup đang che gì, nút ở đâu, máy đang ở màn nào, tab nào) **chỉ từ
  dump/screencap mới capture**. Đối chiếu screenshot + UI dump + handler đang chạy rồi mới kết luận.

## 2. Làm tới đâu check tới đó

- Sau MỖI bước sửa/handle (tap, swipe, set, kill, reboot, sửa code) → **recapture + verify kết quả
  trên màn thật** → mới chuyển bước tiếp.
- Recapture phải **FRESH** — không reuse ảnh/dump cũ của bước trước để "chứng minh" kết quả.
- Không làm cả loạt thao tác rồi mới kiểm tra một lần.

## 3. Vì sao

- Artifact có thể thuộc target khác (mapping máy/serial đổi), session cũ, máy đã reboot,
  hoặc bị handler khác sửa đổi giữa chừng — sửa theo artifact sai = sửa mù.
- Verify từng bước giúp bắt lỗi sai hướng sớm, đúng tinh thần "recovery phải có evidence".