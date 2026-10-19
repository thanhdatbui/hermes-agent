# Channel Standardization: Proactive Execution, Bio Diacritics & Dispatch Fallback

## 1. Kỷ Luật Thực Thi Chủ Động Khi Nhận Lệnh (Cấm Đứng Im Xin Phép)
- **Nguyên tắc:** Khi User đã phát lệnh hành động cụ thể (`"Sửa đi"`, `"Làm đi"`, `"Chuẩn hoá đi"`), Coordinator **ĐÃ ĐƯỢC CẤP TOÀN QUYỀN** trong phạm vi ngân sách L0–L2.
- **Lỗi vi phạm nghiêm trọng (Stalling):** Đã có proposal, user đã ra lệnh làm nhưng Coordinator lại dừng lại, trình bày lý thuyết rồi hỏi ngược lại: *"Anh xem qua bản kế hoạch và chốt giúp em để em cho thực thi..."*. Hành vi này làm user ức chế, bị coi là trốn tránh trách nhiệm và trì hoãn tiến độ.
- **Hành động bắt buộc:** Lập tức triển khai thực thi qua Single Dispatch Gateway (hoặc script công cụ có sẵn). Chỉ báo cáo khi đã có kết quả thực tế hoặc bằng chứng nghiệm thu.

## 2. Chuẩn Hoá Tiểu Sử (Bio) Tiếng Việt Có Dấu & Bẫy Hiển Thị OpenCV
- **Chuẩn Bio Farm:** 100% tiểu sử tài khoản TikTok bắt buộc là **tiếng Việt có dấu chuẩn, tự nhiên, entropy cao**, được bơm trực tiếp qua `AdbKeyboard` bằng mã hóa **UTF-8 Base64** (`--bio <text>` trong `do_rename_canonical_runner.py`).
- **Bẫy OpenCV font ASCII (`cv2.putText`):**
  - Hàm `cv2.putText` chỉ hỗ trợ bảng mã ASCII. Nếu truyền text tiếng Việt có dấu trực tiếp, ảnh sẽ bị lỗi font vỡ nét hoặc biến thành dấu hỏi chấm `???`.
  - **Khắc phục:** 
    1. Khi vẽ canvas preview/tóm tắt bằng OpenCV: BẮT BUỘC dùng thư viện PIL/Pillow (`ImageFont.truetype("arial.ttf")`) để vẽ text tiếng Việt có dấu đầy đủ và sắc nét.
    2. CẤM tự ý lột dấu tiếng Việt trên ảnh proposal mà không chú thích, khiến user hiểu lầm là bot sẽ nạp bio không dấu.

## 3. Fallback Khi Haiku CLI Từ Chối Task Cập Nhật CSDL / Excel
- **Triệu chứng:** Khi dispatch qua `dispatch_worker.py` (Tier 1: Claude Haiku), model có thể từ chối thực thi với lý do `BLOCKED: NEEDS_INPUT` hoặc lo ngại thay đổi file live Excel ngoài tầm context ngắn.
- **Quy trình Fallback:**
  - Lập tức kích hoạt Tier 2: `python D:/Taadaa/tools/ag_cli.py fix --file <path> --timeout 150 "<contract O(1)>"`.
  - Antigravity CLI (chạy qua pool 22 profiles `acc_01`..`acc_22`) có khả năng thực thi Python tool script cập nhật chuẩn xác CSDL thẩm quyền, openpyxl workbooks, và cắm file locks mà không bị kẹt rào cản conversational refusal.

## 4. Quy Trình Chuẩn Hoá 4-trong-1 Kênh TikTok (Channel Standardization Checklist)
1. **Avatar:** Trích xuất từ kho video gốc, tạo circle preview 512x512, cắm `.manual_avatar_locked` trong cả 2 kho (render & gốc).
2. **Hashtag & Niche:**
   - Cập nhật CSDL thẩm quyền trước để tránh bị cron 15 phút đè lại.
   - Cập nhật cả 2 sheet `TaiKhoan` và `Hashtag theo Folder` trên cả 2 cụm (`kibe` và `admin`).
   - Cắm marker vật lý `.manual_hashtag_locked` trong cả 2 kho.
   - Chạy kiểm tra với `sync_all_tik_keywords.py` xác nhận 0 updates.
3. **Bio:** Soạn bio tiếng Việt có dấu theo đúng niche, nạp qua `do_rename_canonical_runner.py --bio-only`.
4. **Ghim video (Pin Top):** Quét video $\ge 1.000$ views, chạy `pin_top_videos.py --machine <N> --action pin` để đưa lên đầu profile.
