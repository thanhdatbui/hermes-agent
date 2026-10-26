# Kiến Trúc Bắt Buộc WinRT OCR Primary vs XML Fallback trên Phone Farm

## Bối Cảnh Thực Tế & Lỗ Hổng Tư Duy
Khi tự động hóa các tác vụ đọc thông tin trên Android Phone Farm (Samsung Galaxy S7 Android 7/8, ~80 máy trên Host Windows 10) như đơn hàng TikTok Shop, mã vận đơn (tracking code), thông báo đơn vị vận chuyển, trạng thái tài khoản:
- Các lập trình viên và Agent AI (Hermes, Claude Worker, Codex) thường có "quán tính lập trình" nhảy vào cào cây Accessibility XML (`uiautomator dump` hoặc `atx-agent` port 7912 `dumpWindowHierarchy`).
- **Thực tế thất bại:**
  1. Giao diện đơn hàng (TikTok Shop / Shopee) bản chất là WebView / Lynx / Canvas. Accessibility Service của Android không đọc được text bên trong các container này, trả về node rỗng `text=""` hoặc rỗng toàn bộ cây XML.
  2. Phần cứng Samsung Galaxy S7 (Exynos 8890) rất yếu. Lệnh dump XML gây áp lực CPU lớn, dễ bị Android kernel kill (Exit 137) hoặc delay >10s làm đứt luồng automation.
  3. Trong khi đó, Host PC chạy Windows 10 đã có sẵn **WinRT OCR (`Windows.Media.Ocr`)**, xử lý trên CPU/GPU máy tính cực nhanh (<0.3s), trích xuất 100% tiếng Việt có dấu chuẩn xác từ ảnh chụp màn hình (`screencap`), giải phóng hoàn toàn tải cho điện thoại.

## Quy Tắc Bắt Buộc (INVARIANT UI-OCR-1)
Từ nay về sau, mọi script automation bóc tách dữ liệu UI trên Farm phải tuân thủ nghiêm ngặt các tầng cưỡng chế:

### 1. Cổng Duy Nhất: `automation_core.ui_extract.extract_ui`
Mọi script đọc/bóc tách UI điện thoại BẮT BUỘC gọi qua `automation_core.ui_extract.extract_ui(serial, query, mode=...)`.

### 2. Pre-fallback Hardening Layer (Không đầu hàng sớm)
Thay vì OCR không thấy là vội vã nhảy sang dump XML, `ui_extract` áp dụng 4 lớp gia cố:
- **Dynamic Upscaling (2x-3x) & Chống Tràn SSD:** Tự động resize ảnh bằng thuật toán PIL LANCZOS trước khi nạp vào WinRT OCR để đọc rõ các chuỗi chữ/số nhỏ. Dùng `tempfile.mkstemp` tạo file tạm ngẫu nhiên để an toàn khi chạy song song nhiều tiến trình, và bọc trong khối `try ... finally` gọi `ocr_image.unlink(missing_ok=True)` để dọn dẹp sạch file tạm ngay lập tức, không làm đầy đĩa SSD farm.
- **Chuẩn hóa ký tự tương đồng thị giác (Confusables):** Chuẩn hóa `O -> 0`, `l/I -> 1`, `S -> 5`, `B -> 8` cho các trường chuỗi mã (như tiền tố `SPXVN...`).
- **Fuzzy Matching Đúng Chuẩn:** So khớp Levenshtein distance với tỷ lệ chuẩn hóa:
  $$\text{ratio} = \frac{\text{levenshtein\_distance}(q, t)}{\max(\text{len}(q), \text{len}(t))}$$
  Bắt buộc chia cho độ dài lớn nhất $\max(\text{len}(q), \text{len}(t))$ thay vì chia cho $\text{len}(q)$, tránh trường hợp từ khóa ngắn (e.g. "đăng nhập") bị khớp nhầm vào câu văn OCR rất dài.
- **Audit Logging An Toàn:** Ghi log JSONL vào `D:/Taadaa/logs/ui_extract_audit.jsonl` ghi lại `source` ('winrt_ocr' vs 'xml'), `shot_sha`, và `confidence`. Mọi thao tác ghi log bọc trong `try...except OSError: pass` để lỗi ghi log không bao giờ làm gián đoạn luồng nghiệp vụ chính.

### 3. Phân Loại Màn Hình Fail-Closed (Context-Aware Fallback)
- **Màn hình WebView/Shop/H5/Canvas (`mode='webview'`, `mode='shop'`):** CẤM TUYỆT ĐỐI XML FALLBACK. Nếu cố tình bật `allow_xml_fallback=True`, `extract_ui` lập tức ném lỗi `WebViewXmlFallbackBannedError`. Không dump XML trên webview vì XML rỗng và gây đơ S7.
- **Màn hình Native Form/Settings (`mode='native'`):** Mới được phép fallback sang XML sau khi WinRT OCR đã miss trên cùng ảnh chụp màn hình.

### 4. Hard Gate Linter & Done Gate Chặn Đứng Tự Động (Chống Khóc Lóc & False Reject)
- **Linter `tools/ui_policy_check.py`:**
  - Banned tokens: `['uiautomator dump', 'dumpWindowHierarchy', 'atx-agent', ':7912', 'import uiautomator2', 'from uiautomator2', 'window_dump.xml', 'dump_hierarchy']`.
  - Allowlist: `ui_extract.py` và thư mục `tests/`.
  - **Chống Chặn Oan (Zero False Positive):**
    * Hỗ trợ cờ `--files [FILES ...]`: Cho phép chỉ định danh sách file thuộc phạm vi task hiện tại.
    * Bỏ qua hoàn toàn thư mục rác: `__pycache__`, `.git`, `cache`, `.venv`, `venv`, `.quarantine`, `.tmp`, `.bak`.
    * Chỉ quét file script (`.py`, `.ps1`, `.sh`, `.bat`).
    * `changed_files_from_git()` chỉ lấy file staged (`git diff --cached`) hoặc file modified trong task, KHÔNG quét lan sang file dirty cũ của repo.
- **Done Gate `tools/done_gate.py`:** Tự động gọi `ui_policy_check.py` với tham số `--files` đối soát trước khi cho phép báo DONE. Bất kỳ script nào vi phạm sẽ bị chặn đứng tại gate `[GATE-FAIL]`.
- **Kỷ Luật Cơ Giới Hóa Thay Vì Memory:** Mọi quy tắc code bắt buộc phải cưỡng chế bằng code (Hard Gate / Linter / Gate check), CẤM nhồi nhét quy tắc code vào persistent memory gây nghẽn context và spam memory.

### 5. Cạm Bẫy Màn Hình Đen Khi Thiết Bị Ngủ (Sleep/Dozing Blackout vs Device Disconnect Trap)
Khi chụp ảnh màn hình bằng ADB screencap trên các máy farm (S7) đang ở trạng thái nghỉ (`mWakefulness=Dozing` hoặc `Asleep`), framebuffer của Android trả về ảnh đen hoàn toàn (`extrema ((0, 0), (0, 0), (0, 0))`), dẫn tới WinRT OCR trả về 0 boxes.
- **CẤM:** Không được phán đoán vội vã là máy bị rớt mạng, rút cáp USB hay hỏng hóc phần cứng.
- **BẮT BUỘC:** Kiểm tra `dumpsys power | grep mWakefulness=`. Nếu Dozing/Asleep, máy vẫn kết nối bình thường, chỉ cần gọi lệnh đánh thức (`KEYCODE_WAKEUP` + `82`) dưới `operator_device_lock` trước khi screencap.

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

## 6. Lỗ Hổng Diff-Only Gate & Cạm Bẫy 145 Legacy `get_ui_xml` Gây Treo Offline S7

### Hiện Tượng & Câu Hỏi Người Dùng (2026-10-26)
- **User thắc mắc:** *"Do k xài winrt ocr mà xài adb à?"* và *"T ép đổi qua winrt ocr ở tất cả script r mà ta"*.
- **Gốc rễ kỹ thuật phát hiện:**
  1. **Lỗ hổng Diff-Only Gate (`ui_policy_check.py`)**: Linter và Done Gate sử dụng hàm `find_diff_violations()` chỉ kiểm tra những dòng code mới được thêm/sửa trong `git diff`. Mục đích ban đầu là tránh false reject / gãy build hàng loạt trên các repo cũ, nhưng vô tình tạo ra **điểm mù**: toàn bộ code legacy đồ sộ viết từ tháng 8–9 không bị gate sờ tới.
  2. **145 Điểm Kẹt XML Dump trong `Tiktok_Reg`**: Cụ thể trong `social_reg_v1.py` và `tiktok_login_v1.py` vẫn tồn tại **145 chỗ gọi `get_ui_xml()`** (bên dưới gọi `atx-agent` port 7912 và `uiautomator dump`).
  3. **Hậu Quả Phần Cứng (Exynos 8890 trên Samsung Galaxy S7)**: Khi kịch bản nuôi feed gọi auto-login recovery sang `tiktok_login_v1.py`, tiến trình spam dump XML liên tục ở mỗi bước (mở profile, mở dropdown, bấm thêm tài khoản, gõ email, xác minh...). Phần cứng S7 bị đẩy CPU lên 100%, binder IPC của Android bị cạn kiệt dẫn tới `atx-agent dump attempt 3/3 failed` $\rightarrow$ daemon `adbd` trên điện thoại crash hoặc treo transport $\rightarrow$ thiết bị rớt sang trạng thái `offline` (`ce021602a92d1a0d04 offline`).
- **Kỷ Luật Khắc Phục:**
  * Mọi module login / reg (kể cả code legacy) khi đụng tới phải dọn dẹp sạch `get_ui_xml()`, thay thế bằng **WinRT OCR screencap (`automation_core.ui_extract.extract_ui` hoặc `ocr_screen_boxes`)** chạy trên CPU máy tính.
  * Samsung S7 chỉ nhận lệnh chụp ảnh `screencap` native trong 0.1s và lệnh `input tap` tọa độ, giải phóng 100% CPU cho điện thoại, triệt tiêu vĩnh viễn hiện tượng spam dump XML làm treo `offline` thiết bị.

