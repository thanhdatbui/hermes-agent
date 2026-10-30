# Bẫy Thuyết Minh Kết Quả Tương Lai Khi Màn Hình Vẫn Ở Trạng Thái Cũ (State-Desync Evidence Trap)

## 1. Hiện Tượng & Nguyên Nhân (Sự Cố Session Muse AI / Facebook OAuth)
- **Bối cảnh:** Khi thực hiện quy trình đăng nhập tài khoản bên thứ 3 (Facebook, Google, TikTok), Agent tường trình bằng lời rằng *"sau khi điền mật khẩu thì Facebook bắt buộc gửi mã về WhatsApp/SMS +216...77 và văng lỗi Invalid Request"*.
- **Sai phạm phát hiện bởi User:**
  - Ảnh `MEDIA:` mà Agent đính kèm thực tế lại là ảnh màn hình đang ở ô nhập mật khẩu (`D:/fb_after_select_pass.png`), ô mật khẩu còn trống hoặc chưa bấm nộp.
  - User lập tức chất vấn: *"Hình mày chụp vẫn đang ở ô nhập mật khẩu"* -> Phản ánh tình trạng **Lệch Pha Trạng Thái (State-Desync)** giữa **Lời Thuyết Minh** và **Nội Dung Ảnh Thực Tế Đính Kèm**.
- **Nguyên nhân gốc rễ:**
  - Agent thực hiện một chuỗi thao tác đa bước (Điền mật khẩu -> Bấm Submit -> Bị văng lỗi -> Chuyển hướng). Nhưng khi gửi báo cáo, Agent lại gửi nhầm ảnh chụp ở bước trung gian (hoặc ảnh chụp trước khi submit) cùng với lời thuyết minh về kết quả của bước sau đó.
  - Người dùng chỉ nhìn thấy ảnh đính kèm và kết luận Agent nói dối hoặc suy diễn kết quả khi ảnh không khớp với lời khẳng định.

## 2. Quy Tắc Bắt Buộc: 1 Cặp Bằng Chứng = 1 Trạng Thái Nhất Quán (Atomic Evidence Pair)
Khi mô tả kết quả của một hành động UI (Ví dụ: "Bấm nút X bị lỗi Y"):
1. **Không thuyết minh kết quả của bước N+1 khi chỉ đính kèm ảnh của bước N:**
   - Nếu chụp ảnh ở màn hình nhập form (Checkpoint 1: Pre-submit) -> Chỉ được xác nhận: *"Dữ liệu đã được điền lên form trước khi submit"*.
   - TUYỆT ĐỐI CẤM đính kèm ảnh Pre-submit rồi khẳng định: *"Nó đã bị lỗi XYZ ở màn hình tiếp theo"*.
2. **Khẳng định kết quả bắt buộc đính kèm chính xác ảnh màn hình kết quả (Checkpoint 2: Post-action):**
   - Muốn báo "Sai mật khẩu" -> BẮT BUỘC chụp và gửi ảnh có dòng chữ đỏ *"Bạn đã nhập sai thông tin đăng nhập"*.
   - Muốn báo "Bắt xác minh WhatsApp" -> BẮT BUỘC chụp và gửi đúng ảnh màn hình có ô nhập mã WhatsApp và số điện thoại.
   - Muốn báo "Bị lỗi Invalid request" -> BẮT BUỘC chụp và gửi đúng ảnh có popup *"Invalid request"*.
3. **Cơ chế kiểm soát trước khi phát ngôn (Pre-delivery Visual Verification):**
   - Trước khi viết lời giải thích, Coordinator phải tự hỏi: *"Bức ảnh mình chuẩn bị đính kèm thẻ MEDIA: này có chứa đúng chi tiết/thông báo mà mình sắp nói không?"*.
   - Nếu ảnh đang là form đăng nhập mà lời nói là "nó đòi mã SMS" -> DỪNG LẠI NGAY, chụp lại đúng màn hình đòi mã SMS rồi mới được phát ngôn.
