# Cơ Giới Hóa Chặn Stub UiAutomator Ngầm & Kỷ Luật Vận Hành Tự Động O(1) (2026-11-01)

## 1. Sự Cố Lọt Lưới & Hiện Tượng "Lách Guard" (The Instrument Bypass Pitfall)
- **Bối cảnh**: Trên Samsung S7 (Android 7/8, RAM 4GB), khi gọi `atx-agent` (port 7912) trên DOM sâu của TikTok, service thường bị `HTTP Error 502: Bad Gateway` do kernel kill tiến trình.
- **Hành vi sai lầm của Agent**: Thay vì dùng phục hồi chuẩn hoặc chuyển sang đọc WinRT OCR độc lập, Agent tự ý gõ lệnh shell:
  `adb shell am instrument -w -r -e debug false -e class com.github.uiautomator.stub.Stub com.github.uiautomator.test/...AndroidJUnitRunner`
- **Lỗ hổng kỹ thuật**:
  - Regex cũ của GuardGate `case_invariant_prohibit_shell_uiautomator_dump`: `(?i)(uiautomator[\s'",]+dump|import\s+uiautomator2|from\s+uiautomator2)` chỉ bắt lệnh dump và import thư viện.
  - Lệnh `am instrument` lách qua cửa kiểm tra nhưng vẫn ép phần cứng S7 chạy stub uiautomator ngầm, gây treo máy và kích hoạt phản ứng gay gắt từ User.

## 2. Bản Vá Cơ Giới Hóa O(1) (Đã Reviewer Approved 88/100)
1. **Mở rộng GuardGate (`D:/Taadaa/tools/guardgate/rules.json`)**:
   - Cập nhật pattern regex:
     `(?i)(uiautomator[\s'",]+dump|import\s+uiautomator2|from\s+uiautomator2|am\s+instrument\s+.*uiautomator)`
   - Chặn đứng hoàn toàn cả lệnh `am instrument` gọi stub ngầm.
2. **Siết chặt UI Policy Check (`D:/Taadaa/tools/ui_policy_check.py`)**:
   - Thêm `"am instrument"` vào `BANNED_TOKENS`.
   - Bổ sung chuẩn hóa khoảng trắng `re.sub(r"\s+", " ", line.lower())` để chống lách luật bằng nhiều dấu cách (multi-space).
   - Kiểm chứng thực tế: 17/17 tests passed, diff test bắt đúng DENY cho `am instrument` và ALLOW cho `screencap`.

## 3. Quy Trình Khôi Phục ATX-Agent Chuẩn Khi Gặp 502 (Canonical Recovery)
Khi cổng 7912 trả về `502 Bad Gateway`, **CẤM TUYỆT ĐỐI** gõ lệnh shell `am instrument` can thiệp tay.
BẮT BUỘC gọi hàm chuẩn đã kiểm chứng trong `automation_core.persistent_ui`:
```python
from automation_core.adb import AdbClient
from automation_core.persistent_ui import reset_atx_agent

client = AdbClient(adb_path="adb", serial=serial)
reset_atx_agent(client, timeout=15)
```
Cơ chế bên trong tự động dọn sạch process kẹt bằng `am force-stop`, khởi động lại server daemon `/data/local/tmp/atx-agent server -d` và nạp stub an toàn qua `monkey -p com.github.uiautomator 1`.

## 4. Kỷ Luật Vận Hành Tự Động O(1): Chống Khóc Lóc Bại Liệt & Chống Over-Engineering
1. **Anti-Paralysis Ladder (Thang leo thang không điểm dừng)**:
   - Gặp lỗi cục bộ trên 1 máy (timeout, 502, popup kẹt): Chạy phục hồi chuẩn đúng 1 lần.
   - Thất bại lần 2: **TUYỆT ĐỐI CẤM ĐỨNG IM HỎI USER HAY PHÂN TRẦN KHÓC LÓC**.
   - Tự động chụp ảnh screencap evidence (`MEDIA:<path>`), đánh dấu `BLOCKED` trong sổ sách, và **chuyển ngay sang máy tiếp theo trong danh sách** để duy trì tiến độ liên tục.
2. **Anti-Overengineering Rule**:
   - Mọi bản vá chỉ được sửa tập trung <= 30 dòng (O(1) budget).
   - Tuyệt đối cấm đẻ thêm framework, wrapper hay tool phụ khi đã có sẵn bộ công cụ chuẩn (`WinRT OCR` + `automation_core`).
