# Action Catalog Guard & Anti-Defensive Paralysis Architecture

## 1. Bản chất: Vì sao Gate cú pháp (Denylist Token) không chặn được chế bánh xe?
- **Gate hiện tại chỉ so khớp token:** Chặn chuỗi cụ thể (`uiautomator dump`, `dumpWindowHierarchy`, `atx-agent`, `:7912`). Khi Agent tự viết `def tap_and_ocr()` hoặc vòng lặp tìm nick bằng tọa độ, code không chứa token cấm nên Gate coi là hợp lệ.
- **Thiếu tầng Discovery ở đầu vào:** Khi Coordinator dispatch Worker, Context Pack không chỉ rõ canonical tool cần import. Worker sạch ngữ cảnh thấy thiếu hàm thì hành vi tự nhiên là tự viết lại hàm.
- **Can thiệp sai thời điểm:** `done_gate` kiểm tra ở cuối khi code đã viết xong, buộc Worker sửa đối phó. Khi reject, Gate không cung cấp import mẫu để thay thế.
- **Nguyên lý cốt lõi:** Phòng chống chế bánh xe ở đầu vào (Discovery / Context Pack) rẻ hơn và hiệu quả hơn chặn ở đầu ra (Enforcement).

## 2. Rủi ro Tê Liệt Phòng Vệ (Defensive Paralysis / Luna Syndrome)
Khi siết Gate kiểm soát hành vi, nếu thiết kế sai sẽ gây ra 3 thảm họa:
1. **False Reject (Chặn oan):** Pattern quá rộng, chặn cả script chẩn đoán ad-hoc một lần, benchmark hoặc tính năng mới chưa kịp vào core.
2. **Defensive Paralysis:** Agent bị chặn 2 lần liên tiếp sẽ sợ hãi, đóng băng, phân bua lằng nhằng hoặc xin phép liên tục.
3. **Gaming (Lách luật đối phó):** Agent đổi tên hàm, chia nhỏ code để lách Regex thay vì tái sử dụng module core.

## 3. Kiến trúc Action Catalog Guard 3 Tầng
Để vừa ngăn chặn chế bánh xe, vừa không gây tê liệt hệ thống:

### Tầng 1: Discover (Đầu vào — Tác dụng lớn nhất, KHÔNG BLOCK)
- Duy trì catalog chuẩn hóa `capabilities.yaml` map rõ ràng:
  * `switch_account` $\to$ `from automation_core.tiktok.account_switcher import ...`
  * `ocr_screen` $\to$ `from automation_core.ocr import ocr_screen_boxes`
  * `device_lock` $\to$ `from automation_core.device_lock import operator_device_lock`
- Coordinator khi dispatch Worker BẮT BUỘC nhúng khối `USE THESE CANONICAL IMPORTS` vào Context Pack.

### Tầng 2: Detect (Quét Diff — Chỉ dòng thêm mới)
- Chỉ quét added lines trong `git diff`, không bao giờ phạt code cũ trong repo legacy.
- Báo lỗi bắt buộc kèm mẫu import sửa:
  `[REJECT] Phát hiện tự viết đổi account. DÙNG: from automation_core.tiktok.account_switcher import select_exact_account`.

### Tầng 3: Decide (Phân mức: Fail-Closed vs Advisory)
- **FAIL-CLOSED (Chặn tuyệt đối):** Chỉ áp dụng cho vùng tài sản nguy hiểm:
  * Logout nick, Account Switcher, Nhập mật khẩu, Device Lock, ADB input text.
- **ADVISORY (Cảnh báo + Cho phép miễn trừ):**
  * Các hàm tiện ích, helper, thử nghiệm. Cho phép qua nếu có comment `# reuse-waiver: <capability> — <lý do>`.

## 4. Ranh giới Kỹ thuật Farm UI: WinRT OCR vs XML
- **TikTok Shop / WebView / Chi tiết đơn hàng:** BẮT BUỘC dùng **WinRT OCR Primary** (vì WebView dump XML toàn ra container rỗng, che tọa độ, lag ATX).
- **Native Shell / Account Switcher / Cài đặt:** BẮT BUỘC dùng **Canonical XML (`account_switcher.py`)** vì OCR đọc nhầm font nhỏ của TikTok (`0` vs `O`, `1` vs `l`, mất dấu chấm, lỗi font tiếng Việt).

## 5. Quy tắc Vận hành An toàn
- **Shadow Mode:** Rule kiểm tra mới phải chạy ghi log 1 tuần trước khi chuyển sang chặn thật.
- **Fail-Open khi Gate lỗi:** Nếu script Gate bị crash, timeout hoặc lỗi catalog, hệ thống phải fail-open kèm cảnh báo lớn; tuyệt đối không để Gate hỏng làm tê liệt toàn bộ Farm.
