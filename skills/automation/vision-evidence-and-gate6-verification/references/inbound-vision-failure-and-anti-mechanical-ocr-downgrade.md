# Kỷ Luật Cấm Hạ Cấp Sang OCR Cơ Học Khi Aux Vision Crash & Khắc Phục Lỗi aux_accounting

## 1. Sự Cố Thực Tế (Phiên Hỏi Lỗi War3)
- **Hiện tượng**: User gửi ảnh chụp màn hình bị lỗi khi chơi game kèm câu hỏi *"lỗi gì khi chơi war3 v"*. Cổng nạp ảnh Telegram gặp sự cố nội bộ `Error: No module named 'agent.aux_accounting'`.
- **Sai lầm tai hại của Coordinator**:
  - Thay vì kích hoạt ngay kênh Vision LLM độc lập (Multimodal LLM) để xem ảnh, Coordinator lại chạy script Windows Native OCR (`run_winrt_ocr.py`) để trích xuất text thô cho nhanh.
  - WinRT OCR là công cụ quang học cơ học, chỉ đọc được các ký tự to, tương phản cao của trang web bảng tính (TikTok Ledger) nằm ở nền sau, và hoàn toàn mù trước hộp thoại xám `Fatal Error` của Warcraft 3 nổi ở giữa màn hình.
  - Coordinator vội vã kết luận *"ảnh không có lỗi War3, chỉ có dashboard TikTok, bạn gửi nhầm ảnh"*.
  - User lập tức chất vấn: *"cái bảng lỗi hiện lên kìa?"* và *"là sao lại dùng OCR mà đéo dùng não của AI đọc ảnh"*.

---

## 2. Bài Học Kỷ Luật Tối Cao: CẤM DÙNG OCR THAY NÃO AI ĐỌC ẢNH
1. **Bản chất khác biệt**:
   - **OCR cơ học (WinRT OCR / Tesseract)**: Chỉ bóc tách ký tự phẳng, mù hoàn toàn về layout, lớp layer đè nhau (z-index, popup/dialog), màu sắc, icon cảnh báo, và ngữ cảnh hình ảnh.
   - **Não Thị Giác AI (Multimodal LLM / Claude Vision / Gemini Vision)**: Nhận biết toàn diện ngữ cảnh, phân biệt rõ cửa sổ nền vs pop-up nổi phía trước, hiểu được thông điệp lỗi trực quan.
2. **Quy định bất biến**:
   - Tuyệt đối CẤM hạ cấp từ Vision sang text OCR để kết luận nội dung ảnh giao diện người dùng (UI/dialog/error popup).
   - Khi luồng nạp ảnh mặc định bị lỗi/gián đoạn, BẮT BUỘC gọi kênh Vision dự phòng của AI (`claude_worker.py --role reviewer` hoặc API Multimodal) mở mắt đọc ảnh ngay turn đầu tiên.

---

## 3. Khắc Phục Triệt Để 2 Tầng Lỗi `aux_accounting` & Mù Ảnh
Sự cố phát sinh từ sự kết hợp của 2 lỗ hổng đồng thời:

### Tầng 1: Lỗi Cấu Hình Hermes (Ép Fallback Ngầm)
- **Nguyên nhân**: Khi dùng model custom (`ag-gemini-pool-3`), nếu trong config để trống `{}` hoặc thiếu `supports_vision: true`, hàm `_prepare_messages_for_non_vision_model` trong `run_agent.py` sẽ tự coi Gemini là model mù, **tước bỏ hoàn toàn pixel ảnh gốc** và ép nhảy sang hàm phụ trợ `vision_tools.py`.
- **Khắc phục**:
  Trong `config.yaml`, đảm bảo:
  ```yaml
  agent:
    image_input_mode: native
  model:
    supports_vision: true
  providers:
    omni:
      models:
        ag-gemini-pool-3:
          supports_vision: true
  ```

### Tầng 2: Thất Lạc Module Core Trong Git Tree
- **Nguyên nhân**: File `agent/aux_accounting.py` (cùng 22 file core khác) bị vô tình xóa khỏi working tree Git (`D agent/aux_accounting.py`), khiến khi bị ép nhảy vào fallback thì chốt chặn `_validate_llm_response` ném `ModuleNotFoundError`.
- **Khắc phục**:
  1. Khôi phục toàn bộ file core bị xóa từ Git HEAD trong repo hermes-agent:
     ```bash
     git status --porcelain | grep "^ D " | awk '{print $2}' | xargs git checkout HEAD --
     ```
  2. Kiểm chứng import và runtime:
     ```bash
     python -c "import agent.aux_accounting; from agent.auxiliary_client import _validate_llm_response; print('PASS')"
     ```
