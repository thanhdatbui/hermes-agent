# Hardware-Anchored Proxy Affinity & Multi-Tenant Stacking Prevention Runbook

## 1. Bối cảnh & Hiện tượng sự cố (Incident Post-Mortem 2026-10-12)

### Hiện tượng:
- Hermes Gateway bị rớt lượt, báo lỗi: `⚠️ The model provider failed after retries`.
- Log OmniRoute (`:20129`) ghi nhận:
  - `[Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:5113`
  - `Model antigravity/gemini-3.8-flash-tiered exceeded 30000ms timeout — falling back`
  - Fallback sang Codex: `codex | all 1 active accounts cooling down for model gpt-5.6-terra (reset after 415h 21m 28s)`
  - Fallback sang ChatGPT Web: `Model chatgpt-web/gpt-5.6-sol-high exceeded 15000ms timeout — falling back` $\rightarrow$ `HTTP 504 Gateway Timeout`.

### Nguyên nhân gốc rễ (Hotspot Stacking):
- Cổng proxy 4G `test.taadaa.click:5113` bị nhồi nhét tới **10 tài khoản khác nhau** (cả Gemini, Codex lẫn ChatGPT Web).
- Trong khi đó, hệ thống có **72 proxy active** nhưng chỉ dùng 45 cổng; có tới **27 cổng proxy MikroTik PPPoE (`10008..10035`) đang bị bỏ trống 100% (0 account)**.
- Khi cổng 4G `5113` bị chập chờn sóng, cả 10 tài khoản gán trên cổng này đồng loạt bị nghẽn. Request chính (Gemini) ngâm 30 giây mới timeout, khiến toàn bộ ngân sách retry của client cạn kiệt trước khi kịp xoay sang các account ở các dải proxy khỏe khác.

---

## 2. Bản chất phân loại tài khoản: Hardware-Anchored vs Standalone

Khi điều phối và gán proxy trong `storage.sqlite` (`proxy_assignments`), **BẮT BUỘC PHẢI PHÂN BIỆT RẠCH RÒI 2 LOẠI TÀI KHOẢN**:

### Loại 1: Tài khoản gắn cứng theo phần cứng (Hardware-Anchored S7 Accounts)
- **Đối tượng:** Các tài khoản Google (Gmail OAuth cho Antigravity / Gemini) nuôi trực tiếp trên dàn điện thoại **Samsung S7 (Main Box Farm)**.
- **Nguồn gốc cấu hình (Source of Truth):** `PROXYgandienthoai.xlsx` (cột `Proxy` của từng máy).
  - Ví dụ: Máy S7 số 11 và số 49 được gán cổng `test.taadaa.click:5113:mobi13:TaadaaMobi#2026!`.
  - Trên Máy 49 có nuôi 3 Gmail: `cathoa060149@gmail.com`, `chuloan02122003@gmail.com`, `sambich2610200149@gmail.com`.
  - Trên Máy 11 có nuôi: `alicelmoralesjvcrj@gmail.com`.
- **Quy tắc bất biến (Affinity Invariant):**
  - Khi pipeline nạp OAuth (`run_oauth_s7_pipeline.py`) kéo token từ điện thoại S7 sang OmniRoute, **BẮT BUỘC PHẢI GÁN ĐÚNG CỔNG PROXY CỦA MÁY ĐÓ TRONG EXCEL (5113)**.
  - **LÝ DO KỸ THUẬT:** Google kiểm tra IP rất nghiêm ngặt. Nếu tài khoản vừa duyệt Google Prompt trên điện thoại qua cổng 5113 mà trên OmniRoute lại gửi request LLM qua một IP khác (ASN mismatch / IP jump), Google sẽ lập tức kích hoạt Security Checkpoint, khóa phiên OAuth hoặc yêu cầu xác minh lại.
  - **KẾT LUẬN:** Việc các tài khoản Google này nằm trên cổng 5113 là **ĐÚNG THEO THỰC TẾ PHẦN CỨNG S7**, không được tùy tiện đổi proxy của chúng.

### Loại 2: Tài khoản độc lập trên môi trường ảo (Standalone Web / Hotmail Accounts)
- **Đối tượng:** Các tài khoản Hotmail (Codex CLI), ChatGPT Web (GPM Login), hoặc tài khoản đăng ký độc lập bằng API/Web.
  - Ví dụ: `vanharlingenmach959@hotmail.com` (Codex), các profile ChatGPT Web.
- **Đặc điểm:** Các tài khoản này **hoàn toàn KHÔNG nằm trên điện thoại S7**. Chúng chạy trên PC hoặc máy ảo/GPM.
- **Sai lầm tai hại (Anti-pattern):**
  - Khi chạy các script salvage tài khoản (như `phone-verified-account-salvage`) hoặc auto-reg ChatGPT, script bốc đại một proxy trong registry hoặc default vào cổng 5113 mà không kiểm tra độ tải của cổng.
  - Hậu quả: Nhồi Hotmail và Web đè lên cổng 4G vốn đã gánh các nick Google của máy S7!

---

## 3. Quy tắc phân bổ Proxy an toàn (Proxy Allocation Governance)

1. **CẤM NHỒI TẠP NHAM (Anti-Pollution Rule):**
   - TUYỆT ĐỐI CẤM gán tài khoản Standalone (Hotmail, ChatGPT Web độc lập) vào các cổng proxy 4G đang gánh máy S7 (như `5113`).
   - Các cổng 4G của S7 chỉ phục vụ đúng các tài khoản Google nằm trên chính các máy S7 đó.

2. **ƯU TIÊN DẢI PROXY RẢNH (Least-Allocated Balancing):**
   - Khi nạp tài khoản Standalone mới (Hotmail / Codex / Web):
     - Luôn truy vấn danh sách proxy active có số lượng account gán ít nhất:
       ```sql
       SELECT p.id, p.host, p.port, COUNT(pa.id) as assigned_count
       FROM proxy_registry p
       LEFT JOIN proxy_assignments pa ON p.id = pa.proxy_id AND pa.scope = 'account'
       WHERE p.status = 'active'
       GROUP BY p.id, p.host, p.port
       ORDER BY assigned_count ASC, p.port ASC;
       ```
     - Ưu tiên tối đa dải **MikroTik PPPoE cố định (`mirotik1.taadaa.click:10008..10035`)** cho các tài khoản Hotmail và ChatGPT Web. Dải này băng thông lớn, không tốn tiền 4G, và không bị nghẽn sóng di động.

3. **TRẦN MẬT ĐỘ TÀI KHOẢN (Density Ceiling):**
   - Cổng 4G MobiProxy (`5101..5138`): Tối đa $\le 3$ accounts / cổng.
   - Cổng MikroTik PPPoE (`10001..10035`): Tối đa $\le 2$ accounts / cổng.
   - Khi phát hiện bất kỳ cổng nào có $> 3$ accounts, lập tức gắn cờ cảnh báo `HOTSPOT_PROXY_CONGESTION` để điều phối lại.

---

## 4. Chuẩn hóa chuỗi Fallback Combo để chống đơ Gateway

Khi thiết kế hoặc cập nhật các combo đa tầng (như `review` hoặc `omni-worker`):
1. **Timeout từng tầng phải giảm dần hoặc khống chế chặt:**
   - Tier 1 (Antigravity): Timeout $\le 20\text{s}$ (không để ngâm tới 30s khi proxy rớt).
   - Fast-fail socket: Khi proxy trả về `Proxy unreachable` (ECONNREFUSED / ETIMEDOUT trong $< 1\text{s}$), OmniRoute phải skip ngay lập tức sang connection tiếp theo thay vì ngâm toàn bộ timeout của target.
2. **Bảo dưỡng Fallback Tiers (Chống Fallback Rỗng):**
   - Tầng Codex (`gpt-5.6-terra`): Nếu toàn bộ tài khoản dính cooldown 415h, combo router phải đánh dấu tier này là `INELIGIBLE` ngay tại pre-dispatch để bỏ qua tức thì (0ms), không để request bị kẹt.
   - Tầng ChatGPT Web (`gpt-5.6-sol-high`): Đặt timeout $\le 15\text{s}$ kèm circuit-breaker nếu web đang quá tải.
