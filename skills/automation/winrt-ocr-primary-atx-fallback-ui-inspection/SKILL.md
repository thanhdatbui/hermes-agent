---
name: winrt-ocr-primary-atx-fallback-ui-inspection
description: "Dùng WinRT OCR trước, ATX-Agent sau. Cấm uiautomator dump."
version: 1.0.0
author: Hermes Coordinator
platforms: [windows]
metadata:
  hermes:
    tags: [winrt, ocr, atx-agent, uiautomator, farm, invariant]
---

# Quy Chuẩn Đọc UI & Xác Minh Màn Hình Farm (WinRT OCR Primary -> ATX-Agent Fallback)

## 1. Triết Lý & Bất Biến Cốt Lõi (Invariants)
- **Tầng 1 (Primary - WinRT OCR Native 0-Token):** Mọi tác vụ kiểm tra trạng thái màn hình (chờ loading spinner, kiểm tra banner, đọc username, nút Follow/Nhắn tin, xem popup lỗi) **BẮT BUỘC ƯU TIÊN SỐ 1 DÙNG WinRT OCR**.
  - Ưu điểm: Đọc trực tiếp byte stream từ screencap, tốn 0.2s, **0 token LLM, 0 đồng API**, không làm nghẽn UI thread của điện thoại và không sợ app lag.
  - Công cụ chuẩn: `media_verify.py` hoặc `ocr_boxes.ps1`.
- **Tầng 2 (Secondary Fallback - ATX-Agent port 7912):** Khi cần đọc toàn bộ cây cấu trúc phân cấp (UI Tree, Bounding Rect chính xác để tap, text ẩn sâu), **BẮT BUỘC DÙNG ATX-AGENT (port 7912)** thông qua `_capture_xml_text()` và `capture_required_ui()` của `automation-core`.
- **CẤM TUYỆT ĐỐI UIAUTOMATOR SHELL DUMP:**
  - CẤM chạy `adb shell uiautomator dump`.
  - CẤM gọi `ctx.adb.dump_ui()` hoặc các hàm ảo tự chế bypass ATX-agent.
  - Trên Samsung S7 Android 7, `uiautomator dump` gây lỗi `EXIT=137 Killed`, treo cứng `UiAutomationService` và làm chết cả dàn máy.

## 2. Bảng Phân Quyền Công Cụ Theo Tình Huống

| Tình huống nghiệp vụ | Cơ chế BẮT BUỘC | Cơ chế Fallback | VÙNG CẤM |
|---|---|---|---|
| Chờ spinner tắt / Loading HUD | WinRT OCR (soi text/marker) | ATX-Agent (`_capture_xml_text`) | `uiautomator dump` |
| Đọc Username / Profile info | WinRT OCR (`media_verify.py`) | ATX-Agent (`_capture_xml_text`) | `uiautomator dump` |
| Tìm nút bấm / Coordinates để tap | ATX-Agent (`_capture_xml_text`) | WinRT OCR (`ocr_boxes.ps1`) | `uiautomator dump` |
| Xác nhận popup cho phép / chặn | WinRT OCR | ATX-Agent (`_capture_xml_text`) | `uiautomator dump` |

## 3. Hook Gate Chặn Vi Phạm
Mọi commit hoặc script tự động hóa:
- Quét và chặn đứng các dòng code chứa chuỗi: `uiautomator dump`, `adb.dump_ui`, `shell(["uiautomator"`.
- Bắt buộc dùng `_capture_xml_text()` hoặc WinRT OCR.
