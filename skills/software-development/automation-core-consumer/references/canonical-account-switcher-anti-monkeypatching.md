# Canonical Account Switcher vs Consumer Patching Discipline

Date: 04/10/2026
Context: Khắc phục lỗi mở Account Switcher trên TikTok v47 (máy farm như Máy 34), bài học từ sự cố Agent nhầm lẫn tap avatar và tự chế monkey-patch trong consumer repo thay vì tuân thủ automation-core.

---

## 1. Bản Chất UI TikTok Account Switcher (Invariant)
1. **Tuyệt đối KHÔNG tap vào Avatar**:
   - Tap vào Avatar trên trang Profile mở xem ảnh đại diện, story hoặc camera; **hoàn toàn KHÔNG mở Account Switcher**.
   - Bất kỳ code hoặc đề xuất nào tap vào Avatar để chuyển nick là sai lệch hoàn toàn với hành vi app thật.
2. **Cơ chế mở Switcher chuẩn**:
   - Điểm kích hoạt là **Tên hiển thị / Username** ở header trên cùng của Profile.
   - Khi cuộn Profile (hoặc ở giao diện sticky), tên/ID ghim ở chính giữa phía trên (`y ≈ 140–160px`). Tap vào tên/ID này sẽ bung bottom sheet danh sách tài khoản (`is_switcher_open`).

---

## 2. Kỷ Luật Anti-Overengineering Với Consumer Repo
1. **Nguồn chân lý duy nhất (Single Source of Truth) là `automation-core`**:
   - Cơ chế mở và chọn tài khoản (`open_switcher`, `select_exact_account`, `find_switcher_anchor`) đã được chuẩn hóa và bao phủ hàng chục variant trong `automation_core.tiktok.account_switcher`.
   - Các consumer repos (`Tiktok-video`, `Tiktok_Reg`, `tiktok-follow`) chỉ đóng vai trò adapter chuyển tiếp sang `automation-core`.
2. **CẤM monkey-patch các hook riêng lẻ ở consumer adapter**:
   - Khi gặp lỗi `SWITCHER_NOT_CONFIRMED` hoặc `ACCOUNT_SWITCHER_FAILED`, CẤM tự ý chế cháo các hàm ad-hoc như `prepare_switcher_anchor` trong `adapter.py` (như tự thêm swipe tùy tiện, thay đổi bộ lọc candidate).
   - Việc chế cháo cục bộ tạo ra hành vi phân mảnh giữa các repo, dễ gây hồi quy chéo (làm đứt các layout khác) và vi phạm kỷ luật chống over-engineering.
3. **Quy trình chuẩn khi switcher gặp trục trặc**:
   - Kiểm tra UI thực tế qua screencap/XML: xác định xem màn hình có đang ở đúng Profile root hay bị popup/subpage/onboarding che khuất.
   - Nếu màn hình bị vướng popup hoặc chưa ở Profile: xử lý dismiss popup hoặc đưa về Profile root sạch.
   - Nếu layout mới chưa được core hỗ trợ: phải cập nhật đúng chuẩn trong `automation-core` kèm test hồi quy, không chắp vá vào consumer script.
