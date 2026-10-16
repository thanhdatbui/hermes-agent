# Shared WinRT OCR Module & Fast Popup Dismissal (`automation_core.ocr`)

## 1. Mục Đích & Vị Trí Kiến Trúc
`src/automation_core/ocr.py` đóng gói toàn bộ tiện ích WinRT OCR native (chạy offline trên Windows qua `D:\Taadaa\tools\ocr_boxes.ps1`), phục vụ cho các repo trong hệ sinh thái Farm (`tiktok-follow`, `tiktok-luot nuoi acc`, `Tiktok_Reg`).

Mục tiêu cốt lõi:
- **Tốc độ:** Chụp ảnh + OCR chỉ mất ~0.3s - 0.5s (nhanh gấp 10-20 lần so với `uiautomator dump` XML 5s - 15s).
- **Kháng đổi Obfuscated ID:** Bất kể TikTok đổi ID nút (`id/fds` $\to$ `id/fmp` $\to$ `id/fo4`), OCR đọc thẳng chữ "Follow", "Theo dõi", "Follow lại" trên màn hình.
- **Dập Popup Thần Tốc:** Quét và bấm các nút đóng popup lành tính ("Để sau", "Không phải bây giờ", "Hủy", "Đóng") trong 0.3s mà không làm gián đoạn nhịp nuôi video.

## 2. API Contract Cốt Lõi

```python
from automation_core.ocr import (
    ocr_screen_boxes,
    find_popup_dismiss_button_ocr,
    classify_profile_action_ocr,
    find_follow_button_center_ocr,
    norm_text,
)
```

### A. `find_popup_dismiss_button_ocr(boxes, dismiss_keywords=None, sensitive_keywords=None) -> (cx, cy) | None`
- Quét tìm nút đóng popup lành tính: `"de sau"`, `"khong phai bay gio"`, `"huy"`, `"dong"`, `"not now"`, `"cancel"`, `"later"`, `"skip"`, `"bo qua"`, `"de luc khac"`, `"close"`, `"dismiss"`.
- **Cầu dao an toàn (Safety Guard):** Nếu trên màn hình xuất hiện bất kỳ từ khóa nhạy cảm / bảo mật nào (`dang nhap`, `tai khoan`, `mat khau`, `credential`, `password`, `payment`, `thanh toan`, `captcha`, `otp`), hàm lập tức trả về `None`, **tuyệt đối không bấm nút đóng khi gặp thử thách xác minh danh tính**.
- Log rõ telemetry: `decision=dismiss reason=keyword_match` hoặc `decision=reject reason=sensitive_keyword`.

### B. `classify_profile_action_ocr(boxes, y_min=0, y_max=1200) -> str`
- **Quy tắc Follow Dominance:**
  - Nếu có bất kỳ nút `not_followed` (`Follow`, `Follow lại`, `Theo dõi`) $\to$ **100% trả về `not_followed`**, bất kể có nút "Nhắn tin" hay không (vì nick chưa follow hoặc bị nhả follow vẫn có nút Nhắn tin).
  - Nếu chỉ có nút `followed` (`Nhắn tin`, `Bạn bè`, `Đang theo dõi`, `Message`) và không có nút Follow $\to$ trả về `followed`.
  - Không có cả 2 $\to$ trả về `unknown`.
- **Bộ lọc loại trừ nhãn thống kê (Stat Counters):**
  - Loại trừ regex: `follower`, `followers`, `dang follow`, `da follow` để không bị bẫy substring `"follow" in "follower"` hay `"follow" in "127 Đã follow"`.
- **Khóa độ dài nhãn (Word Length Guard):**
  - `len(n_txt.split()) > 3` $\to$ loại bỏ ngay, tránh nhận nhầm câu mô tả dài trong Bio có chứa chữ "follow".
- **Khoanh vùng dải Y:** $y < 1200$ (bỏ qua Bio và lưới video bên dưới).

### C. `find_follow_button_center_ocr(boxes, y_min=0, y_max=1200) -> (cx, cy) | None`
- Trả về tọa độ tâm $(cx, cy)$ chính xác của nút follow hợp lệ đầu tiên để click an toàn.

## 3. Mô Hình Phối Hợp Hybrid (XML vs OCR) Cho Farm

| Tác vụ | Mô hình | Nguyên tắc thực thi |
| :--- | :--- | :--- |
| **Dập Popup đè màn hình (`benign_popup`)** | **OCR First-Line (0.3s)** $\to$ Fallback XML | OCR quét nhanh các từ khóa đóng quen thuộc. Thấy là dập ngay trong 0.3s. Nếu không thấy mới gọi XML chuyên sâu của `benign_popup.py`. |
| **Bấm nút đổi ID (`Follow`, `Tiếp tục`)** | **XML trước $\to$ OCR Fallback** | Đọc XML theo selector. Nếu XML trả về `unknown` do TikTok đổi ID $\to$ OCR nhảy vào cứu nguy để bấm, chống timeout/crash. |
| **Định danh UID, Pass, Checkbox, Tab Selected** | **100% XML (CẤM DÙNG OCR)** | Tránh sai số OCR ký tự (`0` vs `O`, `1` vs `l`), và OCR không đọc được các thuộc tính logic `selected="true"`, `checked="true"`, ô pass rỗng. |

## 4. Kỷ Luật Kiểm Thử & Reviewer Gate
- File kiểm thử: `tests/test_ocr.py` (chạy qua `python -m pytest tests/test_ocr.py`).
- Mọi thay đổi logic OCR bắt buộc bổ sung test case bao phủ:
  1. Xử lý return code PowerShell (`r.returncode != 0`).
  2. Safety guard từ chối khi gặp sensitive keyword (`captcha`, `mật khẩu`).
  3. Cặp nút song song (`Follow` + `Nhắn tin` $\to$ `not_followed`).
  4. Loại trừ nhãn đếm (`127 Đã follow`, `10K Follower`).
  5. Loại trừ câu dài > 3 từ.
  6. Audit telemetry log format (`decision=... reason=...`).
