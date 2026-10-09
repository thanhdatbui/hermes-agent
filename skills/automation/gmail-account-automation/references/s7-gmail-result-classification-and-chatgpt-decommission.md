# S7 Gmail Registration: Result Classification & ChatGPT S7 Decommission

**Ngày chốt:** 2026-09-30  
**Nguyên tắc vận hành tối cao:**

## 1. Dừng Vĩnh Viễn Đăng Ký ChatGPT Trên Samsung S7
- **Chỉ thị của Operator:** ĐÃ DỪNG HOÀN TOÀN việc đăng ký/liên kết ChatGPT trên thiết bị Samsung S7 sau khi reg Gmail.
- **Lý do kỹ thuật:**
  1. WebView Android 8.0 (Samsung S7) gặp lỗi Cloudflare Turnstile, layout shift do bàn phím ảo đẩy trúng phím `g` thành `@gmail.comg`, và rate limit OTP.
  2. Mật khẩu mới của OpenAI yêu cầu >= 12 ký tự, bẫy gộp thread email trên S7 dẫn đến nhập sai OTP 3 lần và dính cooldown.
  3. Khi hook ChatGPT trên S7 lỗi hoặc in log dài, nó làm ô nhiễm telemetry của runner và làm chậm batch.
- **Kiến trúc thay thế:**
  - Gmail sau khi reg trên S7 chỉ chạy warmup newsletter an toàn, sau đó để ngâm tĩnh $\ge 7$ ngày trên S7.
  - Sau thời gian ngâm, watchdog chuyển tài khoản lên **GPMLogin trên PC** (máy tính) để đăng nhập Google và thực hiện liên kết ChatGPT / Antigravity qua Playwright.
- **Điểm chốt chặn code (`gmail_reg_v10.py`):**
  - Trong `persist_success_result(acc, device_id)`: KHÔNG gọi `hook_chatgpt_register.register_chatgpt_on_device()`. Bỏ qua hook này, chỉ ghi log chuyển luồng sang GPM.
- **Điểm chốt chặn Cron Reporter & Watchdog (Chống Phantom Reporting):**
  - Dù code core đã ngắt hook, nếu các script watchdog hạ tầng (như `post_noon_chain_watchdog.py`) vẫn giữ dòng template báo cáo hoặc hàm quét log ChatGPT (`parse_chatgpt_warmup_counts`), thì mỗi khi `g_suc > 0` bot vẫn bắn tin Telegram nhắc đến ChatGPT.
  - Phải dọn sạch cả logic thực thi LẪN template báo cáo downstream để tránh tạo ra báo cáo ma (ghost reports).
  - Sau khi sửa script tại `AppData/Local/hermes/scripts/`, bắt buộc chạy `python cron_sync_watchdog.py --force` để đồng bộ sang Deploy và OneDrive.

## 2. Chuẩn Hóa Phân Loại Kết Quả Trong `run_parallel.ps1`
- **Pitfall cũ (Đọc 80 dòng cuối file log):**
  - Runner `run_parallel.ps1` trước đây dùng `Get-RunResultFromLog` đọc 80 dòng cuối (`Select-Object -Last 80`) của `machine_*.log`.
  - Các bước sau khi tạo Gmail (warmup, log kết nối, dọn dẹp) in hơn 80 dòng khiến dòng `SUCCESS: ...` bị trôi ra ngoài.
  - Lệnh tắt `spaymini` nhả ra `[adb warn] Error: java.lang.IllegalArgumentException: Unknown package: com.samsung.android.spaymini`. Dính chữ `Error:` khiến máy đã tạo acc thành công bị đánh trượt thành `FAILED_OTHER`.
- **Quy tắc phân loại chuẩn (Canonical Source of Truth):**
  1. **Ưu tiên số 1:** Kiểm tra file kết quả canonical `results/machine_$Machine.success.json`. Nếu file này tồn tại và có email, xác nhận ngay `status = "SUCCESS"`, `classification = "SUCCESS"`.
  2. **Tìm dòng SUCCESS toàn file:** Nếu chưa có JSON, regex `SUCCESS:\s+([^\s]+@gmail\.com)` phải duyệt toàn bộ nội dung file log (`$content`), không giới hạn 80 dòng cuối.
  3. **Phân biệt Safe Skips vs Lỗi Script Gỡ Tài Khoản (CRITICAL USER CORRECTION):**
     - `FULL_NO_ELIGIBLE_CLEANUP`: Máy đã có 5 tài khoản, chưa có acc nào đủ điều kiện gỡ an toàn (chưa login GPM hoặc chưa đủ tuổi) -> `status = "SKIPPED_FULL"`, `classification = "SKIPPED"`.
     - `REMOVE_FAILED` (LỖI SCRIPT / UI GỠ ACC): Khi việc gỡ tài khoản thất bại do lỗi kẹt UI, không tìm thấy email hoặc crash script -> **BẮT BUỘC BÁO LỖI / FAILED**, TUYỆT ĐỐI CẤM nuốt vào nhóm `SKIPPED` làm ẩn lỗi script khiến máy kẹt slot vô thời hạn mà không ai biết.
     - Các trạng thái `SKIPPED` thực sự (đủ 5 acc ngâm an toàn, device lock từ trước) được tính vào `$skipSafeCount` / `$skipLocked`, không tính vào `$fail`. Nhưng `REMOVE_FAILED` phải alert rõ ràng lên console/báo cáo.
  4. **Loại trừ ADB non-fatal warnings:**
     - Các log chứa `[adb warn]`, `Unknown package:.*spaymini` không được coi là `ERROR` của tiến trình reg.
     - **Lưu ý kiểm soát regex:** CẤM loại trừ chuỗi quá ngắn hoặc chung chung như `spay` hay `warn`, vì sẽ che khuất các lỗi thực sự. Bắt buộc match chính xác package cụ thể (ví dụ `Unknown package:.*spaymini`).
  5. **Bẫy thứ tự regex & Cấm match chuỗi "skip-safe" tùy tiện (CRITICAL PITFALL):**
     - Ở đầu mỗi lượt chạy, runner thường in cảnh báo kiểm tra ngày tháng: `[warn] May 15: last success row has missing/unparseable date, skip-safe`. Chuỗi này xuất hiện trong log của TẤT CẢ các máy!
     - Nếu đặt `-or $joined -match "skip-safe"` hoặc match `Skip an toan` lên trước các nhánh lỗi, các máy thất bại thực sự (`[PHONE_VERIFY]`, `[04_google]`) sẽ bị nhận diện nhầm thành `SKIPPED_SAFE`.
     - **Bắt buộc:** Luôn đặt kiểm tra `[PHONE_VERIFY]` và `[ACCOUNT_CREATION_ERROR]` TRƯỚC các nhánh kiểm tra skip. Chỉ match cấu trúc chính xác `[PREFLIGHT_CLEANUP].*Skip an toan`, `FULL_NO_ELIGIBLE_CLEANUP`, `REMOVE_FAILED`; CẤM TUYỆT ĐỐI match substring `skip-safe` đơn lẻ.

## 3. Tách Bạch Hoàn Toàn Lỗi Script vs Lỗi Nền Tảng (CRITICAL USER CORRECTION)
- **Chỉ thị của Operator:** "Lỗi script phải phân loại khác lỗi nền tảng chứ". Tuyệt đối không gộp chung lỗi do code/automation farm với lỗi do Google/proxy chặn.
- **Phân loại 2 nhóm lỗi độc lập trong `failure_breakdown`:**
  1. **Lỗi Nền tảng (Platform Errors):**
     - `phone_verify`: Google bắt xác minh SĐT do IP, proxy, hoặc device fingerprint.
     - `account_creation_error`: Google từ chối tạo tài khoản ở bước cuối.
     - *Bản chất:* Không phải do script hỏng; cần xoay proxy, đổi IP hoặc để máy nghỉ cooldown.
  2. **Lỗi Kỹ thuật / Script (Script Errors):**
     - `failed_cleanup`: Quá trình gỡ tài khoản trên Android bị lỗi (`REMOVE_FAILED`, vướng UI, lệch màn hình, không tìm thấy email).
     - `failed_other`: Script crash, lỗi cú pháp, timeout bất thường hoặc ngoại lệ chưa xử lý.
     - *Bản chất:* Báo động đỏ kỹ thuật cần sửa code automation ngay lập tức.
- **Cấu trúc metric chuẩn trong `summary.json`:**
  ```json
  "failure_breakdown": {
    "platform_errors": {
      "phone_verify": 5,
      "account_creation_error": 0
    },
    "script_errors": {
      "failed_cleanup": 1,
      "failed_other": 0
    }
  }
  ```
- **Tách biệt `$skipLocked` vs `$skipSafeCount`:**
  - Không được gom chung các máy skip an toàn vào `$skipLocked`.
  - `$skipLocked` CHỈ đếm `SKIP_DEVICE_LOCKED` (máy bị khóa phần cứng/tiến trình khác).
  - Thêm biến `$skipSafeCount` cho nhóm `classification == "SKIPPED"` (an toàn, không lỗi).
  - Output console chuẩn: `KET QUA: OK=$ok | SKIP_DEVICE_LOCKED=$skipLocked | SKIP_SAFE=$skipSafeCount | FAILED=$fail`.
  - Tránh silent catch `catch {}` khi đọc artifact `.success.json`; luôn log cảnh báo rõ ràng kèm số máy để hỗ trợ audit.
  - **Lưu ý merge workbook cuối ca:** Chi tiết về cơ chế Writer Identity Guard và fallback khi merge JSON kết quả thành công vào Excel xem tại `references/register-gmail-merge-writer-identity-and-excel-backfill.md`.

## 4. Chuẩn Kiểm Chứng Reviewer (Closeout Gate Standard >= 85)
- Khi điều chỉnh runner script PowerShell, ngoài các contract test tĩnh (`assert "... in PARALLEL"`), BẮT BUỘC bổ sung các bài test kiểm chứng thực thi runtime (runtime mocked tests):
  1. **Runtime test cho hàm phân loại PowerShell (`Get-RunResultFromLog`):**
     - Sử dụng fixture `tmp_path`, tạo cấu trúc thư mục logs giả lập có `results/machine_1.success.json` và các file `machine_*.log` chứa đầy đủ các biến thể case:
       * Case 1: Có file `.success.json` hợp lệ -> `classification = "SUCCESS"`.
       * Case 2: `FULL_NO_ELIGIBLE_CLEANUP` -> `status = "SKIPPED_FULL"`, `classification = "SKIPPED"`.
       * Case 3: `REMOVE_FAILED. Skip an toan` -> `status = "FAILED_CLEANUP"`, `classification = "FAILED"` (Lỗi script gỡ account).
       * Case 4: `[PREFLIGHT_CLEANUP] Skip an toan` -> `status = "SKIPPED_SAFE"`, `classification = "SKIPPED"`.
       * Case 5: `[PHONE_VERIFY]` -> `status = "PHONE_VERIFY"`, `classification = "FAILED"`.
     - Kỹ thuật gọi PowerShell từ pytest: Tránh dùng `Invoke-Expression` cắt chuỗi (dễ lỗi xuống dòng `\r\n` Windows). Hãy tạo file script `.ps1` tạm thời trong `tmp_path`, dot-source file gốc (`. '<path_to_ps1>'` có nháy đơn bao bọc đường dẫn có khoảng trắng), sau đó gọi qua `subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ...], check=True)`.
  2. **Runtime test cho hook Python (`persist_success_result`):**
     - Đổi logic trong file core (bỏ hook ChatGPT S7): test static `assert "hook_chatgpt_register" not in reg_code` là KHÔNG ĐỦ để đạt điểm Reviewer >= 85.
     - BẮT BUỘC có test runtime có mock (`unittest.mock.patch`), gọi trực tiếp hàm `persist_success_result`, mock `write_success_result_file` và `log`, kiểm tra:
       * Hàm trả về `True` bình thường.
       * Mock `log` bắt được thông điệp `[CHATGPT_S7]`.
       * Không xảy ra ngoại lệ làm đứt gãy luồng ghi kết quả thành công.
  3. **Vệ sinh Code & Observability:**
     - Xóa bỏ triệt để các import chết hoặc khối `try/except: pass` nuốt lỗi trong code chính để bảo toàn khả năng truy vết lỗi (audibility).
     - Luôn bổ sung metric có cấu trúc (`failure_breakdown`, `skip_safe`) trong summary JSON để telemetry minh bạch.

## 5. Chuẩn Hóa Báo Cáo Watchdog & Downstream Reporters (OPERATOR INVARIANT)
- **Chỉ thị của Operator:** "Báo cáo chuẩn hoá theo chưa".
- **Bắt buộc format báo cáo chuẩn:**
  CẤM dùng "Lũy kế", "đợt này", hoặc gộp chung `Fail (11)` không rõ nguyên nhân. Phải dùng format chuẩn ngắn gọn, trực diện:
  ```text
  [BÁO CÁO CHUỖI SAU CA TRƯA] [LANE GMAIL]
  - Thời gian: 15:15 -> 15:33 (18 phút)
  - Phase 1 (Reg Gmail - Code 0):
    • Đã hoàn tất: 7 máy
    • Bỏ qua an toàn: 3 máy (đầy slot)
    • Lỗi nền tảng (5): phone_verify: 5
    • Lỗi script: 0
  ```
- **Kỹ thuật parser downstream & Kỹ thuật Dual-Interface Compatibility:**
  - Watchdog script (`post_noon_chain_watchdog.py`) phải đọc trực tiếp `summary.json` bằng `utf-8-sig` (do PowerShell tạo UTF-8 BOM).
  - **Bẫy Breaking Changes khi đổi return type từ tuple sang dict:**
    * Trước đây hàm `parse_summary_counts` trả về `tuple[int, int, int]` (`tot, suc, fail`). Nếu đổi thẳng sang `dict` thông thường, mọi caller cũ hoặc test mock theo cú pháp unpacking `g_tot, g_suc, g_fail = parse_summary_counts(...)` sẽ throw `ValueError: too many values to unpack` hoặc phá vỡ caller.
    * **Giải pháp chuẩn hóa (Dual-Interface `SummaryResult`):**
      Kế thừa `dict` và override `__iter__`:
      ```python
      class SummaryResult(dict):
          def __iter__(self):
              return iter((self.get("total", 0), self.get("success", 0), self.get("failed", 0)))
      ```
      Vừa hỗ trợ unpack tuple 3 phần tử cho caller cũ, vừa hỗ trợ truy cập dict (`res["skip_safe"]`, `res.get("failure_breakdown")`) cho caller mới!
  - **Kỹ thuật Stub Decommission An Toàn (Chống `AttributeError` đa repo):**
    * Khi decommission một hàm (ví dụ `parse_chatgpt_warmup_counts`), TUYỆT ĐỐI KHÔNG xóa vội khỏi module khi chưa rà soát hết test suite và repo khác.
    * Giữ lại một stub deprecated trả về giá trị mặc định:
      ```python
      def parse_chatgpt_warmup_counts(log_dir_hint: Path | None = None, min_mtime: float | None = None) -> tuple[int, int]:
          """Deprecated: ChatGPT registration on S7 has been disabled."""
          return 0, 0
      ```
      Điều này ngăn chặn triệt để lỗi `AttributeError` khi các caller/test chưa kịp migrate.
  - Trích xuất cấu trúc `failure_breakdown`:
    * `platform_errors`: tính tổng `g_fail_p` và chi tiết các loại lỗi (phone_verify, account_creation_error).
    * `script_errors`: tính tổng `g_fail_s` và chi tiết (failed_cleanup, failed_other).
    * `skip_safe`: đếm số máy an toàn (đầy slot / locked).
  - Nếu `g_fail_p == 0` thì in `• Lỗi nền tảng: 0`. Nếu `g_fail_s == 0` thì in `• Lỗi script: 0`. Tuyệt đối không để trống hoặc báo gộp mập mờ.
  - Đồng bộ ngay lập tức sang Deploy và OneDrive sau khi chỉnh sửa: `python C:/Users/Kibe/AppData/Local/hermes/scripts/cron_sync_watchdog.py --force`.
