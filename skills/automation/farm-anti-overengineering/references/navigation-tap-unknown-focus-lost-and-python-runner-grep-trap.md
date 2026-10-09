# Navigation Tap Unknown Focus Lost & Python Runner Grep Trap

**Date:** 06/09/2026
**Context:** Taadaa Phone Farm — TikTok Nuôi Acc (`D:/Taadaa/tiktok-luot nuoi acc`)

---

## 1. CẠM BẪY TIMEOUT 900S: `grep -rn ... python_runner`

### Hiện tượng
Khi tìm chuỗi lỗi hoặc tên hàm trong codebase `python_runner`, agent chạy lệnh:
```bash
grep -rn "TikTok focus lost after navigation tap" "D:/Taadaa/tiktok-luot nuoi acc/python_runner"
# hoặc
grep -rn "tap_navigation_target" "D:/Taadaa/tiktok-luot nuoi acc/python_runner"
```
Kết quả: Lệnh bị treo và dính `[Command timed out after 900s]` (15 phút), làm cạn kiệt toàn bộ thời gian và ngân sách tool call của phiên làm việc.

### Nguyên nhân
Thư mục `D:/Taadaa/tiktok-luot nuoi acc/python_runner/` chứa thư mục con `runs/` (và thư mục cha chứa `.ai-runs/`, `runs/`).
Thư mục `runs/` chứa hàng nghìn thư mục con của các phiên chạy thực tế, lưu hàng vạn file logs, jsonl, tracebacks và artifacts. Lệnh `grep -rn` quét đệ quy qua hàng triệu dòng log lịch sử trên ổ đĩa vật lý, dẫn tới treo I/O và timeout 900s.

### Quy tắc bất di bất dịch
1. **CẤM TUYỆT ĐỐI** chạy `grep -rn` đệ quy trên thư mục gốc `python_runner` mà không loại trừ thư mục runs.
2. **Chỉ grep trên file hoặc thư mục code thuần túy:**
   ```bash
   grep -n "<chuỗi>" "D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/"*.py
   grep -n "<chuỗi>" "D:/Taadaa/tiktok-luot nuoi acc/python_runner/core/"*.py
   # hoặc dùng cờ exclude:
   grep -rn --exclude-dir=runs --exclude-dir=__pycache__ "<chuỗi>" "D:/Taadaa/tiktok-luot nuoi acc/python_runner"
   ```

---

## 2. GIẢI MÃ LỖI: `TikTok focus lost after navigation tap: unknown`

### Vị trí code
- **File:** `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/calibrate_screens.py`
- **Hàm:** `tap_navigation_target(ctx: DeviceContext, target: CalibrationTarget, ...)`
- **Dòng:** 1981 – 2187

### Cơ chế gây lỗi (Root Cause)
1. Trong hàm `tap_navigation_target`, sau khi gửi lệnh tap tọa độ điều hướng (ví dụ chuyển giữa tab Home và tab Profile):
   ```python
   post_focus = get_focused_activity(ctx)
   post_package = str(post_focus.get("package") or "")
   post_activity = post_focus.get("activity")
   ```
2. Trên các thiết bị Android cũ (như Samsung Galaxy S7 - Máy 69), ngay sau cú tap chuyển tab, giao diện TikTok chuyển tiếp (transition) khiến lệnh `dumpsys window windows` / `dumpsys activity` của `get_focused_activity` tạm thời không parse được package, trả về chuỗi rỗng `post_package = ""`.
3. Code xử lý:
   ```python
   is_launcher_or_systemui_or_unknown = (
       not post_package
       or post_package in {"com.android.systemui", ...}
       or "launcher" in post_package.lower()
       or "systemui" in post_package.lower()
   )
   ```
   Vì `post_package == ""`, điều kiện `not post_package` thành `True`.
4. Script ngộ nhận thiết bị bị rơi về Launcher/SystemUI, liền tự động gửi phím Back (`input keyevent 4`) rồi gọi `monkey -p <expected_package>`.
5. Thực tế app TikTok vẫn đang mở nguyên vẹn tại màn hình Profile (Hồ sơ), việc bấm phím Back không giúp lấy lại focus mà có thể làm rối trạng thái. Nếu `get_focused_activity` vẫn tiếp tục miss, `recovered_focus` là `False`.
6. Script rơi xuống:
   ```python
   if not recovered_focus:
       reason = f"TikTok focus lost after navigation tap: {post_package or 'unknown'}"
   ```
   Sinh ra lỗi: `"TikTok focus lost after navigation tap: unknown"` và trả về `NavigationResult(False, "fail", ...)`.

### Giải pháp khắc phục chuẩn (Resolution Pattern)
1. **Fallback kiểm tra Resumed Activity / Top Activity:**
   Khi `get_focused_activity` trả về `post_package` rỗng, không vội kết luận `unknown`. Sử dụng `dumpsys activity activities | grep mResumedActivity` hoặc kiểm tra xem process TikTok có đang active không.
2. **Không bấm Back mù quáng khi `post_package` rỗng:**
   Chỉ gửi phím Back khi chắc chắn package hiện tại là `com.android.systemui` hoặc launcher đã xác định được tên package. Khi `post_package` là rỗng (`""`), ưu tiên chờ thêm 1-2s cho UI settle và query lại focus.
3. **XML / UI Hierarchy Confirmation:**
   Trước khi fail với lỗi `TikTok focus lost`, kiểm tra nhanh snapshot XML UI nếu có. Nếu XML UI chứa các element thuộc TikTok (như tab Home, Inbox, Profile hoặc class của TikTok), xác nhận TikTok vẫn đang ở foreground và coi navigation tap là hợp lệ.
