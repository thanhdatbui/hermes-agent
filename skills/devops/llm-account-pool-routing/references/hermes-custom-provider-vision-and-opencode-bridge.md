# Hermes Custom Provider Native Vision & OpenCode Bridge

## Overview
Khi cấu hình các local proxy / CLI adapter (như `opencode_bridge.py` trên cổng `127.0.0.1:20130` hoặc các custom OpenAI-compatible endpoints) làm custom provider trong Hermes, có các đặc thù quan trọng về xử lý hình ảnh (Vision), chuỗi dự phòng (Fallback) và đồng bộ danh mục model.

## 1. Native Vision Routing vs Auxiliary Vision Fallback trong Hermes Core
Hermes quyết định chuyển tiếp ảnh thô (`native`) hay chạy qua bộ mô tả ảnh (`text` qua `auxiliary.vision`) tại `agent.image_routing.decide_image_input_mode`:
- Với các custom provider (như `custom:opencode`), Hermes kiểm tra `_lookup_supports_vision`.
- **Nguyên nhân lỗi rỗng ảnh ("Image attachment came through empty")**:
  Nếu trong `config.yaml` không khai báo `supports_vision: true` cho model thuộc `custom_providers`, hàm `_lookup_supports_vision` trả về `None`. Khi đó nếu `auxiliary.vision` được cấu hình nhưng server phụ (OmniRoute `:20129`) bị timeout, mất kết nối hoặc quá tải, Hermes sẽ nuốt ảnh và thay bằng thông báo lỗi:
  ```text
  [The user attached an image. Here's what it contains:
  There was a problem with the request and the image could not be analyzed. Error: ...]
  ```
  Model chính/fallback khi nhận được đoạn text này sẽ phản hồi rằng không nhận được ảnh.
- **Giải pháp dứt điểm**:
  Bắt buộc khai báo rõ ràng `supports_vision: true` cho từng model có khả năng đọc ảnh trong `config.yaml`:
  ```yaml
  custom_providers:
    - name: opencode
      base_url: http://127.0.0.1:20130/v1
      api_mode: chat_completions
      api_key: opencode-local-key
      discover_models: true
      model: muse-spark-1.3
      models:
        muse-spark-1.3:
          context_length: 128000
          supports_vision: true
        mimo-v2.6-flash:
          context_length: 128000
          supports_vision: true
  ```

## 2. Kỹ thuật Xử lý Ảnh trong OpenCode CLI Bridge (`opencode_bridge.py`)
OpenCode CLI (`opencode run`) hỗ trợ nhận file đính kèm qua cờ `-f <đường_dẫn_file>`.
Để cầu nối HTTP tương thích OpenAI (`/v1/chat/completions`) hoạt động trơn tru với hình ảnh:
1. **Trích xuất Payload Ảnh**:
   - Dạng Base64 URL (`data:image/jpeg;base64,...`): Giải mã base64 và ghi ra file tạm (`tempfile.NamedTemporaryFile(suffix=ext, delete=False)`).
   - Dạng URI Cục bộ (`file:///C:/...`): Chuẩn hóa bỏ tiền tố `file:///` để lấy đường dẫn file thực tế trên đĩa.
2. **Gọi CLI với cờ `-f`**:
   Truyền đường dẫn file ảnh vào tham số `['-f', image_path]` của lệnh thực thi `oc_farm.py run --format json`.
3. **Dọn dẹp File Tạm**:
   Đảm bảo luôn xóa các file ảnh tạm sinh ra trong khối `finally` sau khi kết thúc request để tránh rác ổ cứng.

## 3. Cấu hình Chuỗi Fallback Trực tiếp trong Hermes
Để đưa một model từ custom provider lên làm fallback ưu tiên số 1 ngay sau model chính:
```yaml
fallback_providers:
  - model: muse-spark-1.3
    provider: custom:opencode
  - model: cx/gpt-5.6-luna-high
    provider: custom:omni
```
Kiểm tra chuỗi fallback bằng lệnh: `hermes fallback list`.

## 4. Tự động Đồng bộ Model & Phím tắt Telegram (/model)
Để danh mục model và phím tắt `/model` trên Telegram luôn cập nhật các model Free mới nhất từ upstream mà không tốn token LLM:
- Chạy cron định kỳ (ví dụ mỗi 6 giờ) với `no_agent=True` gọi script O(1): `cron_sync_opencode_models_to_hermes.py`.
- Script đọc kết quả từ `opencode models`, cập nhật danh sách model và tự động gán cờ `supports_vision: true` cho các model thuộc họ Vision (`muse-spark-1.3`, `mimo-v2.6-flash`, `longcat-2.5-preview`, `nemotron-3.5-lightning`).
- Tự động tạo alias ngắn gọn vào `model.aliases` (`/model muse`, `/model mimo`, `/model nemotron`...) để chuyển đổi nhanh trên Telegram.
