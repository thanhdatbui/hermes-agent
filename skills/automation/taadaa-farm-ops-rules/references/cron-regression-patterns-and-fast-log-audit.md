# Cron Regression Anti-Patterns & Fast Log Audit Playbook

Tài liệu đúc kết từ thực tế phân tích 24.081 sự kiện trên 448 file `log.jsonl` chạy cron nuôi acc trong 21 ngày (17/08 -> 06/09/2026).

---

## I. 5 ANTI-PATTERNS GÂY RA HIỆN TƯỢNG "SỬA LỖI B LÀM TÁI PHÁT LỖI A" (REGRESSION)

### 1. Scope Leak & Indentation Trap (Sửa ngoại lệ B làm vỡ luồng chính A)
- **Cơ chế:** Khi thêm logic xử lý cho một edge-case B (ví dụ: nick dạng user placeholder `user123456...`), đặt sai thụt lề (indentation) đưa biến hoặc khối kiểm tra ra ngoài phạm vi khối `except` hoặc `if`.
- **Thực tế đã gặp (Case 124 vs Case 126):**
  - Commit `eba47b8` (Case 124) kiểm tra placeholder candidate đọc biến `recaptured_xml`. Nhưng `recaptured_xml` chỉ được khởi tạo trong nhánh lỗi `except AccountSwitcherError:`.
  - Các tài khoản chuẩn không cần switch (như Máy 42) chạy nhánh bình thường (`verified = True`) lập tức crash với lỗi `UnboundLocalError: cannot access local variable 'recaptured_xml'`.
- **Quy tắc ngăn chặn:**
  - BẮT BUỘC khởi tạo giá trị rỗng mặc định (`recaptured_xml = ""`) ngay ở đầu hàm trước khi bước vào các khối `try/except`.
  - Khi viết test, không được chỉ test ca lỗi B; bắt buộc phải chạy kèm test ca thành công chuẩn A.

### 2. Incomplete Caller Wire-up (Vá hàm con nhưng quên truyền tham số từ hàm cha)
- **Cơ chế:** Thêm tham số tự động phục hồi lỗi A ở hàm lõi (callee), nhưng không cập nhật ở các hàm bọc (caller / wrapper trung gian). Khi chạy production qua chuỗi caller đó, lỗi A vẫn tiếp tục nổ.
- **Thực tế đã gặp (Case 125 vs Case 127):**
  - Commit `2124fc5` (Case 125) thêm `raw_xml` vào `safety_check()` để tự recover `focused package unavailable` khi TikTok đang mở.
  - Nhưng hàm bọc `safety_check_attempt()` không được cập nhật để truyền `raw_xml` vào `safety_check()`.
  - Hậu quả: Máy 46 vẫn tiếp tục bị dừng phiên với lỗi `focused package unavailable` (buộc phải ra thêm Case 127).
- **Quy tắc ngăn chặn:**
  - Khi sửa signature hoặc bổ sung fallback cho một hàm lõi, bắt buộc dùng `search_files` tìm tất cả các vị trí gọi hàm đó để wire-up đồng bộ 100%.

### 3. Partial Recovery Injection (Bọc auto-recovery ở hàm chính, bỏ sót ở hàm phụ)
- **Cơ chế:** Nhúng cơ chế tự phục hồi hạ tầng (như `reset_atx_agent` khi mất kết nối uiautomator) vào các hàm điều hướng chính, nhưng bỏ sót ở các hàm kiểm tra phụ trợ.
- **Thực tế đã gặp (Case 108/109 vs Farm Alert Máy 36):**
  - Đã thêm auto-recovery ATX ở `home navigation` và `profile navigation` giúp giảm lỗi ATX từ 50 lần (ngày 05/09) xuống 3 lần (ngày 06/09).
  - Nhưng bỏ sót hàm `_sponsored_present()` khi lướt feed. Khi Máy 36 bị nghẽn socket ATX lúc check sponsored video, ngoại lệ `UIDumpError` không được bọc đã văng ra ngoài dừng toàn bộ phiên nuôi acc.
- **Quy tắc ngăn chặn:**
  - Các bước kiểm tra phụ (heuristic check, sponsored check, badge check) BẮT BUỘC phải thiết kế **fail-soft** (bọc `try...except`, trả về `False` khi lỗi và log degraded), TUYỆT ĐỐI KHÔNG ĐƯỢC raise exception làm sập cả phiên lướt feed khi app TikTok vẫn đang hoạt động.

### 4. Uninitialized Variable in Conditional Branches
- **Cơ chế:** Dùng một biến tạm trong vòng lặp nhưng có một nhánh rẽ điều kiện (branch) không gán giá trị cho biến đó.
- **Thực tế đã gặp (Commit `9eca08a`):**
  - Ngày 30/08/2026, 103 phiên feed crash đồng loạt do `NameError: name 'loop_start' is not defined`.
  - Process chết đột ngột không kịp nhả device lock, dẫn đến dây chuyền 1.507 lần dính `DEVICE_LOCK_STUCK` trong ngày.
- **Quy tắc ngăn chặn:**
  - `py_compile` chỉ bắt lỗi syntax, không bắt được biến chưa khởi tạo trong runtime branch. Bắt buộc rà soát khởi tạo biến trước vòng lặp hoặc dùng linter.

### 5. Strict Artifact Digest without Cache Cleanup
- **Cơ chế:** Thêm cơ chế kiểm tra toàn vẹn chặt chẽ (strict digest/fingerprint) nhưng quy trình sinh manifest lại không dọn dẹp các artifact từ ca trước.
- **Thực tế đã gặp (Commit `b465ad6`):**
  - Ngày 01/09/2026 có 323 phiên feed thất bại với lỗi `cohort artifact assignment digest mismatch`.

### 6. Zombie Summary Fallback & Top-level Variable Ordering Trap (Case GMAIL-NIGHT-CHAIN-06)
- **Cơ chế 1 (Top-level Variable Ordering):**
  - Khi thêm import/logic ở phần đầu file (module top-level), sử dụng biến cấu hình (như `PROJECT_ROOT`) trước khi biến đó được định nghĩa ở phía dưới.
  - Hậu quả: File crash ngay lập tức khi được import (`NameError: name 'PROJECT_ROOT' is not defined`), làm tê liệt các launcher/inventory reader (`run_all.ps1`).
- **Cơ chế 2 (Zombie Summary Fallback):**
  - Pipeline cron cha khi gọi launcher con bị crash (không sinh được `summary.json` mới) lại fallback tìm file `summary.json` hoặc `all_results.json` có `mtime` mới nhất trong thư mục runtime mà KHÔNG kiểm tra giới hạn thời gian (age check).
  - Hậu quả: Pipeline bốc nhầm summary cũ từ nhiều ngày trước ra báo cáo Telegram liên tục qua nhiều đêm, che giấu hoàn toàn lỗi sập runner thực tế và tạo ra các triệu chứng báo động giả (như "proxy timeout" giả mạo).
- **Quy tắc ngăn chặn:**
  - `PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))` BẮT BUỘC đặt ngay đầu file, trước mọi logic ghép đường dẫn phụ trợ.
  - Mọi hàm fallback parse summary trong batch launcher (`parse_gmail_details`, `parse_tiktok_details`...) BẮT BUỘC phải chặn tuổi file: chỉ chấp nhận artifact được tạo trong vòng 3 giờ gần nhất (`time.time() - p.stat().st_mtime <= 10800`). Nếu không có file hợp lệ trong 3 giờ, trả về rỗng hoặc báo lỗi `RUNNER_CRASHED`.

### 7. Dual-Delivery Trap trong Hermes Cron (Báo đúp tin nhắn Telegram khi no_agent=True)
- **Cơ chế:** Khi một Hermes cron job được cấu hình với `no_agent: true` và `deliver: telegram:<chat_id>`:
  - Bản thân scheduler của Hermes sẽ tự động tóm lấy (capture) toàn bộ `stdout` (`print(...)`) của script và gửi nội dung đó làm tin nhắn tới Telegram channel.
  - Nếu bên trong script lại tự viết hàm `send_farm_alert(msg)` hoặc tự gọi Telegram Bot API (`urllib.request` / `curl` tới `sendMessage`), script sẽ phát 1 tin nhắn trực tiếp qua Bot API, rồi sau đó khi thoát process, Hermes scheduler lại lấy chính chuỗi `print(msg)` ra stdout để gửi THÊM 1 tin nhắn thứ 2 (`Cronjob Response: ...`).
  - Hậu quả: Người dùng nhận tin nhắn bị lặp kép (duplicate message) 2 lần liên tục trong cùng 1 phút (ví dụ case `post-evening-avatar-watchdog`).
- **Quy tắc ngăn chặn:**
  - Với mọi watchdog script chạy dưới Hermes cron `no_agent: true` đã có `deliver: telegram:<chat_id>`:
    - **Script CHỈ ĐƯỢC `print()` nội dung báo cáo ra stdout**, để Hermes scheduler tự làm nhiệm vụ delivery.
    - **CẤM TUYỆT ĐỐI** script vừa tự gọi hàm `send_farm_alert()` / Telegram Bot API vừa `print()` cùng một nội dung báo cáo ra stdout.
    - Nếu script là silent watchdog (chỉ báo khi có biến cố / hết ca / hoàn tất): khi bình thường không in gì (`silent`), khi cần báo thì `print(...)` một lần duy nhất.


---

## II. QUY CHUẨN QUÉT LOG CRON DIỆN RỘNG (FAST LOG AUDIT)

Khi cần thống kê lịch sử chạy cron dài ngày trong `D:/Taadaa/runtime/kibe/live`:
- **CẤM TUYỆT ĐỐI:**
  - Dùng `grep -rn`, `find`, `os.walk`, hay `glob.glob(..., recursive=True)` quét diện rộng trên toàn ổ `/d/Taadaa/` hoặc các cây thư mục media (như `D:\TIKTOK-videonuoinick` chứa hàng trăm nghìn file video rendered). Quét đệ quy không giới hạn sẽ gây I/O freeze và TIMEOUT 900s làm sập agent session.
  - Quét sâu vào từng thư mục con `machines/` của từng ngày, hoặc quét đệ quy tìm file lock/log.
  - Luôn chỉ định đích xác file hoặc thư mục đích cụ thể (ví dụ `/d/Taadaa/Tiktok-video/scripts/`, `D:/Taadaa/runtime/kibe/cron-state/`).
  - Trong MSYS bash trên Windows, không dựa vào dấu ngã `~` chưa bung (như `~/.hermes/...`), hãy dùng đường dẫn tuyệt đối chuẩn `/c/Users/Kibe/...` để tránh lỗi exit code 2.
- **VỊ TRÍ DEVICE LOCK CHUẨN:** Toàn bộ lock máy/serial nằm tại `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` và `serial_<serial>.lock.json`. Tuyệt đối không quét đĩa đệ quy tìm thư mục lock.
- **QUY TRÌNH O(1) CHUẨN:**
  1. Mỗi batch run tại `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-*/*` LUÔN có sẵn một file `log.jsonl`.
  2. File `log.jsonl` này ghi nhận tập trung toàn bộ sự kiện của tất cả 74 máy trong đợt chạy đó.
  3. Lấy danh sách file cực nhanh:
     ```python
     from pathlib import Path
     jsonl_files = sorted(list(Path("D:/Taadaa/runtime/kibe/live").glob("2026-*/row-*/*/log.jsonl")))
     ```
     (Chỉ mất ~3s để lấy toàn bộ 448 file của 21 ngày).
  4. Đọc tuần tự `log.jsonl`, bóc tách các dòng có `result in ('failed', 'manual-needed', 'blocked-proxy-vpn')` hoặc trường `error`. Tốc độ xử lý > 20.000 events chỉ mất ~30-40s.

---

## III. PLAYBOOK ĐIỀU TRA NHANH SỰ CỐ "HÀNG LOẠT MÁY BỊ LOCK DIỆN RỘNG BỞI RUNNER PID"

Khi coordinator phát cảnh báo nhiều máy (ví dụ: 26 máy) bị lock bởi 1 tiến trình `run_tiktok.py` (PID X):
1. **Kiểm tra Liveness & CommandLine O(1):**
   ```powershell
   powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'ProcessId = <PID>' | Select-Object ProcessId, Name, CreationDate, CommandLine | Format-List"
   ```
   Lấy ngay: `--machines`, `--max-workers`, và `--artifact-root`.
2. **Đọc log trực tiếp tại artifact root:**
   - Dùng đường dẫn `--artifact-root` từ CommandLine để vào thẳng thư mục batch (ví dụ `D:\Taadaa\runtime\kibe\live\2026-09-06\row-6-204825\20260906-152656\log.jsonl`).
   - Đọc trực tiếp file `log.jsonl` để kiểm tra tiến độ từng máy (success / manual-needed / pending).
3. **Đọc trực tiếp file lock O(1) tại `~/.codex/device-locks`:**
   - Đọc trực tiếp `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` cho các máy được báo cáo.
   - Kiểm tra `pid`, `status` (`running` vs `blocked`), `reason`.
4. **Phân biệt 2 nguyên nhân cốt lõi:**
   - **Do Threadpool Queueing:** Nếu số lượng máy yêu cầu > `--max-workers` (ví dụ 67 máy vs 40 workers), các máy ở cuối danh sách phải xếp hàng chờ nhả slot, dù vẫn giữ lock đăng ký.
   - **Do Lock Retention khi gặp lỗi nghiệp vụ (`manual-needed`):** Nếu máy gặp lỗi như `profile username still mismatched after switch`, worker giải phóng thread slot nhưng **cố tình giữ lock `blocked` (TTL 3600s)** để bảo lưu hiện trường trên điện thoại cho operator inspect (`python D:/Taadaa/tools/inspect_machine.py <N>`). Đây là hành vi mong muốn, không phải treo tiến trình.

---

## V. QUY TẮC TỐC ĐỘ PHẢN HỒI COORDINATOR

**Người dùng rất nhạy cảm với phản hồi chậm — mọi phiên coordinator phải hoàn tất O(1) inspection trong ≤ 2 lượt tool call trước khi dispatch worker.**

- CẤM gọi bất kỳ lệnh terminal nào có rủi ro treo (`find`, `grep -rn`, `os.walk`, `glob(recursive=True)`) trong session chính.
- Khi 1 lệnh terminal bị kẹt/timeout → kill và thông báo cho user ngay, không tiếp tục đọc thêm file.
- Batch nhiều tool call O(1) song song trong 1 lượt thay vì gọi tuần tự từng cái.
- Sau khi xác định được root cause và scope → dispatch `delegate_task` **ngay lập tức**, không đọc thêm code trong session chính.
- **Quy tắc 2 lượt:** Turn 1 = inspect log.jsonl + Get-CimInstance (parallel). Turn 2 = kết luận + dispatch worker. Nếu cần thêm turn thứ 3 do phát hiện hạ tầng (proxy/mạng) → kiểm tra proxy O(1) ngay, không duyệt tiếp source code.

---
 & XỬ LÝ LỖI SWITCH PROFILE

### 1. Hiện tượng "Nhìn màn hình giống hệt đang chạy Reg nhưng thực chất là Feed Reconcile"
- **Triệu chứng:** Người dùng thấy điện thoại mở TikTok, nhập mail, đọc OTP Graph API... và nghi ngờ cron reg ban đêm (`night-chain-reg-pipeline`) chạy nhầm đè vào ca nuôi.
- **Cơ chế thực tế:**
  1. Trong ca nuôi acc (ví dụ Feed Row 6 ngày chẵn), khi mở Account Switcher để chuyển sang nick mục tiêu, nếu gặp lỗi `profile username still mismatched after switch` hoặc thiếu nick trong switcher, runner nuôi acc (`feed_swipe_smoke.py`) tự động kích hoạt cơ chế auto-reconcile:
     ```bash
     python reconcile_tiktok_accounts.py --login-project D:\Taadaa\Tiktok_Reg ...
     ```
  2. Subprocess này dùng chính runner đăng nhập của `Tiktok_Reg` để đăng nhập bù tài khoản vào máy, khiến màn hình hiện các bước login/OTP giống hệt ca reg.
- **Quy trình đối soát O(1):**
  - **Cron check:** `cronjob(action='list')` kiểm tra `night-chain-reg-pipeline` (chỉ chạy lúc `01:00:00` sáng `0 1 * * *`). Nếu thời điểm hiện tại khác 01:00 AM, khẳng định ngay 100% không phải cron reg chạy nhầm.
  - **Process check:** `Get-CimInstance Win32_Process` kiểm tra tiến trình cha. Nếu cha là `run_tiktok.py --mode multi-machine-feed-session --account-row-index <N>`, đây là Auto-Login Reconcile của ca nuôi.

### 2. Nguyên nhân gốc rễ lỗi `profile username still mismatched after switch` diện rộng
- **Không phải văng tài khoản / die nick:** Nick mục tiêu thường đã có sẵn trong Account Switcher (dòng `com.ss.android.ugc.trill:id/lli`).
- **Nguyên nhân cốt lõi:**
  1. **Mất kết nối mạng tại thời điểm switch:** Thanh trạng thái hiển thị `Không có Internet` (`wifi_combo`), TikTok không hoàn tất đổi session trên server và âm thầm giữ nguyên nick cũ.
  2. **Popup chèn đè lên Switcher:** Popup đòi liên kết số điện thoại (`manual-needed:add-phone`: bottom sheet trắng) hoặc popup bảo mật che mất view, làm lệnh tap không ăn.
  3. **Thời gian settle time nạp session chưa đủ:** Cần delay 4.5 - 6.0s sau khi tap để TikTok nạp profile mới trước khi verify.

### 4. Khi lỗi `profile username still mismatched after switch` xảy ra DIỆN RỘNG (≥30% batch) → Nghi HẠTẦNG TRƯỚC, không nghi code
- **Pattern:** Lỗi xảy ra trên nhiều máy đồng thời (ví dụ 39/68 máy), ở cùng một ca chạy, nhưng 19-22 máy khác vẫn chạy thành công = code switch hoạt động đúng trên phần máy có proxy tốt.
- **Kiểm tra proxy O(1) ngay sau khi thấy batch alert lớn:**
  ```bash
  curl -v -m 5 -x http://192.168.110.2:200XX http://api.ipify.org
  ```
  Nếu trả `502 Bad Gateway` hoặc timeout → proxy cổng đó chết → đây là nguyên nhân gốc rễ.
  Tiếp theo kiểm tra MobiProxy box:
  ```bash
  python D:/Taadaa/AI-Tools/scripts/mobiproxy_auto_healer.py --check-and-heal
  ```
- **Quy tắc phân loại trước khi dispatch sub-agent:**
  - Số máy lỗi ≥ 30% batch VÀ có nhiều máy success song song → Nghi hạ tầng (proxy/mạng). Kiểm proxy trước.
  - Số máy lỗi ~ 100% batch VÀ lỗi giống nhau hoàn toàn → Nghi code/logic. Kiểm log detail + dispatch fix.

### 3. Quy chuẩn công cụ và đường dẫn trên Host Windows
- **Canonical ADB Binary:** `adb` không nằm trong Windows system PATH. CẤM gọi bare `adb` trong terminal MSYS/bash (dẫn tới `command not found` hoặc `WinError 2`). Đường dẫn chuẩn tuyệt đối:
  `C:\Program Files (x86)\xiaowei\tools\adb.exe` (hoặc dùng `python D:/Taadaa/tools/inspect_machine.py <N>`).
- **CẤM TUYỆT ĐỐI `find` / `grep -rn` trên `.ai-runs` và `runtime/`:** Thư mục `.ai-runs` và `runtime/kibe/live` chứa hàng nghìn thư mục con và tệp screenshots. Lệnh `find` sẽ bị treo và dính timeout 900s làm tê liệt Coordinator. Luôn tra cứu O(1) qua `Get-CimInstance Win32_Process` lấy `--artifact-root`, sau đó đọc trực tiếp `summary.txt` hoặc `log.jsonl`.
