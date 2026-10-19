# Pre-send Vision Inspection and Anti-Blind Delivery Invariant

## Overview
Whenever an agent produces visual media (screenshots, UI mockups, proposal canvases, or camera crops) and delivers it to the user via `MEDIA:<path>`, there is a strict invariant:
**CẤM TUYỆT ĐỐI gửi ảnh mù / gửi đối phó.**

## The Invariant Checklist
1. **Physical & Hash Verification**:
   - Ensure the image exists at an absolute path and has non-zero size.
   - Verify the image content is fresh, not an old artifact from a previous run or cache.
2. **Visual Inspection Before Sending (`browser_vision` or WinRT OCR)**:
   - Before emitting any `MEDIA:<path>` tag in the final user response, the agent MUST inspect the rendered image using `browser_vision` (navigate to `file:///...`) or WinRT OCR.
   - Confirm:
     * Target screen matches the goal (e.g., Profile, Switcher, Comparison Mosaic).
     * Text elements, metrics, and captions are legible, correctly positioned, and not overlapping.
     * Subject is centered in circles/crops, headroom is balanced (~15–20%), no chopped chins or distorted borders.
     * No black screen, modal popups obscuring content, or rendering glitches.
3. **Evidence-Grounded Response**:
   - In the text accompanying `MEDIA:<path>`, explicitly state the key details seen with the model's own eyes (e.g., specific titles, views, button states, bounding box highlights).
   - Never drop a bare `MEDIA:` tag without confirming the visual content.

4. **Unicode & Vietnamese Diacritics on Proposal Canvases & Mockups**:
   - **Bẫy OpenCV `cv2.putText` lột dấu**: Thư viện OpenCV chỉ hỗ trợ bảng mã ASCII. Khi vẽ tiếng Việt có dấu, OpenCV xuất hiện `???` hoặc ký tự rác, dẫn đến việc lột dấu (`unidecode`) để né lỗi. Điều này gây hiểu lầm nghiêm trọng cho người dùng rằng hệ thống sẽ nạp dữ liệu không dấu lên thiết bị ("Ủa bio t ép ghi tiếng việt có dấu r mà?").
   - **Quy chuẩn bắt buộc**: Khi vẽ văn bản tiếng Việt lên canvas / preview ảnh, BẮT BUỘC dùng PIL/Pillow với TrueType Font (Arial, Tahoma, DejaVuSans) để bảo toàn 100% dấu tiếng Việt và emoji. Trong tin nhắn đính kèm ảnh, BẮT BUỘC xác nhận rõ: dữ liệu nạp lên thiết bị là tiếng Việt có dấu chuẩn UTF-8 Base64.

