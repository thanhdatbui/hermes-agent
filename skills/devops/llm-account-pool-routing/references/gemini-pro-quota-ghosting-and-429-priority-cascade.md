# Gemini Pro Quota Ghosting & 429 Priority Cascade Diagnosis

## Bối cảnh & Hiện tượng
- User thấy Dashboard hiển thị tổng số accounts còn Pro/Active, nhưng trong Request Logs lại đỏ rực lỗi `429 Too Many Requests` và request bị treo ~31-33 giây.
- Nghi vấn: "Tại sao còn quota acc Gemini Pro mà lại lỗi hết ở log?"

## Nguyên nhân thực tế (Root Cause)
1. **Rolling Window Exhaustion vs Account Health:**
   - Account vẫn ở trạng thái `isActive: true`, `status: active` trong database (`/api/providers`).
   - Tuy nhiên, quota rolling window (RPM/TPM/Hourly bucket) của model cụ thể (`gemini-3.8-flash-tiered`) trên các acc Pro này đã cạn sạch (`0% left`, có timer đếm ngược `in 32m`, `in 55m`).
2. **Priority Cascade Latency Trap:**
   - OmniRoute ưu tiên định tuyến vào các acc Pro có Priority cao nhất (Priority 1 -> 16).
   - Khi các acc top priority bị cạn quota rolling, OmniRoute vẫn gửi request lên Google Upstream.
   - Google Upstream giữ kết nối ~31s - 32s trước khi trả về `429 Resource Exhausted`.
   - Chuỗi retry qua các acc Pro tiếp theo lặp lại độ trễ 30s x N lần trước khi chạm ngưỡng retry để kích hoạt failover.
3. **Healing via Failover:**
   - Sau khi cạn attempts trên Gemini Pro pool, router kích hoạt fallback sang Codex pool (`gpt-5.6-luna-high` / `gpt-5.6-luna-medium`), chuyển trạng thái log thành `healed · 3 attempts` (HTTP 200).

## Diagnostic Runbook O(1)
1. **Kiểm tra trạng thái OmniRoute :20129 qua API:**
   - `/api/providers`: Lọc danh sách `antigravity` với `tier: 'g1-pro-tier'`, kiểm tra priority và `isActive`.
   - `/api/resilience`: Kiểm tra config `connectionCooldown`, `waitForCooldown`, `comboCooldownWait`.
   - `/api/combos`: Kiểm tra danh sách models trong pool và strategy failover (`p2c`, `reset-aware`).
2. **Đối soát log với Dashboard Quota:**
   - Lấy email mask từ Request Logs (ví dụ `#94c5`, `#42ff`, `#8679`, `#3723`).
   - Đối chiếu với thời gian reset quota (`in Xm`) trên `http://localhost:20129/dashboard/quota`.
3. **Xử lý nhanh:**
   - Khi Gemini Pro pool cạn rolling quota, chuyển tạm model chính sang `codex-luna` hoặc combo fallback để tránh bị kẹt timeout 30s của upstream Google.
   - Đợi 30 - 60 phút để Google reset quota rolling window cho các account Pro.
