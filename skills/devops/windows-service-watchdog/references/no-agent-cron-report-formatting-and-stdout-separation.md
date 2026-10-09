# No-Agent Cron Report Formatting & Stdout Cleanliness

## Ngữ cảnh & Nguyên lý hoạt động
Trong kiến trúc Hermes Cron:
- Khi một job được cấu hình `no_agent: true`, scheduler sẽ thực thi trực tiếp script Python hoặc Bash và thu thập toàn bộ nội dung từ `stdout` để gửi nguyên văn qua Telegram (`deliver: telegram:...`).
- Nếu `stdout` rỗng (0 bytes), Hermes coi đây là silent tick (watchdog pattern) và không gửi tin nhắn.
- Nếu script in bất kỳ ký tự nào ra `stdout`, nội dung đó lập tức biến thành tin nhắn Telegram gửi tới người dùng.

## Vấn đề thường gặp ("Report nhìn sida khó hiểu")
Khi lập trình viên dùng `print()` xuyên suốt script để debug tiến trình:
```text
[OMNI-FREE-UPDATER] 1. Fetching OpenRouter catalog...
[OMNI-FREE-UPDATER] Candidate pool size: 25. Testing liveness (max_workers=2, target: 4-5 live models)...
  + LIVE: openrouter/liquid/lfm-2.5-2.6b:free (2.30s)
  + LIVE: openrouter/dots-studio/dots-3-note-preview:free (3.48s)
  + LIVE: openrouter/nex-agi/nex-n2.5-pro:free (6.19s)
  + LIVE: openrouter/nvidia/nemotron-3-super-120b-a12b:free-low (2.01s)
  + LIVE: openrouter/inclusionai/ling-3.0-flash-fin:free (2.44s)
[OMNI-FREE-UPDATER] Updating combo omni-free with 7 tiers...
[OMNI-FREE-UPDATER] SUCCESS: omni-free updated with 7 tiers. Top model: openrouter/nvidia/nemotron-3-super-120b-a12b:free-low
```
Tin nhắn trên khiến user bực mình vì:
1. Trông giống raw terminal debug dump hơn là một báo cáo cho con người đọc.
2. Tên model bị dính các prefix/suffix kỹ thuật (`openrouter/`, `:free`, `:free-low`).
3. Thiếu cấu trúc thị giác (visual hierarchy): không rõ trạng thái tổng quan, không có icon phân cấp.

## Chuẩn giải pháp: Phân luồng Stderr vs Stdout

### 1. Phân luồng Log
- **Toàn bộ log tiến trình, debug, cảnh báo kỹ thuật**: BẮT BUỘC ghi vào `sys.stderr`.
  ```python
  def log_debug(msg: str):
      print(msg, file=sys.stderr, flush=True)
  ```
- **Báo cáo kết quả cuối cùng**: DUY NHẤT một chuỗi định dạng Telegram Markdown hoàn chỉnh in ra `sys.stdout`.

### 2. Tiêu chuẩn Báo cáo Telegram Markdown cho Updater/Pool Cron
Một báo cáo trực quan cần có:
1. **Header & Thước kẻ:** Emoji nổi bật kèm thẻ danh mục và thanh kẻ ngang.
2. **Key Metrics:** Dạng bullet list in đậm nhãn (`• *Trạng thái:* ✅ Thành công`, `• *Quy mô pool:* 7 tiers`).
3. **Clean Entity Names:** Hàm helper làm sạch tên kỹ thuật:
   ```python
   def clean_model_name(mid: str) -> str:
       clean = mid
       for prefix in ("openrouter/", "chatgpt-web/"):
           if clean.lower().startswith(prefix):
               clean = clean[len(prefix):]
               break
       for suffix in (":free-low", ":free"):
           if clean.lower().endswith(suffix):
               clean = clean[:-len(suffix)]
               break
       return clean
   ```
4. **Phân cấp Icon cho Routing / Priority Tiers:**
   - Top 1: 🥇 Gold
   - Top 2: 🥈 Silver
   - Top 3: 🥉 Bronze
   - Các tier tiếp theo: 🔹 Bullet
   - Fallback providers khác (Web Pool): 🌐 Globe

### Mẫu định dạng chuẩn
```markdown
⚡ *[OMNI-FREE] CẬP NHẬT POOL THÀNH CÔNG*
───────────────────────────
• *Trạng thái:* ✅ Hoạt động
• *Tổng tiers:* 7 models (5 OpenRouter + 2 ChatGPT Web)
• *Top Model:* `nemotron-3-super-120b` (⚡ 2.01s)
• *Endpoint:* `omni-free` (:20129)

📋 *Thứ tự ưu tiên (Priority Tiers):*
1. 🥇 `nemotron-3-super-120b` (2.01s)
2. 🥈 `lfm-2.5-2.6b` (2.30s)
3. 🥉 `ling-3.0-flash-fin` (2.44s)
4. 🔹 `dots-3-note-preview` (3.48s)
5. 🔹 `nex-n2.5-pro` (6.19s)
6. 🌐 `GPT-5.6 Luna Free (ChatGPT Web Pool)`
7. 🌐 `GPT-5.6 Sol Instant (ChatGPT Web Pool)`
```

### 3. Cạm bẫy Verification Ping & Timeout
- **Nguyên nhân treo:** Khi ping kiểm tra combo mới cập nhật, nếu không gửi `"max_tokens": 5`, các model lớn hoặc reasoning model (như nemotron 550b, nano-omni-reasoning) sẽ sinh hàng trăm thinking tokens khiến socket timeout (>25s).
- **Nguyên nhân fail ảo:** PATCH combo lên OmniRoute đã trả về 200 OK và các model đã test live trước đó, nhưng vì verification ping bị timeout nên script gọi `report_error()` và in `❌ Thất bại` -> gây hoang mang cho user.
- **Giải pháp:**
  - Luôn thêm `"max_tokens": 5` vào verification ping.
  - Xử lý verification ping dưới dạng non-blocking: nếu ping chậm/timeout, chỉ ghi log cảnh báo vào `stderr` và đính kèm ghi chú nhẹ vào báo cáo, KHÔNG đánh fail toàn bộ kết quả cập nhật đã thành công.
