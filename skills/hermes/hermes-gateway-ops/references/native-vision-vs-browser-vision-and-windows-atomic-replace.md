# Native Vision vs Browser Vision & Windows Atomic Replace Resilience (2026-11-03)

## 1. Bẫy Invariant Bắt Gọi Tool Khi Model Đã Có Native Multimodal Vision
- **Hiện tượng:** Model `ag-gemini-pool-3` (Omni) đã cấu hình `supports_vision: true` và `agent.image_input_mode: native`, ảnh được Gateway nạp trực tiếp dạng Base64/pixel vào prompt của Gemini. Tuy nhiên, quy tắc cũ trong `SOUL.md` lại bắt: *"Trước khi đính kèm MEDIA: bắt buộc phải gọi browser_vision mở ảnh ra soi trước"*.
- **Hậu quả:**
  1. Agent dùng `browser_navigate` mở file local `file:///...` rồi gọi `browser_vision` chụp ảnh lại màn hình headless browser.
  2. Tại turn gọi `browser_vision`, LLM thực tế chưa nhận được pixel mà chỉ nhận thông báo text `Image loaded into context`, dẫn tới việc Agent bắt đầu bịa đặt (hallucinate) nội dung ảnh (như bịa ra hình cô gái công sở hay mặt cún cưng).
  3. Làm màu đối phó, lãng phí turns và vi phạm tính trung thực.
- **Giải pháp dứt điểm:**
  - Chuẩn hóa `SOUL.md`: Khi model có Native Vision, LLM đọc trực tiếp từ pixel prompt. CẤM TUYỆT ĐỐI gọi tool `browser_vision` vòng vo để mở ảnh local nhằm đối phó.
  - Gateway bypass Gate: Trong `gateway/run.py`, kiểm tra `_decide_image_input_mode`: nếu `_img_mode == "native"`, tự động bỏ qua chốt chặn Inbound Vision Gate, không bắt buộc tool call.

## 2. Lỗi Windows `atomic_replace` [WinError 5] Access Denied
- **Hiện tượng:** Khi lưu `config.yaml` (`save_config`) hoặc các file qua `atomic_yaml_write` / `atomic_replace` trong `utils.py`, trên Windows thường xuyên xảy ra lỗi:
  `PermissionError: [WinError 5] Access is denied: '...tmp' -> '...config.yaml'`
- **Nguyên nhân:** Trên Windows (NTFS), hàm `os.replace` yêu cầu quyền ghi độc quyền và không thể ghi đè nếu file đích đang được mở bởi bất kỳ tiến trình nào (như watchdog hoặc editor), trả về `winerror == 5`.
- **Giải pháp chuẩn hóa trong `utils.py`:**
  ```python
  try:
      os.replace(tmp_str, real_path)
  except OSError as exc:
      is_windows_access_denied = (
          os.name == "nt"
          and isinstance(exc, PermissionError)
          and getattr(exc, "winerror", None) == 5
      )
      if exc.errno not in (errno.EXDEV, errno.EBUSY) and not is_windows_access_denied:
          raise
      shutil.copyfile(tmp_str, real_path)
      try:
          shutil.copystat(tmp_str, real_path)
      except OSError:
          pass
  ```

## 3. Kỷ luật Giới hạn Phạm vi Phiên (Session Scope Discipline)
- Khi user hỏi các câu hỏi chung như *"Còn gì nữa không"*, *"Tình hình sao rồi"*, Coordinator **BẮT BUỘC chỉ trả lời trong phạm vi công việc của phiên hiện tại**.
- **CẤM TUYỆT ĐỐI:** Tự ý chạy `session_search` lôi các task dở dang từ các session khác (như máy farm khác, đơn hàng, cronjob khác) vào làm loãng phiên và gây khó chịu cho người dùng.
