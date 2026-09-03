# Incident Analysis & Case Fix: Search Landing Screen & Capture-Invalid (28/08/2026)

## 1. Case UI: Màn hình Tìm kiếm / Gợi ý tìm kiếm (Search Landing Screen) gây lỗi `unknown TikTok state`

### Hiện tượng thực tế (Sự cố Máy 10)
- **Script:** `multi-machine-feed-session` (hoặc `feed-session-smoke`).
- **Hiện trường:** TikTok hiển thị trang Tìm kiếm / Gợi ý tìm kiếm (`com.ss.android.ugc.trill`):
  - Ô tìm kiếm chứa gợi ý placeholder (ví dụ: *"Cute Dog Videos..."*), nút *"Tìm kiếm"*, nút Back **`←`** ở góc trên bên trái.
  - Banner điểm thưởng tìm kiếm (*"Tìm kiếm 12 lần để nhận 360 điểm — hãy tiếp tục để mở khóa tới 840 điểm hôm nay!"*).
  - Khối danh sách *"Tìm kiếm gần đây"*, *"Bạn có thể thích"*, thanh công cụ dưới cùng có *"Thoại"*, *"Hỏi AI"*, tab *"Nội dung tìm kiếm thịnh hành"*.
- **Cơ chế gây lỗi (Anti-Pattern):**
  - Trong quá trình khởi động hoặc điều hướng lướt feed, ứng dụng bị chuyển hướng vào trang Tìm kiếm (do chạm nhầm biểu tượng tìm kiếm hoặc deeplink).
  - Bộ phân loại `classifier.py` và `benign_popup_registry.py` chưa có định danh màn hình Tìm kiếm -> rơi vào nhánh `unknown TikTok state` -> script dừng phiên và kích hoạt `status: blocked` giữ nguyên hiện trường.

### Giải pháp chuẩn (Case Fix)
1. **Định danh (Detector):**
   - Nhận diện các dấu hiệu đặc trưng trong UI XML / OCR:
     - Chuỗi: `"bạn có thể thích"`, `"tìm kiếm gần đây"`, `"thêm từ khóa tìm kiếm"`, `"nội dung tìm kiếm thịnh hành"`, `"hỏi ai"`, `"thoại"`, hoặc banner thưởng tìm kiếm.
     - Node input tìm kiếm (`EditText` hoặc resource-id chứa `search_input` / `et_search`).
2. **Xử lý (Dismisser):**
   - Ưu tiên tap nút Back **`←`** ở góc trên bên trái màn hình (hoặc gửi keyevent `BACK` / `input keyevent 4`).
   - Chờ UI hoàn tất chuyển cảnh (1.0s) và xác thực màn hình quay trở lại Bảng tin (Home / FYP feed) trước khi tiếp tục chuỗi lướt.

---

## 2. Case Capture: Lỗi `screen capture invalid; feed not confirmed`

### Hiện tượng thực tế (Sự cố Máy 66)
- Lệnh chụp ảnh ADB (`exec-out screencap -p`) trả về dữ liệu rỗng/hỏng (ví dụ: chỉ 12 bytes header rỗng) hoặc ADB socket timeout / thiết bị phản hồi trễ.
- Runner thử lại theo cấu hình nhưng không nhận được frame hợp lệ để xác thực UI feed.

### Nguyên tắc xử lý (Fail-Closed Enforcement)
- Tuyệt đối không bypass bước xác thực chụp màn hình.
- Khi gặp lỗi capture invalid sau số lần retry quy định: Runner fail-closed, lưu artifact lỗi và chuyển trạng thái `status: blocked` giữ nguyên hiện trường cho đến khi được kiểm tra/giải phóng an toàn.
