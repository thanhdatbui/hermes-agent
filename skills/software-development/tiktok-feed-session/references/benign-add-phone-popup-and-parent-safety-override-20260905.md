# Benign Add Phone Popup Trap, Parent Safety Override & Swipe Recovery Stuck (Case 109, 2026-09-05, Máy 74)

## 1. Triệu chứng & Bối cảnh
- **Alert**: `[MÁY 74] DỪNG PHIÊN`
- **Quy trình**: Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`)
- **Triệu chứng**: `benign Add phone popup detected; dismiss requires explicit flag; swipe recovery (2 swipes) still stuck`
- **Hiện trường**: Màn hình hồ sơ cá nhân hoặc feed xuất hiện popup "Thêm số điện thoại" (Add phone onboarding) hoặc trạng thái kẹt sau preflight.

## 2. Phân tích Nguyên nhân Gốc rễ (Root Cause)
Chuỗi lỗi gồm 3 mắt xích liên hoàn trong `python_runner`:

1. **Bẫy điều kiện `--allow-benign-popup-dismiss` trong `_maybe_dismiss_add_phone_row`**:
   - Trong `python_runner/flows/feed_swipe_smoke.py` (dòng 8191):
     ```python
     if not ctx.config.get("safety", {}).get("allow_benign_popup_dismiss", False):
         row["popup_type"] = "add_phone"
         row["popup_dismiss_action"] = "dismiss_close_x"
         row["popup_dismissed"] = False
         row["reason"] = "Add phone popup detected; --allow-benign-popup-dismiss not set"
         row["safety_reason"] = "benign Add phone popup detected; dismiss requires explicit flag"
         return row
     ```
   - Khi flag này không được bật, hàm từ chối gọi `dismiss_add_phone_popup` và trả về `manual-needed` kèm `safety_reason = "benign Add phone popup detected; dismiss requires explicit flag"`.

2. **Lỗi ghi đè Safety Config trong `multi_machine_feed_session.py`**:
   - Tại dòng 4676 của `flows/multi_machine_feed_session.py`:
     ```python
     child_safety = child_config.setdefault("safety", {})
     # Bật mặc định allow_benign_popup_dismiss để tự động đóng popup vị trí/quyền an toàn
     child_safety["allow_benign_popup_dismiss"] = True
     parent_safety = ctx.config.get("safety", {})
     if isinstance(parent_safety, dict):
         for _key in ("allow_benign_popup_dismiss", "allow_blanket_dismiss", ...):
             if _key in parent_safety:
                 child_safety[_key] = parent_safety[_key]
     ```
   - Mặc dù code đã chủ đích bật mặc định `child_safety["allow_benign_popup_dismiss"] = True`, nhưng vòng lặp `for _key in parent_safety` ngay sau đó lại lấy giá trị từ `parent_safety`. Vì `config.example.yaml` cấu hình `allow_benign_popup_dismiss: false`, nên `parent_safety` luôn chứa `False` (nếu CLI không truyền `--allow-benign-popup-dismiss`).
   - Kết quả: `child_safety["allow_benign_popup_dismiss"]` bị ghi đè ngược lại thành `False`, vô hiệu hóa cơ chế tự động dismiss an toàn trên toàn bộ worker machines.

3. **Bẫy Swipe Recovery không giải phóng được Modal Dialog**:
   - Khi `baseline` hoặc `profile_preflight` bị trả về `manual-needed`, flow gọi `_swipe_recovery_on_stuck(ctx, row=baseline, ...)`.
   - Hàm này thực hiện 2 lần vertical swipe (`input swipe`). Tuy nhiên, đối với modal dialog như "Add phone", thao tác swipe dọc không làm mất dialog.
   - Sau 2 lần swipe thất bại, `_swipe_recovery_on_stuck` ghép chuỗi:
     ```python
     row["reason"] = f"{row.get('reason') or ''}; swipe recovery (2 swipes) still stuck"
     row["safety_reason"] = f"{row.get('safety_reason') or ''}; swipe recovery (2 swipes) still stuck"
     ```
   - Tạo thành thông báo dừng phiên hoàn chỉnh: `benign Add phone popup detected; dismiss requires explicit flag; swipe recovery (2 swipes) still stuck`.

## 3. Quy chuẩn Khắc phục & Phòng vệ (Standard Pattern)

1. **Bảo toàn Default Cho Child Safety trong `multi_machine_feed_session.py`**:
   - Không để `parent_safety` ghi đè `False` lên `child_safety["allow_benign_popup_dismiss"]`.
   - Chỉ ghi đè khi parent có cờ explicit disable hoặc giữ nguyên giá trị `True` an toàn cho feed session.

2. **Auto-Dismiss An Toàn cho Benign Add Phone Popup**:
   - Trong `_maybe_dismiss_add_phone_row` / `_maybe_dismiss_add_phone_baseline`:
     Đối với feed session (`feed-session-smoke`, `multi-machine-feed-session`), "Add phone" là onboarding popup lành tính đã có handler `dismiss_add_phone_popup` đóng bằng nút close-X (`dismiss_close_x`).
     Không được coi việc thiếu flag CLI là lỗi dừng phiên; phải ưu tiên gọi `dismiss_add_phone_popup` để tự động vượt qua.

3. **Cơ Chế Phối Hợp Dismiss trong `_swipe_recovery_on_stuck`**:
   - Trước khi hoặc trong khi thực hiện swipe recovery, nếu phát hiện màn hình là `ADD_PHONE_SCREEN` hoặc các benign popup tương tự, phải gọi handler dismiss tương ứng thay vì chỉ swipe mù quáng.

4. **Kỷ luật Điều phối Coordinator vs Worker**:
   - Coordinator chỉ kiểm tra O(1) hiện trường, không probe tay hay sửa code trực tiếp trên session chính.
   - Dispatch worker subagent thực hiện sửa code, viết focused unit test (<30s) và chạy canary command:
     `powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 74 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`
