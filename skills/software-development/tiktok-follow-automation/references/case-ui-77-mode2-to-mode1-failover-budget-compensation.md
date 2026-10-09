# Case UI-77: Mode 2 Failover Sang Mode 1 Chạy Bù Budget & Giảm Reserve Deadline

## 1. Hiện tượng & Vấn đề thực tế (User Report 29/09/2026)
- **Triệu chứng:** Trong chế độ nuôi follow Hybrid (`mode="both"`), có 15 máy đủ điều kiện chạy follow nhưng chỉ có đúng 1 máy follow được 1 lượt, 7 máy bị báo 0 follow với lý do "đã follow sẵn (skip)".
- **Root Cause:**
  1. Trong `run_session` (`follow_runner/flows/follow_engine.py`):
     - Logic cũ yêu cầu: `if mode in ("1", "both") and res.status == STATE_OK:` mới chạy Mode 1.
     - Nếu Mode 2 gặp lỗi mở tab Following của Anchor (do layout drift, timeout mạng, hoặc selector chưa bắt kịp) sau 2 lần ladder recovery, `res.status` bị gán là `"MANUAL_REVIEW"` hoặc mang trạng thái lỗi.
     - Do đó, điều kiện `res.status == STATE_OK` bị sai $\rightarrow$ **Mode 1 bị triệt tiêu hoàn toàn, không được kích hoạt để chạy bù!**
  2. Ngưỡng thời gian an toàn (`reserve_seconds`):
     - Mode 2 và Mode 1 đều dùng `reserve_seconds = 180.0s` (3 phút).
     - Khi Mode 2 xử lý 3 anchor và retry tốn thời gian, thời gian còn lại trong phiên thường chỉ còn < 3 phút $\rightarrow$ Mode 1 kiểm tra `has_time_for_next_action(180.0)` thấy không đủ thời gian nên dừng ngay lập tức mà không kịp thử tìm kiếm UID nào.

## 2. Invariant & Quy chuẩn xử lý (User Directive: "Module 2 có thất bại cũng phải qua Module 1")
- **Nguyên tắc phân ranh giới lỗi:**
  - Chỉ duy nhất khi tài khoản bị TikTok chặn/nhả follow (`follow_failed == True` / `FOLLOW_FAILED`), runner mới được dừng toàn bộ phiên để bảo vệ nick (cooldown an toàn).
  - Mọi lỗi khác của Mode 2 (lỗi mở tab anchor, anchor private/0 following, anchor không có video, layout drift) đều thuộc diện **Mode 2 Degraded** chứ không phải lỗi tài khoản bị phạt.
- **Quy trình Failover chuẩn:**
  1. Khi Mode 2 hoàn tất (hoặc fail):
     ```python
     if mode == "both" and res.status != STATE_OK and not res.follow_failed and not (self.state is not None and self.state.follow_failed):
         # Chuyển mode2_degraded=True và reset status về OK để Mode 1 tiếp tục chạy bù budget.
         res.details["mode2_degraded"] = True
         if res.reason:
             res.details.setdefault("mode2_degraded_reasons", []).append(res.reason)
         res.status = STATE_OK
         res.failed = False
         res.reason = ""
     ```
  2. Mode 1 tiếp nhận phiên, tính toán số lượt follow còn thiếu (`budget_remaining - len(res.followed)`) và tìm kiếm UID trong farm để follow bù.
  3. Hạ `reserve_seconds` trước và trong Mode 1 xuống `60.0s` (thay vì 180s) để tận dụng tối đa thời gian phiên.
  4. Mở rộng nhận diện `RecyclerView` trong `_classify_follower_surface`: kiểm tra thêm `"recyclerview" in (node.get("class") or "").lower()` bên cạnh whitelist resource-id để chống kẹt timeout 35s.

## 3. Canary Verification Pitfalls & Bài Học Thực Chiến (29/09/2026)
- **Cấm ngộ nhận Unit Test PASS là hoàn tất Canary:**
  - Unit test / mocked pytest chỉ chứng minh syntax và control flow (`mode2_degraded=True` kích hoạt `run_mode1`).
  - Khi user hỏi *"Chạy canary chưa"*, BẮT BUỘC phải chạy targeted canary trên thiết bị thật (`--canary-hook <hook_name> --canary-target <target_uid> --canary-screencap <path>`) và nghiệm thu bằng ảnh UI thật qua `MEDIA:`.
- **Targeted Canary CLI Pitfall (Relative Import):**
  - Chạy `python D:/Taadaa/tiktok-follow/follow_runner/run_follow.py` trực tiếp sẽ dính lỗi: `ImportError: attempted relative import with no known parent package` khi resolve các package nội bộ (`.flows...`).
  - **Cách chạy đúng:** Chạy dạng module với `python -m`:
    ```bash
    PYTHONPATH="D:/Taadaa/tiktok-follow" python -m follow_runner.run_follow --machine <N> --config <path_config> --account-row-index <row> --skip-identity-verify --canary-hook open_following_tab --canary-target <anchor> --canary-screencap <path.png>
    ```
- **Xử lý trung thực khi Canary gặp Precondition / Popup cản trở:**
  - Nếu canary máy thật bị chặn bởi màn hình hệ thống (ví dụ: TikTok bung popup *"Thêm số điện thoại"* chắn mất view), TUYỆT ĐỐI CẤM phán đoán bừa là hook đã chạy thành công.
  - Bắt buộc dùng `screencap` + OCR (qua `windows-native-ocr` WinRT) để đọc text màn hình hiện tại.
  - Gửi ảnh hiện trường `MEDIA:`, báo trạng thái rõ ràng: **CANARY BLOCKED / FAILED (do UI popup chặn precondition, chưa chạm được vào đích hook)**, không được giấu lỗi hay đánh tráo khái niệm giữa "test code xanh" và "canary máy thật thành công".

