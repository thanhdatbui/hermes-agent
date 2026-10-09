# OmniRoute Proxy Fallback & Account Proxy Routing Mechanics

## 1. Cơ chế Provider Pool Fallback khi Proxy của Account Chết (Dead/Timeout)
Khi một tài khoản được gán proxy riêng (`scope='account'`) nhưng proxy đó bị lỗi mạng, timeout hoặc cúp điện:
* Mã nguồn xử lý tại `src/lib/db/settings.ts` (`resolveProxyForConnection` -> Step 3).
* Kiểm tra nhanh TCP reachable qua `isProxyReachable(accountHealthUrl)` trong `< 2s` (cache TTL 30s).
* NẾU proxy account unreachable: OmniRoute **KHÔNG** làm rớt request ngay (kể cả khi `PROXY_FAIL_OPEN=false`), mà sẽ gọi:
  ```typescript
  const providerFallback = await resolveProviderPoolFallbackProxy(connectionProvider, connectionId);
  ```
* Hàm `resolveProviderPoolFallbackProxy` quét toàn bộ proxy đang sống trong pool của provider đó (hoặc proxy registry chung) và thực hiện gán **Deterministic Hash**:
  ```typescript
  const index = hashConnectionId(connectionId) % reachable.length;
  return reachable[index];
  ```
  * `connectionId` là cố định.
  * Khi danh sách proxy sống không đổi, cùng một account sẽ **luôn luôn map vào đúng 1 port proxy fallback duy nhất**, tuyệt đối không bị xoay random lung tung giữa các request.
  * Đây là lý do tại sao dải Mobi cúp điện nhưng các acc Google Pro vẫn đẩy traffic thành công và trả về HTTP 200 (vì chúng đã được tráo sang dải MikroTik cố định tương ứng).

## 2. Phân biệt Quota UI Dashboard vs Traffic Thực Tế
* Các thanh đo Quota trên Dashboard (`/dashboard`) thường chỉ theo dõi các model quota-capped nặng: `claude-opus-4-6-thinking`, `claude-sonnet-4-6`, `gemini-3.1-pro-high`.
* Model `gemini-3.8-flash-tiered` (hoặc các model flash nhẹ) khi chạy sẽ tiêu thụ hàng trăm triệu tokens nhưng **KHÔNG** làm tụt các thanh phần trăm của Opus/Sonnet/Pro-high trên card UI.
* Để kiểm tra traffic và request thật sự của từng account, phải truy vấn API nội bộ:
  * `GET http://192.168.110.123:20129/api/usage/history` -> đọc `byAccount`.
  * `GET http://192.168.110.123:20129/api/providers` -> đọc `lastTested`, `updatedAt`, `tokenExpiresAt`.
* Tuyệt đối không nhìn vào thanh quota UI 100% để kết luận tài khoản không nhận traffic.

## 3. Quy tắc Giao tiếp & Trả lời khi Người Dùng Yêu Cầu Điều Tra
* **CẤM TUYỆT ĐỐI** gọi tool `clarify` để hỏi ý kiến hay hỏi "xử lý thế nào" khi nhiệm vụ điều tra chưa xong hoặc chưa trả lời trực diện câu hỏi của người dùng.
* Khi người dùng hỏi: *"Acc X đang đi qua proxy nào?"* -> **TRẢ LỜI NGAY ĐÍCH DANH IP VÀ PORT PROXY**. Không giải thích vòng vo, không phỏng đoán, không nói lý thuyết cơ chế trước khi đưa ra kết quả cụ thể.
* Phải truy vết dữ liệu thật từ code và socket runtime (`netstat`, `storage.sqlite`, `/api/settings/proxies/assignments`) trước khi đưa ra kết luận.
