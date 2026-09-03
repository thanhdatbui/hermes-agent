# Bài Học Kỹ Thuật AI Auto-Recovery Code-First & Cấp Quyền Hệ Thống (19/08/2026)

## 1. Bản Chất Sự Cố "Auto-Recovery Chỉ Bấm Back Hoài / Không Vá Code"
### Nguyên Nhân Gốc Rễ
1. **Lỗ hổng trong Prompt `vision_client.py`:**
   - Prompt cũ chứa câu thòng: *"Chỉ viết handler nếu chắc chắn đủ bằng chứng từ XML/ảnh; ngược lại để `code_patch` rỗng"*.
   - Hậu quả: Khi gặp các màn hình quen thuộc (tìm kiếm, xem video lẻ, popup...), AI Gemini lười sinh code và để trống `code_patch = ""`, chỉ trả về `action_type = "back"` (hoặc lệnh ADB đơn thuần).
2. **Lỗ hổng Bypass trong `code_patcher.py`:**
   - Khi `code_patch` rỗng, `code_patcher.py` trả về `no_patch_needed` $\rightarrow$ Bỏ qua hoàn toàn các bước: Audit `plan-review` $\rightarrow$ Chạy `pytest` $\rightarrow$ `git commit & push`.
   - `agent.py` nhảy thẳng xuống bước gửi lệnh ADB lên thiết bị $\rightarrow$ Thiết bị được cứu tạm thời nhưng codebase không có rule mới $\rightarrow$ Lần sau máy khác gặp lại tiếp tục kẹt.
3. **Khắc Phục Chuẩn Hóa:**
   - Xóa bỏ hoàn toàn câu thòng trong Prompt.
   - Ép buộc nghiêm ngặt quy tắc **CODE-FIRST ORDER**: Bất kỳ sự cố nào cũng BẮT BUỘC phải sinh code Python / Rule XPath mới vào repo trước khi gửi lệnh can thiệp lên máy thật.

---

## 2. Bài Học Triển Khai Kiểm Thử & Chặn Spam Alert Pytest
### Hiện Tượng
- Khi chạy `pytest` trong repo `tiktok-luot nuoi acc`, các mock test trong `test_multi_machine_feed_session.py` (dùng mock Máy 11, tài khoản `user11`, lỗi *MagicMock*, *no VPN interface*, *child exited*...) gọi hàm `send_farm_machine_alert` và bắn thẳng hàng loạt cảnh báo giả lên nhóm Telegram Farm Alerts.
### Khắc Phục
- Thêm chốt chặn an toàn ngay đầu hàm `send_farm_machine_alert` trong `automation-core/src/automation_core/alerts.py`:
  ```python
  if "PYTEST_CURRENT_TEST" in os.environ:
      return False
  ```
- Đảm bảo môi trường chạy unit test/pytest hoàn toàn im lặng, chỉ có runtime thiết bị thật mới được gửi cảnh báo.

---

## 3. Khắc Phục Lỗi Quyền Vị Trí Android (PackageInstaller) Trên Máy 19
### Hiện Tượng
- Máy 19 gặp hộp thoại hệ thống *"Cho phép TikTok truy cập vị trí của thiết bị này?"* (có checkbox *"Không hỏi lại"* và nút *"TỪ CHỐI"* / *"CHO PHÉP"*).
- Mặc dù cấp `automation-core` đã có hàm `detect_packageinstaller_permission_dialog` và `dismiss_packageinstaller_dialog` hoàn chỉnh, nhưng máy vẫn dừng phiên báo `manual-needed`.
### Nguyên Nhân Kỹ Thuật
1. **Cờ `allow_benign_popup_dismiss` bị `False`:**
   - Trong `multi_machine_feed_session.py`, cấu hình con kế thừa cờ an toàn nhưng mặc định không bật `allow_benign_popup_dismiss = True` $\rightarrow$ Khi gặp hộp thoại quyền hệ thống, runner phát hiện ra nhưng bị cấm tự dismiss $\rightarrow$ Báo `manual-needed`.
2. **Xung Đột Selector `live_room_exit`:**
   - Rule `live_room_exit` trong `feed_swipe_smoke.py` chứa selector `com.ss.android.ugc.trill:id/long_press_layout` (vốn là container của mọi video Feed thông thường) $\rightarrow$ Video Feed bình thường bị nhận diện nhầm là phòng Live $\rightarrow$ Gây lỗi chuỗi khi kiểm tra.
### Khắc Phục
1. Set cứng `child_safety["allow_benign_popup_dismiss"] = True` trong `multi_machine_feed_session.py`.
2. Loại bỏ `long_press_layout` khỏi `live_room_exit`, chỉ match các dấu hiệu Live thực sự (`live_room_container`, text *"Phòng LIVE"*, *"Bảng xếp hạng hàng ngày"*, id `gu4`).

---

## 4. Bổ Sung Swipe Recovery Ở Đầu Phiên (`before_swipe`)
- Popup quảng cáo in-app xuất hiện ngay lúc mở app (như sữa Enfagrow A+ trên Máy 34) cần được xử lý bằng cơ chế vuốt lướt cứu hộ (`_swipe_recovery_on_stuck`) ở ngay phase `before_swipe`, tránh trường hợp vừa mở app gặp overlay là dừng phiên ngay.
