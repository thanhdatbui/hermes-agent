# Parasite Account Reconcile & Safe Account Swap / Logout Verification Protocol

## 1. Bản Chất Nick "Ký Sinh" vs Nick "Reg Chưa Kịp Ghi Info" (User Correction 2026-09-19)
- **Tư duy tối thượng về tài sản Farm**:
  * MỌI tài khoản xuất hiện trên thiết bị farm đều là tài sản của farm — tuyệt đối KHÔNG có khái niệm "nick rác ngoài luồng vứt bỏ tùy tiện".
  * Có 2 loại tài khoản cần phân biệt rạch ròi trước khi thao tác:
    1. **Nick ký sinh (Parasite Account)**: Là tài khoản chính chủ của MÁY KHÁC (do đợt batch cũ bốc trùng email hoặc chuyển giao lệch máy). CHỈ ĐƯỢC PHÉP ĐĂNG XUẤT NICK KÝ SINH KHI ĐÃ XÁC MINH NICK NÀY ĐÃ ĐƯỢC LƯU VÀ ĐĂNG NHẬP TRÊN MÁY CHỦ SỞ HỮU GỐC.
    2. **Nick vừa reg chưa ghi info (Unrecorded Fresh Account)**: Là tài khoản được reg từ chính email cấp cho máy đó trong `gmail_clean_v2.xlsx`, nhưng tiến trình reg bị văng/timeout ở bước ghi file (Deferred Tracking Writer). **BẮT BUỘC BẢO TOÀN TUYỆT ĐỐI**, truy vết mail nguồn và backfill ngay vào Excel (`taikhoan_dat_v2_updated .xlsx` & `taikhoan_run_safe.xlsx`), CẤM ĐĂNG XUẤT HOẶC XÓA BỎ.

---

## 2. Bẫy Tử Thần Nghiệm Thu Dối Khi Đăng Xuất (False-Positive Logout Report)
- **Nguyên nhân sự cố**:
  * Phiên trước báo cáo "đã logout sạch nick ký sinh" nhưng thực tế nick vẫn nằm nguyên trong Switcher.
  * Trong script logout cũ (`watchdog_idle_parasite_reconcile.py`), khi bấm "Đăng xuất" ở Settings, TikTok bật popup xác nhận *"Bạn có chắc chắn muốn đăng xuất không?"*. Tọa độ tap bị trượt hoặc dialog không ăn, nhưng script không kiểm tra lại Switcher mà cứ thế chụp ảnh và ghi nhận `"DONE"`.
- **Quy trình nghiệm thu 2 lớp bắt buộc (Fail-Closed Verification)**:
  1. Sau khi tap nút xác nhận Đăng xuất trên popup (màu đỏ tại `(540, 1640)` hoặc bounds tương ứng):
  2. BẮT BUỘC mở lại Profile (`972, 1857`) -> mở lại Switcher (`540, 140` hoặc sticky header).
  3. Dump UI XML hoặc OCR đọc lại toàn bộ danh sách tài khoản:
     - Nếu nick cần logout VẪN CÒN TRONG DANH SÁCH: Coi là **THẤT BẠI HOÀN TOÀN**, cấm báo cáo xong.
     - Chỉ chấp nhận hoàn thành khi nick đã biến mất và xuất hiện lại nút **"Thêm tài khoản"** (Add account) hoặc tổng số nick trên máy giảm xuống đúng 7.

---

## 3. Quy Trình Logout Bằng Coordinates & OCR Tránh Treo UiAutomator
- **Pitfall trên Samsung Galaxy S7**:
  * `uiautomator dump` trên Samsung S7 rất dễ bị kernel futex deadlock hoặc văng mã lỗi `137` (SIGKILL do OOM).
  * Lệnh `subprocess.run(["adb", ...])` nếu KHÔNG có `timeout=15` sẽ làm subagent bị đóng băng vĩnh viễn tới 600s.
- **Công thức điều hướng chuẩn xác**:
  1. **Wake & Mở app**: `input keyevent 224 && input keyevent 82` -> `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1` (timeout 15s).
  2. **Vào Profile**: `input tap 972 1857`.
  3. **Mở Switcher**: Vuốt nhẹ `input swipe 540 1000 540 500 250` để header dính xuất hiện -> tap `(500, 140)`.
  4. **Chọn nick cần out**: Tap vào dòng nick cần logout (x=400, y xác định qua OCR bounding box).
  5. **Vào Settings**: Vào Profile (`972, 1857`) -> Menu 3 gạch (`1005, 150`) -> Cài đặt và quyền riêng tư (`540, 1250` hoặc đáy menu).
  6. **Cuộn đáy Settings**: Vuốt 6 lần `input swipe 540 1600 540 300 250`.
  7. **Đăng xuất**: Tap `(300, 1640)` -> Trên popup xác nhận tap `(540, 1640)`.
  8. **Nghiệm thu**: Mở lại Switcher, chụp ảnh `MEDIA:<path>`, OCR kiểm tra nick biến mất. Force-stop về Home.
