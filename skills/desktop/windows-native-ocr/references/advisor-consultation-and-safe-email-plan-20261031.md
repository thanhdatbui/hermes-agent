# Quy Trình Thảo Luận Advisor & Chốt Plan An Toàn Cho Tác Vụ Đổi Email Farm (31/10/2026)

## 1. Bối Cảnh & Chỉ Đạo Của User
Khi phát hiện vi phạm gate và lỗi thao tác trên màn hình nhạy cảm (nhảy vào trang Hủy kích hoạt tài khoản), User chỉ đạo:
> *"Fix đi. Nhưg yêu cầu k over engineer k gây bại liệt thảo luận vs các advisor r chốt plan"*

## 2. Kỷ Luật Vận Hành
1. **Triệu Hồi Dual Advisor Qua `consult_advisor.py`**:
   - Chạy lệnh: `python D:/Taadaa/tools/consult_advisor.py --query "<nội dung plan>" --advisor both`.
   - Lấy ý kiến phản biện từ Sol (nghiệp vụ Farm) và Claude CLI (kiến trúc an toàn).
2. **Khóa Chặt Invariant UI-OCR-1**:
   - Sử dụng `automation_core.ui_extract.ocr_screen_boxes` (WinRT OCR) đọc text trực tiếp từ ảnh chụp màn hình native.
   - Click tâm bounding box từ OCR, tuyệt đối cấm tọa độ pixel cố định.
   - Cấm `dumpWindowHierarchy` XML làm quá tải phần cứng Exynos S7.
3. **Fail-Safe Cưỡng Chế**:
   - Quét màn hình trước mỗi thao tác; nếu thấy từ khóa "xóa", "hủy kích hoạt", "delete", "deactivate" thì bấm Back và abort ngay lập tức.
4. **Thi Công Tuần Tự O(1) (Chống Bại Liệt)**:
   - Chạy tuần tự 1-by-1 từng máy thay vì spam song song 15 luồng.
   - Sau khi Sol và Claude duyệt các điểm cốt lõi, Coordinator chốt ngay action items và kích hoạt thi công, không kéo dài thảo luận lý thuyết.
