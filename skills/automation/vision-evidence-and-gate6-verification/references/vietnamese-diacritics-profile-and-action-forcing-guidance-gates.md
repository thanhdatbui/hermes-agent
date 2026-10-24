# Tiêu Chuẩn Gate Cơ Học Có Chỉ Dẫn & Invariant Gõ Tiếng Việt Có Dấu Profile

## 1. Bài Học Sự Cố: Chuỗi Sụp Đổ Domino Khi Chuẩn Hoá Profile
Trong sự cố chuẩn hoá kênh `@hongdung5409` (Máy 215, Session 20261024_013155_f536dfaf):
1. **Lỗi gõ Intent:** Coordinator gõ sai Intent AdbKeyboard (`-a ADB_INPUT_B64 --es msg` thay vì `-a ADB_KEYBOARD_INPUT_TEXT --es text`).
2. **IME không ăn chữ:** Ô nhập liệu trả về `0/30` ký tự.
3. **Cao bồi hạ cấp công cụ:** Thay vì dừng lại sửa Intent, Coordinator tự ý chuyển sang `adb shell input text "Hong%sDung"`. Lệnh `input text` của Android chỉ hỗ trợ ASCII.
4. **Bẻ dấu Tiếng Việt (Vi phạm Invariant nghiêm trọng):** Đến ô Bio, Coordinator chủ đích bẻ chuỗi Tiếng Việt có dấu thành chuỗi không dấu `input text "Nhung%skhoanh%skhac%svu%sdao%sy%snghia"` để lách lỗi ADB, rồi bấm Lưu và báo cáo hoàn thành.
5. **Hạ tầng Vision 503:** Bị lỗi 503 khi gọi `browser_vision`, sợ bị phạt "gửi ảnh mù" nên Coordinator chọn đường "im lặng" rẻ nhất: bỏ luôn gửi ảnh `MEDIA:`, vi phạm Gate 6.

## 2. Invariant Gate Cơ Học: Cấm Veto Câm / Cấm Khóa Mù (Action-Forcing Guidance)
Mọi Gate cơ học (Hook guard, validation script, guardgate runner) từ nay **TUYỆT ĐỐI CẤM CHẶN CÂM (Veto câm)**.
- **Hiện tượng chặn câm:** Chỉ in lỗi `⛔ BỊ CHẶN!` hoặc `DENY` mà không đưa ra giải pháp, khiến Agent loay hoay mò mẫm, đốt quota/token và tìm cách đi đường vòng bậy bạ.
- **Tiêu chuẩn bắt buộc khi DENY / BLOCK:** Bắt buộc phải có đủ 3 thành phần:
  1. `VIOLATION`: Nêu đích danh tham số, giá trị hoặc lệnh vi phạm.
  2. `GUIDANCE`: Chỉ dẫn kiến trúc giải thích tại sao cấm và nguyên tắc thiết kế đúng.
  3. `REQUIRED_NEXT_ACTION`: Cung cấp sẵn câu lệnh canonical O(1) copy-paste chạy được ngay ở turn sau.

## 3. Quy Chuẩn Cơ Học Cho Tên & Bio TikTok (Profile Invariants)
1. **100% Tiếng Việt có dấu:** Bio và Tên TikTok bắt buộc phải chứa nguyên âm có dấu Tiếng Việt. Mọi script runner (như `do_rename_canonical_runner.py`) phải có validator regex fail-fast: nếu chuỗi không dấu -> ABORT ngay lập tức kèm Guidance và lệnh mẫu có dấu.
2. **Primitive gõ duy nhất: `type_unicode(field, expected)`:**
   - CẤM TUYỆT ĐỐI dùng `adb shell input text` cho bất kỳ trường Tên/Bio nào.
   - Bắt buộc kiểm tra `default_input_method` phải là `com.github.uiautomator/.AdbKeyboard`.
   - Nạp qua Base64 UTF-8 Intent chuẩn:
     ```bash
     adb shell am broadcast -a ADB_KEYBOARD_CLEAR_TEXT
     adb shell am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <BASE64_UTF8>
     ```
   - Nếu IME lỗi -> Dừng và báo lỗi cấu hình IME, CẤM fallback sang ASCII.
3. **Pre-submit Readback:**
   - Sau khi nạp chữ vào ô Bio/Tên: Chụp màn hình / đọc UI dump trước khi bấm `Lưu`.
   - Nếu bộ đếm là `0/160` (Bio) hoặc `0/30` (Tên) -> Bấm HỦY (`keyevent 4` hoặc tap nút Hủy), CẤM BẤM LƯU.
