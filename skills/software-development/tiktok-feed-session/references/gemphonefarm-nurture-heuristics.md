# GemPhoneFarm TikTok Nurture Logic Analysis & Heuristics

Tài liệu phân tích kỹ thuật từ kịch bản trực quan của GemPhoneFarm (`TIKTOK-Nuôi-Tài-Khoản-Goc`, 205 nodes, 481 edges) và các heuristic nuôi nick TikTok có thể áp dụng cho các runner tự động (`automation-core`, `tiktok-luot nuoi acc`).

## 1. Cơ chế Skip Quảng Cáo (Ad Fast-Skip)
- **Dấu hiệu nhận biết:** Node văn bản chứa `Được tài trợ` (`//node[@text="Được tài trợ"]`).
- **Hành vi chuẩn:**
  - Không dừng lại xem quá lâu.
  - Không thực hiện bất kỳ tương tác like/comment/share nào.
  - Delay tối thiểu 0.5s - 1.0s và thực hiện ngay thao tác `swipe-scroll` lên để chuyển sang video tự nhiên kế tiếp.

## 2. Mô hình phân bổ phiên lướt (Tab & Session Entropy)
Script sử dụng xúc xắc ngẫu nhiên với tỷ lệ:
- **Đề xuất (For You):** ~60% (Random 1-9 trên thang 15).
- **Đang Follow (Following):** ~20% (Random 10-12).
- **Bạn bè (Friends):** ~20% (Random 13-15).

Số lượng video mỗi tab được chia nhánh theo các loop riêng biệt (ví dụ For You có 5 nhánh: 14, 17, 20, 23, 25 video) giúp tránh pattern đồng nhất giữa các tài khoản nuôi trong cùng 1 dàn máy.

## 3. Heuristic Thả Tim An Toàn (Natural Like Behavior)
- **Tỷ lệ thả tim:** Mặc định từ 10% - 15% tổng số video xem.
- **Quy trình like 3 bước:**
  1. **Pre-like Watch Time:** Không thả tim ngay khi video vừa tải. Giữ chân xem từ 4.4s đến 16.4s (mô phỏng người dùng xem hết nửa video hoặc có hứng thú).
  2. **Verify State:** Luôn kiểm tra `content-desc="Thích"` và tránh bấm nếu đã là `content-desc="Đã thích video"`.
  3. **Post-like Rest:** Nghỉ 1.5s - 3.8s sau khi thả tim trước khi quyết định vuốt tiếp.

## 4. Xử lý Popup & Chặn CAPTCHA nhẹ
- **CAPTCHA Close Bar:** Quét tìm `verify-bar-close` (`//node[@resource-id="verify-bar-close"]`). Bấm nút `X` để đóng popup trượt xác minh thử xem có trở lại feed bình thường không trước khi coi là kẹt hoàn toàn.
- **Benign Popups:**
  - Email / SĐT liên kết: `//node[@text="Để sau"]`.
  - Quyền danh bạ / Facebook: `//node[@text="Không cho phép"]`.
  - Lịch sử xem hồ sơ: `//node[@text="Lưu"]`.
