# Quy trình Dismiss Popup "Trạng thái tài khoản" & Reconcile Login Tài khoản Thiếu (2026-09-01)

## Bối cảnh & Nguyên tắc cốt lõi
1. **Không dừng lại sau khi chỉ đóng popup:**
   - Khi gặp popup `Trạng thái tài khoản` (*"Tài khoản của bạn đã bị đăng xuất. Hãy thử đăng nhập lại."* / `LogoutDialogActivity`):
     + Tọa độ nút `OK` ở góc dưới bên phải modal: tâm **`(921, 1144)`** (bounds text `[888, 1127][955, 1161]` trên màn hình 1080x1920).
     + Bấm `input tap 921 1144` để giải phóng giao diện và trả focus về `MainActivity`/`SplashActivity`.
   - Việc bấm nút `OK` chỉ là bước giải phóng giao diện.
   - BẮT BUỘC tiếp tục chạy ngay flow kiểm tra và đối chiếu tài khoản (`reconcile_tiktok_accounts.py` hoặc `SourceProjectNavigator.open_account_switcher()`) để xác định nick nào còn trên máy và nick nào bị văng.
   - Nếu phát hiện thiếu nick so với `taikhoan_run_safe.xlsx`, phải tiến hành đăng nhập bù ngay lập tức cho đủ số lượng account quy định của máy. Sau đó switch vào đúng nick ca hiện tại và xác nhận active profile trước khi tiếp tục feed.

2. **Bẫy `PROFILE_SUBPAGE_STUCK` trên Profile Root (TikTok 46.x):**
   - **Hiện tượng:** Khi mở Account Switcher từ Profile Root, core `account_switcher.py` báo `PROFILE_SUBPAGE_STUCK: Profile subpage remained open`.
   - **Nguyên nhân:** Icon mắt xem lượt xem hồ sơ trên header có `content-desc="Số lượt xem hồ sơ"` khớp với `_SUBPAGE_MARKERS`. Hàm `_is_profile_subpage` nhận nhầm đây là subpage và bấm `Back` (keyevent 4), làm app thoát Profile về Feed hoặc văng ra ngoài.
   - **Khắc phục:** `_is_profile_subpage` phải kiểm tra nếu `"menu hồ sơ"` / `"profile menu"` tồn tại hoặc `_selected_bottom_tab(node_list) is True` (và không có prompt lưu tiểu sử) thì trả về `False` (đang ở Profile root chính).

3. **Tọa độ mở Account Switcher trên Profile Root TikTok 46.x:**
   - Header tên `@username` dưới avatar `(540, 594)` là nút sao chép / sửa.
   - Tọa độ `(540, 150)` là bubble nhật ký / status ("Trà hay cà phê?").
   - Nút mở Account Switcher chuẩn là Display Name `(540, 552)` (`id/sv6`).

4. **Đăng nhập Hotmail không 2FA qua Outlook App & Fast-path TikTok:**
   - Với tài khoản Hotmail không 2FA:
     1. Đăng nhập hòm mail vào Outlook app trước (`login_outlook_one_machine.py` hoặc thao tác mở Outlook -> THÊM TÀI KHOẢN -> Chọn loại tài khoản -> Microsoft Outlook -> Chuyển sang "Sử dụng mật khẩu của bạn" -> Nhập pass -> Chấp nhận điều khoản -> Vào Inbox).
     2. Mở TikTok -> Profile -> Chuyển đổi tài khoản -> Thêm tài khoản.
     3. Nếu TikTok hiện gợi ý "Tiếp tục với tên @<username>" -> Tap fast-path `(540, 1250)`.
     4. Khi TikTok yêu cầu OTP: Mở Outlook app, vuốt kéo refresh hộp thư đến -> Đọc mã 6 số mới nhất -> Chuyển về TikTok gõ OTP -> Đăng nhập thành công.
     5. Mở Account Switcher xác nhận đủ 3/3 tài khoản.
