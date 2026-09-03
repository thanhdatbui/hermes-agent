# AI Autonomous Recovery & 2-Part Farm Alerts Protocol (19/08/2026)

## 1. Bản Chất Của Auto-Recovery Bằng AI
- Khi thiết bị farm gặp sự cố gián đoạn (popup lạ, ad feedback, live room, recommendation card, mismatch state...):
  - **CẤM RẬP KHUÔN IF/ELSE HOẶC BÁO CÁO LÝ THUYẾT**: Tuyệt đối không dùng các câu lệnh if/else cứng nhắc để phán đoán lỗi chung chung ("Dừng phiên bất thường ➔ Đưa về Home") hay đưa ra các đề nghị suông ("Đề nghị cung cấp XML...").
  - **AI CỦA SESSION TRỰC CHIẾN XỬ LÝ**: AI của chính session chat đọc trực tiếp ảnh chụp hiện trường và ngữ cảnh để:
    1. Chuẩn đoán đích danh nguyên nhân kẹt tại màn hình.
    2. Tự động nhảy vào vá code / cập nhật rule trong repo tương ứng.
    3. Xuất diff và gọi Model Plan-Review độc lập (`claude -p --effort max` / `9router plan-review`) audit an toàn và nhận `VERDICT: APPROVED`.
    4. **Test trực tiếp hàm vừa sửa ngay tại hiện trường máy đang kẹt** (CẤM chạy lại từ đầu).
    5. Báo cáo kết quả hoàn tất vào nhóm Farm Alerts và push Git đồng bộ toàn farm.

## 2. Quy Chuẩn Tin Nhắn Báo Cáo 2 Phần Vào Nhóm Farm Alerts (`-5373649734`)

### Phần 1: Báo lỗi hiện trường nguyên trạng
- Chụp ảnh màn hình lúc kẹt, vẽ Banner Đỏ `[MAY XX] - HH:MM DD/MM` ở đỉnh ảnh.
- Caption kèm ảnh:
  ```
  🚨 [MÁY XX] DỪNG PHIÊN
  • Script: <tên_script>
  • Tài khoản: <username>
  • Lý do: <lý_do_kỹ_thuật_cụ_thể>
  • Trạng thái: 🟢 ĐANG MỞ (Tự động chạy tiếp phiên sau)
  ```

### Phần 2: Báo cáo AI Auto-Recovery
- Gửi tin nhắn text ngay sau ảnh, gồm 2 mục cốt lõi: **Hướng sửa** & **Kết quả**:
  ```
  🛠️ [AI AUTO-RECOVERY - MÁY XX]
  • Hướng sửa: <Phân tích màn hình thực tế và giải thích logic vá script/handler>
  • Kết quả: <Hành động cụ thể đã thực hiện & kết quả test vượt qua bước kẹt về Feed/Hoàn thành>
  • (Nếu đúng ý bạn im lặng bỏ qua, cần sửa cách khác hãy nhắn lại)
  ```

## 3. Pitfall Tiến Trình Chạy Ngầm Trong RAM (Stale Memory Bytecode)
- Khi phát hiện alert vẫn gửi theo mẫu cũ hoặc hành vi cũ sau khi đã sửa code:
  - **Nguyên nhân**: Các tiến trình Python chạy nền (feed session, follow, reg...) được khởi động từ trước vẫn đang chạy và giữ bytecode cũ trong RAM.
  - **Xử lý**: Rà soát `psutil.process_iter` / `tasklist`, kill sạch các tiến trình cũ trước khi chạy kiểm tra lại.

## 4. Xử Lý Các Thẻ / Popup Đặc Thù
- **Thẻ gợi ý "Người mà bạn có thể biết" / "Hằng nguyễn"**: Người vận hành chỉ định **BẤM NÚT "Follow lại"** (màu đỏ) thay vì "Không quan tâm".
- **Khảo sát quảng cáo (Pepsi / Brand Ad)**: Vuốt trượt dứt khoát sang video tiếp theo.
- **Phòng Live / TikTok Shop / Recent apps rỗng**: Tự động thoát và quay về Feed chính.
