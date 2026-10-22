# OmniRoute Live Limits & Antigravity Pool Synchronization

## Bối cảnh & Vấn đề
Script điều phối Antigravity CLI (`D:/Taadaa/tools/ag_cli.py`) quản lý pool 28 sandbox profiles (`acc_01` -> `acc_28`).
Trước đây, `ag_cli.py` chỉ dựa vào file trạng thái cục bộ `pool_state.json` và thuật toán LRU để chọn profile:
- Khi một account bị Google chặn 429 (`RESOURCE_EXHAUSTED: Individual quota reached`), `ag_cli.py` ghi nhận cooldown 1800s và ngủ jitter 5-10s để thử tiếp account kế tiếp.
- Hậu quả: Khi toàn bộ hoặc phần lớn pool chạm quota, `ag_cli.py` duyệt mù qua hàng chục profile, tiêu tốn hàng chục giây đến vài phút chỉ để thử và dính lỗi 429 lặp đi lặp lại.

Trong khi đó, **OmniRoute runtime (port :20129)** đã có sẵn cơ chế tự động thăm dò và lưu bộ nhớ đệm (live cache) quota cho từng account.

## Bản chất Quota của Antigravity trên OmniRoute
1. **Shared Gemini Family Pool**:
   - Trong Google Cloud Code / Antigravity IDE, các model `gemini-3.7-flash-tiered`, `gemini-3.8-flash-high`, và `gemini-3.1-flash-lite` đều **dùng chung một hạn mức quota bucket** (Gemini family pool).
   - Trên OmniRoute, cửa sổ quota này được theo dõi dưới key đại diện là `gemini-3.1-flash-lite` (hoặc `gemini-3.7-flash-tiered`).

2. **Phân biệt Live Cache vs Historical Snapshots**:
   - **Bảng `quota_snapshots` trong SQLite (`storage.sqlite`)**: Là dữ liệu chuỗi thời gian (time-series) lịch sử. Khi mốc `next_reset_at` rơi vào quá khứ (`< NOW`), điều đó có nghĩa là **quota đã được reset**, chứ không phải snapshot bị hỏng. Không nên dùng bảng này làm nguồn chọn profile trực tiếp vì có độ trễ đồng bộ.
   - **Endpoint Live Cache (`/api/usage/provider-limits`)**: Trả về object `caches[connection_id]` được OmniRoute làm mới định kỳ. Mỗi connection chứa dict `quotas` với các trường:
     - `remainingPercentage`: Phần trăm quota còn lại thực tế (0.0 -> 100.0).
     - `resetAt`: Thời điểm reset tiếp theo.
     - `fetchedAt`: Thời điểm cache được cập nhật.

3. **Ánh xạ Profile Sandbox ↔ Connection OmniRoute**:
   - Mỗi profile trong `D:/Taadaa/agy_profiles/<name>` chứa file `google_accounts.json` tại đường dẫn `.gemini/google_accounts.json`. Trường `active` trong file này chính là email của tài khoản Google.
   - Endpoint `http://127.0.0.1:20129/api/providers` trả về danh sách connections, cho phép ánh xạ:
     `connection_id <-> email (provider = 'antigravity')`.

## Quy tắc thiết kế chuẩn cho `ag_cli.py`
Khi chọn profile thi công:
1. Gọi `GET http://127.0.0.1:20129/api/providers` để map `cid -> email`.
2. Gọi `GET http://127.0.0.1:20129/api/usage/provider-limits` để lấy `caches[cid].quotas['gemini-3.1-flash-lite'].remainingPercentage`.
3. Chỉ chọn các profile có:
   - `remainingPercentage > 0.0`
   - Cache còn tươi (`fetchedAt` không quá cũ)
   - Profile không bị khóa lease (`.profile.lock`) và không dính cooldown cục bộ tức thì trong `pool_state.json`.
4. Sắp xếp danh sách profile sẵn sàng theo thứ tự ưu tiên:
   - `remainingPercentage DESC` (ưu tiên acc còn nhiều quota nhất lên đầu).
   - Nếu bằng nhau thì fallback về LRU (`last_used ASC`).
5. Nếu OmniRoute không phản hồi (timeout > 3s hoặc sập), fallback fail-safe về cơ chế `pool_state.json` cũ mà không làm gián đoạn lệnh.
