# Playwright Gmail Web: OTP Extraction, Snippet Truncation & Thread Navigation Pitfalls

## Context
Khi tự động hóa đăng ký tài khoản (như ChatGPT, OpenAI, dịch vụ web) qua GPM Profile + Playwright kết nối trực tiếp tab Gmail để lấy OTP xác thực.

## Pitfalls & Solutions

### 1. Snippet Truncation Trap (Dấu ba chấm `...`)
* **Hiện tượng**: Tiêu đề và snippet trên Gmail Inbox thường có dạng:
  `ChatGPT — Your temporary ChatGPT verification code is 123456`
  Tuy nhiên, giao diện bảng danh sách email của Gmail thu gọn đoạn trích bằng `...` (ví dụ: `ChatGPT — Your temporary ChatGPT verification ...`).
* **Hậu quả**: Regex trích xuất 6 số trực tiếp từ `body.inner_text()` hoặc danh sách `tr` bị miss vì 6 chữ số nằm sau điểm bị cắt.
* **Quy tắc**:
  - Không coi việc bốc OTP từ snippet là phương thức duy nhất.
  - Vẫn giữ regex snippet nếu snippet tình cờ chứa số (ví dụ email ngắn), nhưng LUÔN chuẩn bị mở trực tiếp luồng thư (thread).

### 2. `div[role="main"]` False Positive Trap
* **Hiện tượng**: Selector `div[role="main"]` tồn tại ở **cả màn hình danh sách hộp thư** lẫn **màn hình chi tiết thư**.
* **Hậu quả**: Nếu kiểm tra `if "chatgpt" in div[role="main"].inner_text():` thì điều kiện này luôn `True` ngay cả khi click mở thư thất bại (vì dòng tóm tắt trên danh sách vẫn có chữ "chatgpt"). Code tưởng đã vào trang chi tiết, tìm 6 số không thấy, rồi lập tức nhảy vào nhánh bấm nút Refresh (`div[act="20"]`). Việc refresh liên tục khiến thư không bao giờ mở kịp, dẫn đến `FAIL_OTP_TIMEOUT`.
* **Khắc phục**:
  - Luôn gate trạng thái mở thư bằng phần tử chỉ có trong view đọc thư: `div.adn`, `div[role="listitem"]`, hoặc kiểm tra URL chứa thread ID: `re.search(r"/#inbox/[a-zA-Z0-9]+", mail_page.url)`.

### 3. Click mở hàng thư không trigger sự kiện mở thread
* **Hiện tượng**: `target_row.click()` hoặc click vào `span:has-text("ChatGPT")` thường chỉ click vào ô tên người gửi hoặc vùng trống của hàng, hoặc bị chặn bởi banner chào mừng (*"Get started with Gmail"* / *"Customize your inbox"*).
* **Khắc phục**:
  - Click trực tiếp vào tiêu đề/subject cell:
    ```python
    subj = target_row.locator('span.bog, td.xY, td.yX, span[data-thread-id]').first
    if subj.is_visible(timeout=1500):
        subj.click(force=True)
    else:
        target_row.click(force=True)
    ```
  - Hoặc dùng keyboard event chuẩn của Gmail:
    ```python
    target_row.press("Enter")
    ```
  - Chờ tối thiểu 2-3s và verify URL hoặc `div.adn` hiển thị trước khi đọc nội dung thư.
