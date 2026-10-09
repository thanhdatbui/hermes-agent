# Stale Post Receipt & Missing Account Login Recovery (2026-10-02)

## 1. XỬ LÝ LỖI STALE POST RECEIPT (`COMPAT-POST-VERIFY-004`)
### Dấu hiệu:
- Chạy video 1 trên nick mới hoặc nick chưa từng đăng (`Video Đã Đăng = 0`), runner dừng ngay tại `VERIFY_POST` hoặc trước `MEDIA_PUSH` với lỗi:
  `[MANUAL_REVIEW] [POST_SUBMISSION_UNKNOWN] post_submission_state=UNKNOWN: không có bằng chứng TikTok ACCEPTED submission; không được ghi workbook hay báo success (COMPAT-POST-VERIFY-004)`
- Kiểm tra `execution.log` thấy log:
  `[POST_RECEIPT] Receipt chưa hoàn tất; chuyển thẳng VERIFY_POST trước MEDIA_PUSH (baseline=0)`
  `Post verification blocked: submission state UNKNOWN (no ACCEPTED evidence); manual review required`

### Nguyên nhân gốc:
- Trong thư mục `D:\CodexRuntime\tiktok-video\idempotency\post-attempts\`, máy đang tồn tại file receipt cũ dạng `machine_<M>_account_<ACC>_video_1.json` với `status: "intent_pending"`, `post_tapped_at: null` từ một lần chạy trước đó (thậm chí từ nhiều tuần trước).
- Do video chưa từng bấm Đăng, `post_submission_state` lưu là `UNKNOWN`.
- Cơ chế fail-closed `COMPAT-POST-VERIFY-004` chặn không cho đăng video mới vì sợ đè lên bài đăng dở.

### Quy trình giải phóng an toàn (O(1)):
1. **Archive file receipt cũ**:
   - Backup file receipt sang thư mục backup hoặc đổi đuôi sang `.json.bak-stale-intent-<timestamp>` (CẤM xóa thẳng không backup).
   - Đảm bảo `_find_pending_post_receipts_for_machine()` không còn quét trúng file này.
2. **Kiểm tra Media Fingerprint**:
   - Xem trường `media_fingerprint_path` trong receipt. Nếu file json trong `idempotency\media-fingerprints\` vẫn ở trạng thái `reserved`, hệ thống sẽ tự động giải phóng nếu `age > stale_after_seconds` (30 phút).
3. **Chạy lại upload**:
   - Runner sẽ nhận diện sạch receipt và tiến hành flow chuẩn: `READ_WORKBOOK -> MEDIA_PUSH -> VIDEO_PICK -> POST -> VERIFY_POST`.

---

## 2. KỶ LUẬT PHỤC HỒI NHIỀU MÁY: CHẠY SONG SONG (PARALLEL MODE)
- Khi user phát lệnh "chạy song song" / fix hàng loạt máy:
  - CẤM chạy vòng lặp tuần tự `for m in machines` từng máy một gây nghẽn thời gian.
  - Sử dụng launcher đa luồng (threading / multiprocessing / PowerShell Start-Job) với **stagger 2-3s** giữa các máy để tránh xung đột USB ADB bus.
  - Mỗi luồng độc lập có timeout riêng (500s - 600s) để đủ thời gian transcode video và quét 4 viewport profile grid.
  - Tách riêng file log cho từng máy: `parallel_machine_<M>.log`.

---

## 3. CƠ CHẾ TỰ ĐỘNG KÍCH HOẠT TIKTOK LOGIN KHI THIẾU NICK / VĂNG ACCOUNT
### Vấn đề kiến trúc phát hiện (2026-10-02):
- Trước đây, khi Account Switcher không thấy nick của Row (`ACCOUNT_MISSING`), workflow chỉ dừng báo `MANUAL_REVIEW`.
- `config-machine-62.yaml` trỏ `login_recovery_command` vào worktree ma đã bị xóa (`D:\Taadaa\Tiktok_Reg-worktrees\...`).
- `run_tiktok_upload_batch.ps1` từng bị xóa mất hàm `Start-LoginRecoveryRunner` và gán cứng lệnh in `Write-Host "dừng fail-closed"`.

### Giải pháp cầu nối chuẩn (`recover_missing_tiktok_login.py`):
- Khi gặp `ACCOUNT_MISSING` hoặc `NO_ACCOUNT_LOGIN_REQUIRED`, BẮT BUỘC gọi script cầu nối:
  `python D:\Taadaa\tools\recover_missing_tiktok_login.py --machine <M> --account <USER>`
  (hoặc tự tra username từ `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` qua `--row <1-8>`).
- Script cầu nối tự động gọi engine login chuẩn của farm:
  `python D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py <M> --email <USER> --ss`
- Sau khi nạp nick thành công (`rc=0`), runner upload tiếp tục thực hiện đăng video bình thường, không được để task rơi vào trạng thái đứng im thụ động.

---

## 4. BẪY KỊCH TRẦN 8 TÀI KHOẢN (`MACHINE_FULL_8_ACCOUNTS`) & NICK KÝ SINH LỆCH MÁY
### Dấu hiệu:
- Chạy `tiktok_login_v1.py` / `recover_missing_tiktok_login.py` để nạp nick nhưng bị timeout 300s hoặc văng lỗi:
  `RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`
- Trên UI: Khi mở Account Switcher / Bottom sheet, **nút "Thêm tài khoản" (Add account) biến mất hoàn toàn**. Script cố cuộn tìm 3 lần đều không thấy.

### Nguyên nhân gốc:
- TikTok quy định cứng tối đa 8 tài khoản đăng nhập đồng thời trên một thiết bị. Khi đã đủ 8 nick, TikTok ẩn nút Add account, chặn mọi thao tác thêm nick mới.
- **Hiện tượng Nick Ký Sinh**: Thiết bị đang lưu 8 nick của máy khác (ví dụ: M48 ngậm 8 nick của M20). Dẫn tới nick phân bổ chuẩn của máy trong workbook không còn slot để đăng nhập.

### Quy trình xử lý chuẩn:
1. **Kế thừa Lock an toàn**:
   - BẮT BUỘC dùng `--allow-parent-lock` khi chạy recovery giữa ca để kế thừa `device-lock` từ parent project (`tiktok-luot nuoi acc`), tránh đụng độ lock.
2. **Kiểm tra danh sách tài khoản thực tế**:
   - Đọc danh sách tài khoản từ log `social_reg_log.txt` hoặc qua `account_inventory.py` / `_account_names`.
   - Đối soát từng username với `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` để xác định nick nào là nick ký sinh (sai STT) và nick nào là nick hợp lệ của máy.
3. **Giải phóng slot có kiểm soát (CẤM Clear Data bừa bãi)**:
   - Nick TikTok là tài sản: CẤM TUYỆT ĐỐI `pm clear com.ss.android.ugc.trill` vì sẽ làm mất sạch session của toàn bộ nick trên máy.
   - Chỉ đăng xuất có chủ đích các nick ký sinh đã xác định rõ chủ máy ở thiết bị khác, đưa tổng số nick trên máy về < 8 để nút "Thêm tài khoản" xuất hiện trở lại.
4. **Nạp nick chuẩn**:
   - Chạy `python D:\Taadaa\tools\recover_missing_tiktok_login.py --machine <M> --account <USER>` để nạp nick chính thức của máy.

