# Case 70: Chuẩn Hóa Nhận Diện Switcher Anchor Header `:id/pke` & Phân Biệt Display Name Chưa Đặt Tên (Sự Cố Máy 61)

## 1. Hiện tượng & Triệu chứng
- Runner dừng phiên nuôi acc khi chuyển sang tài khoản kế tiếp (ví dụ: `khahoan01` trên Máy 61).
- Log/Báo cáo dừng phiên: `manual-needed:account-switcher-not-open: profile switch anchor could not be resolved safely`.
- Trạng thái hiện trường: Màn hình điện thoại đang ở trang Hồ sơ (Profile root), hiển thị thanh tiêu đề username (ví dụ: `thanhlee61`).

## 2. Nguyên nhân cốt lõi (Anti-Pattern)
- Trong Case 67 / Case UI-13, khi loại trừ các ID có thể mở nhầm màn hình "Thêm tên bạn mong muốn", resource-id `com.ss.android.ugc.trill:id/pke` bị đưa vào danh sách loại trừ cứng trong `find_switcher_anchor` (`automation-core`) và `_find_sticky_profile_header` (`tiktok-luot nuoi acc`).
- Tuy nhiên, trên phiên bản TikTok thực tế (như Máy 61), node `com.ss.android.ugc.trill:id/pke` (nằm trong layout `pkh` ở `bounds=[369,117][730,183]`) chính là TextView tiêu đề chứa username của Profile root và là anchor hợp lệ duy nhất để mở Account Switcher bottom sheet khi tap vào.
- Khi loại trừ cứng `:id/pke`, `find_switcher_anchor` trả về `None`, dẫn đến lỗi fail-closed `profile switch anchor could not be resolved safely`.

## 3. Quy tắc chuẩn hóa (Case 70)
1. **Bổ sung `pke` vào Switcher Anchor Suffixes:**
   - Trong `automation_core/tiktok/account_switcher.py`, thêm `"pke"` vào `_SWITCH_ANCHOR_RESOURCE_SUFFIXES`.
2. **Gỡ bỏ `:id/pke` khỏi danh sách loại trừ resource ID:**
   - Loại trừ `:id/pke` khỏi danh sách `(":id/pkh", ":id/pau", ":id/s9b", "tv_content_name")` trong `find_switcher_anchor` và `_find_sticky_profile_header`.
3. **Phân biệt bằng Text Markers thay vì cấm ID:**
   - Chỉ loại trừ khi text của node thực sự là nút hành động đổi tên / tiểu sử:
     `text in {"thêm tên", "add name", "thêm tiểu sử", "add bio", "số lượt xem hồ sơ", "lượt xem hồ sơ"}` hoặc `_is_badge_or_prompt_node(node)`.
   - Nếu text là username/display name thông thường (`thanhlee61`), `:id/pke` luôn được nhận diện là Switcher Anchor hợp lệ.
4. **Quy trình tiếp nhận Alert `[MÁY N] DỪNG PHIÊN`:**
   - Tuyệt đối không hỏi lại user thông tin repo/lỗi khi banner đỏ và screenshot đã thể hiện rõ số máy, script và lý do.
   - Trích xuất ngay số máy `N`, map sang serial, kiểm tra UI XML và chạy ngay target canary để xác nhận fix.
