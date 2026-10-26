# Chống Chụp Ảnh Mù Đối Phó & Ép Buộc Soi Mắt Trước Khi Gửi (Anti-Fake Screenshot & Mandatory Inspection Receipt)

## 1. Bối Cảnh & Vấn Đề
Trong quá trình vận hành farm và tự động hóa giao diện, có 2 hiện tượng vi phạm Gate 6 nghiêm trọng:
1. **Chụp láo toét đối phó (Coping / Fake Screencap):**
   - Một số model (đặc biệt là Gemini hoặc subagents khi bị ép buộc phải có thẻ `MEDIA:`) có xu hướng chụp bất kỳ màn hình nào đang hiển thị: màn hình chính Samsung (LauncherActivity), màn hình đen xì do máy ngủ (Dozing/Sleep), hoặc popup quảng cáo che khuất rồi ném link ảnh vào tin nhắn và khẳng định "đã hoàn tất".
2. **Gửi mù không soi mắt (Unverified Media Push):**
   - Agent chụp ảnh xong nhưng không mở ảnh ra xem nội dung, vứt thẳng thẻ `MEDIA:<path>` vào tin nhắn cho User. Hậu quả là nếu ảnh bị đen, bị che, hoặc sai tài khoản, Agent không hề biết mà vẫn tuyên bố bừa bãi.

## 2. Cơ Chế Thẩm Định Target Screen Anchor (Chống Chụp Mù Đối Phó)
Để ngăn chặn chụp ảnh đối phó mà **không gây bại liệt / khóc lóc**:
- Sử dụng WinRT OCR hoặc pre-capture dumpsys focus để xác định đặc trưng của màn hình đích:
  * **Màn hình Profile TikTok:** Bắt buộc OCR phải đọc được nhãn `Sửa hồ sơ` / `Edit profile` hoặc đúng `@username` của kênh mục tiêu.
  * **Dấu hiệu chụp đối phó:**
    - OCR phát hiện các từ khóa Launcher: `Điện thoại`, `Tin nhắn`, `Cài đặt`, `Thời tiết`, `CH Play`, `Samsung` -> Xác định ngay là màn hình chính Launcher.
    - OCR trả về 0 bytes text -> Xác định màn hình đen / máy đang tắt màn hình.
    - OCR phát hiện popup che: `Cho phép`, `Cập nhật`, `Để sau`, `Đóng`.
- **Xử lý khi phát hiện chụp đối phó (Action-Forcing Guidance O(1)):**
  - CẤM quở trách mơ hồ khiến LLM rơi vào vòng lặp xin lỗi, bại liệt.
  - Hook lập tức inject Guidance lệnh O(1) cụ thể:
    ```json
    {
      "action": "rewrite",
      "rule_id": "SCREEN_NOT_AT_TARGET_PROFILE",
      "detected_screen": "LauncherActivity",
      "guidance": "Ảnh chụp máy N đang ở màn hình chính, chưa vào Profile. BẮT BUỘC chạy lệnh: python D:/Taadaa/tools/pin_top_videos.py --machine <N> --account <user> để mở đúng Profile."
    }
    ```

## 3. Cơ Chế Ép Buộc Soi Mắt Trước Khi Gửi (Mandatory Inspection Receipt)
- Trong plugin / runtime hook `transform_llm_output`:
  - Hook kiểm tra danh sách `verified_media_paths` được nạp từ `post_tool_call` của `browser_vision` hoặc `run_winrt_ocr.py`.
  - Mọi thẻ `MEDIA:<path>` trong câu trả lời chuẩn bị gửi User BẮT BUỘC phải nằm trong `verified_media_paths` (đã được Agent thực sự mở ra đọc trong phiên).
  - **Nếu CHƯA được soi mắt:**
    - Hook chặn câu trả lời và trả về lệnh cưỡng chế O(1):
      ```text
      [MANDATORY_INSPECTION_REQUIRED]
      Ảnh MEDIA:<path> CHƯA ĐƯỢC SOI MẮT KIỂM TRA TRONG PHIÊN!
      YÊU CẦU: Gọi ngay browser_vision(url="file:///<path>") hoặc python D:/Taadaa/tools/run_winrt_ocr.py "<path>" để mở ảnh ra đọc trước khi gửi User.
      ```
  - Agent nhận chỉ thị rõ ràng, bắt buộc phải gọi tool đọc ảnh, nạp `verified_media_paths` rồi mới được gửi kết quả. Triệt tiêu 100% thói gửi ảnh mù và báo cáo vô căn cứ.
