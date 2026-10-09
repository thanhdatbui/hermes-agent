# Case 147: Profile Username Still Mismatched After Switch (Lỗi Mạng Settle / 'Đã xảy ra lỗi')

**Ngày ghi nhận:** 11/09/2026  
**Module liên quan:** `python_runner/flows/feed_swipe_smoke.py` (`verify_and_switch_profile`, `_find_account_switch_option`)  
**Triệu chứng:**
- Máy báo lỗi `profile username still mismatched after switch` sau 3 lần switch attempt.
- Kiểm tra XML/screenshot (`profile_preflight_switcher_N_guard` / `profile_preflight_verify_N_identity_guard`):
  - Nick mục tiêu (vd: `phanlan097`) ĐÃ CÓ trong danh sách switcher sheet.
  - Script đã tìm thấy và tap đúng tọa độ của account mục tiêu.
  - Sau khi tap và đóng sheet quay lại Profile, profile vẫn hiển thị username cũ (vd: `lebaothao8787`).
  - Màn hình Profile xuất hiện view lỗi: `Đã xảy ra lỗi` / `Thử lại sau` kèm nút `Thử lại` (`com.ss.android.ugc.trill:id/dcj`).
  - Do settle time quá ngắn hoặc mạng chậm, request switch session của TikTok server bị lỗi / chưa nạp xong, dẫn đến đọc lại profile vẫn là nick cũ.

**Khắc phục chuẩn:**
1. Trong `verify_and_switch_profile`, bổ sung kiểm tra màn hình Profile sau khi switch xem có nút `Thử lại` (`z6g` / `dcj` / text `Đã xảy ra lỗi`) hay không. Nếu có, bấm `Thử lại` và đợi settle 3-5s trước khi kết luận switch thất bại.
2. **Pitfall lấy XML & Tap element động (BẮT BUỘC):**
   - Không kiểm tra chuỗi trên `latest_identity.get("xml_text")` vì trường này có thể là object representation hoặc None/empty, dẫn tới check fail silent. Phải đọc file XML thật từ `latest_identity.get("xml_path")` (hoặc `artifact_path / "ui.xml"`).
   - Tuyệt đối KHÔNG hardcode tọa độ tap (ví dụ: `tap 540 1436`). Phải parse XML (`parse_xml`), tìm UI element có `resource-id` chứa `:id/dcj` hoặc text `"Thử lại"` / `"Retry"`, sau đó tính center coordinates (`element.center` hoặc parse bounds) để gửi lệnh tap ADB.
3. Đảm bảo `_is_account_switcher_missing_expected_reason` và auto-reconcile fallback chỉ kích hoạt khi thực sự thiếu tài khoản; nếu tài khoản đã tồn tại trong switcher sheet thì tập trung retry switch / xử lý modal retry mạng thay vì rơi vào `manual-needed`.
4. Kiểm tra cú pháp bằng `py_compile` và chạy Canary test với `-RecoveryTestSwipes 2` để xác nhận switch thành công và hoàn tất swipe.
