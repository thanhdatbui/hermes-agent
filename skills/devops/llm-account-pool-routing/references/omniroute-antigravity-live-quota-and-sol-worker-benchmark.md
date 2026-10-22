# OmniRoute Live Quota Retrieval & Antigravity Pool Routing

## 1. Kiến trúc Quota Live OmniRoute (:20129) cho Antigravity

### 1.1 Khác biệt giữa SQLite Quota Snapshots vs Live Quota API
- **Bảng `quota_snapshots` (SQLite `storage.sqlite`):** Là chuỗi dữ liệu lịch sử time-series. Rất nhiều snapshot có `next_reset_at < now` mang tính chất lưu vết, nếu đọc trực tiếp để check status thì sẽ nhầm lẫn trạng thái đã reset với trạng thái đang cạn.
- **Endpoint Live `/api/usage/provider-limits`:** Là cache thời gian thực được OmniRoute cập nhật định kỳ từ Google Cloud Code (`retrieveUserQuota` / `fetchAvailableModels`). Đây là nguồn sự thật duy nhất (Single Source of Truth) để kiểm tra quota live của từng connection.

### 1.2 Family Pool Mapping của Google Antigravity
- Toàn bộ các model Gemini Flash (`gemini-3.1-flash-lite`, `gemini-3.7-flash-tiered`, `gemini-3.8-flash-high`, `gemini-3.8-flash-medium`, `gemini-3.8-flash-low`) **dùng chung một quota bucket** (Gemini family pool).
- Trong payload của `/api/usage/provider-limits`, quota của family này được lưu dưới key `"gemini-3.1-flash-lite"`.
- Cấu trúc dữ liệu:
  ```json
  "gemini-3.1-flash-lite": {
      "used": 275,
      "total": 1000,
      "resetAt": "2026-10-22T18:49:06.000Z",
      "remainingPercentage": 72.53,
      "is_exhausted": false
  }
  ```

### 1.3 Mapping Account giữa Sandbox và OmniRoute
- File cấu hình Google trong sandbox Antigravity (`D:/Taadaa/agy_profiles/<profile>/.gemini/google_accounts.json`) lưu email tài khoản đang active tại key `"active"`.
- Gọi `GET http://127.0.0.1:20129/api/providers` để lấy danh sách connections, map `connection_id` $\leftrightarrow$ `email`.
- Từ `connection_id`, tra cứu vào `caches[connection_id]["quotas"]["gemini-3.1-flash-lite"]` để lấy `remainingPercentage`.

### 1.4 Quy tắc lựa chọn Profile trong `ag_cli.py`
1. Lọc bỏ hoàn toàn các profile có `remainingPercentage <= 0.0` hoặc `is_exhausted = True`.
2. Sắp xếp danh sách `ready_profiles` ưu tiên theo: `(-remainingPercentage, last_used, calls)`. Profile còn nhiều quota nhất luôn được gắp chạy trước, triệt tiêu 100% tình trạng duyệt mù dính 429 và delay jitter.

---

## 2. Năng lực & Cấu hình Sol Worker (`gpt-web-sol` qua :20129)

### 2.1 Benchmark đối đầu Phone Farm (Sol vs Gemini Flash)
Trong bài test thực tế theo `benchmark_sol_spec.md`:
- **Test 1 (TikTok UI Drift Surgery):** Sol đạt 19.5/20 (vượt Gemini 17/20) nhờ nhận diện đúng `resource-id` rỗng và chỉ sửa 6 dòng logic text.
- **Test 2 (Device Lock Race Condition Surgery):** Sol đạt 24/25 (vượt Gemini 18/25 và Luna 22/25) nhờ bắt đúng bệnh Lost Update, thiết kế mutex `fcntl.flock` bọc toàn bộ chu trình `read -> mutate -> write` và cảnh báo ranh giới đa host.

### 2.2 Quy tắc vận hành Sol Worker
- **Timeout per-turn:** 300s là hoàn toàn an toàn (thực tế OmniRoute trả về trong 15–25s).
- **Max turns:** Bắt buộc đặt `max_turns >= 8` (khuyên dùng 10). Nếu đặt $\le 6$ turns, Sol sẽ cạn turns ở các bước đọc/kiểm tra trước khi kịp phát lệnh `ACTION: DONE`.
- **Cung cấp exact contract:** Sol dễ bị ảo giác endpoint/port nếu để tự đoán (tự bịa port 20128 hoặc endpoint 404). Coordinator bắt buộc phải cấp sẵn URL, port thật (`20129`) và schema chính xác trong prompt.
