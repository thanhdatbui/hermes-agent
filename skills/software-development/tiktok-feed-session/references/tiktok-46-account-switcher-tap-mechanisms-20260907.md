# TikTok 46.x Account Switcher Tap Failure & Mechanism Analysis (2026-09-07)

## Triệu chứng & Hiện trường
- **Phiên bản TikTok**: 46.2.3 (Máy 78, 79) và 46.8.3 (Máy 46, `com.ss.android.ugc.trill`).
- **Hiện tượng**: Khi mở bottom sheet "Chuyển đổi tài khoản", script tìm thấy tài khoản mục tiêu nhưng tap không kích hoạt đổi tài khoản; checkmark (`Dấu kiểm`) vẫn giữ nguyên ở nick cũ, recaptured screen vẫn ở Profile nick cũ.
- **Resource IDs theo phiên bản**:
  - TikTok 46.2.3: row container `id/l9b`, username text `id/mtx`.
  - TikTok 46.8.3: row container `id/lpw` (gán `content-desc="<username>"` trên container full-width `[0, 1080]`), username text `id/nba` (`bounds=[252, y][542, y+h]`), active checkmark `id/fmc`, sheet container `id/g0z`, sheet title `id/pq2`.
- **Cạm bẫy Selector & Tọa độ**:
  - Khi selector match theo `content-desc`, hệ thống nhắm vào container cha `id/lpw` thay vì text node con `id/nba`.
  - Center của container cha `id/lpw` là `x=540` (rơi vào mép phải text node `x=542` hoặc dead whitespace của row), khiến sự kiện tap bị nuốt. Cần clamp tọa độ $x \approx 200..350$ hoặc resolve trực tiếp node `id/nba`.

## Nguyên nhân gốc (Root Cause)
1. **0ms Touch Event vs Custom UI Listener**:
   Lệnh `adb shell input tap x y` bắn chuỗi sự kiện `ACTION_DOWN` và `ACTION_UP` gần như tức thời (0ms interval). Trên TikTok 46.2.3, component `id/l9b` (hoặc container bottom-sheet Material/Compose mới) có threshold debounce hoặc touch-slop/event listener lọc bỏ các tap không có touch duration tối thiểu (hoặc bị event interceptor nuốt nếu không có motion duration).
2. **Khu vực tương tác**:
   Node `id/l9b` có thể yêu cầu click vào avatar container bên trái ($x \approx 120..150$) thay vì vùng text/giữa row, hoặc cần ATX JSON-RPC `click([x, y])` (đi qua AccessibilityNodeInfo / UiAutomation) để trigger click listener trực tiếp thay vì phụ thuộc vào kernel input driver.

## Các cơ chế cần verify qua Script Reproduce cô lập
Khi gặp tình trạng tap switcher không ăn trên TikTok 46.x:
- **Option A (Avatar tap)**: Tap vào vùng Avatar bên trái của row ($x \approx 120..150, y = \text{row\_center\_y}$).
- **Option B (Slight duration touch)**: Sử dụng `adb shell input swipe {x} {y} {x} {y} 100` (hoặc 150ms) thay vì `input tap` để đảm bảo hệ điều hành ghi nhận touch down/up hợp lệ có thời gian giữ.
- **Option C (ATX JSON-RPC click)**: Gọi endpoint JSON-RPC của `atx-agent` (`/session/{pid}:com.github.uiautomator/jsonrpc/0` method `click` params `[x, y]`), bypass hoàn toàn layer ADB shell input.

## Quy tắc thực thi (Bắt buộc)
1. **CẤM gõ tay ADB bừa bãi ngoài script reproduce**: Mọi thử nghiệm phải nằm trong script Python cô lập có ghi log, kiểm tra XML / screenshot trước và sau tap.
2. **CẤM quét đĩa (`os.walk`, `find`, `grep -rn`)**: Không quét tìm adb hoặc file log trên toàn ổ đĩa tránh timeout 900s. Sử dụng đường dẫn chuẩn `C:\Program Files (x86)\xiaowei\tools\adb.exe`.
