# Case 99: Lỗi Switch Account Mismatch & Khắc phục nhận diện Profile (2026-09-04)

## 1. Hiện tượng & Triệu chứng
- **Alert**: `[ALERT] [MÁY N] Dừng: manual-needed | Lý do: profile username still mismatched after switch`
- **Ngữ cảnh**: Tài khoản trong sheet hoặc account switcher hiển thị Display Name hoặc Handle có prefix `@`, badge số đính kèm, hoặc dấu tiếng Việt / khoảng trắng (ví dụ: handle `quch.trangg` vs display name `Quách Trangg1`).
- Màn hình account switcher mở lên có tài khoản mục tiêu nhưng script không chuyển hoặc chuyển xong không verify được và dừng ở `manual-needed`.

## 2. Nguyên nhân kỹ thuật
1. **Fuzzy Identity Matching thiếu sót**:
   - `find_exact_account` và `verify_selected_account` trong `automation_core.tiktok.account_switcher` trước đây chỉ dùng `_normalize(val) == expected`, không tận dụng hàm fuzzy `matches_switcher_identity`. Khi TikTok trả về node có `@`, số badge, hoặc tên hiển thị tương đương, hàm báo duplicate hoặc không tìm thấy.
2. **Bounds chạm trên Switcher Row**:
   - Node Button (`com.ss.android.ugc.trill:id/lkp`) có độ rộng toàn màn hình (`[0, y1][1080, y2]`). Khi tap vào tọa độ center `(540, y)`, điểm chạm có thể nằm vào khoảng trống hoặc không trigger được sự kiện chọn tài khoản trên một số bản TikTok.
3. **Modal Switcher không tự đóng sau khi chọn**:
   - Trên một số máy, sau khi tap chọn tài khoản (trạng thái đổi thành `selected="true"` / `checked="true"`), bottom sheet không tự ẩn -> script bị kẹt hoặc classify nhầm là `manual-needed:account-switcher`.
4. **Follow Hook chạy dài trong canary test**:
   - Chạy test recovery với `-RecoveryTestSwipes 2` nhưng runner lại tự động kích hoạt `_run_follow_hook` (chạy script follow tới 20 phút), khiến lệnh PowerShell canary tưởng như bị treo.

## 3. Giải pháp chuẩn đã triển khai

1. **Cập nhật `automation_core.tiktok.account_switcher`**:
   - `find_exact_account`: Tích hợp `matches_switcher_identity(value, expected)` kết hợp ưu tiên `exact_tappable` khi có cả container button và textview con.
   - `verify_selected_account`: Hỗ trợ xác nhận thành công nếu xuất hiện node khớp theo `matches_switcher_identity`.

2. **Cập nhật `feed_swipe_smoke.py`**:
   - Trong `_find_account_switch_option`: Thu hẹp bounds trả về thành bounds của inner TextView để tap chính xác vào khu vực text/avatar.
   - Tự động bắt sự kiện `is_already_selected` hoặc post-tap selected và gửi keyevent `4` (BACK) để đóng sheet.
   - Trong `verify_and_switch_profile` / `_profile_preflight_row`: Bổ sung kiểm tra cả `display_name` với `matches_switcher_identity`.

3. **Cập nhật `multi_machine_feed_session.py`**:
   - Thêm điều kiện skip `_run_follow_hook` khi `_recovery_test_swipes` được truyền vào `config`, giúp canary test hoàn tất nhanh chóng và trả về kết quả ngay lập tức.
