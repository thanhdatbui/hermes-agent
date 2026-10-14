# Benny Triage, Device Lock Separation, & Feature Map Protocol (2026-10-15)

## 1. Bối cảnh & Tư duy Tự trị (Benny Bot Pattern)
- Học từ kiến trúc tự trị của **Laurin Tran** (SpaceX AI / Cursor) và bot Benny:
  - Tự nhận diện hiện trường sự cố máy `[MÁY N]`.
  - Tự reproduce / phân loại nguyên nhân O(1) qua telemetry chuẩn.
  - Tự kích hoạt kịch bản cứu hộ tương ứng nếu đủ điều kiện an toàn.
  - Trả về `BLOCKED` kèm exact evidence nếu ngoài khả năng tự phục hồi — cấm chạy vòng lặp mò mẫm.

## 2. Phân tách rạch ròi: Read-Only Triage vs State-Changing Auto-Heal

### A. Read-Only Triage (`benny_farm_triage.py --machine <N>`)
- **Đặc tính:** Hoàn toàn phi xâm lấn (non-invasive), đọc trạng thái tĩnh.
- **An toàn tuyệt đối:** Được phép chạy bất kỳ lúc nào, KHÔNG cần chiếm giữ Device Lock độc quyền.
- **Phạm vi hỗ trợ:** Cả 2 cụm máy:
  - Kibe Local (`1 <= N < 200`): ADB trực tiếp cổng USB host.
  - Admin Remote (`N >= 200`): ADB qua socket TCP `192.168.110.119:5037`.
- **Phân loại chẩn đoán (Verdicts):**
  - `CRASH_LAUNCHER`: Focus rơi vào `com.sec.android.app.launcher/LauncherActivity` -> Đề xuất restart TikTok qua `am start`.
  - `OFFLINE`: `adb get-state` trả về khác `device` -> Đề xuất cứu hộ kết nối Level 1.
  - `FROZEN`: App dính ANR / crash dialog -> Đề xuất soft-reboot Level 2.
  - `POPUP_BLOCKED`: Màn hình bị dialog hoặc captcha chặn -> Đề xuất dismiss qua Feature Map.
  - `OK`: Thiết bị hoạt động bình thường trong ứng dụng mục tiêu.

### B. State-Changing Auto-Heal (`--auto-heal`)
- **Đặc tính:** Thay đổi trạng thái phần cứng/phần mềm (restart app, force-stop, reboot, click tọa độ).
- **INVARIANT BẮT BUỘC:** Mọi hành vi auto-heal can thiệp vào máy thật **BẮT BUỘC** phải bọc qua:
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- python D:/Taadaa/tools/benny_farm_triage.py --machine <N> --auto-heal
  ```
- **Xử lý xung đột Ca Nuôi (Active Reservation Conflict):**
  - Nếu `with_device_lock.py` báo TIMEOUT: Kiểm tra thông tin lock owner trả về.
  - Nếu PID owner vẫn đang sống (ví dụ `run_tiktok.py --mode multi-machine-feed-session reservation`): **CẤM TUYỆT ĐỐI** force-stop hay reboot máy! Máy đang trong ca nuôi active, việc gián đoạn sẽ gây hỏng nick / mất cookie.
  - Chỉ được phép auto-heal khi: máy rảnh (không có lock) HOẶC lock thuộc về tiến trình chết (zombie PID).

## 3. TikTok UI Feature Map (`tiktok_feature_map.json`)
- **Mục tiêu:** Chống đốt ngân sách 15 iterations của Worker subagent khi đi tìm selector/Xpath trên giao diện Android.
- **Vị trí SoT:** `D:/Taadaa/tools/tiktok_feature_map.json` (được trích xuất từ `automation-core/src/automation_core/tiktok/`).
- **Các anchor chuẩn đã được đóng gói O(1):**
  - `profile_root`:
    - Tab Hồ sơ: `//node[@content-desc='Hồ sơ' or @content-desc='Profile']`
    - Switcher trigger: `//node[@content-desc='Chuyển đổi tài khoản']`
    - Sửa hồ sơ: `//node[@text='Sửa hồ sơ' or @text='Edit profile']`
  - `account_switcher`:
    - Thêm tài khoản: `//node[@text='Thêm tài khoản' or @text='Add account']`
    - Danh sách account node: `//node[starts-with(@text, '@') or starts-with(@content-desc, '@')]`
  - `popups_and_dialogs`:
    - Bỏ qua: `//node[@text='Để sau' or @text='Not now' or @text='Later']`
    - Đóng dialog: `//node[@content-desc='Đóng' or @content-desc='Close']`
    - Từ chối quyền: `//node[@text='Không cho phép' or @text='Từ Chối' or @text='Deny']`
    - Captcha slider close: `//node[@resource-id='verify-bar-close']`
- **Kỷ luật Dispatch:** Khi Coordinator giao task liên quan đến UI TikTok cho Worker, BẮT BUỘC đính kèm các selector này trong context để Worker trỏ thẳng, cấm Worker tự biên dịch lại hoặc mò mẫm XML từ đầu.

## 4. Kỷ luật Trung thực & Bằng chứng Thực tế (Anti-Khai Láo)
- Khi User hỏi: *"Test thực tế chưa hay mới code lý thuyết?"*:
- BẮT BUỘC phân định rành mạch 4 tầng bằng chứng:
  1. **Telemetry / Query thật:** Đã bắn lệnh ADB đọc state thật trên máy vật lý (ghi nhận rõ serial, pin, focus thật).
  2. **Offline Mocked Unit Test:** Đã chạy pytest trên fixture/mock độc lập để chứng minh logic code không lỗi cú pháp / regression.
  3. **Dry-Run Simulation:** Đã chạy qua flag `--dry-run` để đối soát tham số trước khi bắn lệnh.
  4. **Live Execution & Visual Evidence:** Đã can thiệp máy thật thành công, có ảnh chụp màn hình `MEDIA:<path>` được soi mắt xác nhận qua vision/OCR.
- **CẤM TUYỆT ĐỐI:** Dùng kết quả của tầng (1), (2), hoặc (3) để kết luận bừa bãi rằng tầng (4) "đã hoàn tất".
