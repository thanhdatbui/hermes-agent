# Fallback Chain Discipline & OpenCode Multimodal Limitations

## 1. Context & Architecture (2026-09-28)
Khi Hermes Agent được cấu hình model chính là cụm Gemini (`ag-gemini-pool-3`), khi gặp sự cố cạn Quota / 429 Rate Limit trên toàn bộ tài khoản Google Antigravity, hệ thống kích hoạt cơ chế `fallback_providers` trong `config.yaml`.

## 2. Pitfalls & Lessons Learned

### Pitfall 1: Quan niệm sai lầm "OpenCode hoàn toàn Text-Only" vs Bản chất Native Vision qua cờ `-f`
* **Hiểu lầm cũ (2026-09-28):** Tưởng rằng toàn bộ model Free trên OpenCode CLI (như `muse-spark-1.3`) là Text-Only và bị "mù ảnh".
* **Sự thật kỹ thuật được xác minh thực nghiệm (2026-09-29):**
  - **`muse-spark-1.3-contributor-free` NATIVELY hỗ trợ Vision đa phương tiện!**
  - Trong OpenCode CLI, model nhận file ảnh trực tiếp qua cờ **`-f <đường_dẫn_ảnh>`**:
    ```bash
    python D:/Taadaa/tools/oc_farm.py run -f "C:/path/to/screenshot.jpg" -m opencode/muse-spark-1.3-contributor-free "Đọc các thẻ viền đỏ trên ảnh"
    ```
    Model đọc chính xác 100% từng chi tiết UI, text dark mode, số lượng thẻ quota, thanh tiến trình màu sắc.
  - **Nguyên nhân gây lỗi lúc trước:** Nằm ở bộ chuyển đổi `opencode_bridge.py`: Hermes gửi payload OpenAI chứa `image_url` (dạng `data:image/jpeg;base64,...` hoặc `file:///...`), nhưng bridge cũ chỉ bóc text và bỏ rơi khối ảnh, dẫn đến việc CLI không nhận được file ảnh đính kèm.

### Pitfall 2: Giải pháp Native Vision Bridge cho OpenCode (`opencode_bridge.py`)
* Để Muse Spark đọc được ảnh từ Hermes / Telegram mà không cần model OCR trung gian:
  1. Trích xuất `image_url` từ mảng `messages` trong request `/v1/chat/completions`.
  2. Nếu là `data:image/...;base64`: decode ra file tạm (`tempfile.NamedTemporaryFile`).
  3. Nếu là đường dẫn file cục bộ: trích xuất đường dẫn sạch trên disk.
  4. Truyền danh sách file ảnh vào cờ `-f <file_path>` của câu lệnh `oc_farm.py`.
  5. Dọn dẹp file tạm trong khối `finally` sau khi hoàn tất stream.
* Nhờ cơ chế này, `muse-spark-1.3` có thể giải mã và trả lời trôi chảy mọi câu hỏi về screenshot màn hình / UI farm mà không bị phụ thuộc vào quota của Google hay OpenAI.

### 3. Canonical Fallback Chain Specification
Chuỗi Fallback chuẩn mực bắt buộc phải chèn model có Vision gốc (Native Multimodal) dồi dào tài khoản đứng trước OpenCode:

```yaml
fallback_providers:
  - model: cx/gpt-5.6-luna-high
    provider: custom:omni
  - model: muse-spark-1.3
    provider: custom:opencode
```

* **Tier 1 - Codex Luna High (`cx/gpt-5.6-luna-high` qua OmniRoute `:20129`):** Có đầy đủ Vision Encoder, đọc hiểu screenshot giao diện tức thì, có 21 connection tài khoản xoay vòng, không bao giờ bị tình trạng "mù ảnh".
* **Tier 2 - OpenCode (`muse-spark-1.3` qua `:20130`):** Chốt chặn sinh tồn cuối cùng (Survival Net) cho các lệnh text/code cơ bản khi cả Google lẫn OpenAI pool đều sập mạng.
