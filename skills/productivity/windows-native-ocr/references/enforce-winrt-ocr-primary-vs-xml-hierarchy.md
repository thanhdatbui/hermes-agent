# Kiến Trúc Bắt Buộc WinRT OCR Primary vs XML Fallback trên Phone Farm

## Bối Cảnh Thực Tế & Lỗ Hổng Tư Duy
Khi tự động hóa các tác vụ đọc thông tin trên Android Phone Farm (Samsung Galaxy S7 Android 7/8, ~80 máy trên Host Windows 10) như đơn hàng TikTok Shop, mã vận đơn (tracking code), thông báo đơn vị vận chuyển, trạng thái tài khoản:
- Các lập trình viên và Agent AI (Hermes, Claude Worker, Codex) thường có "quán tính lập trình" nhảy vào cào cây Accessibility XML (`uiautomator dump` hoặc `atx-agent` port 7912 `dumpWindowHierarchy`).
- **Thực tế thất bại:**
  1. Giao diện đơn hàng (TikTok Shop / Shopee) bản chất là WebView / Lynx / Canvas. Accessibility Service của Android không đọc được text bên trong các container này, trả về node rỗng `text=""` hoặc rỗng toàn bộ cây XML.
  2. Phần cứng Samsung Galaxy S7 (Exynos 8890) rất yếu. Lệnh dump XML gây áp lực CPU lớn, dễ bị Android kernel kill (Exit 137) hoặc delay >10s làm đứt luồng automation.
  3. Trong khi đó, Host PC chạy Windows 10 đã có sẵn **WinRT OCR (`Windows.Media.Ocr`)**, xử lý trên CPU/GPU máy tính cực nhanh (<0.3s), trích xuất 100% tiếng Việt có dấu chuẩn xác từ ảnh chụp màn hình (`screencap`), giải phóng hoàn toàn tải cho điện thoại.

## Quy Tắc Bắt Buộc (INVARIANT UI-OCR-1)
Từ nay về sau, mọi script automation bóc tách dữ liệu UI trên Farm phải tuân thủ nghiêm ngặt 3 tầng cưỡng chế:

### 1. Cổng Duy Nhất: `automation_core.ui_extract.extract_ui`
Mọi script đọc/bóc tách UI điện thoại BẮT BUỘC gọi qua `automation_core.ui_extract.extract_ui(serial, query, mode=...)`.

### 2. Pre-fallback Hardening Layer (Không đầu hàng sớm)
Thay vì OCR không thấy là vội vã nhảy sang dump XML, `ui_extract` áp dụng 4 lớp gia cố:
- **Dynamic Upscaling (2x-3x):** Tự động resize ảnh bằng thuật toán PIL LANCZOS trước khi nạp vào WinRT OCR để đọc rõ các chuỗi chữ/số nhỏ (mã vận đơn, serial, OTP).
- **Chuẩn hóa ký tự tương đồng thị giác (Confusables):** Chuẩn hóa `O -> 0`, `l/I -> 1`, `S -> 5`, `B -> 8` cho các trường chuỗi mã (như tiền tố `SPXVN...`).
- **Fuzzy Matching:** So khớp Levenshtein distance <= 2 cho các từ có độ dài >= 4 ký tự.
- **Audit Logging:** Ghi log JSONL vào `D:/Taadaa/logs/ui_extract_audit.jsonl` ghi lại `source` ('winrt_ocr' vs 'xml'), `shot_sha`, và `confidence`.

### 3. Phân Loại Màn Hình Fail-Closed (Context-Aware Fallback)
- **Màn hình WebView/Shop/H5/Canvas (`mode='webview'`, `mode='shop'`):** CẤM TUYỆT ĐỐI XML FALLBACK. Nếu cố tình bật `allow_xml_fallback=True`, `extract_ui` lập tức ném lỗi `WebViewXmlFallbackBannedError`. Không dump XML trên webview vì XML rỗng và gây đơ S7.
- **Màn hình Native Form/Settings (`mode='native'`):** Mới được phép fallback sang XML sau khi WinRT OCR đã miss trên cùng ảnh chụp màn hình.

### 4. Hard Gate Linter & Done Gate Chặn Đứng Tự Động
- **Linter `tools/ui_policy_check.py`:** Quét toàn bộ file thay đổi từ git status. Banned tokens gồm:
  `['uiautomator dump', 'dumpWindowHierarchy', 'atx-agent', ':7912', 'import uiautomator2', 'from uiautomator2', 'window_dump.xml', 'dump_hierarchy']`.
  Allowlist duy nhất: `ui_extract.py` và thư mục `tests/`. Phát hiện vi phạm -> Trả về Exit 1 `[REJECTED]`.
- **Done Gate `tools/done_gate.py`:** Tự động gọi `ui_policy_check.py` đối soát trước khi cho phép báo DONE. Bất kỳ script nào vi phạm sẽ bị chặn đứng tại gate `[GATE-FAIL]`.

## Mẫu Triển Khai Chuẩn (Canonical Usage)

```python
from automation_core.ui_extract import extract_ui, UIHit, UIExtractError

# 1. Đọc màn hình TikTok Shop / Đơn hàng (Cấm XML fallback)
hit = extract_ui(
    serial="ce06160685310f1c04",
    query="SPXVN",
    mode="shop",
    screenshot_path="D:/OneDrive/TaadaaData/kibe/orders/images/order.jpg",
    allow_xml_fallback=False,  # Bắt buộc False trên WebView/Shop
    upscale=2,
    lang="vi-VN"
)
print("Hit source:", hit.source)        # 'winrt_ocr' hoặc 'ocr_fuzzy'
print("Found text:", hit.text)
print("Center bounds:", hit.center)

# 2. Đọc màn hình Native Settings / Form Android (Được phép XML fallback khi OCR miss)
hit_native = extract_ui(
    serial="ce06160685310f1c04",
    query="Cài đặt bổ sung",
    mode="native",
    screenshot_path="D:/Taadaa/screencap.png",
    allow_xml_fallback=True,
    xml_provider=lambda s: get_native_xml_boxes(s)
)
```
