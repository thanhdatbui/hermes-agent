# Transition Spinner Trap & Settled State Evidence Verification

**Ngày chốt:** 2026-10-29  
**Bối cảnh:** Sự cố Canary Reg Gmail Máy 03 — Agent gửi ảnh chụp lúc 08:12:48 hiển thị loading spinner xoay vòng (*"Google — Quá trình này có thể mất vài phút..."*) nhưng lại nhìn vào file XML lúc 08:13:02 để tuyên bố đã thấy màn hình nhập số điện thoại xác minh, bị User bắt lỗi trực diện (*"Gì v màn này đang load mà?"*).

---

## 1. Bản Chất Kỹ Thuật Của Bẫy Transition Spinner
- **Độ trễ tải trang (Network/RPC Latency):** Khi bấm nút hành động (Tiếp theo / Submit / Next / Login), trang web hoặc app Android gửi request lên backend (ví dụ Google WebView gửi RPC `AccountLifecyclePlatformSignupUi`). Quá trình xử lý mạng thường mất 5 - 15 giây.
- **Thời điểm chụp ảnh bị lệch (Desync Capture Timing):**
  - Runner thường gọi hàm chụp ảnh hoặc hook `shot(...)` ngay lập tức sau cú tap nút để ghi nhận đã bấm.
  - Ảnh sinh ra tại thời điểm $T_0$ là **màn hình trung gian chuyển cảnh (Loading Spinner / Progress Bar)**: *"Quá trình này có thể mất vài phút..."*, icon xoay tròn, màn hình trắng hoặc placeholder.
  - Sau đó runner bước vào vòng lặp chờ (`polling / wait_for_node`). Khi màn hình đích xuất hiện tại $T_1 = T_0 + 14s$, runner nhận diện được XML và dừng lại.
- **Ảo giác đối phó của AI (Hallucination & Careless Grounding):**
  - AI đọc file log hoặc file XML tại $T_1$ thấy có nội dung màn hình đích (ví dụ: *"Xác minh số điện thoại của bạn"*).
  - Nhưng khi đính kèm thẻ `MEDIA:<path>`, AI lại bốc nhầm file ảnh chụp tại $T_0$ (ảnh spinner).
  - Thay vì nhìn thực tế vào ảnh $T_0$ để biết ảnh đang load, AI lại lấy nội dung từ XML $T_1$ để "thuyết minh" cho bức ảnh $T_0$.
  - Hậu quả: Người dùng mở ảnh ra thấy rõ ràng màn hình đang quay vòng, trong khi AI chém gió là đã nhìn thấy nút bấm và ô nhập liệu. Đây là hành vi vi phạm nghiêm trọng Invariant Soi Mắt Đọc Ảnh.

---

## 2. Invariant Rules: Bắt Buộc Settled State Trước Khi Nghiệm Thu
1. **Quy Tắc Đối Soát Timestamp Kép (Screenshot ↔ UI Dump Timestamp):**
   - File ảnh nghiệm thu checkpoint BẮT BUỘC phải có timestamp bằng hoặc sau thời điểm file XML dump phát hiện trạng thái đích (`mtime(screenshot) >= mtime(ui_dump)`).
   - Nếu thư mục có nhiều ảnh cùng step (ví dụ `03_10_pass_next_attempt1_081248.png` vs `phone_verify_03_after_pass_081302.png`), BẮT BUỘC chọn file ảnh mang nhãn trạng thái đích cuối cùng (`phone_verify_*.png`), CẤM bốc ảnh hành động trung gian (`pass_next_attempt*.png`).

2. **Dấu Hiệu Nhận Diện Màn Hình Đang Tải (Transition State Markers):**
   Khi mở ảnh qua `browser_vision` hoặc WinRT OCR, nếu phát hiện bất kỳ dấu hiệu nào sau đây, **TUYỆT ĐỐI CẤM DÙNG LÀM ẢNH NGHIỆM THU CUỐI**:
   - Vòng tròn xoay / Loading Spinner / Progress indicator.
   - Text thông báo chuyển tiếp:
     * *"Quá trình này có thể mất vài phút..."* / *"This may take a few minutes..."*
     * *"Đang tải..."* / *"Loading..."* / *"Vui lòng chờ..."* / *"Please wait..."*
     * *"Đang kiểm tra thông tin..."* / *"Checking info..."*
   - Giao diện trống rỗng / Màn hình trắng đang đợi DOM render.

3. **Xử Lý Khi Bắt Gặp Màn Hình Đang Tải:**
   - **Không gửi ảnh mù:** CẤM gửi ảnh transition spinner kèm lời khẳng định đã tới màn hình đích.
   - **Chờ trang ổn định (Wait for Settled State):** Chờ thêm $3 - 5$ giây cho trang render xong hoàn toàn.
   - **Chụp lại Fresh Screencap:** Kéo ảnh chụp màn hình mới nhất từ thiết bị về đĩa, mở ra soi mắt lại qua vision xác nhận đã có đủ form/tiêu đề/nút bấm của màn hình đích rồi mới gửi `MEDIA:`.
