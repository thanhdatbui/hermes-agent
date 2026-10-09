# OmniRoute Proxy Routing Quirks & Antigravity 403 / Nested Combo Handling

## 1. Scope-Level Proxy Resolution Asymmetry (Lỗ hổng kiểm tra sống chết)

OmniRoute áp dụng 2 cơ chế kiểm tra proxy hoàn toàn khác nhau tùy thuộc vào scope:

### A. Account-Level (`scope='account'`, vd: Antigravity / Gemini accounts)
* Đầy đủ preflight probe (`isProxyReachable` trong `settings.ts:Step 3`).
* Khi proxy gán vào account bị chết, OmniRoute tự gọi `resolveProviderPoolFallbackProxy` để lọc ứng viên sống trong pool provider và hash-distribute sang cổng sống.
* **Hành vi:** Proxy chết $\rightarrow$ tự nhảy sang proxy sống cùng provider (vd: MobiProxy chết $\rightarrow$ nhảy sang MikroTik).

### B. Provider / Combo Scope (`scope='provider'`, `scope_id='opencode'` cho `omni-free`)
* **KHÔNG CÓ preflight probe** tại thời điểm resolve (`resolveScopePoolInternal` trong `rotation.ts`).
* Chỉ lọc thô trong SQLite: `status NOT IN ('inactive', 'error', 'disabled', 'dead', 'down')`.
* Nếu proxy thực tế đã sập nhưng trong DB vẫn mang `status = 'active'`, con trỏ Round-Robin vẫn bốc trúng cổng chết.
* **Hậu quả:** Không có retry sang proxy khác trong cùng request. Request dính ngay HTTP 502 / Socket Hang Up / Timeout.
* **Quy tắc an toàn:** Tuyệt đối KHÔNG gán dải proxy chưa được xác minh hoặc đang chập chờn/sập (như MobiProxy khi sập) vào provider pool `opencode`. Chỉ giữ các cổng 100% sống (như MikroTik).

---

## 2. Nested Combos & The 63-Account Retry Trap

### Vấn đề khi Combo con là một Account Pool lớn
* Cấu trúc combo:
  * Tier 1: `combo/ag-gemini-pool-3` (63 accounts Antigravity)
  * Tier 2: `combo/ag-claude`
  * Tier 3: `combo/omni-free` (OpenCode via MikroTik)
* Khi Google chặn HTTP 403 (Forbidden) hàng loạt trên Antigravity:
  * OmniRoute bung toàn bộ 63 target ra thử tuần tự.
  * Mỗi account lỗi mất 1.5s - 2s $\rightarrow$ 63 accounts ngốn ~120s.
  * Client (Hermes/curl) timeout trước khi kịp rơi xuống Tier 3 (`omni-free`).

### Bản chất Cooldown trong OmniRoute Core
* Cooldown mặc định là **per-connection** (`cooldownKey(provider, connectionId)`), KHÔNG PHẢI per-provider.
* Khi 63 acc cùng ăn 403, mỗi acc nhận cooldown riêng. Ở request đầu tiên, nó vẫn phải thử từng acc một.
* Cooldown chỉ giúp các request tiếp theo trong vòng `minRetryCooldownMs` lướt qua nhanh (0.1ms skip).

### Cách xử lý đúng chuẩn (Không sửa code OmniRoute)
1. **Tuyệt đối không can thiệp sửa code lõi của OmniRoute** (giữ code vanilla, chỉ cấu hình qua DB/settings).
2. **Swap Model chủ động:** Khi thấy dàn Gemini dính bão 403, chuyển client/agent sang dùng trực tiếp model `combo/omni-free` thay vì dùng `combo/omni-worker` rồi ngồi đợi timeout fallback.
3. **Phân tích bản chất 403 của Google:**
   * 403 của Google Antigravity thường đến **theo sóng** (có những khung giờ 100% OK, có khung giờ dính 30-50%).
   * Không phải bị ban vĩnh viễn (cook hẳn).
   * Không nên tăng initial cooldown lên quá cao (như 5m - 30m) vì sẽ chặn oan các acc vừa hồi phục sau khi sóng 403 đi qua. Giữ `initial: 30000` (30s) + exponential backoff là tối ưu nhất.

---

## 3. Proxy Rotation Strategies: Round-Robin vs Random cho Free Providers
* Với provider miễn phí không cần auth (`opencode` / `omni-free`):
  * **Round-Robin là tối ưu nhất:** Phân bổ đều 100% tải lên toàn bộ dải cổng (`cursor % N`). Mỗi cổng được nghỉ tối đa ($N-1$ request) trước khi bị gọi lại, tránh kích hoạt rate-limit IP (429) và challenge Cloudflare.
  * **Random kém hơn:** Dễ dính hiện tượng Birthday Paradox (ngẫu nhiên bắn 2-3 request liên tiếp vào cùng 1 cổng IP), làm chết cổng và ăn rate-limit sớm.
