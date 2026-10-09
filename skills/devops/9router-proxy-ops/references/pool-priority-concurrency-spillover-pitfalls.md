# Pitfall: Large Quota Pool Falling Back to Free Tiers (Spillover Bottlenecks)

## Triệu chứng
- Pool tài khoản chính (Gemini / Claude qua Antigravity hoặc Codex) có danh nghĩa hàng chục đến hàng trăm tài khoản, quota dồi dào.
- Nhưng khi gọi model qua combo cha (ví dụ `omni-worker`), request bất ngờ nhảy xuống Tier Free (`muse-spark`, `mimo`, `nemotron`, `big-pickle`).
- Kiểm tra log thấy chỉ 2-3 tài khoản đầu danh sách nhận request, còn lại không hề chạy hoặc ít chạy.

## Nguyên nhân gốc rễ (3 yếu tố kết hợp)

1. **Cơ chế Ordered Priority (Thác đổ):**
   - Các connection trong provider được gán `priority` tăng dần (1, 2, 3...).
   - Router luôn rót request vào các tài khoản có priority cao nhất trước. Chỉ khi các tài khoản này bận hoặc lỗi mới tràn xuống dưới.
   - Khi tài khoản top đầu xử lý xong 1 request, request tiếp theo lại ngay lập tức dồn ngược về chúng thay vì chia đều sang các tài khoản chưa chạy (Round-Robin). Dẫn đến hiện tượng "thắt cổ chai" ở 5-10 tài khoản đầu bảng.

2. **Giới hạn Concurrency (`maxConcurrent`):**
   - Mỗi connection Antigravity thường có `maxConcurrent = 2` để tránh bị upstream rate-limit.
   - Khi các request có context lớn (Tx ~90k - 150k tokens, streaming mất 15-30s), toàn bộ slot concurrency của nhóm tài khoản đầu bị chiếm giữ.

3. **Cấu hình Combo Cha kích hoạt Failover tức thì:**
   - Combo cha (như `omni-worker`) chứa các combo con theo dạng lồng nhau (nested combos) với strategy `priority`.
   - Khi cấu hình:
     ```json
     {
       "failoverBeforeRetry": true,
       "retryDelayMs": 0,
       "maxRetries": 0
     }
     ```
   - Router **không xếp hàng đợi (Queue Admission = 0ms)** khi nhóm tài khoản đầu bận slot concurrency. Thay vì chờ vài giây để nhả slot hoặc quét tiếp xuống các tài khoản priority thấp hơn, router lập tức kích hoạt `failoverBeforeRetry`, trượt qua Tier 1 (Gemini) -> trượt qua Tier 2 (Claude) -> rơi thẳng xuống Tier 3 (Free pool).

## Phân biệt 9Router (:20128) vs OmniRoute (:20129)
- Không nhầm lẫn database của 9Router và OmniRoute:
  - 9Router (`:20128`): Data tại `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite` (thường là instance proxy phụ hoặc đời cũ).
  - OmniRoute (`:20129`): Quản lý toàn bộ 80+ connection Antigravity live qua endpoint `http://127.0.0.1:20129/api/providers` và `http://127.0.0.1:20129/api/combos`.
- Khi debug pool, bắt buộc inspect API trực tiếp trên port đang active (`:20129`) để đếm chính xác số lượng connection active thay vì chỉ đọc nhầm sqlite của 9Router.

## Giải pháp kiến trúc
1. **Ở combo con (`ag-gemini-pool-3`):** Đổi Strategy sang **`round-robin`**, **`least-used`** hoặc **`p2c`** (Power of Two Choices) thay vì ordered priority thuần túy. Điều này giúp 80+ tài khoản xoay vòng đều, không bao giờ bị nghẽn đồng loạt `maxConcurrent: 2`.
2. **Ở combo cha (`omni-worker`):** Tăng `retryDelayMs` (ví dụ 1000 - 2000ms) và cho phép `maxRetries: 2` để request kiên nhẫn xếp hàng đợi slot nhả thay vì spillover tức thì sang Tier Free.
