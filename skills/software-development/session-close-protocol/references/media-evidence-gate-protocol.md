# Quy Chuẩn Nghiệm Thu Bằng Chứng Ảnh Màn Hình Thật (MEDIA Evidence Gate Protocol)

Ngày ban hành: 12/09/2026.
Tác nhân: Claude Code CLI Audit theo yêu cầu của Tad sau sự cố Admin Hermes Bot quên gửi ảnh kết quả chạy máy M246.

---

## 1. NGUYÊN NHÂN SỰ CỐ "QUÊN GỬI ẢNH KẾT QUẢ"
- **Bẫy điều kiện mềm ("Khi cần" / "Khi có yêu cầu"):** Trong prompt cũ, câu chữ mang tính tùy chọn khiến LLM tự suy diễn rằng "task thành công theo stdout rồi thì không cần gửi ảnh nữa".
- **Xung đột phân vai (Diffusion of Responsibility):** Coordinator ở main session nghĩ Worker subagent đã gửi; Worker trong subagent không có kênh Telegram nên chỉ log text; cuối cùng không ai gửi ảnh cho User.
- **Xung đột Budget:** Khi gần cạn tool budget hoặc context window, LLM ưu tiên text summary và cắt bỏ bước capture screencap.

---

## 2. QUY TẮC CỨNG (INVARIANT CONTRACT)

### Điều 1: Phạm Vi Bắt Buộc
Áp dụng cho TOÀN BỘ các phiên làm việc có can thiệp máy farm (chạy batch script, test automation, fix lỗi UI/popup, farm alert, recovery, live canary).

### Điều 2: Trách Nhiệm Phân Tầng
1. **Worker (Subagent):**
   - Sau khi hoàn thành thao tác automation, Worker BẮT BUỘC chụp screencap màn hình máy thật lưu file local.
   - Bàn giao đường dẫn tuyệt đối của file ảnh trong kết quả trả về cho Coordinator (ví dụ: `ARTIFACT_IMAGE: C:/Users/Kibe/m246_verified.png`).
2. **Coordinator (Main Session):**
   - Kiểm tra đường dẫn ảnh từ Worker (hoặc tự chạy ADB screencap O(1) theo serial nếu Worker thiếu).
   - Đính kèm thẻ `MEDIA:<đường_dẫn_tuyệt_đối>` ở dòng riêng biệt trong tin nhắn báo cáo kết quả gửi User.
   - **TỪ CHỐI BÁO CÁO:** Báo cáo task farm mà THIẾU thẻ `MEDIA:` bị coi là VI PHẠM GATE NGHIỆM THU, TASK CHƯA HOÀN THÀNH.

---

## 3. BẪY KỸ THUẬT ĐƯỜNG DẪN ẢNH (MEDIA TAG PATH PITFALLS - 13/09/2026)
1. **Ký tự Escape Backslash (`\\`) trên Windows:**
   - Khi viết đường dẫn dùng dấu gạch chéo ngược Windows (ví dụ `D:\\Taadaa\\...\\thachkieu.png`), cụm `\\t` bị Python/JSON diễn giải thành ký tự **Tab (`\\t`)**, làm hỏng đường dẫn thực tế (`...\\	hachkieu.png`).
   - Hậu quả: Gateway không tìm thấy file, tự động bỏ qua việc gửi ảnh và để nguyên chuỗi text `MEDIA:...`.
   - **Quy tắc bắt buộc:** MỌI thẻ `MEDIA:` BẮT BUỘC dùng dấu gạch chéo xuôi `/` (ví dụ `MEDIA:D:/Taadaa/...`). CẤM TUYỆT ĐỐI dùng `\\`.
2. **Khoảng trắng trong đường dẫn (Space Pitfall):**
   - Thư mục chứa dấu cách (ví dụ `D:/Taadaa/GPM auto/...`) khiến Regex parser của Telegram Gateway nhận diện sai ranh giới đường dẫn hoặc match hỏng đuôi mở rộng `.png`.
   - **Quy tắc bắt buộc:** Nếu thư mục nguồn có dấu cách (như `GPM auto`), Coordinator phải copy ảnh sang thư mục chuẩn không có dấu cách (ví dụ `C:/Users/Kibe/AppData/Local/hermes/image_cache/proof_<name>.png`) trước khi phát thẻ `MEDIA:`.
