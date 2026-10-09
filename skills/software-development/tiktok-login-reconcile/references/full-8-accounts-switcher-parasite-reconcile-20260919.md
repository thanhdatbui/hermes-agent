# Quy Trình Đối Soát Hiện Trường Khi Máy Chạm Trần 8 Nick (MACHINE_FULL_8_ACCOUNTS)

## 1. Bối cảnh & Hiện tượng (2026-09-19)
- **Triệu chứng**: Khi chạy reg bù (Row 7 hoặc Row 8) hoặc auto-login reconcile, runner văng lỗi:
  - `[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`
  - Hoặc: `[04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account', ...)`
- **Nghịch lý dữ liệu**:
  - Master Excel (`taikhoan_dat_v2_updated .xlsx`) và Safe Excel (`taikhoan_run_safe.xlsx`) ghi nhận máy mới có 6 hoặc 7 nick (chưa đầy 8).
  - Nhưng trên máy thật, app TikTok từ chối hiển thị nút "Thêm tài khoản".

---

## 2. Phương pháp Đối Soát Hiện Trường O(1) (Không Quét Đĩa)

Thay vì chạy grep/find diện rộng hoặc đoán mò, Coordinator thực hiện 3 bước O(1):

1. **Trích xuất Artifact Run Thất Bại Gần Nhất**:
   - Kiểm tra thư mục artifacts run: `D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/<latest_run_id>/`
   - Đọc XML dump lúc fail: `D:/Taadaa/runtime/kibe/artifacts/ui_dumps/fail_04_add_account_*.xml`
   - Lấy danh sách `<node resource-id="...:id/ndk" text="<username>">` để xem chính xác 8 nick đang có trong Switcher.

2. **OCR / Screencap Dropdown Switcher**:
   - Nếu XML bị kẹt hoặc stale, dùng ảnh chụp dropdown lúc fail:
     `D:/Taadaa/Tiktok_Reg/screenshots_social/<machine>_03_dropdown_*.png`
   - Chạy OCR nhanh qua Windows Native OCR (`do_ocr.ps1` với đường dẫn Windows chuẩn `D:\Taadaa\...`) để đọc 8 handle.

3. **Đối chiếu Chéo (Cross-Check) với Master DAT**:
   - Với mỗi nick xuất hiện trên máy thật: tra cứu xem nick đó thuộc máy nào trong `taikhoan_dat_v2_updated .xlsx`.
   - Phân loại 2 nguồn nick gây đầy trần:
     - **Nick đi lạc (Cross-machine parasite)**: Nick chính chủ của máy khác (ví dụ nick của M16 hoặc M26 xuất hiện trên M40, M42).
     - **Nick ngoài luồng (Unrecorded / zombie)**: Nick tạo thử nghiệm hoặc reg dở dang nhưng chưa kịp ghi vào Excel (ví dụ `@guadazvvrn5`, `@thanhlee327`).

---

## 3. Quy trình Xử lý An Toàn (Zero-Logout Collateral Protection)

1. **TUYỆT ĐỐI CẤM**:
   - Bấm "Đăng xuất" trong Settings của app TikTok khi đang ở profile bất kỳ mà không kiểm tra (Settings -> Log out sẽ xóa sạch phiên của TẤT CẢ các nick trên thiết bị).

2. **Quy trình Logout Chuẩn cho Nick Ký Sinh**:
   - Bước 1: Mở app TikTok, vào tab Profile -> Mở dropdown Switcher.
   - Bước 2: Tap switch sang đúng nick ký sinh mục tiêu.
   - Bước 3: Vào Menu 3 gạch -> Settings and privacy -> Cuộn xuống đáy -> Bấm Đăng xuất -> Xác nhận đăng xuất nick đó.
   - Bước 4: Sau khi đăng xuất, TikTok tự động chuyển về nick còn lại trên máy. Mở lại Switcher để xác minh nút "Thêm tài khoản" đã tái xuất hiện (số nick < 8).
   - Bước 5: Đưa app về Home và tắt màn hình / nhả lock.
