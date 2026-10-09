# Bài Học Sự Cố Máy 72: Bẫy Điều Tra Lan Man Vượt Quá 1h Device Lock Làm Mất Hiện Trường Cho Cron Batch Giành Máy (07/09/2026)

## 1. Bối cảnh & Hiện trường sự cố

- **Thời điểm nhận alert:** 09:01 sáng.
- **Alert:** `🚨 [FARM ALERT: MÁY 72] DỪNG PHIÊN`.
  - Quy trình: Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`).
  - Máy: 72 | Serial: `ce12160cd19f847f0c` | Nick: `m.ngc4624`.
  - Triệu chứng: `adb command timed out: ('.../adb.exe', '-s', 'ce12160cd19f847f0c', 'shell', '<redacted>', '-p', 'com.ss.android.ugc.trill', '-c', 'android.intent.category.LAUNCHER', '1')`.
  - Hiện trường: TikTok thực tế đã và đang mở sẵn tại Home Feed (Đề xuất).

## 2. Diễn biến sai lầm & Phản ứng của User

1. **Sai lầm ở Turn 1 (Dispatch mù / Điều tra mở):**
   - Alert đã chỉ rõ ràng lệnh gây lỗi: `monkey` launch bị ADB timeout (`<redacted>` che chữ `key` trong `monkey`). Hiện trường TikTok đã mở sẵn.
   - Tuy nhiên, Coordinator lại dispatch worker với goal điều tra chung chung: *"phân tích root cause từ latest summary.txt -> bọc timeout/exception -> test -> canary"*.
2. **Hậu quả Runaway / Analysis Paralysis:**
   - Worker subagent đầu tiên sa vào bẫy đọc phân tích codebase, truy vết cây gọi từ `device_prepare.py`, `actions.py`, `feed_swipe_smoke.py`, `calibrate_screens.py`...
   - Worker chạy hết 35 lượt gọi và ngốn tới **5.125 giây (85 phút!)** từ 09:04 đến 10:29 mà **CHƯA HỀ GHI ĐĨA MỘT DÒNG CODE NÀO**, chỉ trả về một bản báo cáo phân tích lý thuyết!
3. **Sập bẫy Device Lock TTL (1 giờ / 3600s):**
   - Theo cơ chế Fast-Fail của farm, máy lỗi chỉ được giữ device lock tối đa 1 giờ (`FAST_FAIL_LOCK_HOURS = 1`) để phục vụ inspect.
   - Vì worker ngâm tới 85 phút (> 60 phút), file lock của Máy 72 tự động hết hạn (stale lease).
   - Cron batch định kỳ lúc 10:32 (`multi-machine-feed-session` chạy 80 máy) thấy Máy 72 không còn lock hợp lệ liền nhảy vào giành quyền điều khiển (`PID 184892`).
4. **Phản ứng gay gắt từ User:**
   - *"Tính ra tao gửi từ 9h01 mày over engineer tới tận 10h30 r bảo máy khác chiếm (vì lock giữ đc có 1h) Con cụ mày"*.
   - Đây là sự ức chế hoàn toàn chính đáng do thói quen phân tích lan man, không tôn trọng ngân sách thời gian và cơ chế lease vật lý của hệ thống.

## 3. Khắc phục thực tế & Kết quả

1. **Turn 2 (Cưỡng chế Patch Contract chuẩn xác):**
   - Coordinator lập tức khóa scope: chỉ định đích danh file `python_runner/flows/device_prepare.py`, 2 hàm `force_stop_and_relaunch_tiktok` và `_relaunch`.
   - Áp Patch Contract bọc `try / except Exception` quanh lệnh `monkey`, fallback gọi `get_focused_activity`: nếu package đã là `com.ss.android.ugc.trill` thì trả về `exit_code=0` (`AdbResult.ok=True`).
   - Worker thứ hai hoàn thành toàn bộ việc ghi đĩa và py_compile chỉ trong **6,5 phút (397 giây)**!
2. **Canary & Chốt phiên:**
   - Ngay khi cron batch nhả lock, Coordinator chạy Live Canary trên Máy 72: hoàn thành đủ 2/2 recovery swipes (`final_status: success`, exit code 0).
   - Ghi nhận Case 141 vào `docs/farm-automation-cases.md`.
   - Gate 1 Plan-Review qua OmniRoute model `ag-claude`: `VERDICT: APPROVED`.
   - Push commit `e07ae1f` lên remote `origin/master`.

---

## 4. Kỷ Luật Rút Ra & Quy Tắc Bắt Buộc Cho Tương Lai

1. **Quy Tắc Vàng: KHÔNG BAO GIỜ VƯỢT QUÁ 15 PHÚT KHI XỬ LÝ ALERT:**
   - Fast-fail device lock có TTL cứng là 1 giờ (3600s). Mọi sự chậm trễ quá 30 phút đều đối mặt với nguy cơ bị cron batch cướp máy, mất hiện trường và gãy quy trình phục hồi.
   - Mục tiêu thời gian cho toàn bộ quy trình xử lý Alert (từ lúc nhận đến khi canary xong): **<= 12 - 15 phút**.
2. **CẤM DISPATCH ĐIỀU TRA MỞ KHI TRIỆU CHỨNG ĐÃ RÕ RÀNG:**
   - Khi alert đã có ảnh màn hình hoặc log traceback chỉ rõ lệnh ADB/hàm lỗi: CẤM TUYỆT ĐỐI dispatch worker với mục tiêu "tìm nguyên nhân", "khảo sát codebase".
   - BẮT BUỘC Coordinator phải soạn ngay **Patch Contract** (file, hàm, logic try/catch/fallback, verify command) và dispatch worker thực thi ghi đĩa ngay turn đầu tiên.
3. **CƠ CHẾ TIMEOUT CHO WORKER SUBAGENT:**
   - Nếu worker chạy quá 10 phút mà chưa ghi đĩa, đó là dấu hiệu chắc chắn của Analysis Paralysis.
   - Worker fix alert chỉ được cấp ngân sách: `max_iterations <= 12`, hoàn tất dưới 10 phút.
