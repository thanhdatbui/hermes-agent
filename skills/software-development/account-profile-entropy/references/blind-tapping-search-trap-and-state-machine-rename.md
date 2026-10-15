# Lessons Learned: Bẫy Blind Tapping Tọa Độ Top-Left (75, 150) & Cú Lừa Tìm Kiếm Bạn Bè Trên TikTok S7

## 1. Hiện Tượng Thực Tế
Khi điều khiển giao diện TikTok Android (bản v47.x trên Samsung S7 độ phân giải 1080x1920) để thực hiện đổi Tên hiển thị (Display Name):
- Script tự động tap mù vào tọa độ `(75, 150)` với suy nghĩ đây là nút Back/Quay lại.
- Trên thực tế:
  * Góc trên bên trái của trang **Hồ sơ (Profile)** là icon **"Tìm bạn bè / Thêm bạn" (Find Friends)** (hình người có dấu `+`), hoàn toàn không phải nút Quay lại.
  * Cú tap vào `(75, 150)` mở màn hình **Tìm bạn bè**.
  * Thanh Search trên cùng tự động được chọn (focused).
  * Lệnh gõ tên mới tiếp theo qua `AdbKeyboard` gõ thẳng chuỗi tên (ví dụ: `Hải Cường`) vào ô Search và tự động kích hoạt tìm kiếm!
  * Màn hình TikTok hiển thị:
    - Search box: `Hải Cường`
    - Nội dung giữa màn hình: **`Không tìm thấy kết quả`**
    - Đáy màn hình: Bàn phím AdbKeyboard hiển thị 4 nút: `[∞] [Clear Text] [Search] [Switch IME]`.

## 2. Hậu Quả & Rủi Ro Nghiêm Trọng
- Script không có khâu OCR Readback Verification:
  * Chụp ảnh màn hình "Không tìm thấy kết quả" nhưng vẫn ngộ nhận là đã đổi tên thành công.
  * Báo cáo ảo hoàn tất lên hệ thống trong khi tên nick không hề đổi.

## 3. Quy Chuẩn Kỹ Thuật Bắt Buộc (Anti-Blind Tapping Invariant)
1. **Tuyệt đối cấm tap mù tọa độ**:
   - CẤM gọi `tap(75, 150)` trên màn hình Profile.
   - Để vào trang Sửa hồ sơ, BẮT BUỘC dùng OCR tìm text `Sửa hồ sơ` / `Chỉnh sửa hồ sơ` (`(210, 865)`) hoặc icon cây bút chì bên phải dòng tên `(870, 558)`.
2. **State-Machine 5 Trạng Thái Khép Kín**:
   - `FEED` -> tap tab Hồ sơ `(972, 1857)`.
   - `PROFILE` -> đọc `nickname_on_profile`. Nếu chưa đúng acc mục tiêu thì mở Switcher.
   - `EDIT_PROFILE` -> OCR tìm dòng có chữ "Tên" rồi mới tap mở ô sửa tên.
   - `NAME_EDIT` -> gõ AdbKeyboard -> BẮT BUỘC đọc lại OCR kiểm tra tên mới + bộ đếm ký tự `{len}/30` -> tap Lưu `(980, 140)`.
   - `PROFILE (Readback)` -> Trở lại Profile, OCR đọc lại dòng ngay trên `@username`. Chỉ khi tên thật trên Profile khớp 100% với tên mới thì mới lưu trạng thái hoàn thành.

## 4. Quy Chuẩn Vận Hành 25 Workers Song Song & Fail-Safe Vững Chắc

1. **Back an toàn bằng phím cứng KEYCODE_BACK**:
   - Mọi thao tác lùi trang (từ Sửa tên về Sửa hồ sơ, từ Sửa hồ sơ về Hồ sơ) **BẮT BUỘC dùng `input keyevent 4`**.
   - Tuyệt đối CẤM tap tọa độ góc trên bên trái (`75, 150` hay `72, 148`) vì nếu màn hình vô tình ở tab khác hoặc đã back về Profile sớm, cú tap đó sẽ rơi trúng icon "Tìm bạn bè".

2. **Switcher Preflight Guard (Chống Sửa Đè Nick Khác)**:
   - Trước khi sửa tên, bắt buộc đọc `@username` trên Profile.
   - Nếu `active_user != target_user`: Mở Switcher tại `(500, 140)`.
   - Tìm kiếm `target_user` trong Switcher:
     * Nếu tìm thấy: Tap chọn để chuyển nick (chờ 6s).
     * Nếu KHÔNG tìm thấy: Bấm `keyevent 4` thoát an toàn và trả về `(None, False)`. **CẤM TUYỆT ĐỐI sửa đè lên nick đang active trên máy!**

3. **Chống Crash Toàn Cụm Khi Đơ ADB Transport**:
   - Khi chạy 25 workers đồng loạt, nếu 1 máy bị lỏng cáp hoặc ADB daemon trên điện thoại bị đơ, lệnh ADB sẽ văng `subprocess.TimeoutExpired`.
   - Hàm `adb(serial, *args, timeout=15)` bắt buộc bọc `try...except Exception: return ""` (hạ timeout xuống 15s).
   - Vòng lặp thu thập kết quả `as_completed([pool.submit(_worker, t) for t in targets])` bắt buộc bọc `try...except Exception: pass` cho từng `fut.result()` để sự cố của 1 máy không bao giờ làm sập cả batch.

4. **Cấu Hình Cronjob Hermes Tránh False Alert Timeout**:
   - Tác vụ 25 workers song song thực thi qua ADB + OCR thường mất từ 60s – 120s.
   - Cronjob của Hermes nếu để `deliver: 'origin'` sẽ bị gateway timeout sau 60s và bắn tin nhắn cảnh báo giả `provider timeout` về Telegram dù tiến trình nền vẫn hoàn tất 100%.
   - **BẮT BUỘC đặt `deliver: 'local'`** cho các batch watchdog nặng để tiến trình chạy ngầm im lặng, ghi log local và triệt tiêu tin nhắn spam báo ảo.

5. **Độ Trễ Khởi Động App (Splash / Cold Boot Latency Trap trên Samsung S7)**:
   - Trên các thiết bị phần cứng cũ (Galaxy S7), TikTok khởi động nguội (cold boot) thường mất từ 10–20s để vượt qua màn hình Splash ("TikTok" logo giữa màn hình đen/trắng).
   - **Cạm bẫy kịch bản tuyến tính (Linear Script)**: Dùng `time.sleep(5-6s)` cố định rồi tap ngay vào tab Hồ sơ sẽ khiến cú tap rơi vào màn hình Splash và bị nuốt chửng (dropped). Sau đó các cú tap tiếp theo rơi lệch vào Feed hoặc LIVE.
   - **Quy chuẩn State Machine bắt buộc**:
     * Nếu OCR thấy `UNKNOWN` (chỉ có chữ "TikTok" hoặc ít hơn 3 dòng text không có nút bấm): tiếp tục chờ 3-4s và chụp lại, CẤM tap mù tiếp theo.
     * Tự động dọn dẹp Search kẹt từ phiên trước: Nếu mở app lên mà thấy màn hình Search / Search Results (`id/hu0` hoặc thanh tìm kiếm có nút X), BẮT BUỘC bấm `keyevent 4` (Back) 2–3 lần để lùi về Feed/Home trước khi vào Profile.

6. **Kỷ Luật Phản Hồi Khi User Hỏi Số Worker**:
   - Khi User hỏi *"Đang chạy worker bn đó"*, Coordinator phải phân biệt chính xác ngữ cảnh tác vụ User đang quan tâm (ví dụ: số worker của watchdog đang cấu hình vs số worker của ca nuôi feed toàn farm), cấm trả lời lệch trọng tâm gây hiểu lầm.

