# Session Stickiness Semaphore Deadlock & ChatGPT-Web 413 Fallback Trap

## 1. Hiện tượng & Triệu chứng
- **Hiện tượng**: Log OmniRoute (:20129) báo lỗi hàng loạt `429 Semaphore timeout after 30000ms for antigravity:<conn_id> (<email>)` mặc dù pool Pro (16 acc) và pool Free (87 acc) còn rất nhiều tài khoản đang ở trạng thái `active` và không hề bị rate limit / quota exhausted từ upstream Google.
- **Biểu hiện**: Request bị treo đơ đúng 30-31s (`TI: 0 TO: 0`), sau đó liên tục retry vào cùng 1 tài khoản duy nhất đang bị quá tải (concurrency full).
- **Hệ quả dây chuyền**: Khi tầng Gemini nổ 429 sau các lần retry kiệt quệ, combo fallback nhảy xuống tầng tiếp theo (ví dụ ChatGPT-Web pool) và lập tức nổ thêm lỗi `413 Payload Too Large` do payload của session dài vượt ngưỡng web upstream.

## 2. Root Cause Giải Phẫu (Tại sao xảy ra?)
1. **Bẫy `applySessionStickiness` trong `open-sse/services/combo/sessionStickiness.ts`**:
   - Khi `disableSessionStickiness: false`, OmniRoute băm hash chuỗi tin nhắn (`messages`) của conversation.
   - Nếu conversation đó từng gọi thành công vào Account X, hàm `applySessionStickiness` sẽ **LUÔN LUÔN PROMOTE ACCOUNT X LÊN VỊ TRÍ SỐ 0 (ĐẦU DANH SÁCH)** ở mọi turn tiếp theo.
   - **Tử huyệt của logic**: Code stickiness chỉ gỡ cờ pin khi account bị Google trả về `BANNED`, `RATE_LIMITED` hoặc `QUOTA_EXHAUSTED`. **Nó hoàn toàn không kiểm tra xem account đó có đang bị nghẽn Semaphore nội bộ (concurrency full) hay không!**
   - Khi có nhiều subagent/request đồng thời trong cùng conversation hash hoặc traffic dồn vào Account X (`maxConcurrent: 2`), các request đến sau bị kẹt ở Semaphore queue, chờ đủ 30.000ms thì văng `429 Semaphore timeout`.
2. **Bẫy `failoverBeforeRetry: false`**:
   - Combo con (`ag-gemini-pool-3`, `ag-gemini-free-pool`) nếu để `failoverBeforeRetry: false` sẽ ép request phải thử lại (retry 3 lần) vào đúng cái account đang bị kẹt semaphore đó trước khi cho phép combo cha nhảy tầng, biến thời gian treo thành 90s - 120s.
3. **Bẫy tầng ChatGPT-Web trong `omni-worker`**:
   - Khi `chatgpt-web` nằm ở Tier 3 (trước Claude Sonnet hoặc Free Tier), request context lớn khi fallback xuống web sẽ chết ngay lập tức vì lỗi 413 của giao diện Web, chặn đứng cơ hội chạm tới Tier Claude Sonnet dồi dào quota.

## 3. Quy tắc cấu hình khắc phục triệt để
Khi vận hành agent đa luồng hoặc farm nhiều tác vụ đồng thời, BẮT BUỘC cấu hình:

1. **Vô hiệu hoá Conversation Stickiness**:
   - PATCH `http://127.0.0.1:20129/api/settings`:
     `{"disableSessionStickiness": true}`
   - Trên các combo (`omni-worker`, `ag-gemini-pool-3`, `ag-gemini-free-pool`, `ag-claude`):
     `config.disableSessionStickiness = true`
2. **Ép Pure Round-Robin (nhảy acc lập tức)**:
   - Đặt `stickyRoundRobinLimit = 1` trên cả settings và combos để mỗi request tự động xoay ngay lập tức sang account tiếp theo trong pool, phân bổ đều tải trên toàn bộ 16 acc Pro và 87 acc Free.
3. **Bật Failover Trước Khi Retry**:
   - Đặt `config.failoverBeforeRetry = true` để nếu một account chớm bận hoặc lỗi, router chuyển ngay lập tức sang account kế tiếp thay vì đứng chờ retry account cũ.
4. **Hạ ChatGPT-Web xuống đáy cùng**:
   - Trong combo `omni-worker`, sắp xếp thứ tự:
     - Tier 1: `ag-gemini-pool-3` (16 Pro)
     - Tier 2: `ag-gemini-free-pool` (87 Free)
     - Tier 3: `omni-free` (Free pool)
     - Tier 4: `ag-claude` (Sonnet 4.6)
     - Tier 5: `chatgpt-web-pool` (Đáy cùng, tránh nuốt chửng context lớn bằng lỗi 413).
