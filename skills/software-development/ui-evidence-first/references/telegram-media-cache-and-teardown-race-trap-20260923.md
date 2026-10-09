# Telegram Media Cache Collision & Capture-Before-Teardown Race Trap

**Thời điểm ghi nhận:** 23/09/2026  
**Ngữ cảnh:** Tác vụ đăng xuất nick ký sinh / dọn dẹp tài khoản TikTok trên Máy 53 và gửi ảnh nghiệm thu giao diện Account Switcher.

---

## 1. Hiện tượng & Vấn đề thực tế

### Sự cố 1: Bẫy Teardown Trước Chụp Ảnh (Capture-After-Teardown Trap)
* Worker subagent chạy quy trình đăng xuất nick ký sinh trên app TikTok.
* Trong script Python (`reconcile_m53_chichi.py`), bước chụp ảnh `proof = get_screen(REPORT_PATH)` bị trễ hoặc đặt sau lệnh `adb shell am force-stop com.ss.android.ugc.trill && input keyevent 3`.
* Kết quả: Ảnh chụp nghiệm thu thu được là **màn hình Home của Android** (Launcher) thay vì màn hình TikTok Account Switcher. User lập tức phản hồi bức xúc: *"mày dọn xong thì gửi ảnh ở account switcher t xem là dọn kí sinh chưa chứ gửi ảnh này chi v"*.

### Sự cố 2: Bẫy Đệm Ảnh / Media Cache Collision Của Telegram Platform
* Sau khi phát hiện ảnh gửi là màn hình Home, Agent chụp lại ảnh mới trên thiết bị và lưu ra file ảnh (ví dụ `m53_account_switcher_true.png` hoặc `m53_switcher_verified_logout.png`).
* Khi Agent phát tin nhắn `MEDIA:<path>` ngay sau đó, Telegram platform adapter hoặc cache upload của Telegram API nhận diện file cùng đường dẫn / cùng hash cũ từ session stream gần nhất, hoặc bắt trúng file cache dở dang, dẫn đến việc tin nhắn gửi đến người dùng vẫn là **ảnh màn hình Home cũ**.
* User gửi lại ảnh chụp Telegram với câu hỏi: *"ảnh chuẩn của mày đây hả?"* (kèm screenshot thể hiện tin nhắn của Agent gửi đúng ảnh Home cũ).

---

## 2. Nguyên nhân cốt lõi (Root Cause)

1. **Vi phạm Capture-Before-Teardown Invariant:**
   * Script tự động hóa thường có thói quen "dọn dẹp sạch sẽ" (`force-stop`, `keyevent 3`) ở khối `finally:` hoặc cuối script.
   * Nếu hàm chụp ảnh nghiệm thu đặt sau hoặc cùng khối teardown, race condition giữa tiến trình dừng app của Android OS và lệnh `screencap` sẽ làm screencap chụp trúng Launcher.

2. **Cơ chế Media Caching & Name Collision của Chat Gateway (Telegram):**
   * Telegram Bot API và adapter local thường cache `file_id` hoặc upload buffer theo file path / metadata nếu file vừa được upload trong cùng một cửa sổ vài phút.
   * Khi gửi lại file ảnh sửa lỗi bằng đúng tên file cũ (hoặc file bị ghi đè in-place nhưng timestamp/path không đổi), adapter có thể tái sử dụng `file_id` hoặc buffer cũ để tối ưu băng thông, khiến User nhận lại ảnh cũ rác.

---

## 3. Quy trình chuẩn khắc phục (Standard Procedure)

### Bước 1: Kỷ luật Bất Biến "Capture First, Teardown Last"
* **Luôn chụp ảnh trước khi đụng vào Teardown:**
  1. Điều hướng đến màn hình đích cần nghiệm thu (ví dụ: bung Account Switcher bằng cách vào Cài đặt -> cuộn đáy -> tap "Chuyển đổi tài khoản" hoặc tap header).
  2. Dừng `time.sleep(2-3s)` để UI ổn định.
  3. Chụp screencap và verify ngay bằng WinRT OCR hoặc XML inspection.
  4. Xác nhận ảnh có chứa Artifact mục tiêu (nút "Thêm tài khoản", nick active, danh sách tài khoản đã biến mất nick rác).
  5. **CHỈ SAU KHI ĐÃ CÓ ẢNH ĐÍCH** mới được chạy lệnh teardown (`force-stop`, `keyevent 3`).

### Bước 2: Kỹ thuật Phá Vỡ Cache Media Của Telegram (Cache-Busting Discipline)
Khi chụp ảnh mới để sửa sai hoặc gửi lại bằng chứng nghiệm thu cho User:
1. **Tuyệt đối CẤM ghi đè vào file cũ:** Không dùng lại đường dẫn file ảnh đã gửi thất bại/gửi nhầm trước đó.
2. **Đặt tên file với Timestamp & Tag duy nhất:**
   * Định dạng chuẩn: `<report_dir>/<machine>_<action>_<YYYYMMDD_HHMMSS>_<unique_suffix>.<ext>`
   * Ví dụ: `D:/Taadaa/reports/m53_account_switcher_20260923_103015_clean.jpg`
3. **Đổi định dạng / Convert sang JPG mới:**
   * Chuyển đổi định dạng (PNG $\rightarrow$ JPG với quality 95) làm thay đổi hoàn toàn hash byte stream và header, buộc Telegram Bot API phải upload một media object mới 100%.
4. **Cắt ảnh tập trung (Target Crop):**
   * Ngoài ảnh toàn màn hình, tạo thêm 1 ảnh crop vùng trọng tâm (ví dụ crop vùng đáy hiển thị nút `[+] Thêm tài khoản` hoặc danh sách tên tài khoản).
   * Gửi kèm ảnh crop để User kiểm tra trực diện ngay trên thumbnail Telegram mà không cần bấm phóng to.

---

## 4. Checklist Thẩm Định Trước Khi Gửi Ảnh Nghiệm Thu (Pre-Send Gate)
- [ ] Ảnh đã chụp TRƯỚC KHI gửi bất kỳ lệnh `force-stop` hay `keyevent 3` nào chưa?
- [ ] Tên file ảnh có chứa timestamp hoặc hậu tố độc nhất mới tinh chưa (không dùng lại file cũ)?
- [ ] Đã kiểm tra dung lượng ảnh (> 40KB) và xác nhận không phải màn hình đen / dozing chưa?
- [ ] Đã kiểm tra text trên ảnh (OCR/XML) để chắc chắn KHÔNG PHẢI màn hình Home (Launcher) chưa?
- [ ] Có kèm ảnh crop chi tiết vùng thay đổi nếu là màn hình dài/phức tạp không?
