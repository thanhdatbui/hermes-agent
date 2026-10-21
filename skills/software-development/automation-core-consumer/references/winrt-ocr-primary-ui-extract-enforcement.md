# WinRT OCR Primary UI Extraction & Hard Gate Enforcement

## Bối cảnh & Sự cố Thay đổi Kiến trúc (2026-10-21)
- Trước đây, hệ thống farm quy định dùng `atx-agent` (port 7912 qua HTTP JSONRPC) làm cơ chế Primary để thay thế lệnh `uiautomator dump` bị Android 7 kernel kill (Exit 137).
- **Hạn chế chết người phát hiện ngày 2026-10-21:**
  1. Trên các màn hình thương mại điện tử (TikTok Shop, Shopee, Lazada, WebView/H5/Canvas), cấu trúc XML hoàn toàn rỗng hoặc thiếu node text. Dump XML vừa vô ích vừa làm đơ máy S7.
  2. Bắt chip Exynos già cỗi của S7 duyệt accessibility tree gây quá tải thiết bị.
  3. Consumer script bị bẫy "Anchoring Bias": hễ thấy S7 là tự động dump XML thay vì dùng WinRT OCR.

## Invariant UI-OCR-1: WinRT OCR Là Primary Toàn Farm
1. **Cổng duy nhất (Single Gateway):** Mọi script đọc/bóc tách UI điện thoại BẮT BUỘC gọi qua `automation_core.ui_extract.extract_ui()`.
2. **CẤM TUYỆT ĐỐI dump XML trực tiếp:** Cấm gọi `uiautomator dump`, `dumpWindowHierarchy`, `atx-agent` (:7912), `import uiautomator2`, `window_dump.xml` ở bất kỳ consumer script nào ngoài module `ui_extract.py`.
3. **Màn hình WebView/Shop:** CẤM TUYỆT ĐỐI XML fallback (`mode='webview'`, `mode='shop'`). Nếu cố tình bật `allow_xml_fallback=True`, `extract_ui` lập tức bắn `WebViewXmlFallbackBannedError`. Bắt buộc dùng 100% WinRT OCR kết hợp Layer Hardening.
4. **Màn hình Native form/Settings:** Chỉ được phép fallback sang XML (`mode='native'`) sau khi WinRT OCR đã miss trên cùng ảnh chụp màn hình.

## Pre-fallback Hardening Layer cho OCR
Thay vì đầu hàng sớm để nhảy XML, `automation_core.ui_extract` áp dụng:
1. **Dynamic Upscaling (2x-3x):** Tự động resize ảnh bằng thuật toán PIL LANCZOS trước khi nạp vào WinRT OCR để đọc rõ các chuỗi chữ/số nhỏ (mã vận đơn, serial, OTP).
2. **Ký tự tương đồng thị giác (Confusables):** Chuẩn hóa `O -> 0`, `l/I -> 1`, `S -> 5`, `B -> 8` cho các trường chuỗi mã.
3. **Fuzzy Matching:** So khớp Levenshtein distance <= 2 cho các từ có độ dài >= 4 ký tự.
4. **Audit Logging:** Ghi log JSONL vào `D:/Taadaa/logs/ui_extract_audit.jsonl` ghi lại `source` ('winrt_ocr' vs 'xml'), `shot_sha`, và `confidence`.

## Linter Hard Gate & Done Gate Enforcement
- **Linter `tools/ui_policy_check.py`:** Quét toàn bộ file thay đổi từ git status. Nếu phát hiện bất kỳ token dump XML trực tiếp nào ngoài allowlist (`ui_extract.py` và `tests/`) -> Trả về Exit 1 `[REJECTED]`.
- **Done Gate `tools/done_gate.py`:** Tự động gọi `ui_policy_check.py` đối soát trước khi cho phép báo DONE. Bất kỳ script nào vi phạm sẽ bị chặn đứng tại gate `[GATE-FAIL]`.
