# Quy Chuẩn Đọc UI Farm: WinRT OCR Primary -> ATX-Agent Fallback & Chốt Chặn Cơ Học Git Hook (18/10/2026)

## 1. Bối cảnh & Bài học thực tế
Trong sự cố sập mẻ 79/80 máy tại Farm Kibe (`tiktok-luot nuoi acc`), commit hồi quy `f4391be` đã đưa lời gọi `ctx.adb.dump_ui()` (vốn gọi UiAutomator dump) vào hàm `_wait_for_profile_loading_spinner`, kết hợp với `except Exception: return False` làm 33 máy văng lỗi spinner ngay giây đầu tiên. Ngoài ra, việc dùng shell dump XML trên Samsung S7 Android 7 gây lỗi `EXIT=137 Killed` và làm đơ `UiAutomationService`.

Operator đã chấn chỉnh triệt để:
1. **Cấm dùng UiAutomator dump trên toàn farm.**
2. **Ưu tiên số 1: WinRT OCR 0-token** cho mọi tác vụ kiểm tra màn hình (chờ loading spinner, banner, username, popup).
3. **Fallback số 2: ATX-Agent port 7912** (`_capture_xml_text`) khi cần cấu trúc phân cấp UI và bounding rect để tap.
4. **Cơ giới hóa bằng Git Hook Gate thay vì Prompt tiêm:** Không dùng file markdown hay memory để dặn dò suông; phải cài đặt kiểm tra cơ học tại `.git/hooks/pre-commit` và `.git/hooks/pre-push` chặn đứng code vi phạm ngay lúc commit. Xóa sạch prompt tiêm thừa khi đã có hook cơ học.
5. **Chọn máy Canary linh hoạt:** Nếu máy đại diện M1 đang bận/lock hợp lệ, lập tức chọn máy rảnh khác trong cùng cụm lỗi (ví dụ M2) để chạy canary, cấm đứng im báo kẹt.

## 2. Kiến Trúc 3 Bậc Đọc UI (UI Inspection Hierarchy)

| Bậc | Công nghệ | Công cụ / Hàm | Tình huống sử dụng | Chi phí & Rủi ro |
|---|---|---|---|---|
| **Bậc 1 (Primary)** | **WinRT OCR** | `media_verify.py`<br>`ocr_boxes.ps1` | Chờ loading spinner tắt, đọc username, kiểm tra banner, popup thông báo | 0.2s trên CPU host, **0 token, 0 đồng**, không chiếm UI thread Android |
| **Bậc 2 (Fallback)** | **ATX-Agent (port 7912)** | `_capture_xml_text()`<br>`capture_required_ui()` | Bóc tách cây UI phân cấp, lấy tọa độ bounds chính xác để tap | HTTP request tới daemon local trên máy điện thoại |
| **Vùng cấm** | **UiAutomator Shell Dump** | `adb shell uiautomator dump`<br>`ctx.adb.dump_ui()` | **CẤM TUYỆT ĐỐI** trên toàn bộ farm | Gây `EXIT=137 Killed`, treo `UiAutomationService`, sập mẻ |

## 3. Chốt Chặn Cơ Học (Git Hook Gate)
Các repo automation trên farm bắt buộc kích hoạt chốt chặn cơ học vật lý:
- `.git/hooks/pre-commit`: Quét diff staged của các file script (`.py`, `.sh`, `.ps1`, `.bat`). Chặn đứng nếu phát hiện các regex cấm:
  `FORBIDDEN_UI_REGEX="(uiautomator dump|adb\.dump_ui|ctx\.adb\.dump_ui|shell.*uiautomator.*dump|am start.*com\.github\.uiautomator)"`
  (loại trừ dòng comment `#`, `//`, `/*`, `*`).
- `.git/hooks/pre-push`: Quét toàn bộ commit diff so với remote upstream (`remote_oid..local_oid`). Chặn push nếu có vi phạm.

## 4. Kỷ Luật Canary & Điều Phối Hiện Trường
1. **Dynamic Canary Machine:** Khi nhận alert batch lỗi diện rộng, nếu máy 1 bị tiến trình hợp lệ khác giữ lock, Coordinator phải lập tức bốc máy rảnh tiếp theo trong cùng cụm lỗi (ví dụ M2) để chạy Canary O(1), tuyệt đối không ngồi chờ hoặc báo kẹt thụ động.
2. **Triệt tiêu khóc lóc & viện cớ Tool Guard:** Khi lệnh wrapper bị guard chặn (ví dụ PowerShell bị deny), phải chủ động đổi sang lệnh trực tiếp (Python) nằm trong allowlist. Không biến lỗi gõ lệnh của bản thân thành "blocker hệ thống" để đùn việc cho người dùng.
3. **Báo cáo thực chất:** Báo cáo đúng bản chất logic đã sửa và bằng chứng OCR trên màn hình thực tế, cấm nói vẹt tham số CLI kỹ thuật (`--recovery-test-swipes 2`).
