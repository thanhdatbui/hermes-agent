# Quy Chuẩn Kiểm Tra UI Farm: WinRT OCR Primary -> ATX-Agent Fallback & Chốt Chặn Cơ Học (18/10/2026)

## 1. Triết Lý Vận Hành 2 Bậc
- **Bậc 1 (Primary - WinRT OCR 0-token):** 
  - Mọi thao tác kiểm tra trạng thái màn hình (chờ loading spinner, HUD biến mất, đọc username profile, xác nhận popup cho phép/chặn) **BẮT BUỘC ƯU TIÊN SỐ 1 DÙNG WinRT OCR NATIVE**.
  - Không dump XML qua Accessibility Service khi chỉ cần kiểm tra sự hiện diện của text hoặc trạng thái tĩnh.
  - Ưu thế: Đọc trực tiếp byte stream ảnh qua CPU host Windows trong 0.2s, 0 token LLM, 0 đồng API, không chiếm dụng và không làm nghẽn UI thread của máy Android yếu (Samsung S7).
  - Công cụ chuẩn: `media_verify.py` hoặc `ocr_boxes.ps1`.
- **Bậc 2 (Secondary Fallback - ATX-Agent port 7912):**
  - Khi cần bóc tách toàn bộ cây phân cấp UI, lấy bounding rect chính xác của nút bấm để tap, hoặc tương tác sâu: **BẮT BUỘC DÙNG ATX-AGENT port 7912** thông qua `_capture_xml_text()` và `capture_required_ui()` của `automation-core`.
- **VÙNG CẤM TUYỆT ĐỐI:**
  - CẤM gọi `adb shell uiautomator dump`.
  - CẤM gọi `ctx.adb.dump_ui()` hoặc các method ảo không tồn tại.

## 2. Cơ Giới Hóa Bằng Git Hook (Fail-Closed) & Xóa Bỏ Prompt Tiêm
- **Bài học cốt lõi:** Luật mềm, prompt dặn dò trong file markdown hoàn toàn vô hiệu trước tình trạng drift của LLM/worker. Khi phát sinh quy tắc cấm, **BẮT BUỘC THIẾT LẬP HOOK CƠ HỌC VẬT LÝ VÀ XÓA BỎ FILE PROMPT TIÊM**.
- **Cấu hình Git Hook tại repo:**
  - `.git/hooks/pre-commit`: Quét diff staged (`git diff --cached`) trên toàn bộ code `.py`, `.sh`, `.ps1`, `.bat`. Chặn đứng ngay khi phát hiện `uiautomator dump`, `adb.dump_ui`, `ctx.adb.dump_ui`.
  - `.git/hooks/pre-push`: Quét diff commit sắp push so với remote (`origin/master..HEAD`) để đảm bảo không có bất kỳ dòng lệnh cấm nào lọt lên farm.
- **Tiêu chuẩn thẩm định:** Mọi giải pháp chốt chặn cơ học phải được đưa qua **Claude CLI Reviewer** (`claude_worker.py --role reviewer`) audit độc lập để xác nhận tính chặt chẽ trước khi áp dụng.
