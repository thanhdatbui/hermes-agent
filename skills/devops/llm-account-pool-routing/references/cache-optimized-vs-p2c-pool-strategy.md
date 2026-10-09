# Phân Tầng Chiến Lược Routing Pool Đa Tài Khoản: Cache-Optimized vs P2C (2026-09-21)

## 1. Bản Chất Các Lỗi Routing Cũ (Anti-Patterns)
1. **Bẫy Session Stickiness Vô Hạn (`stickyRoundRobinLimit >= 200`):**
   - Khi bật session stickiness với limit quá lớn trên pool mà mỗi account có `maxConcurrent = 2` (Antigravity):
   - Mọi request của cùng session / burst đều bị pin vào duy nhất 1 connection.
   - Khi có concurrent requests, connection đó kẹt semaphore, các request sau bị đẩy vào hàng đợi chờ tới 30 giây rồi nổ lỗi 429 Semaphore Timeout, trong khi hàng chục account còn lại trong pool hoàn toàn rảnh rỗi.
2. **Bẫy Round-Robin Máy Móc & Fill-First:**
   - **Fill-First:** Dồn toàn bộ tải vào 1 acc cho tới chết -> tạo "Hot Account", Google Anomaly Detection quét ra spike bất thường gắn cờ ban acc, con đó chết thì sụp đổ dây chuyền (cascade death).
   - **Round-Robin thuần túy:** Xoay mù quáng không xét độ tải, dễ bị quét ra bot pattern vì timing quá đều đặn, đồng thời phá vỡ 100% Prompt Cache vì mỗi turn nhảy sang 1 acc mới.

## 2. Kiến Trúc Đồng Thuận Chuẩn (Sol GPT-5.6 & Claude Code CLI)
Phân định ranh giới rạch ròi theo bản chất tài nguyên:
- **Tài nguyên Quý (Pro):** Tối ưu Cache và ngữ cảnh liên tục.
- **Tài nguyên Đông / Mỏng Quota (Free):** Tối ưu tuổi thọ, tự cân bằng tải và phân tán rủi ro.

### A. Pool Pro (Tài nguyên quý - ví dụ: 16 acc Antigravity Pro):
- **Strategy:** `cache-optimized` (Router soi mã băm prompt, ưu tiên đưa vào account đang giữ Prompt Cache ấm nhất).
- **Sticky Batch:** `stickyRoundRobinLimit = 8` (Công thức an toàn: $2 \times \text{maxConcurrent} \dots 4 \times \text{maxConcurrent}$, đủ cho 1 session agent làm việc trọn vẹn mà không gây nghẽn).
- **Session Stickiness:** `disableSessionStickiness: false` (Bảo tồn cache session).
- **Micro-Queue:** `queueDepth = 1`, `queueTimeoutMs = 1000` (Chỉ cho phép chờ tối đa 1 giây để hấp thụ burst ngắn; nếu sau 1s connection không free thì failover ngay lập tức, triệt tiêu bẫy treo 30s).
- **Failover:** `failoverBeforeRetry = true` (Chuyển connection trong pool ngay khi chớm lỗi hoặc bận).

### B. Pool Free & Số Lượng Lớn (Free Gemini, Claude Sonnet, Claude Opus, ChatGPT Web):
- **Strategy:** `p2c` (Power of Two Choices - Mỗi request bốc ngẫu nhiên 2 accounts, so sánh độ tải/latency rồi chọn con rảnh hơn).
  - Ưu điểm: Phân tán tải tự nhiên, xóa bỏ tính máy móc của Round-Robin, tự né các account đang bận/nóng mà không cần scan toàn bộ pool.
- **Sticky:** `stickyRoundRobinLimit = 0`, `disableSessionStickiness: true` (Không ghim session, rải đều toàn bộ đàn acc).
- **Hàng đợi:** `queueDepth = 0`, `queueTimeoutMs = 1000` (Cấm xếp hàng dài).
- **Failover:** `failoverBeforeRetry = true`.

## 3. Quy Tắc Gộp Account Giữa Các Provider
- **Google Gemini:** BẮT BUỘC TÁCH BIỆT 2 combo riêng:
  - `ag-gemini-pool-3`: Chỉ chứa đúng các acc Pro (chạy `cache-optimized`).
  - `ag-gemini-free-pool`: Chứa toàn bộ các acc Free (chạy `p2c`).
- **Claude Sonnet & Opus:** GỘP CHUNG toàn bộ tài khoản Antigravity (cả Pro lẫn Free) vào chung 1 pool `ag-claude` và `ag-opus`, chạy theo chuẩn `p2c`.
- **Combo Tổng Worker (`omni-worker`):** Strategy `priority` (Tier 1 Pro -> Tier 2 Free -> Tier 3 Claude). Gỡ bỏ hoàn toàn các model web hoặc free rác có nguy cơ gây lỗi 413 (Payload Too Large) hoặc 401/403.
