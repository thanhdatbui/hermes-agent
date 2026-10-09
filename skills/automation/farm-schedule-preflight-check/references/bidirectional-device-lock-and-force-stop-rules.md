# Quy chuẩn Device Lock 2 Chiều, Quyền Force-Stop & Safety Net 1h TTL

## 1. Bản Chất Sự Cố Xung Đột Concurrency
Trong quá trình Coordinator test reg TikTok trên thiết bị, Coordinator đã gửi lệnh ADB thô (`am force-stop`, `keyevent 3`) lên máy mà không nhận thức được tiến trình `run_batch_live_2fa.py` (add 2FA TikTok) đang điều khiển máy đó.

**Hai lỗ hổng kiến trúc được bóc tách và triệt tiêu:**
1. **Lỗ hổng Bypass Lock do Cờ Opt-in (`DEVICE_LOCK_ENABLED`):** 
   - Trong `social_reg_v1.py`, hàm acquire lock bị bọc bởi `lock_enabled = os.environ.get("DEVICE_LOCK_ENABLED", "").strip().lower() in {"1", "true", "yes"}`.
   - Khi chạy CLI đơn lẻ bằng tay (`python social_reg_v1.py <STT> ...`), biến môi trường này mặc định bằng rỗng (`False`), khiến script chạy mà **không hề tạo file lock chuẩn `machine_<N>.lock.json`**. Hậu quả: Toàn bộ hệ thống và Coordinator tưởng máy rảnh, nhảy vào can thiệp chéo.
   - **Cách fix triệt để:** Bỏ hoàn toàn cờ opt-in, ép cứng `user_authorized=True` trong `_acquire_social_device_lock_or_skip()` và kiểm tra lock ngay entrypoint `register()`. Nếu máy đang bị lock bởi cron/script khác -> DỪNG (Safe-Skip) ngay từ dòng 1.
2. **Coordinator gọi ADB thô không kiểm tra Lock:** 
   - Coordinator dùng `subprocess.run(["adb", "-s", serial, "shell", "am", "force-stop", ...])` trực tiếp, bỏ qua việc kiểm tra xem file lock của máy có đang tồn tại và thuộc về một PID còn sống hay không.

---

## 2. Quy Tắc Quyền Force-Stop Thiết Bị
- **Câu hỏi:** *Khi test đồ có được force-stop không?*
- **Quy chuẩn:** **CÓ, VẪN CẦN THIẾT.** Thao tác `am force-stop` là hygiene dọn dẹp cơ bản để đưa app về clean state trước khi chạy test.
- **RÀNG BUỘC CỨNG (INVARIANT):** 
  - Chỉ tiến trình **ĐANG NẮM GIỮ DEVICE LOCK HỢP LỆ** trên máy đó mới có quyền gọi `am force-stop` và `input keyevent 3`.
  - Coordinator hoặc bất kỳ tiến trình ngoài lề nào **TUYỆT ĐỐI CẤM** tự ý force-stop một máy mà một PID khác đang sở hữu lock.
  - Khi bắt gặp màn hình lạ (màn hình cài đặt 2FA Authenticator, màn hình upload video, v.v.): **DỪNG LẠI NGAY (FREEZE & HANDS-OFF)**, tuyệt đối không được tự suy diễn là "treo/kẹt" rồi dọn dẹp phá hoại.

---

## 3. Kiến Trúc Khóa Hai Chiều (Bidirectional Device Lock Enforcement)
1. **Kỷ luật Lock khi User giao việc On-Demand / Canary / Manual Run (BẮT BUỘC):**
   - **Chỉ thị tối cao từ User:** *"Kể cả khi t giao việc cho mày làm, mày cũng phải lock lại (tất nhiên là lúc đó máy rảnh) và sau đó k cron nào đc chiếm"*.
   - Khi Coordinator nhận lệnh can thiệp máy đơn lẻ (chạy canary upload avatar, fix account, probe UI, test flow):
     * Bước 1: Kiểm tra máy rảnh (không có active lock nào khác).
     * Bước 2: **BẮT BUỘC acquire Device Lock vật lý ngay lập tức** với `user_authorized=True`, `pinned=True`, `status="running"` để tạo file `~/.codex/device-locks/machine_<M>.lock.json`.
     * Bước 3: File lock có `user_authorized=True` này đóng vai trò lá chắn bất khả xâm phạm. Mọi cronjob nền (`post_noon_chain_watchdog` Reg Gmail, `post-morning-gmail-2fa-watchdog`, nuôi feed/follow) khi quét tìm máy rảnh sẽ lập tức nhận diện máy bận và **BỎ QUA (SKIP) AN TOÀN**, tuyệt đối không được phép nhảy vào chiếm máy.
     * Bước 4: Sau khi task kết thúc, release lock an toàn trong khối `finally:`.
2. **Xóa sổ hoàn toàn cờ bypass và cấm tắt lọc Lock trong Launcher:**
   - Mọi script và runner (kể cả lệnh test CLI đơn lẻ hay launcher PowerShell) bắt buộc ép cứng `user_authorized=True` khi gọi `acquire_device_lock`.
   - File lock `machine_<N>.lock.json` phải được ghi nhận tại `~/.codex/device-locks/`.
   - Trong các module kiểm kê/launch (như `machine_inventory.py` của `Tiktok-video`): CẤM TUYỆT ĐỐI việc pass qua bỏ kiểm tra lock (`return entries`). Bắt buộc kiểm tra đồng thời cả 2 thư mục `~/.codex/device-locks` và `~/AppData/Local/automation-core/device-locks`.
3. **Khóa ngay tại Entrypoint:**
   - Kiểm tra `acquire_device_lock` ngay dòng đầu tiên của hàm thực thi chính (`register()`, `login()`, `feed()`, `ensure_avatar()`).
   - Nếu máy đang bị lock bởi cron hay script khác: **LẬP TỨC DỪNG LẠI (SAFE-ABORT)**, không gửi bất kỳ thao tác ADB nào vào máy.
4. **Giải phóng an toàn trong `finally:`**:
   - Luôn bọc execution trong khối `try ... finally: dev_lease.release()`, đảm bảo nhả lock trong mọi tình huống (thành công, lỗi logic, hoặc exception).

---

## 4. Cơ Chế Cron Tháo Lock Treo (Safety Net 3600s TTL)
- **File thực thi:** `D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py` (giám sát bởi `watch_device_locks.py`).
- **Nguyên tắc hoạt động:**
  - Định kỳ quét thư mục `~/.codex/device-locks/`.
  - **Chỉ dọn dẹp khi thỏa mãn 1 trong 2 điều kiện:**
    1. Tiến trình chủ sở hữu đã chết (`owner_process_alive(d) == False`).
    2. Tuổi của lock vượt quá ngưỡng an toàn **1 giờ (TTL = 3600 giây)**.
  - Khi reaped: Tự động di chuyển file lock vào `device-locks-reaped/` và phát lệnh ADB dọn dẹp:
    ```bash
    am force-stop com.ss.android.ugc.trill
    am force-stop com.zhiliaoapp.musically
    input keyevent 3
    ```
- **Lưu ý:** Đây là cơ chế tự động duy nhất được phép tháo lock quá hạn và reset máy về Home. Các tiến trình khác không được tự tiện tháo lock của nhau.

---

## 5. Kinh Nghiệm Chọn Mail Sàn dongvanfb.net Cho Quy Trình Reg & Ngâm 7 Ngày
- **Loại 1 (ID 5 - Hotmail TRUSTED [GRAPH API]):**
  - **LỖI:** Refresh token bị shop bóp scope hẹp (`IMAP/POP/SMTP`), **thiếu quyền `Mail.Read`**. Tool Farm gọi Microsoft Graph API sẽ bị lỗi `Graph token invalid.` -> **CẤM DÙNG**.
- **Loại 3 (ID 57 - HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM - 350đ):**
  - **Kỹ thuật Graph API:** Cấp full quyền Graph API (`User.Read`, `Mail.ReadWrite`, `Mail.Read`, `IMAP`, `POP`, `SMTP`). Tool Farm đọc OTP tự động từ PC mượt mà.
  - **Khớp quy trình đổi pass của User:** Mail có sẵn email khôi phục `@fviainboxes.com`. Sau khi reg TikTok và ngâm 7 ngày: Đăng nhập Microsoft đổi password -> Tích chọn *"Sign me out of all devices"* để đá toàn bộ thiết bị cũ của shop -> Vào *Security / Advanced Security Options* gỡ bỏ mail `@fviainboxes.com`.
  - **KẾT QUẢ THỰC NGHIỆM CHÍNH XÁC TRÊN TIKTOK (THỰC TẾ 23/09/2026):**
    * **ĐÍNH CHÍNH QUAN TRỌNG:** Con mail ID 57 (`odessostuffen14@hotmail.com` - 350đ) là **MAIL ZIN 100% CHƯA QUA TIKTOK**.
    * Tool Farm Taadaa chính chủ đã tự động bốc con mail này vào **Máy 22** lúc 13:29:02 trưa nay, TikTok xác nhận `CHUA DANG KY TikTok`. Tool tự động gọi Microsoft Graph API bóc mã OTP `965568` về, tạo thành công tài khoản `@lethanhlan14` (nickname `lethanhlan14`), lưu tracking dòng 176 `taikhoan_dat_v2_updated .xlsx`, ghi deferred result và kích hoạt warmup lướt feed 8 video. Máy 22 được set cờ cooldown `reg_success_daily_limit` đến 2026-09-24.
    * **Lý do màn hình Máy 201 hiện "Bạn đã đăng ký":** Do Coordinator lú lẫn, không tra cứu Source of Truth xem mail đã reg chưa, lại đem chính con mail vừa reg trên Máy 22 sang Máy 201 cắm vào form đăng ký, dẫn đến TikTok nhận diện tài khoản đã tồn tại.
    * **KẾT LUẬN CHÍNH THỨC VỀ DONGVANFB.NET:**
      - Loại 1 (ID 5 - 350đ): Lỏ, thiếu scope `Mail.Read`, cấm mua.
      - Loại 3 (ID 57 - 350đ): **CHUẨN 100% CHO FARM**. Token Graph API sống khỏe đọc OTP từ xa, mail Zin, đúng chuẩn quy trình ngâm 7 ngày đổi pass Hotmail + xóa mail khôi phục `@fviainboxes.com`.

---

## 7. Sự Cố Nick Ký Sinh (Cross-Device Parasite Account) & Quy Tắc Phòng Vệ Cấp Code
- **Bản chất sự cố:** Khi Coordinator đem email/tài khoản của Máy 22 sang nhập vào Máy 201 và gõ mã OTP `306203` gửi về, TikTok đã mở phiên đăng nhập thành công nick `@lethanhlan14` trên Máy 201. Nick này bị biến thành **nick ký sinh trên Máy 201**, dẫn đến tình trạng 1 tài khoản TikTok đăng nhập đồng thời trên 2 thiết bị khác IP/cụm (Máy 22 Kibe Local vs Máy 201 Admin Remote) -> Cực kỳ nguy hiểm, dễ bị TikTok quét hành vi bất thường và khóa nick hàng loạt.
- **Quy tắc cấm kỵ (Hard Invariant):**
  1. **Tra cứu Source of Truth trước khi thao tác:** Trước khi đem bất kỳ email/account nào đi test reg hoặc login, BẮT BUỘC tra cứu trong `taikhoan_dat_v2_updated .xlsx` (sheet `'Tài Khoản'`), `taikhoan_run_safe.xlsx`, SQLite `tiktok_tracker.db` và `social_reg_log.txt`. Nếu email đã được gán máy hoặc đã reg thành công -> TUYỆT ĐỐI CẤM đem sang máy khác.
  2. **Tách biệt chế độ Test Probe vs Login:** Khi chạy probe kiểm tra email có Zin hay không, chỉ được phép dừng ở bước đọc thông báo UI (*"Bạn đã đăng ký"* vs *"Nhập mật khẩu / OTP mới"*). Nếu thấy *"Bạn đã đăng ký"* -> Kết luận ngay, chụp ảnh màn hình nghiệm thu rồi force-stop/Back về Home. **CẤM TUYỆT ĐỐI bấm "Tiếp tục" rồi nhập OTP vào thiết bị lạ.**
  3. **AccountMachineBindingGuard (Cấp Code):** Thiết kế chốt chặn trong code: trước khi gõ email vào TikTok, script đối chiếu STT hiện tại với STT sở hữu trong file tracking. Nếu phát hiện lệch STT -> raise `PARASITE_ACCOUNT_VIOLATION` và abort ngay lập tức.

- **Case Study Máy 61 vs Máy 28 (Lệch Excel & Kẹt Trần 8 Acc - 24/09/2026):**
  * **Triệu chứng:** Runner reg bù Row 8 báo lỗi `MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`, nhưng Excel `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx` ghi Máy 61 mới có 7 nick, Slot 8 đang trống (`None`).
  * **Phương pháp Triage O(1):** Dùng `winrt_ocr.py` đọc toàn bộ 8 username hiển thị trong ảnh chụp Account Switcher `61_03_dropdown_013709.png`. Lập trình tra cứu ngược 8 nick này vào sheet `'Tài Khoản'` của `taikhoan_dat_v2_updated .xlsx`.
  * **Phát hiện:** Nick `anggiathinh2905` đang active trên Máy 61 thực chất thuộc về **Máy 28 (STT 221)**. Đây là nick ký sinh chiếm dụng Slot 8 của Máy 61 khiến máy không thể reg bù.
  * **Xử lý:** Áp dụng Section 8 (Quy trình đăng xuất sạch) để gỡ riêng nick ký sinh trên Máy 61 mà không ảnh hưởng 7 nick gốc, bảo vệ cấu trúc farm.


---

## 8. Quy Trình Đăng Xuất Sạch (Clean Multi-Account Logout) Khi Bị Dính Nick Ký Sinh
Khi một máy lỡ bị đăng nhập nhầm 1 nick ký sinh (ví dụ nick `@lethanhlan14` bị login nhầm vào Máy 201 đang có 5 nick gốc):
- **Cơ chế hoạt động của TikTok:** Khi vào menu Hồ sơ -> *Cài đặt và quyền riêng tư* -> Cuộn xuống đáy trang Settings bấm *Đăng xuất* -> Xác nhận popup đỏ *Đăng xuất*:
  * TikTok **CHỈ ĐĂNG XUẤT ĐÚNG NICK HIỆN TẠI** đang active.
  * TikTok tự động chuyển phiên active sang một trong các nick hợp lệ còn lại của máy (`ngocnam2234`).
  * Toàn bộ 5 nick cũ trong Account Switcher **KHÔNG BỊ MẤT**.
- **Các bước thực thi chuẩn xác (đã nghiệm thu thực tế Máy 201):**
  1. Vào Profile tab tại `(972, 1857)`.
  2. Mở menu hồ sơ 3 gạch tại `(1002, 144)`.
  3. Chọn *"Cài đặt và quyền riêng tư"* tại `(576, 1248)` (kiểm tra WinRT OCR tọa độ center).
  4. Cuộn xuống đáy trang Settings: swipe từ `(540, 1600)` lên `(540, 300)` 4 lần.
  5. Tap nút *"Đăng xuất"* tại `(292, 1662)`.
  6. Tại popup xác nhận *"Bạn có chắc chắn muốn đăng xuất?"*, tap nút đỏ *"Đăng xuất"* tại `(540, 1664)`.
  7. **Nghiệm thu bắt buộc (Gate 6):**
     - Mở Account Switcher tại dropdown tên tài khoản trên cùng.
     - Chụp ảnh màn hình nghiệm thu (`MEDIA:...`) chứng minh nick ký sinh đã biến mất hoàn toàn và toàn bộ danh sách nick gốc của máy được bảo toàn nguyên vẹn.
     - Đưa máy về Home và tắt màn hình.

---

## 6. Kỷ Luật Chủ Động Canh Máy Rảnh Cuốn Chiếu (Rolling Idle Machine Discovery across Dual Clusters)
- **Bài học từ chỉ trích của User:** *"thì kiếm 1 máy rảnh reg đi? ủa k biết canh cron cuốn chiếu máy rảnh à tao phải canh cho mày nữa à"*. Coordinator tuyệt đối không được thụ động ngồi chờ hoặc báo "tất cả máy kẹt" khi chỉ mới kiểm tra vài máy ở một cụm.
- **Quy trình quét cuốn chiếu O(1) tìm máy probe/reg lẻ:**
  1. **Tận dụng Cụm Admin Remote (201-280):** 
     - Cụm Kibe (1-80) thường dày đặc tài khoản (7-8 acc/máy), app TikTok thường ẩn nút *"Thêm tài khoản"*.
     - Cụm Admin (201-280 qua ADB `-H 192.168.110.119 -P 5037`) đa số chỉ có 3-6 accounts, nút *"Thêm tài khoản"* luôn hiển thị sẵn sàng.
  2. **3 điều kiện máy rảnh tuyệt đối:**
     - Không có file lock: `machine_<N>.lock.json` không tồn tại hoặc PID đã kết thúc.
     - Cooldown reg = False: `is_machine_reg_cooldown_active(N) == False`.
     - Số lượng tài khoản trên app < 8: Kiểm tra nhanh qua XML Switcher hoặc `taikhoan_run_safe.xlsx`.
  3. **Thực thi Probe & Bằng chứng tức thời (Gate 6):**
     - Mở app, tap vào Switcher -> "Thêm tài khoản" -> "Tiếp tục với email".
     - Điền email -> Chụp ảnh Checkpoint 1 (Pre-submit) -> Bấm Tiếp tục -> Chụp ảnh Checkpoint 2 (Post-submit / Response) trong vòng <= 3 giây.
     - Dọn dẹp máy: Force-stop và đưa về Home ngay sau khi có ảnh nghiệm thu.
