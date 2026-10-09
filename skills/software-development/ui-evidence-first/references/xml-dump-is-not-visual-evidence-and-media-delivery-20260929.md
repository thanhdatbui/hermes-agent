# Kỷ Luật "XML Dump Không Thay Thế Được MEDIA: Ảnh Thật" & Bẫy Snapshot Lệch Giờ (2026-09-29)

## 1. Sự cố "Hình đâu" — XML dump không phải là Visual Evidence
- **Bối cảnh:** Khi điều phối fix tài khoản M53 (`@mgpovhrgnnq`), Coordinator đã chạy canary login, đọc file UI XML dump (`profile_53_after_ensure_235557.xml`) thấy rõ text `@mgpovhrgnnq` và tuyên bố trong tin nhắn:
  *"ĐÃ HOÀN TẤT TRỌN VẸN CẢ 2 NỘI DUNG... Bằng chứng UI XML: File dump profile_53_after_ensure_235557.xml xác nhận tài khoản @mgpovhrgnnq đã active bình thường"*.
- **Phản ứng của User:** Ngay lập tức chất vấn: **"Hình đâu"**.
- **Bài học cốt lõi (Gate 6 Invariant):**
  - **Text trích từ XML dump chỉ là dữ liệu kỹ thuật trung gian**, KHÔNG PHẢI là Visual Evidence (bằng chứng thị giác).
  - Người vận hành cần nhìn thấy ảnh chụp thực tế bằng mắt trên Telegram để đối soát nhanh (tên hiển thị, avatar, giao diện app, pop-up che khuất nếu có).
  - **Quy tắc bất biến:** Turn báo cáo kết quả can thiệp UI/thiết bị BẮT BUỘC phải đính kèm dòng `MEDIA:<duong_dan_anh_tuyet_doi>` ngay trong turn đó.
  - Tuyệt đối CẤM báo xong bằng text thuần hoặc chỉ dẫn đường dẫn file XML mà bỏ quên ảnh chụp màn hình.

---

## 2. Quy trình chuẩn khi nghiệm thu tài khoản trên thiết bị
1. **Chụp ảnh trước khi teardown:**
   - Chụp màn hình đích (Profile hoặc Account Switcher).
   - Nếu màn hình đang bị dialog/popup che (ví dụ: popup hỏi quyền danh bạ/Facebook), phải bấm từ chối/đóng dialog rồi chụp lại ảnh sạch.
2. **WinRT OCR readback:**
   - Chạy OCR đọc lại ảnh vừa chụp để xác nhận có đúng handle/ID mục tiêu (`@username`).
3. **Đính kèm `MEDIA:` vào phản hồi:**
   - Đặt thẻ `MEDIA:<path>` ở đầu tin nhắn hoặc phần bằng chứng.
   - Gửi kèm 2 góc nhìn nếu là multi-account: (a) Màn hình Profile cá nhân; (b) Menu Account Switcher (chứng minh tài khoản active và các tài khoản khác trên máy an toàn).
4. **Mới được teardown:**
   - Sau khi ảnh đã lưu và verify OK mới gửi lệnh `input keyevent 3` (HOME) và tắt màn hình.

---

## 3. Bẫy Snapshot Báo Cáo Định Kỳ Lệch Thời Gian (Report Timing Mismatch)
- **Hiện tượng:** User vừa cập nhật danh sách mật khẩu/token Hotmail lúc 18:10, nhưng báo cáo 6h định kỳ lúc 18:00 vẫn ghi 5 tài khoản bị `BLOCKED: Rate limit do thu sai mat khau` khiến User tưởng hệ thống vẫn tiếp tục nhập sai pass.
- **Kỷ luật điều phối:**
  - Báo cáo định kỳ chỉ là snapshot tại thời điểm $T_{cron}$.
  - Khi User hỏi về lỗi trong báo cáo: BẮT BUỘC kiểm tra timestamp của `updated_at` trong `state.json` và log mới nhất so với thời điểm User thao tác.
  - Phân định rõ ràng giữa **"Lỗi cũ trong snapshot trước đó"** vs **"Lỗi đang tiếp diễn ở hiện tại"** để tránh hoang mang và không đổ oan cho hệ thống.
