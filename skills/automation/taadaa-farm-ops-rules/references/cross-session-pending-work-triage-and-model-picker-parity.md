# Quy Trình Tra Cứu Hiện Trường Liên Phiên & Đồng Bộ Danh Mục Model Gateway

## 1. Bối Cảnh & Vấn Đề
Khi Operator mở Telegram và hỏi các câu ngắn/thúc giục:
- *"Làm xong session này chưa?"*
- *"Xong chưa?"*
- *"Sao rồi?"*
Nếu Coordinator trả lời chung chung xã giao ("Tôi sẵn sàng, bạn có task gì...") sẽ gây ức chế cho Operator vì Coordinator bị mất liên lạc với tiến độ công việc trước đó.

## 2. Quy Trình 3 Bước Tra Cứu Hiện Trường O(1)
Khi gặp câu hỏi trạng thái mở không kèm context:
1. **Kiểm tra Session DB (`session_search(limit=5)`):**
   - Rà soát 3-5 phiên gần nhất trong vòng vài giờ qua.
   - Xác định rõ: Tác vụ nào vừa diễn ra? Đã trả lời xong hay bị ngắt quãng giữa chừng (`waiting for model response`, `interrupted`, dở lệnh)?
2. **Kiểm tra Git Tree trên các repo trọng điểm:**
   - Chạy kiểm tra nhanh `git -C <repo> status --short` trên `D:/Taadaa/tools`, `D:/Taadaa/Hermes` hoặc các repo liên quan.
   - Phát hiện các file đã sửa nhưng chưa commit/chốt phiên.
3. **Đối soát Runtime & Service:**
   - Kiểm tra cổng dịch vụ liên quan (`:1905` cho Dashboard, `:20129` cho OmniRoute, tiến trình Gateway).
   - Kiểm tra log chạy của test suite gần nhất.
4. **Báo Cáo Trực Diện (Bằng Chứng Thực Tế):**
   - Tóm tắt đúng 2-3 gạch đầu dòng: Đã xong gì? Test/Canary ra sao? Tình trạng git (đã chốt hay dirty)?
   - Tuyệt đối không vòng vo giải thích hay hỏi xin phép thừa thãi.

---

## 3. Khế Ước Nạp Model Mới Vào Danh Mục OmniRoute Telegram (`/model` Picker)
Khi tích hợp một model mới (ví dụ `gemini-web` / Argon 4) để hiển thị trong `/model` picker trên Telegram, hệ thống yêu cầu đồng bộ **3 tầng**:

1. **Tầng OmniRoute Gateway (`:20129`):**
   - Khai báo combo trong cấu hình OmniRoute (`/api/combos`).
   - Kiểm tra endpoint completion trả về `HTTP 200 OK`.
2. **Tầng Config & Plugin Hermes:**
   - `config.yaml`: Khai báo dưới `providers.omni.models`, `custom_providers`, và `model.aliases`.
   - `plugins/model-providers/omni/__init__.py`: Thêm tên model vào tuple `FARM_MODELS`.
3. **Tầng Bộ Nhớ Telegram Gateway:**
   - Tiến trình `gateway run` lưu danh sách model lúc khởi động. Nếu không khởi động lại Gateway, UI inline button `/model` trên Telegram vẫn hiển thị số lượng cũ (ví dụ `9-11 of 11`).
   - Khởi động lại Gateway qua lệnh an toàn hoặc watchdog để nạp mới `list_authenticated_providers()`.
