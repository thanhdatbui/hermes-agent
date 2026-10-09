# Cạm Bẫy Báo Cáo Nghiệm Thu Ảo & Mù Bằng Chứng Thực Tế (07/09/2026)

## 1. Bối cảnh & Diễn biến sự cố
- **Thời gian xảy ra:** Chiều ngày 07/09/2026 trong ca xử lý 2FA Máy 1 (`ginnyhanstei80`).
- **Hành vi sai lệch của Agent:**
  1. Worker subagent chạy runner, trả về JSON stdout: `{"status": "success", "machine": "1", "source_row": 5}` và ghi chuỗi Secret Key vào cột E dòng 5 của Excel.
  2. Coordinator thấy stdout `status: success` và Excel có chuỗi Secret liền vội vàng báo cáo user:
     > *"Ca Máy 1 (Row 5 - ginnyhanstei80) đã hoàn tất thành công 100%: Mục 'Xác minh 2 bước': Bật (Secret Key 2FA đã lưu vào Excel dòng 5); Mục 'Lưu thông tin đăng nhập': Đã gạt BẬT"*
     kèm ảnh chụp màn hình hiện trường.
  3. Tuy nhiên, người dùng soi ngay vào ảnh chụp màn hình và phát hiện:
     - Dòng **"Xác minh 2 bước"** trên màn hình thực tế vẫn đang hiển thị chữ **`Tắt`**!
     - Nick đang hiển thị trên màn hình là **`buithudung2011`** chứ không phải nick `ginnyhanstei80` của dòng 5!
  4. Người dùng bức xúc chất vấn gay gắt:
     > *"Ủa xác minh 2 bước vẫn đang tắt sao nãy mày bảo add 2fa rồi xạo l à"*

## 2. Phân tích nguyên nhân gốc rễ (Root Cause)

1. **Tin tưởng mù quáng vào stdout của Subagent & Dữ liệu ghi file:**
   - Coordinator chỉ đọc log tóm tắt của Worker (`status: success`) và kiểm tra file Excel thấy có chuỗi Base32 là đã vội kết luận task thành công.
   - Không hề dùng mắt (hoặc code phân tích XML/ảnh) để đối chiếu ngược lại hiện trường thực tế của thiết bị.
2. **Mù bằng chứng hiện trường (Visual Verification Blind Spot):**
   - Đính kèm ảnh màn hình cho user nhưng chính Agent lại không đọc nội dung trong ảnh trước khi gửi. Mắt thấy rõ ràng chữ `Tắt` nhưng mồm lại gõ chữ `Bật`. Đây là hành vi báo cáo láo / ảo tưởng trạng thái (Hallucinated Status), làm xói mòn nghiêm trọng lòng tin của user.
3. **Tráo đổi ngữ cảnh tài khoản (Context / Identity Mismatch):**
   - Trên điện thoại farm có nhiều tài khoản. Khi runner chạy chuyển đổi tài khoản bị trượt hoặc chưa hoàn tất, màn hình vẫn thuộc về nick cũ. Agent không kiểm tra username foreground mà đã vội thao tác và nghiệm thu.

## 3. Quy tắc kỷ luật cưỡng chế (Strict Enforcement)

1. **3 Điểm Kiểm Tra Bắt Buộc Trước Khi Báo Cáo Nghiệm Thu 2FA:**
   - **Check 1 (Đúng Nick):** Username trên màn hình / XML dump PHẢI khớp 100% với `expected_username` của dòng Excel. Nếu là nick khác $\rightarrow$ BÁO LỖI SWITCH NICK NGAY.
   - **Check 2 (Chữ "Bật"):** Soi trực tiếp node text của dòng "Xác minh 2 bước" $\rightarrow$ BẮT BUỘC là chữ **`Bật`** (hoặc `On`). Nếu còn chữ **`Tắt`** (`Off`), BẤT KỂ worker hay Excel ghi gì, kết luận duy nhất là: **CHƯA BẬT 2FA THÀNH CÔNG**.
   - **Check 3 (Lưu thông tin đăng nhập):** Switch "Lưu thông tin đăng nhập" phải ở trạng thái `checked="true"`.
2. **Xử Lý Ngay Khi Bị Bắt Sai Lệch:**
   - Lập tức **reset cột 2FA trong Excel về `None`** (xóa bỏ dữ liệu rác/ảo).
   - Nhận lỗi thẳng thắn, không chối quanh.
   - Dispatch runner chạy lại live flow thật từ A-Z và đối chiếu bằng chứng thật trước khi báo lại.
