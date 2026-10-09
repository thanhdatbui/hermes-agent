# Bẫy Provider Cooldown Cascade & Giải pháp Cấu hình Sạch (Không sửa code)

## 1. Bối cảnh & Hiện tượng
Trong hệ thống OmniRoute (`:20129`), một combo phân tầng (ví dụ `omni-worker`) có cấu trúc:
- **Tier 1 (Chủ lực):** `ag-gemini-pool-3` (hơn 70–80 tài khoản Google Antigravity).
- **Tier 2 (Dự phòng):** `omni-free` (OpenCode/Free).
- **Tier 3 (Cứu hộ cuối):** `ag-claude` (Claude Sonnet qua Antigravity).

Khi chạy thực tế, xảy ra hiện tượng **bỏ rơi sạch hàng chục account Gemini còn quota để nhảy thẳng xuống Tier Free / Claude**, gây chậm trễ và timeout.

## 2. Bản chất Cơ chế Lỗi: Provider Cooldown Cascade
Tại `open-sse/services/combo.ts`:
```typescript
if (
  resilienceSettings.providerCooldown.enabled &&
  Boolean(provider && provider !== "unknown") &&
  isProviderInCooldown(provider, target.connectionId ?? undefined, resilienceSettings)
) {
  log.info("COMBO", `Skipping ${modelStr} — provider ${provider} in global cooldown`);
}
```
Khi 1 account Antigravity gặp lỗi không có `connectionId` (hoặc lỗi cấp provider như 404 No active credentials), router gọi:
```typescript
recordProviderCooldown("antigravity", undefined);
```
Hệ thống phạt toàn bộ provider `"antigravity"` vào bảng phạt cấp toàn cục (`cooldownMap`).
Hậu quả: Toàn bộ 70+ account Gemini tiếp theo đều mang tên provider `"antigravity"` nên bị router **skip sạch sẽ trong 0.001s**, làm request rơi thẳng xuống Tier dưới!

## 3. Lỗi tư duy Coordinator: Xóa tầng cứu hộ (Anti-Pattern)
- **Sai lầm:** Khi thấy Tier dưới (Claude / Free) bị lỗi hoặc ngâm semaphore, Coordinator đề xuất xóa hẳn Tier cứu hộ ra khỏi combo cha hoặc ép dùng trực tiếp combo con `ag-gemini-pool-3`.
- **Phản ứng của User:** *"giải pháp của mày khác gì dùng trực tiếp combo ag gemini đâu"*.
- **Nguyên tắc đúng:** Combo cha sinh ra là để có fallback cứu hộ. Nhiệm vụ của Coordinator là **sửa cơ chế định tuyến để Tier 1 gánh hết tải trước khi cạn**, chứ không phải chặt bỏ phao cứu sinh của hệ thống.

## 4. Giải pháp Chuẩn: Tắt Provider Cooldown bằng Cấu hình (Không sửa code)
OmniRoute vốn có sẵn API quản lý `resilienceSettings`. Đối với các pool đa tài khoản lớn (70-80 accs), cơ chế `providerCooldown` toàn cục là sai lầm và phải tắt qua API:

### Lệnh PATCH tắt Cooldown cấp Provider:
```bash
curl -X PATCH "http://127.0.0.1:20129/api/resilience" \
  -H "Content-Type: application/json" \
  -d '{"providerCooldown": {"enabled": false}}'
```

### Reset bộ nhớ phạt cũ:
```bash
curl -X POST "http://127.0.0.1:20129/api/resilience/reset" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Tại sao ưu tiên Cấu hình hơn Sửa code repo?
1. **Zero-Code:** Giữ nguyên git tree sạch 100%, không bị conflict khi pull/update OmniRoute sau này.
2. **Có hiệu lực ngay lập tức:** Không cần build lại hay restart tiến trình Node.js.
3. **An toàn cho từng tài khoản:** Tắt `providerCooldown` (cấp toàn cụm) KHÔNG làm mất cơ chế bảo vệ của từng account (`connectionCooldown` và `maxConcurrency: 2` vẫn bảo vệ độc lập cho từng account sạch).
