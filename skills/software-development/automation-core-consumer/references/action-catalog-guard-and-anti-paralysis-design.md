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

## 3. Kiến trúc Action Catalog Guard 3 Tầng Thực Tế (Triển khai 2026-10-22)

### Tầng 1: Discover (`D:/Taadaa/tools/capabilities.json` + `dispatch_worker.py`)
- Duy trì catalog chuẩn hóa `capabilities.json` map rõ ràng:
  * `switch_tiktok_account` $\to$ `from automation_core.tiktok.account_switcher import open_account_switcher, select_exact_account, verify_selected_account`
  * `device_lock` $\to$ `from automation_core.device_lock import operator_device_lock`
  * `logout_account` $\to$ `do_logout_account.py`
  * `winrt_ocr` $\to$ `from automation_core.ocr import ocr_screen_boxes, norm_text`
- `dispatch_worker.py`: Hàm `match_canonical_capabilities()` tự động match keyword từ prompt (ví dụ: `switch_account`, `switcher`, `chuyen_acc`) và chèn khối `[CANONICAL REUSE MANDATE - DO NOT REINVENT THE WHEEL]` vào đầu prompt trước khi dispatch Worker.

### Tầng 2: Detect (`D:/Taadaa/tools/ui_policy_check.py`)
- Chỉ quét added lines trong `git diff` (hoặc untracked files), không bao giờ phạt code cũ trong repo legacy.
- Quét `signature_patterns` từ `capabilities.json` cho các capability có `severity: "block"`:
  * Bắt các hàm tự chế như `def switch_account(...)`, `def select_account(...)`, `def lock_device(...)`.
- Báo lỗi bắt buộc kèm mẫu import sửa trực tiếp:
  `[REJECTED: REINVENTING_WHEEL] Tự chế lại {title} tại {path}:{line}! Bắt buộc dùng: {canonical_import} (hoặc ghi '# reuse-waiver: <lý do>' nếu là ngoại lệ)`.

### Tầng 3: Decide (Phân mức: Fail-Closed vs Advisory)
- **FAIL-CLOSED (Chặn tuyệt đối):** Chỉ áp dụng cho vùng tài sản nguy hiểm:
  * Logout nick, Account Switcher, Nhập mật khẩu, Device Lock, ADB input text.
- **ADVISORY (Cảnh báo + Cho phép miễn trừ):**
  * Các hàm tiện ích, helper, thử nghiệm. Cho phép qua nếu trong file có comment `# reuse-waiver: <lý do>` (lối thoát khẩn cấp chống tê liệt).
- **FAIL-OPEN KHI GATE LỖI:** Nếu script Gate bị crash, timeout hoặc `capabilities.json` bị thiếu/lỗi parse, Gate ghi stderr warning và cho qua, tuyệt đối không để Gate hỏng làm tê liệt toàn bộ Farm.

## 4. Ranh giới Kỹ thuật Farm UI: WinRT OCR vs XML
- **TikTok Shop / WebView / Chi tiết đơn hàng:** BẮT BUỘC dùng **WinRT OCR Primary** (vì WebView dump XML toàn ra container rỗng, che tọa độ, lag ATX).
- **Native Shell / Account Switcher / Cài đặt:** BẮT BUỘC dùng **Canonical XML (`account_switcher.py`)** vì OCR đọc nhầm font nhỏ của TikTok (`0` vs `O`, `1` vs `l`, mất dấu chấm, lỗi font tiếng Việt).

## 5. Bằng chứng Kiểm thử Xác thực (Test Evidence)
- `tools/tests/test_ui_policy_check.py`: 16/16 passed
- `tools/tests/test_done_gate.py`: 19/19 passed
- `tools/tests/test_dispatch_worker.py`: 15/15 passed
- Toàn bộ suite 50/50 passed 100%.
