# False-Positive Manual Challenge do Caption Video & Chuẩn Hóa Cảnh Báo Batch (Case 144, 2026-09-19)

## 1. Bối cảnh & Hiện tượng (Incident Máy 35)
- **Cảnh báo hệ thống:**
  `🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG`
  `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện 1 máy dính lỗi login/xác minh: Máy M35: manual_challenge marker detected`
- **Thực tế hiện trường (Evidence-First):**
  - Mở app TikTok: Màn hình đang ở Home Feed (For You / Đề xuất) xem video hoàn toàn bình thường, không có captcha hay challenge modal nào.
  - Mở bottom-sheet **Chuyển đổi tài khoản**: WinRT OCR đọc danh sách nick xác nhận đầy đủ 7/7 nick (`tubanlrnrmg`, `thanhh.trcc3`, `ngoc.phan39`, `duongnqaksl`, `phungmwgtc4`, `clayemiw0in`, `martinbwahb`).
  - **Kết luận:** Alert báo động giả 100% (False-Positive). Không có tài khoản nào bị văng hay mất phiên.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lỗ hổng quét text không giới hạn trong `classifier.py`:**
   - Trong `python_runner/core/classifier.py`, khi element `verify-bar-close` xuất hiện (view ẩn tàn dư từ bản ROM cũ hoặc service ngầm) hoặc khi quét `manual_challenge_terms = ("manual_challenge", "Xác minh", "xác minh", "kiểm tra bảo mật")`, logic lấy toàn bộ `texts` và `descs` trên toàn màn hình.
   - Khi video đang phát trên Feed có chứa chữ "xác minh" trong mô tả caption (`:id/desc`), tiêu đề (`:id/title`) hoặc thông báo Android SystemUI, `classifier.py` đánh giá nhầm toàn bộ màn hình là `manual-needed:manual_challenge`.
2. **Quy chụp sai mức độ nghiêm trọng trong `batch_aggregator.py`:**
   - Trong `automation-core/src/automation_core/batch_aggregator.py`, danh sách `AUTH_CRITICAL_KEYWORDS` gộp chung cả `"verification"`, `"manual_challenge"`, `"checkpoint"` vào cùng nhóm với `"login"`, `"văng"`.
   - Bất kỳ lỗi captcha/challenge tạm thời nào cũng bị nâng cấp thành `[P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`, gây hoang mang và hiểu lầm về hiện trạng tài sản farm.

## 3. Quy chuẩn Khắc phục (2 Tầng Phòng Vệ)
1. **Tầng Classifier (`classifier.py`): Feed Detail Controls Guard:**
   - Trước khi phân loại một màn hình là `manual-needed:manual_challenge` hoặc `manual-needed:verification`, BẮT BUỘC kiểm tra trạng thái Feed:
     * Nếu `_has_feed_detail_controls(elements)` là `True` (có các nút like, comment, share, avatar...) hoặc có thanh điều hướng đáy (`Trang chủ`, `Hồ sơ`), **TUYỆT ĐỐI KHÔNG gán nhãn `manual_challenge`**. Captcha/challenge thật của TikTok luôn là modal chiếm trọn màn hình và che khuất hoàn toàn các nút feed.
     * Khi thu thập `texts` và `descs` để so khớp từ khóa bảo mật, loại trừ các node có resource-id thuộc video metadata (`:id/desc`, `:id/title`, `:id/comment_text`) và package `com.android.systemui`.
2. **Tầng Giám sát Batch (`batch_aggregator.py`): Phân loại chuẩn xác:**
   - **`SESSION_LOST_KEYWORDS` (P0 Thực sự):** Chỉ kích hoạt khi có bằng chứng mất session/đăng xuất thật: `"logged out"`, `"signed out"`, `"session expired"`, `"phiên đã hết hạn"`, `"văng"`, `"login screen"`, `"đăng nhập lại"`.
   - **`CHALLENGE_KEYWORDS` (Cảnh báo Thử thách tạm thời):** Đối với `"captcha"`, `"manual_challenge"`, `"checkpoint"`, `"verification"`, hiển thị nhãn `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`, tuyệt đối không gắn mác P0 MẤT PHIÊN.

## 4. Kỷ luật Điều phối Coordinator
- Khi nhận Farm Alert `[MÁY N]` báo mất phiên:
  1. **Không hoảng loạn can thiệp thô bạo:** Tuyệt đối không chạy script login đè hoặc xóa app khi chưa đối soát.
  2. **Inspect O(1) hiện trường:** Mở TikTok, mở trực tiếp Account Switcher (`input swipe 540 1200 540 800 200 && input tap 500 140`), chụp screencap và dùng WinRT OCR đếm số lượng tài khoản thực tế.
  3. **Chỉ kết luận văng nick khi OCR Switcher thiếu nick so với Excel.**
