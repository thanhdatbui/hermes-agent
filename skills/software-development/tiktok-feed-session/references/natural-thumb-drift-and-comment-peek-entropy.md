# Natural Thumb Drift, Deep Engagement Entropy & Canary Execution Protocol

## 1. Natural Thumb Drift Swipe (Phá Bỏ Chữ Ký Bot Tuyến Tính dx = 0)
- **Vấn đề phát hiện bởi ByteDance Security SDK (`libmetasec_ml.so` / Bdturing)**:
  - Cử chỉ vuốt thẳng tắp $dx = 0$ kéo dài qua hàng trăm video là signature cơ học (synthetic interaction) với phương sai vận tốc bằng 0 (`velocity variance = 0`).
- **Quy chuẩn cử chỉ tự nhiên có kiểm soát (Natural Finger Drift)**:
  - `start_x`: Chọn ngẫu nhiên trong vùng trung tâm `[465, 525]` px.
  - `drift`: Độ lệch ngón tay cái tự nhiên `random.randint(-18, 12)` px.
  - `end_x`: Clamped nghiêm ngặt trong hành lang an toàn `[450, 540]` px (cách xa vùng biên lật trang Camera `0..150px` và Profile `930..1080px` tối thiểu 300px).
  - **Dangerous Skew Fallback**: Nếu tham số truyền vào từ bên ngoài bị lệch nguy hiểm ($|\Delta X| > 30\text{ px}$), hệ thống BẮT BUỘC ép thẳng đứng $start\_x = end\_x$ để triệt tiêu 100% rủi ro văng màn hình.

## 2. Deep Engagement Entropy: Bookmark & Comment Peek
- **Lưu Bookmark / Favorite Video khi Like**:
  - Chỉ kích hoạt khi video đã được thả tim (`_maybe_like_video`) thành công.
  - Tỷ lệ ngẫu nhiên: **15% – 30%**.
  - Dwell time: Nghỉ tự nhiên 0.8s – 1.8s sau khi Like rồi mới tap nút Lưu (`center[0] >= 750`), sau đó nghỉ 0.4s – 0.8s.
- **Xem lướt Bình luận (Comment Peek)**:
  - **Gating độc quyền**: BẮT BUỘC chỉ chạy trên các video **Deep Inspect** (`after["is_deep_inspect"] == True` và có `raw_xml` tươi). CẤM chạy trên video fast-swipe.
  - **Tỷ lệ**: **12%** trên video deep inspect.
  - **Hành vi**:
    1. Tap nút Comment trên toolbar phải (`center[0] >= 750`).
    2. Ngâm đọc bình luận **2.0s – 4.0s**.
    3. Xác suất 50% cuộn nhẹ 1 nhịp ngắn (300ms) đọc tiếp 1.0s – 2.0s.
    4. Bấm `KEYCODE_BACK` đóng sheet, nghỉ 0.6s – 1.2s.
  - **Fail-Closed Verification**: Kiểm tra `get_focused_activity(ctx)`. Nếu mất focus TikTok (`com.ss.android.ugc.trill`, `musically`, `aweme`) hoặc phát sinh exception, BẮT BUỘC ghi log `result="failed_dismissal"` và trả về `False`.

## 3. Upload Hook Policy (Bảo Toàn Kho Video Khi Nick Cooldown)
- **Quy tắc**: Trong chu kỳ ca 2 phiên, **CHỈ Phiên 2 (phiên cuối ca)** mới được phép kích hoạt hook upload video (`$AllowUploadHook -or $SessionIndex -eq 2`).
- **Ý nghĩa**: Tránh xả sạch kho video trong thời gian nick đang dính án phạt nhả follow; nếu phiên 2 gặp lỗi thì 4 ngày tiếp theo nick mới có lượt đăng tiếp, đúng nhịp sinh học tự nhiên.

## 4. Kỷ Luật Canary Runner Môi Trường Python (Isolate PYTHONPATH)
- Khi chạy canary on-demand bằng Python interpreter của `D:\Taadaa\python-envs\automation\Scripts\python.exe` từ subprocess trong môi trường Hermes Agent:
  - BẮT BUỘC set tường minh `env["PYTHONPATH"] = r"D:\Taadaa\tiktok-luot nuoi acc\python_runner"`.
  - CẤM để kế thừa `PYTHONPATH` mặc định của Hermes Agent venv vì sẽ gây xung đột binary extension (ví dụ: `ImportError: cannot import name '_imaging' from 'PIL'`).
