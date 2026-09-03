# Quy tắc xử lý & Auto-Dismiss Popup TikTok Tổng Quát (Benign Dialogs)

## 1. Nguyên nhân lỗi "unexpected popup/dialog marker detected" lặp lại nhiều lần
- **Hardcoded chuỗi text đơn lẻ:** Trước đây mỗi khi phát sinh popup mới (xin quyền truy cập bạn bè Facebook/email, Google Smart Lock, đánh giá sao, đồng bộ danh bạ...), script thường chỉ thêm text cụ thể vào danh sách. Khi TikTok đổi wording hoặc ra dialog mới, script không match được $\rightarrow$ dừng phiên (`unexpected popup`).
- **Xử lý cục bộ từng máy:** Lấy lệnh ADB bấm tắt trên 1 máy chỉ giải quyết hiện tượng tức thời, máy khác trong 80–160 máy gặp lại sẽ tiếp tục dừng phiên.

## 2. Quy tắc thiết kế Generic Dismiss Matcher trong Codebase
Trong các flow `benign_popup.py`, `feed_swipe_smoke.py`, `device_prepare.py`:
1. **Tìm nút phủ định an toàn (Negative/Dismiss Actions):**
   - Tiếng Việt: `Không cho phép`, `Để sau`, `Lúc khác`, `Hủy`, `Bỏ qua`, `Không phải bây giờ`, `Đóng`, `Từ chối`.
   - Tiếng Anh: `Don't allow`, `Not now`, `Later`, `Cancel`, `Skip`, `Dismiss`, `No thanks`, `Close`.
   - Resource ID / Icon: `iv_close`, `btn_close`, `dismiss_btn`, `close_button`, nút có bounds ở góc trên modal.
2. **Cơ chế xử lý theo thứ tự ưu tiên:**
   - Ưu tiên 1: Bấm nút từ chối / bỏ qua (Dismiss) để tránh cấp quyền ngoài ý muốn.
   - Ưu tiên 2: Nếu dialog chỉ có 1 nút xác nhận duy nhất (`OK`, `Đã hiểu`, `Tiếp tục`), kiểm tra tiêu đề/nội dung có thuộc nhóm thông báo hệ thống lành tính (benign) hay không $\rightarrow$ bấm để đóng.
   - Ưu tiên 3: Nếu dialog không có nút bấm rõ ràng, thử nút `Back` Android (`input keyevent 4`) 1 lần để thoát overlay.

## 3. Quy trình 5 bước chuẩn khi nhận Farm Alert [MÁY N] về Popup
1. **B1 (Inspect):** `python D:/Taadaa/tools/inspect_machine.py <N>` để lấy XML và screenshot hiện trường (CẤM grep/find quét đĩa).
2. **B2 (Root Cause):** Mở `benign_popup.py` hoặc flow phụ trách để kiểm tra xem loại dialog này đã có trong bộ nhận diện chưa.
3. **B3 (Patch Script):** Thêm pattern hoặc nút bấm vào danh mục generic dismiss trong codebase để 160 máy đều dùng chung.
4. **B4 (Canary Test):** Chạy lệnh canary chuẩn:
   `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`
5. **B5 (Verify):** Kiểm tra exit code = 0 và xác nhận feed tiếp tục trơn tru.

## 4. Phân biệt ngữ cảnh điều phối (Context Hygiene)
- Khi user phản ánh lỗi lặp lại ("sao bị hoài v") mà không nêu đích danh công cụ: BẮT BUỘC kiểm tra trạng thái hoạt động thực tế hiện tại của Farm TikTok (các cảnh báo dừng phiên, farm alerts) trước, tránh liên đới sang các tác vụ ngoại vi cũ (như GPM Login hay VPS) đã chốt trước đó.
