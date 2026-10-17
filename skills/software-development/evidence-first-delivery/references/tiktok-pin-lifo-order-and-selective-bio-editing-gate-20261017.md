# TikTok Pin LIFO Order & Selective Bio Editing Gate (17/10/2026)

## 1. Sự Cố Ảo Giác Thứ Tự Ghim (TikTok Pin Order Hallucination Trap)
- **Bối cảnh thực tế**: Kênh `@huy010822` (Máy 18) đang có sẵn 2 video ghim: `22,1K` và `5.2K`. Khi ghim thêm video `4.3K`, TikTok đưa video `4.3K` lên vị trí Cột 1 (trên cùng bên trái), đẩy `22,1K` sang Cột 2 (ở giữa), và `5.2K` sang Cột 3 (bên phải).
- **Sai phạm của Coordinator**: Coordinator gửi ảnh nhưng không đọc ảnh, tự suy diễn logic theo lý thuyết chủ quan rằng "video to nhất 22K sẽ đứng đầu", và phát ngôn báo cáo láo: *"1. Video Trái: 22,1K view - 2. Video Giữa: 5.2K view - 3. Video Phải: 4.3K view"*. User soi ảnh và chấn chỉnh ngay: *"Mày có đọc hình mày gửi chưa mà dám bảo video 22k đứng đầu? R đổi bio cho kênh này"*.
- **Bản chất cơ chế TikTok**:
  * TikTok hoạt động theo cơ chế **LIFO (Last-In-First-Out)** đối với các video ghim.
  * **Video nào ghim sau cùng sẽ LUÔN LUÔN nhảy vào ô đầu tiên bên trái `[0, 0]`**, đẩy các video đã ghim trước đó sang phải.
  * **Kỹ thuật Đảo Thứ Tự Ghim (LIFO Re-Pin Technique)**: Nếu muốn đưa video Hot nhất (ví dụ 22K) ra vị trí số 1 ngoài cùng bên trái khi nó đang bị đẩy vào giữa:
    1. Bấm **Bỏ ghim (UNPIN)** video 22K.
    2. Bấm **Ghim lại (RE-PIN)** ngay lập tức video 22K.
    👉 Vì 22K được ghim sau cùng, TikTok sẽ giật nó lên vị trí Cột 1 (Top-Left), đẩy các video 4.3K và 5.2K về sau: `[22K] - [4.3K] - [5.2K]`.
- **Kỷ luật Soi Mắt Độc Lập**:
  * Khi nghiệm thu lưới video ghim, BẮT BUỘC soi mắt hoặc chạy WinRT OCR độc lập từng cột:
    - Cột 1 (Trái, $x \approx 0..360$): Đọc chính xác số view thực tế.
    - Cột 2 (Giữa, $x \approx 360..720$): Đọc chính xác số view thực tế.
    - Cột 3 (Phải, $x \approx 720..1080$): Đọc chính xác số view thực tế.
  * TUYỆT ĐỐI CẤM giả định rằng video view cao nhất tự động đứng đầu.

---

## 2. Quy Trình Đổi Bio Chọn Lọc (Selective Bio Optimization) Cho Kênh Hot
- **Nguyên tắc phân tầng Farm (User Invariant)**:
  * **Kênh thường / Kênh mới (< 1.000 view)**: CẤM đổi bio hàng loạt tự động bằng script. Hành vi hàng chục máy cùng sửa profile trong thời gian ngắn (behavioral burst) làm lộ dấu chân farm và tụt trust score, dễ dính hạn chế phân phối (0 view / sandbox) dù AI có viết 80 câu bio khác nhau.
  * **Kênh HOT / Đã cắn đề xuất (> 10K view, > 500 follower như `@huy010822`)**: RẤT NÊN đổi bio. Kênh đã có trust score cao từ tương tác thật, việc cập nhật bio riêng lẻ giúp tăng mạnh tỷ lệ chuyển đổi từ người xem clip sang follower.
- **Quy trình thao tác UI qua ADB (TikTok v47+ Android 8)**:
  1. **Mở ProfileEditActivity**: Từ trang Profile chính, tap trực tiếp vào dòng chữ Bio hiện tại (hoặc "Thêm tiểu sử" tại tọa độ `(200, 660)`).
  2. **Vào màn hình Sửa tiểu sử**: Trong `ProfileEditActivity`, tìm dòng "Tiểu sử" (`com.ss.android.ugc.trill:id/tvLabel` tại `[84, 1284][414, 1380]`) và tap vào ô nội dung `(600, 1338)`.
  3. **Xóa nội dung cũ**:
     - Tap ô nhập liệu: `input tap 500 600`.
     - Nhảy về cuối: `input keyevent KEYCODE_MOVE_END (123)`.
     - Xóa sạch: Gửi `KEYCODE_DEL (67)` 15 lần.
  4. **Nhập Bio mới**:
     - Dùng lệnh `input text <escaped_text>` (thay khoảng trắng bằng `%s`, dùng tiếng Việt không dấu hoặc ASCII an toàn để tránh lỗi IME).
     - Ví dụ: `input text Hoc%ssinh%sngoan%snhung%shoi%sbat%son%s-%sFollow%stui%snha`.
  5. **CHECKPOINT 1 (Pre-submit / Post-fill - Bắt buộc)**:
     - Screencap lưu file `m18_bio_filled_chk1.png`.
     - Assert text mới đã nằm trọn vẹn trong ô input `EditText` (`[48, 540][1032, 990]`).
     - Assert nút "Lưu" (`[925, 72][1056, 204]`, tâm `(990, 138)`) đang sáng đỏ active.
     - Soi mắt qua `browser_vision` và gửi `MEDIA:`.
  6. **Bấm Lưu (Submit)**:
     - Tap nút Lưu tại `(990, 138)`.
     - Chờ 2.0 giây cho request lưu gửi lên server TikTok.
  7. **Thoát về Profile Root**:
     - Kiểm tra nếu còn trong `ProfileEditActivity` thì bấm Back `input keyevent 4`.
     - Tap tab Hồ sơ `input tap 972 1857` để refresh giao diện.
  8. **CHECKPOINT 2 (Post-submit / Verification - Bắt buộc)**:
     - Screencap lưu file `m18_profile_bio_updated_chk2.png`.
     - Chạy `verify_media_target(path, expected_handle)` qua `media_verify.py` đối soát WinRT OCR khớp 100% handle `@huy010822`.
     - Kiểm tra dòng Bio mới đã hiển thị công khai ngay dưới tên kênh.
     - Soi mắt qua `browser_vision` xác nhận không lỗi hiển thị, gửi `MEDIA:`.
