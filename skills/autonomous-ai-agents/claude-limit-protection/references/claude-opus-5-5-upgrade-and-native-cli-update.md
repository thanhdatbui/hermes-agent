# Claude Opus 5.5 Upgrade & Claude Code CLI Native Update (24/09/2026)

## 1. Nâng cấp Claude Code CLI lên bản mới nhất
- **Hiện tượng:** Chạy `claude update` báo có bản `2.1.281`, nhưng chạy `winget upgrade Anthropic.ClaudeCode` lại báo `"No available upgrade found"` do kho winget chưa đồng bộ kịp.
- **Giải pháp chính thức:**
  ```bash
  claude install latest
  ```
  Lệnh này tải trực tiếp native binary mới nhất từ CDN của Anthropic về `C:\Users\<user>\.local\bin\claude.exe`.
  Sau đó đồng bộ vào PATH hoặc sao chép đè vào package thư mục winget hiện tại để lệnh `claude` toàn cục nhận đúng bản mới.

## 2. Bản phát hành Claude Opus 5.5 (21/09/2026)
- **Model ID:** `claude-opus-5-5` (hoặc alias `opus` trên CLI v2.1.281+).
- **Đặc tính kỹ thuật cốt lõi:**
  - Context Window: 1,000,000 tokens (1M).
  - Max Output Tokens: 128,000 tokens (128k).
  - Mandatory Deep Reasoning: Luôn bật suy luận sâu (`reasoning.mandatory: true`), hỗ trợ các mức effort: `low`, `medium`, `high`, `xhigh`, `max`.
  - Benchmark: Intelligence Index tăng vọt lên `57.6` (so với `50.8` của Opus 5 cũ).
  - Chi phí Token: Rẻ hơn 20% so với Opus 5 ($4/$20 per MTok), chi phí đọc cache giảm 60% ($0.2 per MTok).
- **Cấu hình Model mặc định cho Claude CLI:**
  Tại file `~/.claude/settings.json`:
  ```json
  {
    "effortLevel": "medium",
    "theme": "dark",
    "switchModelsOnFlag": false,
    "autoUpdatesChannel": "latest",
    "model": "claude-opus-5-5"
  }
  ```
- **Kiểm tra thực tế:**
  ```bash
  claude -p "cho biết model bạn đang dùng và model id" --max-turns 3
  # Output: Mình đang chạy trên Claude Opus 5.5, model ID là claude-opus-5-5.
  ```
