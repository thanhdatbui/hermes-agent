# TikTok Reg UI Detours: Camera/LIVE Dismiss & Parasite Account Triage (24/09/2026)

## 1. Bẫy Kẹt Màn Hình Camera / Phát LIVE TikTok (`ttlive_preview_surfaceview`)
- **Hiện tượng (Case Máy 69 - 24/09/2026):**
  - Trong luồng reg tại bước `[2] Go to profile tab` hoặc `[3] Open account dropdown`, TikTok tự động mở màn hình phát video/LIVE (`ttlive_preview_surfaceview`).
  - Script nhận diện màn hình có các chữ "ĐĂNG", "TẠO", "LIVE" và cố gắng dismiss, nhưng bộ lọc `find_text_tap` tap nhầm vào node `com.ss.android.ugc.trill:id/z2q` ("Trò chơi di động" tại bounds `[393,1638][742,1694]`).
  - Điều này tạo ra vòng lặp vô tận: mỗi lần tap vào "Trò chơi di động", màn hình LIVE vẫn giữ nguyên, khiến script vắt kiệt thời gian và ném lỗi `[03_dropdown] Khong mo duoc account dropdown`.
- **Giải pháp dứt điểm:**
  - Bắt buộc kiểm tra chuỗi `ttlive_preview_surfaceview` hoặc text "Phát LIVE" / "Kiểm tra quyền truy cập LIVE".
  - Tap chính xác nút quay lại:
    - Resource ID: `com.ss.android.ugc.trill:id/eaw` (Button "Quay lại màn hình trước" tại `[18,72][150,204]`).
    - Fallback: `keyevent 4` (KEYCODE_BACK) để thoát dứt điểm màn hình LIVE về lại trang Profile chính.
    - Tuyệt đối KHÔNG tap vào các tab con trong RecyclerView đáy màn hình LIVE ("Máy ảnh thiết bị", "Trò chơi di động").

---

## 2. Xử Lý Lỗi `MACHINE_FULL_8_ACCOUNTS` (Lệch Excel & Nick Ký Sinh)
- **Hiện tượng (Case Máy 3 & Máy 61):**
  - Khi script mở Switcher tài khoản nhưng không tìm thấy nút "Thêm tài khoản", script đếm số lượng node tài khoản và báo lỗi `MACHINE_FULL_8_ACCOUNTS` (đã có 8 tài khoản trên app).
  - Tuy nhiên trong Excel (`taikhoan_dat_v2_updated .xlsx` & `taikhoan_run_safe.xlsx`), máy chỉ có 7 tài khoản (Slot 8 đang `None`).
- **Phân Loại Nguyên Nhân:**
  1. **Do Nick Ký Sinh (Đăng nhập nhầm từ máy khác):**
     - Ví dụ: Máy 61 chứa nick `@anggiathinh2905` (thuộc Máy 28 STT 221).
     - **Cách xử lý chuẩn:** Switch sang nick ký sinh -> Vào Menu 3 gạch -> Cài đặt và quyền riêng tư -> Cuộn xuống đáy chọn *Đăng xuất* -> Xác nhận.
     - *Lưu ý quan trọng:* User đã xác nhận *"Log out kí sinh đc mà k lỗi đâu"*. TikTok chỉ đăng xuất đúng nick đó, toàn bộ 7 nick còn lại được giữ nguyên 100%. Sau khi logout, Slot 8 được giải phóng và sẵn sàng reg bù.
  2. **Do Nút "Thêm Tài Khoản" Bị Che Khuất (Occluded UI):**
     - Ví dụ Máy 3: Switcher thực tế chỉ có 7 nick nhưng bottom sheet cần vuốt nhẹ lên để bộc lộ nút "Thêm tài khoản", tránh đếm nhầm node avatar/header thành nick thứ 8.
