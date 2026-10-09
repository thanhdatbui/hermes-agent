# OpenCode Native Vision, Hermes Bridge & Direct Fallback Architecture (2026-09-30)

## 1. Đính chính Kiến thức Cũ (2026-09-28 vs 2026-09-30)
- **Sai lầm cũ**: Trước đây cho rằng OpenCode CLI và `muse-spark-1.3` là "Text-only", không có mắt nhìn ảnh và phải cấm gửi ảnh qua OpenCode.
- **Thực tế đã chứng minh (2026-09-30)**:
  1. OpenCode CLI (`opencode run`) **HỖ TRỢ NATIVE MULTIMODAL/VISION** qua tham số `-f <đường_dẫn_ảnh>`. Các model như `muse-spark-1.3`, `mimo-v2.6-flash`, `longcat-2.5-preview`, `nemotron-3.5-lightning` đều giải mã hình ảnh cực tốt.
  2. Lỗi trước đây ("Your image attachment came through empty" hoặc timeout) thực chất do **2 nguyên nhân kỹ thuật**:
     - **Ở tầng Bridge (`opencode_bridge.py`)**: Bridge cũ chỉ lọc text, bỏ qua `image_url` và không kẹp `-f` khi gọi `oc_farm.py`.
     - **Ở tầng Core Hermes (`agent/image_routing.py` & `run_agent.py`)**: Khi model thuộc `custom_providers` không được khai báo `supports_vision: true` trong `config.yaml`, Hermes coi model đó là non-vision và tự động chuyển hướng ảnh sang `auxiliary.vision` (OmniRoute `:20129`). Khi OmniRoute phụ bị chậm/timeout, Hermes nuốt ảnh, thay bằng chuỗi text lỗi và gửi sang model.

## 2. Chuẩn hóa Kỹ thuật Bridge Đọc Ảnh (`opencode_bridge.py`)
Cầu nối HTTP `:20130` (`opencode_bridge.py`) đã được nâng cấp xử lý ảnh toàn diện:
1. **Bắt Image Parts trong messages**:
   - Nếu là Base64 Data URL (`data:image/...`): Tự động giải mã và ghi ra file tạm (`NamedTemporaryFile`), kẹp đường dẫn vào tham số `-f`.
   - Nếu là URI cục bộ (`file:///...`): Bóc tách tiền tố `file:///`, kiểm tra file tồn tại trên đĩa và kẹp `-f`.
2. **Gọi qua Proxy Farm**: Truyền `-f <file>` vào `oc_farm.py run --format json`.
3. **Dọn dẹp trong `finally`**: Xóa toàn bộ file ảnh tạm sau khi request hoàn tất, chống tràn ổ cứng.
4. **Giữ Port 20130 Sống 24/7**: Watchdog định kỳ (`hermes_stale_watchdog.py`) tự động kiểm tra `http://127.0.0.1:20130/health` mỗi 2 phút; nếu bridge chết sẽ tự động hồi sinh ngầm.

## 3. Cấu hình Bắt buộc trong Hermes `config.yaml` (`supports_vision: true`)
Trong `config.yaml`, mọi model Vision thuộc `custom_providers` BẮT BUỘC phải có cờ `supports_vision: true`:
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
      longcat-2.5-preview:
        context_length: 128000
        supports_vision: true
      nemotron-3.5-lightning:
        context_length: 128000
        supports_vision: true
```

## 4. Chuỗi Fallback Trực tiếp theo Chỉ đạo User (User Directive 2026-09-30)
User yêu cầu cài OpenCode (`muse-spark-1.3`) làm fallback trực tiếp ngay sau model chính:
```yaml
fallback_providers:
  - model: muse-spark-1.3
    provider: custom:opencode
  - model: cx/gpt-5.6-luna-high
    provider: custom:omni
```
- Khi `omni-worker` gặp sự cố (timeout, 5xx, rate-limit), Hermes trượt ngay lập tức sang `muse-spark-1.3` (xử lý mượt mà cả Text & Vision trong 3–4 giây).
- Nếu OpenCode bridge gặp sự cố, Hermes tiếp tục trượt sang `cx/gpt-5.6-luna-high` (OmniRoute).

## 5. Tự động Đồng bộ Model OpenCode vào Telegram (`cron_sync_opencode_models_to_hermes.py`)
- Cron job `sync-opencode-models-to-hermes` (schedule `0 */6 * * *`, `no_agent=True`) chạy ngầm mỗi 6 tiếng:
  - Quét `opencode models` lấy danh sách model Free mới nhất.
  - Tự động nạp vào `custom_providers[name=opencode].models`, gán sẵn `supports_vision: true` cho các model thuộc họ Vision.
  - Cập nhật alias vào `model.aliases` để người dùng chuyển model nhanh trên Telegram (`/model muse`, `/model mimo`, `/model nemotron`, `/model longcat`, v.v.).
  - Hoạt động im lặng tuyệt đối, không tiêu tốn token LLM.
