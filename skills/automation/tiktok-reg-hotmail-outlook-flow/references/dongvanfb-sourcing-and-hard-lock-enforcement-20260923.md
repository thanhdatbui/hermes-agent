# DongVanFB Mail Sourcing, Hard Lock Enforcement & Cuốn Chiếu Máy Rảnh (23/09/2026)

## 1. Đánh giá thực tế các loại Hotmail trên DongVanFB.net

- **Bản chất sàn DongVanFB.net**: Sàn chuyên bán Hotmail/Gmail phục vụ nuôi nick Facebook (tệp via FB). Trên giao diện và API **hoàn toàn KHÔNG có cam kết "Chưa qua TikTok" hay "Chưa qua dịch vụ"**.
- **So sánh 2 gói Hotmail Graph API phổ biến**:
  - **Loại 1 (ID 5 - Hotmail TRUSTED [GRAPH API] - 350đ)**: 👉 **LỎ, TUYỆT ĐỐI KHÔNG DÙNG**.
    - Token shop cấp bị Microsoft bóp scope chỉ có: `IMAP.AccessAsUser.All`, `POP.AccessAsUser.All`, `SMTP.Send`.
    - **Hoàn toàn THIẾU quyền `Mail.Read` và `Mail.ReadWrite`** của Microsoft Graph API. Khi gọi `graph.microsoft.com/v1.0/me/messages` lấy OTP trên PC bị trả về lỗi `Graph token invalid` (HTTP 401/403). Bắt buộc phải mở app Outlook trên phone gõ pass thủ công rất dễ dính checkpoint.
  - **Loại 3 (ID 57 - HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM - 350đ)**: 👉 **CHUẨN KỸ THUẬT CHO FARM**.
    - Token shop cấp có trọn bộ scope chuẩn: `openid`, `profile`, `User.Read`, `Mail.ReadWrite`, `Mail.Send`, `Mail.Read`, `IMAP`, `POP`, `SMTP`.
    - Gọi Microsoft Graph API lấy OTP và Magic Link trên PC chạy mượt mà 100%.
    - Phù hợp flow user: Reg TikTok -> Nuôi ngâm 7 ngày -> Đổi password Hotmail (tích chọn *"Sign me out of all devices"* để đá toàn bộ thiết bị cũ của shop) -> Vào Security xóa địa chỉ `@fviainboxes.com` để biến thành mail sở hữu độc quyền.
- **Sự thật về mail ID 57 (Sự cố Nick Ký Sinh & Bào Chữa Sai Lệch)**:
  - Mail ID 57 (`odessostuffen14@hotmail.com`): **LÀ MAIL ZIN 100% CHƯA QUA TIKTOK**.
  - **Sự thật lịch sử Farm**: Vào lúc 13:29 trưa ngày 23/09/2026, tool của Farm đã bốc mail này reg thành công rực rỡ trên **Máy 22** thành tài khoản `@lethanhlan14`, lưu tracking dòng 176 `taikhoan_dat_v2_updated .xlsx` và đặt cooldown 24h cho Máy 22.
  - **Sự cố lú lẫn của Coordinator**: Chiều cùng ngày, Coordinator không kiểm tra Source of Truth mà vác con mail này đi cắm vào **Máy 201** để test. Khi TikTok phát hiện mail đã có tài khoản và báo *"Bạn đã đăng ký"*, Coordinator lại ngộ nhận là *"mail cũ bị ai đó reg trước đem bán"*, rồi **tự ý bấm Tiếp tục và nhập OTP từ Graph API**, làm tài khoản `@lethanhlan14` bị đăng nhập song song lên Máy 201 $\rightarrow$ **Tạo thành nick ký sinh (Parasite Account) nguy hiểm trên 2 thiết bị vật lý**.
  - **Đã khắc phục hiện trường**: Đăng xuất sạch sẽ `@lethanhlan14` ra khỏi Máy 201, trả Máy 201 về nguyên trạng 5 nick hợp lệ, bảo toàn nick an toàn trên Máy 22.
  - 👉 **Kết luận chuẩn xác**: Mail Loại 3 (ID 57 - 350đ) trên DongVanFB.net là **Zin 100%, token Graph API sống khỏe, Farm tự động reg nick và đọc OTP mượt mà 100%**.

---

## 2. Phòng Chống Nick Ký Sinh & Kiến Trúc ParasiteAccountGuard (Commit `cc05cf6`)

1. **Check Source of Truth trước khi test**: BẮT BUỘC tra cứu workbook tracking (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`) / DB / log trước khi đem mail đi test. CẤM tự suy diễn mail cũ khi chưa đối soát lịch sử reg của Farm.
2. **Cấm Reg Hijacking (Screen State Chokepoint)**: 
   - Trong `social_reg_v1.py` (`_find_or_fallback_email`), khi gặp trạng thái `registered` hoặc `registered_otp`:
     ```python
     log(f"   ✗ {em}: DA CO TikTok va dang o OTP/verify → ABORT email nay tren luong reg, CAM login len!")
     save_ui_xml(device_id, f"fail_{stt}_email_already_registered_otp_{idx}")
     shell(device_id, "input", "keyevent", "4")
     time.sleep(2.0)
     continue
     ```
   - CẤM TUYỆT ĐỐI bấm Tiếp tục hay nhập OTP để đăng nhập lén vào máy khác.
3. **Module Chặn Cứng Cấp Hệ Thống (`parasite_guard.py`)**:
   - `assert_account_machine_binding(target_stt, account_identifier, allow_override=False, operator_reason="", audit_file=None)`:
     - Tra cứu STT máy sở hữu từ master tracking workbook (`find_account_owner_stt`).
     - Nếu `owner_stt != target_stt` và không có cờ `allow_override` -> Ném ngay ngoại lệ `ParasiteAccountViolation`, chặn đứng hoàn toàn thao tác gõ phím / login.
   - **Tích hợp kép**:
     - Trong `tiktok_login_v1.py` (`login_one_account`): Kiểm tra cả `account['id']` và `account['login_email']`. Hỗ trợ CLI flag `--override-machine`.
     - Trong `social_reg_v1.py` (`register`): Kiểm tra `target_email` trước khi khởi chạy form reg.
   - **Structured Telemetry & Audit Persistence**:
     - Ghi log định danh `[telemetry:parasite-guard] action=... target_stt=... account=... status=... reason=...`.
     - Persist toàn bộ audit events dạng JSONL vào `D:/Taadaa/runtime/audit/parasite_guard_audit.jsonl`.
4. **Phân định rõ ràng không cản trở nghiệp vụ**:
   - *Pool Auto (Batch)*: Chặn cứng 100% nếu mail/id đã thuộc máy khác trong tracking.
   - *Canary Explicit (`--email`)*: Lệnh chỉ định của User chỉ warn & audit log, tuyệt đối không chặn nhầm canary của User.
   - *Re-login nick bị văng*: Chạy bằng `tiktok_login_v1.py` trên cùng máy luôn được phép 100%. Chuyển máy (migration) dùng cờ `--override-machine`.

---

## 3. Lỗ hổng bypass Lock cũ & Cơ chế Hard Lock 2 chiều (`social_reg_v1.py`)

### Nguy cơ đã xảy ra (Sự cố phá hoại flow 2FA)
- Coordinator thấy màn hình máy phụ thuộc flow khác (màn hình "Thiết lập xác minh 2 bước" / Authenticator App của batch `tiktok-add-bao-mat-f2a`) đã ngộ nhận là máy bị treo, tự ý gọi `am force-stop` và `input keyevent 3` (Home), phá vỡ tiến trình đang chạy của user.
- **Nguyên nhân kỹ thuật**: Trong `social_reg_v1.py`, hàm `_acquire_social_device_lock_or_skip` dùng cơ chế opt-in:
  ```python
  lock_enabled = os.environ.get("DEVICE_LOCK_ENABLED", "").strip().lower() in {"1", "true", "yes"}
  ```
  Khi chạy lệnh CLI đơn lẻ, biến môi trường này rỗng (False), khiến script bypass hoàn toàn `acquire_device_lock`, không tạo file `machine_<N>.lock.json`. Do đó, script lao vào can thiệp máy mà không bị cơ chế lock của farm ngăn chặn.

### Giải pháp Hard Enforcement đã triển khai (Commit `a73e863`)
1. **Ép cứng `user_authorized=True`**:
   - Xóa bỏ cờ bypass `DEVICE_LOCK_ENABLED`. Mọi lần chạy `social_reg_v1.py` bắt buộc phải acquire file lock chuẩn `machine_<N>.lock.json` tại `~/.codex/device-locks/`.
2. **Chặn cứng ngay tại entrypoint `register()`**:
   ```python
   # HARD LOCK ENFORCEMENT: Phải acquire được device lock của farm trước
   dev_lease = _acquire_social_device_lock_or_skip(stt, device_id, "register")
   if dev_lease is None:
       log(f"[telemetry:device-lock] machine={stt} serial={device_id} action=acquire_conflict status=safe_abort reason=active_lock_by_other_process")
       log(f"⚠ STT {stt} đang bị khóa bởi tiến trình/cron khác -> DỪNG để đảm bảo an toàn.")
       return False
   ```
   Nếu máy đang bị khóa bởi bất kỳ tiến trình nào (`run_batch_live_2fa.py`, `run_tiktok.py` feed session, v.v.), script lập tức **Safe-Abort**, không thể mở app hay gửi lệnh ADB vào thiết bị.
3. **Bảo đảm giải phóng lock**:
   ```python
   finally:
       try:
           if not reg_success:
               release_machine_reg_reservation(stt, token=res_token)
               _post_reg_cleanup(device_id, stt=stt)
       finally:
           dev_lease.release()
           log(f"[telemetry:device-lock] machine={stt} serial={device_id} action=released status=closed")
   ```
4. **Bộ test hồi quy bắt buộc**: File `tests/test_register_hard_lock.py` bao phủ đủ 5/5 trường hợp:
   - Abort ngay khi device lock unavailable.
   - Acquire và release chuẩn trong `finally` khi success.
   - Release chuẩn trong `finally` khi gặp exception.
   - Release lock khi cooldown active.
   - Release lock khi reserve slot thất bại.

---

## 4. Kỷ luật Coordinator: Quét cuốn chiếu tìm máy rảnh liên cụm

- **Quy tắc bất khả xâm phạm**: Khi một máy có tiến trình khác đang giữ lock hoặc app đang ở màn hình của flow khác (như 2FA setup, lướt feed, captcha) -> **HANDS OFF TUYỆT ĐỐI**. Cấm tự tiện force-stop hay bấm Home.
- **Tư duy cuốn chiếu chủ động (Anti-Waiting)**:
  - Khi user yêu cầu test đồ hoặc reg tài khoản, Coordinator **CẤM bị động ngồi chờ** hoặc chỉ chăm chăm vào 1 máy quen thuộc rồi dừng lại báo bận.
  - Phải lập tức truy vấn danh sách máy rảnh thỏa mãn đủ 3 điều kiện:
    1. **Không bị lock**: Không có file `machine_<N>.lock.json` của PID còn sống (`psutil.pid_exists(pid)`).
    2. **Không cooldown**: `is_machine_reg_cooldown_active(m) == False`.
    3. **Chưa đủ 8 tài khoản**: Trên app TikTok phải có `< 8 tài khoản` (nếu đủ 8 tài khoản, TikTok tự ẩn nút "Thêm tài khoản" gây lỗi `MACHINE_FULL_8_ACCOUNTS`).
  - **Mở rộng phạm vi liên cụm (Kibe 1-80 ↔ Admin 201-280)**:
    - Nếu toàn bộ cụm Kibe Local (1-80) đang chạy ca nuôi/2FA hoặc đã login đủ 8 acc, **chủ động chuyển ngay sang cụm Admin Remote (`192.168.110.119:5037`) từ máy 201-280**.
    - Cụm Admin có nhiều máy mới chỉ đăng nhập 4-5 tài khoản, nút *"Thêm tài khoản"* luôn hiển thị sẵn sàng nhận job test tức thì.
