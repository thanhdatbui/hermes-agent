# Kỷ Luật Đối Soát Hiện Trường & Chống Báo Cáo Ảo Khi Thay Đổi Thông Tin TikTok Farm

## 1. Bối cảnh & Các Sai Phạm Thực Tế (Session 31/10/2026)
Trong quá trình tự động hóa thay thế Hotmail sạch cho các tài khoản dính Gmail DIE:
1. **Lỗi click tọa độ cứng sát đáy màn hình:** Dùng tọa độ `(540, 1810)` trong mục Cài đặt Tài khoản dẫn tới việc click trúng nút `"Hủy kích hoạt hoặc xóa tài khoản"`.
2. **Lỗi báo cáo ảo Captcha / Đình chỉ:** Agent nhìn thoáng hoặc suy diễn không căn cứ, báo "Máy 07 dính Captcha" (thực chất là màn hình Hủy kích hoạt), hoặc báo "Máy 02 đổi thành công" trong khi máy đang kẹt ở khung bình luận video.
3. **Lỗi tự chế script ngoài luồng:** Tự viết script mới (`batch_replace_hotmail.py`) dùng XML dump thay vì module chuẩn `automation_core.ui_extract.extract_ui` (WinRT OCR).

## 2. Invariant Đối Soát Thực Tế Bắt Buộc (Evidence-First Verification)
- **CẤM TUYỆT ĐỐI báo cáo dựa trên suy đoán hoặc chỉ nhìn text trả về từ tool:**
  * Mọi kết luận về trạng thái màn hình (Captcha, Challenge, Bị đình chỉ, Đổi mail thành công) **BẮT BUỘC PHẢI CÓ**:
    1. Ảnh chụp màn hình rõ nét (`MEDIA:<path>`).
    2. Receipt bóc tách từ **WinRT OCR** (`automation_core.ui_extract.ocr_screen_boxes`) chứa đúng từ khóa đó.
- **Fail-Safe Chống Bấm Nhầm Xóa Tài Khoản:**
  * Trước mọi thao tác click trong menu Tài khoản, BẮT BUỘC quét OCR màn hình. Nếu thấy bất kỳ cụm từ nào: `"xóa tài khoản"`, `"hủy kích hoạt"`, `"delete account"`, `"deactivate"` $\rightarrow$ **Lập tức bấm nút `Back` (keyevent 4) và Abort ngay lập tức**.
  * CẤM TUYỆT ĐỐI dùng tọa độ pixel cứng ở nửa dưới màn hình (`y > 1600`). Bắt buộc click đúng tâm bounds do OCR hoặc node XML của ATX-Agent trả về.

## 3. Luồng Điều Hướng Chuẩn Bắt Buộc Khi Đổi Email
CẤM tìm kiếm mù chữ `"Email"` từ màn hình chính vì sẽ bấm nhầm vào bình luận video hoặc các mục khác. Bắt buộc đi tuần tự 5 Checkpoint:
1. **Checkpoint 1 (Về Profile):** Tap tab Hồ sơ góc dưới bên phải `[972, 1860]`. Xác nhận đang ở Profile bằng OCR/XML thấy username.
2. **Checkpoint 2 (Bung Menu):** Tap icon 3 gạch góc trên bên phải `[1005, 150]`.
3. **Checkpoint 3 (Mở Cài đặt):** Quét tìm chữ `"Cài đặt và quyền riêng tư"` $\rightarrow$ Tap tâm.
4. **Checkpoint 4 (Mở Tài khoản):** Quét tìm chữ `"Tài khoản"` (thường nằm ở dòng đầu tiên của mục Tài khoản) $\rightarrow$ Tap tâm.
5. **Checkpoint 5 (Vào Form Email):** Quét tìm `"Thông tin tài khoản"` $\rightarrow$ Quét `"Email"` $\rightarrow$ Bấm `"Thay đổi email"` $\rightarrow$ Xác nhận thấy ô `"Nhập email của bạn"` rồi mới được phép điền mail mới.
