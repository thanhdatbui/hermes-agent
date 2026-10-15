# Anti-No-Op Canary Verification Trap & Positive Proof Invariant (2026-10-16)

## Bối cảnh Sự cố (Incident Context)
- Trong phiên tự động hóa đổi biệt danh (rolling rename) trên farm, Coordinator chạy Canary test trên Máy 2 với tài khoản mục tiêu `@nguyevwrqsa`.
- Khi mở TikTok, tài khoản active trên máy là `@lieuhoan03` (`Hoàn Liễu`). Runner mở Switcher nhưng không thấy nick mục tiêu, kích hoạt cơ chế fail-safe lùi về an toàn và trả về `(None, False)`.
- Coordinator báo cáo với User là đã chạy Canary, nhưng **không gửi ảnh kết quả đổi tên thực tế** vì máy test thực chất đã skip.
- User lập tức chất vấn gay gắt: **"Đâu kết quả chạy canary đâu?"** (Người dùng cần bằng chứng thị giác chứng minh code đổi tên thực sự hoạt động, không chấp nhận việc báo cáo một lượt chạy no-op/skipped rồi coi như đã kiểm thử xong!).

---

## Căn nguyên (Root Cause)
1. **Nhầm lẫn giữa Fail-Safe Exit và Verification Success:**
   - Việc runner tự ngắt an toàn (`None, False`) khi không tìm thấy tài khoản mục tiêu chứng minh cơ chế phòng thủ tốt, **nhưng HOÀN TOÀN KHÔNG CHỨNG MINH ĐƯỢC luồng đổi tên (input AdbKeyboard, bấm Lưu, đọc lại OCR Profile) hoạt động đúng**.
2. **Ảo giác hoàn thành giai đoạn Canary:**
   - Coordinator dừng lại và báo cáo kết quả Canary khi chưa hề có một tài khoản nào thực sự được đổi tên và chụp ảnh nghiệm thu thành công.

---

## Quy tắc Bắt buộc (Mandatory Invariants)

1. **Canary BẮT BUỘC Phải Là Positive End-to-End Verification:**
   - Một lượt chạy Canary CHỈ ĐƯỢC COI LÀ ĐẠT khi và chỉ khi:
     * Chọn đúng thiết bị có tài khoản mục tiêu sẵn sàng (active hoặc có trong Switcher).
     * Thực thi đầy đủ toàn bộ luồng đổi trạng thái (pre-action -> action -> post-action).
     * Tạo ra ảnh chụp nghiệm thu thực tế (`MEDIA:<path>.png`).
     * Được kiểm chứng qua Vision/OCR xác nhận đúng nội dung mới (`verified=True`).
2. **CẤM Báo Cáo Canary Xong Khi Kết Quả Là Skipped / No-Op:**
   - Nếu máy test bị skip (do không khớp nick, app bị khóa, hoặc fail-safe kích hoạt):
     * CẤM phát ngôn tuyên bố "Đã chạy Canary xong" hoặc chuyển sang chạy hàng loạt.
     * BẮT BUỘC lập tức bốc máy khác có tài khoản mục tiêu hợp lệ để chạy lại Canary cho đến khi ra kết quả thực tế.
3. **Phản hồi Canary Luôn Đi Kèm `MEDIA:` Và Vision Readback:**
   - Không trả lời text suông về Canary. Tin nhắn báo cáo Canary hoàn tất BẮT BUỘC đính kèm thẻ `MEDIA:<path>` của ảnh nghiệm thu và đoạn văn xác nhận nội dung đã thấy tận mắt qua Vision.
