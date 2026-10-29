# Telegram Model Picker Cache & Provider Discovery Governance

## 1. Cơ chế State của Inline Keyboard Model Picker trên Telegram
- Khi người dùng gửi lệnh `/model`, adapter khởi tạo `send_model_picker` và lưu snapshot vào `self._model_picker_state[chat_id]`.
- Khi người dùng bấm `Next` / `Prev` / `Back` trên một **tin nhắn cũ đã gửi ra trước đó**, Telegram callback (`mpv:`, `mg:`) đọc dữ liệu từ `picker_state` của tin nhắn đó chứ không tự động render lại danh mục mới trên backend.
- Muốn thấy model hoặc provider vừa cập nhật, bắt buộc người dùng phải gõ một lệnh `/model` **mới tinh** vào chat, hoặc dùng lệnh direct switch: `/model <model-name>` (hoặc `/model <alias>`).

## 2. Nguồn gốc các Provider "rác" trong Menu `/model`
Hàm `list_picker_providers` trong `hermes_cli.model_switch` mặc định thực hiện auto-discovery trên toàn bộ môi trường OS:
- **GitHub Copilot:** Tự phát hiện token qua `gh auth status` / GitHub CLI trên máy.
- **Anthropic:** Tự phát hiện token OAuth của Claude Code trong `~/.claude/.credentials.json`.
- **Google AI Studio:** Tự nạp từ biến môi trường `GEMINI_API_KEY`.
- **OpenCode Go:** Tự nạp từ key còn sót trong `auth.json` (`credential_pool`).
- **cockpit / custom:opencode:** Nằm trong khối `custom_providers` của `config.yaml`.
- **Mixture of Agents (MoA):** Virtual provider mặc định của Hermes tự inject vào đầu danh sách nếu chưa bị tắt.

## 3. Quy chuẩn Dọn dẹp Triệt để (CẤM monkey-patch adapter)
Tuyệt đối không sửa đè (monkey-patch) hàm render trong `plugins/platforms/telegram/adapter.py` vì sẽ bị ghi đè sau mỗi lần restart hoặc đồng bộ source. Cần cấu hình gốc:
1. Khai báo `model_catalog.excluded_providers` trong `config.yaml`:
   ```yaml
   model_catalog:
     excluded_providers:
       - copilot
       - anthropic
       - google
       - opencode-go
       - moa
   ```
2. Tắt virtual provider MoA:
   ```yaml
   moa:
     presets:
       default:
         enabled: false
   ```
3. Xóa các endpoint custom chết khỏi `custom_providers`.
4. Dọn sạch token hết hạn khỏi `auth.json`.
5. Xóa file cache model để làm mới: `from hermes_cli.models import clear_provider_models_cache; clear_provider_models_cache()`.

## 4. An toàn Restart Gateway & Auto-Resume Session
Khi cần restart Gateway ngầm (`delayed_kill_restart.py`):
- Luôn đảm bảo script gọi `auto_resume_startup_hook.py` (`preserve_in_flight_sessions(lookback_minutes=180)`) trước khi kill PID cũ.
- Khi Gateway mới online, Hermes sẽ tự động dispatch auto-continue nối lại các session in-flight mà không làm đứt mạch trao đổi của người dùng.
