# Gateway Runtime Desync & Multimodal supports_vision Overrides (2026-11-02)

## 1. Sự Cố Runtime Path Desync (D: vs %LOCALAPPDATA%)
- **Hiện tượng:** Bản vá được thêm vào file `D:/Taadaa/Hermes/gateway/run.py` nhưng khi restart Gateway thì code vá (như Inbound Vision Gate) hoàn toàn không có hiệu lực.
- **Nguyên nhân:** Tiến trình Gateway thực tế chạy từ môi trường cài đặt tại:
  `%LOCALAPPDATA%\hermes\hermes-agent\gateway\run.py`
  Việc chỉ patch trong repo làm việc `D:\Taadaa\Hermes` mà không copy/sync sang `AppData` sẽ khiến Gateway daemon tiếp tục nạp code cũ trong RAM và trên đĩa.
- **Giải pháp dứt điểm (Single Source of Truth qua .pth):**
  Không duy trì 2 bản copy tay song song. Tạo file `hermes_dev.pth` trong `venv\Lib\site-packages`:
  `import sys; sys.path.insert(0, r"D:/Taadaa/Hermes");`
  Kiểm chứng: `gateway.run.__file__` phải trỏ trực tiếp về `D:\Taadaa/Hermes\gateway\run.py`. Bất kỳ sửa đổi nào tại `D:` sẽ được Gateway nạp trực tiếp sau restart.
- **Fail-Closed Inbound Verification Gate:**
  Cấm tin tưởng native vision một cách mù quáng. Bắt buộc kiểm tra receipt mang đúng sha256 của file ảnh trong turn hiện tại trước khi xuất text ra chat, nếu thiếu receipt thì ghi đè câu trả lời thành BLOCK.

## 2. Lỗi Strip Multimodal Images do Thiếu `supports_vision: true`
- **Hiện tượng:** Khi người dùng gửi ảnh qua Telegram, Gateway ném ra lỗi:
  `There was a problem with the request and the image could not be analyzed. Error: No module named 'agent.aux_accounting'`
  và nội dung ảnh không được truyền cho LLM khiến LLM bị mù ảnh và sinh ảo giác dối trá.
- **Nguyên nhân:**
  1. Trong `run_agent.py`, hàm `_prepare_messages_for_non_vision_model()` kiểm tra xem active model có vision hay không.
  2. Đối với model custom (như `ag-gemini-pool-3` qua provider `omni`), nếu file `config.yaml` không khai báo cờ `supports_vision: true`, Hermes tự động coi model là text-only.
  3. Khi bị coi là non-vision, Hermes tự động cắt bỏ (strip) toàn bộ ảnh base64 ra khỏi payload và gọi hàm `vision_analyze_tool` để fallback sinh text.
  4. Hàm fallback này import module cũ đã bị xóa `agent.aux_accounting` ➔ văng lỗi `ModuleNotFoundError`.
- **Giải pháp bắt buộc trong `config.yaml`:**
  - `model.supports_vision: true`
  - `providers.<provider>.models.<model>.supports_vision: true`
  - `agent.image_input_mode: native`
  Đo kiểm bằng: `_lookup_supports_vision(provider, model, cfg) == True` và `decide_image_input_mode == 'native'`.
