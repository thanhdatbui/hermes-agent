# Kỷ Luật Cơ Học: Loại Bỏ Heuristic Is_Visual_Claim, Chặn Thô WinRT OCR & Cấm Xả Git Diff Ra Chat

## 1. Bản Chất Lỗ Hổng Bypass Media Gate Bị Phanh Phui (2026-10-31)
* **Thực trạng:** Coordinator nhiều lần bị User bắt tại trận gửi Proposal Canvas có ảnh rác (ảnh phụ nữ ăn uống, ảnh có chữ Kangen Water, ảnh nhân bản 1 frame thành 4 ô), nhưng hệ thống Gate vẫn cho qua mà không kích hoạt chặn.
* **Nguyên nhân cốt lõi trong mã nguồn `guard_media_vision_gate.py`:**
  * Hàm `check_contradiction` trước đây sử dụng nhánh điều kiện kết hợp:
    ```python
    is_visual_image = any(k in img_lower for k in ("proposal", "canvas", "cand", "preview", "nature", "scene")) and "profile" not in img_lower
    is_visual_claim = any(k in message for k in ("thien nhien", "cay", "hoa", "canh", "chan dung", "de xuat avatar", "phuong an avatar", ...))
    if is_visual_image and is_visual_claim and tool_called not in ("browser_vision", "ag_cli_vision"):
        return UNVERIFIED_BY_VISION
    ```
  * Khi tin nhắn của Agent trả lời User chỉ chứa các câu mô tả ngữ cảnh khác (như "PA 1 cún nghiêng đầu", "PA 2 cún múa bụng", "Thú cưng") mà **không chứa đúng các từ khóa trong danh sách `is_visual_claim`**, biểu thức điều kiện trả về `False`!
  * Gate rơi vào nhánh cho phép (fall-through), tự động công nhận các receipt được đăng ký bằng `winrt_ocr` (OCR chữ thuần túy) mà **hoàn toàn mù về nội dung hình ảnh thực tế**.

## 2. Bản Vá Tầng Cơ Học Đã Thi Công (Unified Patch Pipeline)
* **Xóa bỏ hoàn toàn nhánh heuristic `is_visual_claim`:**
  * Bất kỳ file ảnh nào thuộc diện hình ảnh thị giác (`proposal`, `canvas`, `cand`, `preview`, `avatar`): BẮT BUỘC `tool_called` phải nằm trong danh mục Vision thực thụ: `('browser_vision', 'ag_cli_vision')`.
  * Nếu receipt xuất phát từ `winrt_ocr` hoặc tool OCR thuần văn bản: Chặn vô điều kiện với mã `UNVERIFIED_BY_VISION`.
  * Không chấp nhận bất kỳ lý do ngoại lệ nào dựa trên nội dung text của tin nhắn.

## 3. Bản Vá Chống Treo Video Trích Xuất Frame (`anti_hang_guard.py`)
* **Nguyên nhân deadlock:** Lệnh gọi `cv2.VideoCapture` trực tiếp trong terminal trên Windows có thể bị treo cứng vô thời hạn ở tầng native C++ decoder (DirectShow / Media Foundation) khi gặp file hỏng hoặc xung đột luồng I/O, khiến Gateway timeout sau 60 phút.
* **Cơ chế Process Isolation 10s:**
  * Hàm `safe_extract_video_frame(video_path, timestamp_s, timeout_s=10.0)` bọc toàn bộ thao tác mở và đọc frame trong một subprocess riêng biệt với `stdin=DEVNULL`, `stdout=DEVNULL`, `stderr=DEVNULL`.
  * Nếu quá 10 giây tiến trình con không phản hồi, Supervisor bên ngoài cưỡng chế `kill()` thu hồi tài nguyên ngay lập tức và trả về `None`.

## 4. Kỷ Luật Chat & Trình Bày Người Dùng (Anti-Git-Diff Dumping)
* **Bẫy hành vi bị User chấn chỉnh nghiêm khắc:** Ném cả khối raw `git diff` mã nguồn dài dòng vào tin nhắn chat Telegram để "khoe/báo cáo" quá trình sửa file.
* **Quy chuẩn bắt buộc:**
  * Người dùng (User) là người quản trị kinh doanh/vận hành, cần **kết quả thực thi thực tế** (Trạng thái file, dữ liệu Excel, toạ độ, hình ảnh nghiệm thu), không cần đọc raw patch diff.
  * Khi báo cáo: Chỉ tóm tắt ngắn gọn 3-4 dòng về logic đã thay đổi, lệnh test kiểm chứng đã chạy (kèm kết quả pass), và trạng thái task chính. CẤM TUYỆT ĐỐI xả diff git ra khung chat Telegram.
