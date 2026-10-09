# Priority Combo Unrolling & Tier Fallback Mechanics in OmniRoute

## 1. Bản chất Combo Unrolling (DAG Flattening)

Khi client gọi một combo đa tầng (như `omni-worker`), OmniRoute không dispatch từng tầng một cách biệt lập mà giải mã cấu trúc DAG thông qua hàm:
`resolveNestedComboTargets` (trong `open-sse/services/combo/comboStructure.ts`).

- Mọi nút lồng nhau (`kind: "combo-ref"`) được đệ quy bung phẳng thành một danh sách tuyến tính duy nhất `orderedTargets`.
- **Cấu trúc thực tế của `omni-worker`**:
  - **Tier 1 (`ag-gemini-pool-3`)**: 63 targets `antigravity/gemini-3.8-flash-tiered`, mỗi target gán cứng (`hard-bound`) với đúng 1 `connectionId`.
  - **Tier 2 (`ag-claude`)**: 2 targets (Claude Sonnet 4.6 primary + pool gemini fallback).
  - **Tier 3 (`omni-free`)**: ~64 targets (các model miễn phí dự phòng cuối cùng).
- Tổng cộng: **129 target execution keys** được xếp thành mảng tuần tự từ vị trí index `0` đến `128`.

## 2. Strategy `priority`: Duyệt TUẦN TỰ 100%, KHÔNG Ngẫu Nhiên

Khác với các strategy khác trong `applyStrategyOrdering.ts`:
- `random`: Xáo trộn ngẫu nhiên qua Fisher-Yates shuffle.
- `strict-random`: Rút thẻ ngẫu nhiên không hoàn lại (`shuffleDeck`).
- `p2c`: Chọn 2 target ngẫu nhiên rồi lấy target ít tải hơn (Power of Two Choices).
- `weighted`: Bốc target theo tỉ lệ trọng số.

**Strategy `priority` KHÔNG can thiệp xáo trộn mảng**:
- Thứ tự trong `orderedTargets` được bảo toàn nguyên vẹn theo đúng cấu hình JSON của combo.
- Vòng lặp `executeTarget(i)` trong `open-sse/services/combo.ts` chạy từ `i = 0` đến `orderedTargets.length - 1`.
- **Hệ quả**: Hệ thống luôn thử **toàn bộ 63 target của Tier 1 TRƯỚC** khi chạm tới target đầu tiên của Tier 2.

## 3. Hiện tượng "Lướt qua 63 target trong mili-giây" (Pre-dispatch Skip)

Tại sao có trường hợp hệ thống nhảy sang Claude gần như tức thì khiến người dùng lầm tưởng chỉ thử 1-3 acc?

1. **Cơ chế Hard-Bound Isolation (`auth.ts`)**:
   Mỗi step trong `ag-gemini-pool-3` là một target có `connectionId` cố định. Khi chạy step đó, hàm `resolveForcedConnectionForCredentialPool` chỉ định duy nhất connection đó:
   - Nếu connection đó:
     - `isQuotaExhausted`: Quota tuần còn dưới ngưỡng cutoff (<2%).
     - `rateLimitedUntil`: Đang trong thời gian cooldown sau lỗi 429.
     - `isQuotaPolicyBlocked` / `familyLocked` / `modelLocked`.
     - Chạm trần `concurrency cap` (ví dụ đang gánh tối đa luồng song song).
   - Tầng Auth lập tức trả về `null` và ghi log:
     `antigravity | hard-bound connection <id> unavailable; refusing sibling selection`
   - **Luật bất di bất dịch**: OmniRoute **CẤM** tự ý lấy một tài khoản Gemini khác để đắp vào step này (nhằm bảo vệ giới hạn concurrency và tính cô lập tài khoản).
2. **Tốc độ loại bỏ O(1) in-memory**:
   Việc kiểm tra trạng thái của connection diễn ra trong bộ nhớ (in-memory) mất < 1ms mỗi target. Do đó, 63 targets của Tier 1 có thể bị từ chối chỉ trong **30–50 mili-giây**.
3. **Kích hoạt Failover sang Tier kế tiếp**:
   Khi toàn bộ 63 targets của Tier 1 đều không lấy được credential hợp lệ, hệ thống ghi:
   `AUTH No credentials for combo`
   Vòng lặp `executeTarget(i)` lập tức tiến tới index kế tiếp (Target #64 - bắt đầu của Tier 2 `ag-claude`).

## 4. Bẫy Hiểu Lầm Thường Gặp

1. **Bẫy "Chỉ thử 3 acc ngẫu nhiên"**:
   - Người dùng thấy log Telegram hoặc summary báo "27 fallbacks" hoặc thấy vài dòng log trong `call_logs` nên tưởng lầm là chỉ thử vài acc rồi bỏ cuộc.
   - **Thực tế**: Bảng `call_logs` chỉ ghi nhận các request thực sự đã gửi HTTP request ra ngoài (dispatch network). Các target bị từ chối ở tầng auth pre-dispatch **hoàn toàn không tạo row trong `call_logs`**.
2. **Bẫy "Hết sạch Gemini rồi mới nhảy Claude"**:
   - Khi nhảy sang Claude, log có thể vẫn báo: `quota-aware: 19 with quota, skipping 36 exhausted`.
   - Tức là vẫn còn **19 tài khoản Gemini có quota**. Tuy nhiên, tại đúng thời điểm mili-giây đó, cả 19 tài khoản này đều đang ở trạng thái bận (chạm concurrency cap), dính rate-limit tạm thời, hoặc dính family lock ngắn hạn.
   - Sau vài phút (khi request trước hoàn tất hoặc hết cooldown), Tier 1 sẽ tự động nhận request trở lại bình thường.

## 5. Quy Trình Chẩn Đoán Khi Nghi Vấn Nhảy Tier

1. **Kiểm tra mốc thời gian nhảy Tier trong `app.log`**:
   Lọc sự kiện:
   ```bash
   grep -E "(No credentials for combo|Trying model 1/.*claude)" C:/Users/Kibe/.omniroute/logs/application/app.*.log
   ```
2. **Xem lý do các target Tier 1 bị từ chối**:
   Quét 50 dòng log trước thời điểm nhảy để xác định nguyên nhân:
   - `hard-bound connection ... unavailable`: Connection bị khóa hoặc cạn quota.
   - `is at max concurrency cap (N); spilling to next priority target`: Do đầy luồng đồng thời.
   - `provider antigravity in global cooldown`: Do dính lỗi hệ thống cấp provider (ví dụ 403 hàng loạt).
3. **Đối chiếu quota thực tế của pool qua SQLite**:
   ```python
   import sqlite3
   c = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite').cursor()
   c.execute("""
       SELECT connection_id, remaining_percentage, is_exhausted, next_reset_at 
       FROM quota_snapshots 
       WHERE window_key = 'gemini-3.8-flash-tiered' 
       ORDER BY created_at DESC LIMIT 20
   """)
   for r in c.fetchall():
       print(r)
   ```
