# Mechanical Visual Evidence Judge: Claude Reviewer Approval & Anti-Ad-Hoc Script Invariant (2026-10-18)

## 1. Sự Cố Thực Tế & Lời Chấn Chỉnh Từ Người Dùng
Trong phiên làm việc xử lý đổi Avatar cho Máy 34 (Slot 6, `@yobi1965`):
- **Bẫy Đẻ Script Ad-Hoc**: Khi runner chuẩn `run_avatar_batch_3accs.py` bốc nhầm ảnh chậu cây kim tiền (do rác MediaStore và cache thumbnail video cũ), Coordinator thay vì dọn dẹp MediaStore sạch sẽ lại tự tiện viết script ad-hoc tap ADB trần (`do_save_avatar_m34.py`, `do_upload_avatar_m34_exact.py`). Hậu quả: tap trượt tọa độ, tap nhầm ảnh trình duyệt, vướng checkbox Story, làm kẹt nick và mất thời gian cả buổi chiều.
- **Phản ứng gay gắt của User**: 
  > *"Và tại sao lại có cái script lồn gì avatar 34.py? Tao đã thiết kế script upload ava r mà?"*
  > *"Là h mọi công việc khi llm gửi ảnh đều đọc lại ảnh trc khi gửi chưa"*
  > *"kiểm tra hệ thống có cái guard tương tự sẵn chưa, chưa có thfi mày thi công luôn đi"*
  > *"Claude cli hồi r bảo nó chấm điểm / R mày làm đến khi nó duyệt"*

## 2. Lỗ Hổng Kiến Trúc Claude Sonnet 5.5 Bóc Tách (Strike 1 Review)
Khi Claude Sonnet 5.5 Reviewer thẩm định bản thảo đầu tiên của `visual_judge.py` và `verify_media_gate.py`, reviewer đã **REJECT** và chỉ rõ 4 lỗ hổng chí mạng:
1. **Bẫy Claim Chung Chung Vô Nghĩa (Meaningless Static Claim)**:
   - File gate luôn dùng claim tĩnh `"Visual evidence verified for farm delivery"`. Vision model nhìn vào ảnh sạch (kể cả màn hình lỗi rõ ràng) vẫn trả về PASS vì claim không mang tính kiểm chứng nghiệp vụ.
   - **Khắc phục**: Claim bắt buộc trích xuất động từ chính nội dung câu nói/yêu cầu của Coordinator (`_parse_message`), chỉ fallback claim tĩnh khi rỗng.
2. **Bẫy Đo Freshness Bằng Timestamp Ghi Verdict Thay Vì File MTime**:
   - Gate đo độ tươi mới từ `judged_at` (thời điểm ghi file json). Ảnh cũ từ phiên trước hoặc từ máy khác đưa vào vẫn có `judged_at` mới và được PASS!
   - **Khắc phục**: Bắt buộc assert trực tiếp thời gian tạo/sửa đổi file ảnh trên đĩa: `_image_is_fresh(path)` với `age <= 180s`.
3. **Bẫy Cache Verdict Khớp Mỗi Hash Ảnh Không Khớp Claim (Claim Hash Binding)**:
   - Gate chấp nhận file `verdict_<sha>.json` nếu có `verdict == PASS` mà không đối soát nội dung claim đã được duyệt. Kết quả: một verdict PASS của claim A có thể dùng hợp thức hóa cho claim B hoàn toàn khác.
   - **Khắc phục**: File cache bắt buộc ghi và kiểm tra đồng thời cả `image_sha256` VÀ `claim_sha256`. Bất kỳ sự lệch pha nào đều buộc phải gọi lượt judge mới.
4. **Bẫy Regex Nuốt Đường Dẫn Có Khoảng Trắng (Spaces & Quotes in Path)**:
   - Regex `MEDIA:([^\s]+)` bị cụt ngay khoảng trắng đầu tiên, làm gãy các đường dẫn farm có dấu cách như `D:\Taadaa\tiktok-luot nuoi acc\...` hoặc `D:\Taadaa\GPM auto\...`.
   - **Khắc phục**: Nâng cấp regex hỗ trợ đường dẫn bọc ngoặc kép, đường dẫn không ngoặc kép kéo dài đến đuôi mở rộng ảnh (`.png`, `.jpg`, `.jpeg`, `.webp`), và hỗ trợ khoảng trắng sau dấu hai chấm (`MEDIA: <path>`).
5. **Bẫy Ghi Evidence Vào Thư Mục Đồng Bộ OneDrive**:
   - `tools/evidence` nằm trong thư mục code được sync qua OneDrive và read-only trên Admin machine, gây xung đột file json và phình dung lượng git.
   - **Khắc phục**: Chuyển toàn bộ `EVIDENCE_DIR` sang thư mục runtime không đồng bộ: `D:/CodexRuntime/evidence`.

## 3. Bản Vá Hoàn Chỉnh & Phê Duyệt Của Claude Sonnet 5.5 (Strike 2)
Sau khi khắc phục toàn bộ 5 điểm trên và hoàn thiện 37 unit tests (`test_visual_judge.py` + `test_verify_media_gate.py`):
- Claude Sonnet 5.5 Reviewer chính thức cấp: **`VERDICT: APPROVED`**.
- Toàn bộ các nhánh thất bại (OCR lỗi, timeout vision, model chưa cấu hình, hash lệch, ảnh quá 180s) đều **Fail-Closed** cơ học (trả về `UNCERTAIN` hoặc `False`, strip toàn bộ thẻ `MEDIA:` và gắn cờ `[UNVERIFIED_VISUAL_EVIDENCE - REJECTED]`).

## 4. Kỷ Luật Bất Biến Về Runner Avatar Farm
1. **CẤM TUYỆT ĐỐI ĐẺ SCRIPT AD-HOC TAP TAY ADB**: Mọi tác vụ đổi avatar BẮT BUỘC dùng canonical tool `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <tik> --machine <machine>`.
2. **Quy trình chuẩn bị nguồn ảnh**:
   - Copy ảnh chuẩn 512x512 sạch chữ vào cả 2 thư mục: `D:/video goc/<F_src>/avatar.jpg` và `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`.
   - Cắm marker file `.manual_avatar_locked` tại cả 2 thư mục để ngăn cron ghi đè.
   - Đặt cột `Avatar = PENDING` trên file `Tik*.xlsx` và cập nhật hàng đợi `tiktok_tracker.db`.
3. **Khi runner bốc nhầm ảnh cũ**:
   - Không được tự viết script tap tay.
   - Nguyên nhân là do MediaStore index rác hoặc `.thumbnails`. Hãy dọn dẹp sạch `/sdcard/DCIM/.thumbnails/` và các file ảnh lạ trong `/sdcard/DCIM/Camera/` rồi để canonical tool tự động bốc ảnh duy nhất.
