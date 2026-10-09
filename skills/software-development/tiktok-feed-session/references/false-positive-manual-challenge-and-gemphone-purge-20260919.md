# Case Study & Triage: False-Positive Manual Challenge & Farm Alert Purge (GemPhone Legacy)

## 1. Context & Root Cause (Sự cố 2026-09-19 - Máy 35)
- **Triệu chứng:** Hệ thống phát ra cảnh báo đỏ:
  `🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG`
  `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Máy M35: manual_challenge marker detected`
- **Thực tế hiện trường qua Canary Inspect & Account Switcher:**
  - Ứng dụng TikTok vẫn đang chạy bình thường ở For You feed.
  - Kiểm tra Switcher bottom-sheet bằng OCR: Đầy đủ 7/7 tài khoản active, hoàn toàn KHÔNG mất phiên, KHÔNG văng nick.
- **Root Causes:**
  1. **Tàn dư GemPhone trong Code (`python_runner/core/classifier.py`):** Code cũ giả định view `verify-bar-close` là banner của GemPhone và kết hợp quét text toàn màn hình (`[*texts, *descs]`). Khi video caption, tiêu đề hoặc bình luận chứa chữ "xác minh" (ví dụ `#hongkong #viral ... cần xác minh`), bộ phân loại bị lừa và gán nhãn `manual-needed:manual_challenge`.
  2. **Gộp chung Auth & Challenge trong `batch_aggregator.py`:** Bộ gom lỗi (`batch_aggregator.py`) xếp chung từ khóa `verification`, `manual_challenge`, `checkpoint` vào `AUTH_CRITICAL_KEYWORDS`, tự động kích hoạt cảnh báo đỏ giật gân `[P0 MẤT PHIÊN / VĂNG ACCOUNT]`.
  3. **User Clarification:** User xác nhận **Farm hoàn toàn không dùng GemPhone**; các class/rule có tên GemPhone là tàn dư copy code từ các bản cũ.

## 2. Giải pháp kỹ thuật chuẩn hóa (Standard Fix)

### A. Triệt tiêu logic `verify-bar-close` và bảo vệ Home Feed
Trong `python_runner/core/classifier.py`:
- **Xóa bỏ hoàn toàn** nhánh `if "verify-bar-close" in resource_ids:`.
- **Feed Controls Guard:** Kiểm tra `_has_feed_detail_controls(elements)`. Nếu màn hình có đầy đủ các nút tương tác video (like, comment, share, avatar...) thì **tuyệt đối không được gán nhãn `manual-needed:verification` hay `manual-needed:manual_challenge`** dù trong caption/mô tả có chứa từ "xác minh".
- Trong `python_runner/flows/feed_swipe_smoke.py`: Xóa bỏ rule rác `verify_bar_close` khỏi `GEMPHONEFARM_BLIND_POPUP_RULES`.

### B. Tách biệt cấp độ cảnh báo trong `batch_aggregator.py`
Trong `automation_core/batch_aggregator.py`:
- **Tách riêng 2 nhóm từ khóa:**
  - `SESSION_LOST_KEYWORDS`: Chỉ dành cho mất phiên thật (`logged out`, `signed out`, `session expired`, `phiên đã hết hạn`, `login screen`, `account screen`, `văng`). $\rightarrow$ Báo động `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`.
  - `CHALLENGE_KEYWORDS`: Dành cho thử thách/captcha tạm thời (`verification`, `manual_challenge`, `checkpoint`, `captcha`, `verify`). $\rightarrow$ Báo động `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`.
- Đồng bộ file đã sửa sang site-packages:
  `cp -rf src/automation_core/batch_aggregator.py "/d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/batch_aggregator.py"`
