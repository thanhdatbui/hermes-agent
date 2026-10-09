# Đồng bộ Combo OmniRoute sang Hermes Model Picker

## 1. Bản chất kiến trúc đồng bộ OmniRoute ↔ Hermes

Khi tạo mới hoặc đổi tên Combo trên OmniRoute (`:20129`) để dùng trên Hermes Agent:
1. **OmniRoute Combo API (`:20129`)**:
   - Tạo combo: `POST /api/combos`
   - Đổi tên / update: `PATCH /api/combos/<id>`
   - Chiến lược: `cache-optimized` (cho session stickiness + prompt cache affinity) hoặc `p2c` (cho web pool).
   - Mô hình upstream: vd `codex/gpt-5.6-terra-medium`, `chatgpt-web/gpt-5.6-sol-high`.

2. **Hermes Provider Plugin (`plugins/model-providers/omni/__init__.py`)**:
   - Hermes nạp profile cho provider `omni` qua class `OmniProfile(ProviderProfile)`.
   - `OmniProfile.fetch_models()` chặn live discovery tới `:20129/v1/models` (return `None`) để bảo vệ farm, và ép dùng `fallback_models = FARM_MODELS`.
   - **BẪY CHẾT NGƯỜI**: Chỉ khai báo model trong `config.yaml` (`providers.omni.models` hay `custom_providers`) là KHÔNG ĐỦ. Nếu không thêm tên model vào tuple `FARM_MODELS` trong `plugins/model-providers/omni/__init__.py`, Hermes sẽ hoàn toàn bỏ qua và không bao giờ hiển thị model đó trên `/model` picker!
   - Cần cập nhật ở cả:
     - `C:/Users/Kibe/AppData/Local/hermes/plugins/model-providers/omni/__init__.py`
     - `C:/Users/Kibe/AppData/Local/hermes/hermes-agent/venv/Lib/site-packages/plugins/model-providers/omni/__init__.py`

3. **Disk Cache (`provider_models_cache.json`)**:
   - Hermes lưu cache danh sách model của từng provider tại `C:/Users/Kibe/AppData/Local/hermes/provider_models_cache.json`.
   - Khi cập nhật plugin hoặc config, BẮT BUỘC gọi:
     ```python
     from hermes_cli.models import clear_provider_models_cache, cached_provider_model_ids
     clear_provider_models_cache('omni')
     cached_provider_model_ids('omni', force_refresh=True)
     ```
   - Nếu không xóa cache, Hermes vẫn đọc 5 model cũ từ disk cache và không nạp model mới cho đến khi hết TTL.

4. **Khai báo Aliases trong `config.yaml`**:
   - Bổ sung cả dạng có dấu gạch nối và dấu cách để user gõ tự nhiên:
     ```yaml
     model:
       aliases:
         codex-terra: custom:omni/codex-terra
         codex-luna: custom:omni/codex-luna
         gpt-web-sol: custom:omni/gpt-web-sol
         "codex terra": custom:omni/codex-terra
         "codex luna": custom:omni/codex-luna
         "gpt web sol": custom:omni/gpt-web-sol
         terra: custom:omni/codex-terra
         luna: custom:omni/codex-luna
     ```
   - Trong `agent.reasoning_overrides`: thêm `codex-terra: medium`, `codex-luna: medium`.
   - Tránh dùng `hermes config set` với key có dấu chấm (như `gpt-5.6-terra`) vì parser YAML sẽ tách thành object con `gpt-5: {6-terra: medium}` gây hỏng cấu trúc.

5. **Telegram UI Picker State (Inline Keyboard)**:
   - Khi user gõ `/model`, bot Telegram gửi ra 1 message chứa Inline Keyboard và lưu snapshot danh sách model vào bộ nhớ `_model_picker_state[chat_id]`.
   - Nếu tin nhắn `/model` được sinh ra **trước** khi cache hoàn tất làm mới, tin nhắn đó sẽ giữ nguyên danh sách nút cũ.
   - User bấm `◀ Back` rồi chọn lại provider trong tin nhắn cũ đó VẪN ra danh sách cũ.
   - **Cách xử lý**: Yêu cầu user gõ một lệnh `/model` MỚI hoàn toàn vào khung chat, hoặc gõ trực tiếp lệnh switch dạng `/model <alias>`.
