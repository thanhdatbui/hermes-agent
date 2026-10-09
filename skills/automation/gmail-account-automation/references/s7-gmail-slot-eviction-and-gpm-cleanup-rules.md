# Quy Tắc Giải Phóng Slot S7 & Điều Kiện Gỡ Tài Khoản Google Khỏi Thiết Bị

**Ngày cập nhật:** 2026-10-02  
**Chỉ thị từ Sếp (Operator Invariant):** Cứ tài khoản nào ĐÃ LOGIN LÊN GPM ĐƯỢC THÌ CHO PHÉP GỠ KHỎI S7 NGAY LẬP TỨC.

---

## 1. Bản Chất Mục Đích Vận Hành Farm S7 vs GPM
- **Mục đích của việc tạo Gmail trên S7:** Điện thoại Android vật lý chỉ đóng vai trò là "máy ấp/ngâm" ban đầu để vượt qua cơ chế bot detection của Google khi tạo tài khoản mới.
- **Mục tiêu cuối cùng:** Đưa toàn bộ tài khoản Gmail sống lên cụm **GPMLogin trên PC** (máy tính) để thực hiện các tác vụ nặng: nuôi lướt web, kích hoạt 2FA, nạp OAuth Google / Antigravity, cấp tài khoản cho pool.
- **Nguyên lý giải phóng slot (Slot Eviction):** 
  - Mỗi máy Samsung S7 mặc định chứa tối đa **8 tài khoản Google** (Cập nhật 04/10/2026: User Directive "8 acc đi", đồng bộ với chuẩn 8 nick/máy của Farm; cấu hình qua `MAX_S7_ACCOUNTS = int(os.environ.get("MAX_S7_ACCOUNTS", "8"))`).
  - Nếu tài khoản đã được kéo lên GPMLogin thành công (nhóm `Google_Live_Ready` / Group 10, hoặc đã có profile GPM login sống) ➔ **Phải giải phóng ngay khỏi máy S7** để nhường chỗ trống cho máy tiếp tục tạo nick mới.
  - Việc giữ khư khư nick cũ trên máy S7 vừa gây chật bộ nhớ, vừa chặn đứng khả năng reg mới của máy khi chạm trần 8 acc.

---

## 2. Thay Đổi Điều Kiện Gỡ Cuốn Chiếu (Rolling Cleanup Eviction Policy)
Trước đây script (`preflight_s7_rolling_cleanup.py`) yêu cầu quá cứng nhắc cả 3 gates: `Gate 1 (2FA) + Gate 2 (OAuth) + Gate 3 (Tuổi >= 30 ngày)`. Điều này dẫn đến tình trạng:
- Nhiều nick đã ngâm 3–7 tháng (68 đến 210 ngày tuổi) nhưng chưa có OAuth thì script vẫn từ chối gỡ, rồi in ra dòng log template gây hiểu nhầm: *"Máy đã có 5 accs nhưng chưa có acc nào đủ tuổi (>= 30 ngày)"*.

### Quy tắc mới (Hierarchical Eviction Rule — Cập nhật 02/10/2026):
- **KHÓA BẢO VỆ TỐI CAO — TIKTOK BINDING GATE (User Directive 02/10/2026):**
  + Trước khi gỡ bất kỳ Gmail nào trên máy S7 (kể cả khi `checkmail.live` báo DIE hay dọn dẹp khi đầy 5 acc), BẮT BUỘC gọi `get_tiktok_bound_emails(machine_id)` đối soát với `taikhoan_dat_v2_updated .xlsx`.
  + **NẾU EMAIL ĐANG GẮN VỚI NICK TIKTOK TRÊN MÁY:** **TUYỆT ĐỐI CẤM GỠ!** Phải giữ nguyên trên máy để nhận OTP/2FA cho TikTok (tránh thảm họa xóa nhầm mail như ca M3 `an.nhuan.work64541@gmail.com`).
1. **Ưu tiên 0 (Tài khoản DIE — Miễn trừ Ping Google):** Nếu phát hiện tài khoản trên máy bị Google khóa (DIE qua `checkmail.live`) VÀ KHÔNG LIÊN KẾT TIKTOK ➔ **Được phép gỡ ngay lập tức để dọn slot, không cần ping lại Google** (User instruction 02/10/2026).
2. **Ưu tiên 1 (Đã lên GPM thành công — USER CORRECTION):** 
   - Kiểm tra API GPMLogin (`http://127.0.0.1:19995/api/v3/profiles`): Nếu tài khoản đã có profile thuộc Group 10 (`Google_Live_Ready`) hoặc đã có session login hợp lệ VÀ KHÔNG LIÊN KẾT TIKTOK ➔ **Đủ điều kiện gỡ khỏi S7 ngay lập tức**.
3. **Ưu tiên 2 (Nick ngâm lâu năm $\ge 30$ ngày):**
   - Nếu chưa có thông tin GPM nhưng nick đã ngâm $\ge 30$ ngày, có 2FA VÀ KHÔNG LIÊN KẾT TIKTOK ➔ Cho phép gỡ cuốn chiếu theo thứ tự ngày tạo cũ nhất lên đầu.

---

## 3. Bẫy Lỗi UI Khi Gỡ Tài Khoản Trên Samsung S7 (`preflight_s7_rolling_cleanup.py`)
### Bug UI bấm nhầm chữ "Google":
- **Hiện tượng:** Khi mở `android.settings.SYNC_SETTINGS`, giao diện hiển thị danh sách tài khoản. Ở mỗi tài khoản Google, hệ thống Android hiển thị:
  - Dòng 1 (Tiêu đề): `<tên_email>@gmail.com`
  - Dòng 2 (Phụ đề): `Google`
- **Pitfall:** Nếu script tìm node có text là `"Google"` để click, nó sẽ bấm trúng phụ đề của tài khoản ĐẦU TIÊN trong danh sách, dẫn đến việc màn hình nhảy vào trang chi tiết của tài khoản đó. Khi đó, script tìm kiếm email mục tiêu cần gỡ sẽ báo lỗi: *"Không tìm thấy email ... trên màn hình Cài đặt"*.
- **Giải pháp chuẩn hóa (theo `tools/remove_device_google_account.py` & đã patch triệt để vào `preflight_s7_rolling_cleanup.py`):**
  - **TUYỆT ĐỐI KHÔNG** click vào chữ "Google" (đã xóa hẳn đoạn code legacy `# 3. Tap vào mục 'Google' nếu có nhóm Google`).
  - Tìm trực tiếp node chứa text chính xác là `<target_email>` hoặc content-desc của email trên danh sách `SYNC_SETTINGS`.
  - Nếu không thấy ở màn hình đầu ➔ Thực hiện vuốt `swipe 500 1200 500 600 300` để cuộn xuống tìm tiếp.
  - Click trực tiếp vào email ➔ Bấm "XÓA TÀI KHOẢN" (hoặc menu 3 chấm) ➔ Xác nhận popup "XÓA TÀI KHOẢN".

---

## 4. Kỷ Luật Báo Cáo: Cấm Nuốt Lỗi Script & Tách Bạch Lỗi Nền Tảng (OPERATOR INVARIANT)
- **Chỉ thị của Sếp:** "Lỗi script phải phân loại khác lỗi nền tảng chứ".
- Khi một máy cần dọn dẹp slot nhưng quá trình gỡ tài khoản thất bại (`REMOVE_FAILED`):
  - **Lỗi kỹ thuật:** Đây là lỗi tương tác UI hoặc lỗi kết nối thiết bị của script gỡ (`FAILED_CLEANUP`).
  - **Kỷ luật báo cáo:** Bắt buộc runner phải gắn nhãn **`FAILED` (Lỗi script gỡ account)**, hiển thị rõ lý do để kỹ thuật can thiệp sửa ngay.
  - **CẤM TUYỆT ĐỐI:** Phân loại `REMOVE_FAILED` vào nhóm "Skip an toàn", vì điều này làm ẩn giấu lỗi script, khiến máy bị tắc slot hàng tuần mà không phát ra bất kỳ cảnh báo nào.
  - **Sửa trong code runner:** Trong `gmail_reg_v10.py` và `run_parallel.ps1`, khi status là `REMOVE_FAILED` thì gán `exitCode = 1`, phân loại `FAILED_CLEANUP` (thuộc nhóm `FAILED`), cấm cộng dồn vào `skipSafeCount` / `skipLocked`.
- **Tách bạch trong Telemetry (`summary.json`):**
  - Nhóm 1: `platform_errors` (`phone_verify`, `account_creation_error`) ➔ Lỗi do Google / Proxy / Fingerprint.
  - Nhóm 2: `script_errors` (`failed_cleanup`, `failed_other`) ➔ Lỗi do script automation / UI tương tác. Cần fix code ngay.

---

## 5. Kỷ Luật Báo Cáo Khi Dọn Dẹp Tài Khoản S7 (User Directive 02/10/2026)
- **Chỉ đạo dứt khoát từ Sếp:**
  + *"Nếu v báo cáo khi dọn cũng phải ghi để t biết"*
  + *"Nhật kí dài dòng thế ghi ngắn gọn thoii. Còn cái đó thiết kế trong script r, lưu memory chi v"*
  + *"Là sao rolling là cái gì. Chỉ ghi gọn gàng die đã dọn dẹp: ... lỗi script: Khi dọn mail die, Khi reg. Đơn giản v mà"*
  + *"Phase 2 cx ghi như phase 1"*
- **Quy tắc thiết kế báo cáo & nhật ký chuẩn:**
  1. **Báo cáo chuỗi sau ca trưa (`post_noon_chain_watchdog.py`) — Đối xứng 2 Phase:**
     ```text
     [BÁO CÁO CHUỖI SAU CA TRƯA] Reg Gmail -> Add 2FA TikTok
     - Thời gian: 14:30 -> 15:35 (65 phút)

     - Phase 1 (Reg Gmail - Code 0):
       + Tổng máy: 40
       + Thành công: 38
       + Thất bại: 2
       + Die đã dọn dẹp: 1
       + Lỗi script:
         * Khi dọn mail die: 0
         * Khi reg: 0

     - Phase 2 (Add 2FA TikTok - Code 0):
       + Tổng máy: 20
       + Thành công: 20
       + Thất bại: 0
       + 2FA đã bật: 20
       + Lỗi script:
         * Khi đổi pass: 0
         * Khi add 2fa: 0
     ```
  2. **Audit Trail thời gian thực (`gmail_cleanup_history.txt`):**
     - Tuyệt đối KHÔNG viết dài dòng. Định dạng chuẩn mỗi dòng đúng 1 format gọn nhẹ, bắt buộc giữ thông tin serial trong ngoặc để phục vụ truy vết downstream device-to-account:
       `[YYYY-MM-DD HH:MM:SS] M<ID> (<serial>) | <DIE|ROLLING> | <email>`
       (Ví dụ: `[2026-10-02 14:38:12] M03 (9885e6344655484754) | DIE | an.nhuan.work64541@gmail.com`)
  3. Kỷ luật lưu trữ Memory vs Script:
     - Những gì đã được cấu hình chặt chẽ bằng code/script (đối soát file Excel, hàm helper, đường dẫn file log) thì **CẤM đưa vào Memory làm phình context vô ích**. Memory chỉ lưu các nguyên tắc vận hành cốt lõi và sở thích/kỷ luật của Sếp.

---

## 5.1. Kỷ Luật Điều Tra Mật Khẩu, Lịch Sử Reg & Đối Soát Workbook (OPERATOR CORRECTION)
- **Chỉ thị của Sếp:** "kiểm tra nick đó reg lúc nào sao k lưu pass, chắc chắn có pass trong log".
- Xem chi tiết tại: `references/credential-registration-audit-and-workbook-drift.md`.
- **Nguyên tắc cốt lõi:**
  1. Khi script báo `MISSING_PASSWORD` hoặc nick không có pass trong Excel, **TUYỆT ĐỐI CẤM** suy diễn vội vã rằng nick không có pass, nick là khoaleemagic hay chưa từng được reg.
  2. Phải truy vết ngược theo exact email/username vào log tổng (`reg_log.txt`), log batch (`logs_parallel_*`), database GPM (`profile_data.db`) để bốc:
     - Thời điểm reg (ngày giờ, timestamp).
     - Máy thực hiện reg (Machine ID / Device Serial).
     - Mật khẩu gốc được sinh ra hoặc sử dụng tại bước `[10] Password`.
     - Lý do vì sao sót trong Excel: write concurrency race condition, script batch chưa nối hàm sync, hay file Excel bị rollback.
  3. Phân định rạch ròi các trạng thái: `NOT_IN_WORKBOOK`, `BLANK_PASSWORD_IN_WORKBOOK`, `PASSWORD_FOUND_IN_REG_LOG`, `RECOVERY_EXCLUDED`. Cấm gộp chung thành "thiếu pass".
  4. TUYỆT ĐỐI KHÔNG dùng session_search làm bằng chứng hiện trường duy nhất; chỉ coi session history là manh mối để truy lục artifact thật trên đĩa.

---

## 6. Chẩn Đoán Khi Nhận Alert "Bỏ qua an toàn: N máy (đầy slot / nhường cron khác)"
- **Hiện tượng:** Runner báo `SKIPPED_FULL` / `FULL_NO_ELIGIBLE_CLEANUP`. User chỉ thị "điều tra", "fix này".
- **Kỷ luật đối soát trước khi can thiệp (Chống tự ý hạ gate an toàn):**
  1. Chạy `adb -s <serial> shell dumpsys account` lấy danh sách tài khoản Google thực tế trên máy.
  2. Đối soát `get_tiktok_bound_emails(machine_id)`: Xác định các acc bị khóa cứng bởi TikTok Binding Gate.
  3. Đối soát ngày tạo & GPM status của các acc còn lại: Kiểm tra xem đã có profile Group 10 (`Google_Live_Ready`) hoặc tuổi $\ge 30$ ngày kèm 2FA chưa.
- **Bản chất khi không có candidate:**
  - Nếu tất cả acc đều là TikTok-bound hoặc mới reg (7-15 ngày tuổi, chưa lên GPM, chưa 2FA) ➔ **ĐÂY LÀ HÀNH VI TỰ VỆ ĐÚNG CỦA HỆ THỐNG**, tuyệt đối KHÔNG coi là bug và KHÔNG được tự ý hạ chuẩn an toàn hay ép xóa nick.
- **Giải pháp giải phóng slot chuẩn luồng (Khử nghẽn S7 ➔ GPM):**
  - Điểm nghẽn thực sự là khâu nạp GPM chưa kéo kịp các acc mới này lên PC.
  - Giải pháp đúng đắn: Kích hoạt `post_evening_gpm_login_watchdog.py` nạp các acc phụ lên GPM trước. Khi acc đã lên GPM Live, preflight của máy S7 sẽ tự động nhận diện `has_gpm_live=True` và gỡ cuốn chiếu an toàn để nhường slot reg mới.
- **Phân định trần số nick (Capacity Policy vs Eviction Policy):**
  - Chi tiết quy trình xử lý xem tại: `references/slot-capacity-and-eviction-policy.md`.
  - Mở rộng trần số nick tối đa trên máy là thay đổi hạn mức phần cứng/nghiệp vụ, KHÔNG PHẢI thay đổi logic gỡ bỏ (eviction gate). Bắt buộc phải có chỉ thị rõ con số từ User trước khi sửa code.
