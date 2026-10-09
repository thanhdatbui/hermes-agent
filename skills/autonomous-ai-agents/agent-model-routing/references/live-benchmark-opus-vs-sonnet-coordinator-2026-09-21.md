# Live Benchmark: Claude Opus (`ag-opus`) vs Sonnet (`ag-claude`) - Farm Coordinator Role (2026-09-21)

## Bối cảnh & Phương pháp đo lường
- **Hạ tầng thi đấu:** Cụm proxy OmniRoute (`http://localhost:20129/v1/chat/completions`).
- **Giám khảo ra đề & chấm độc lập:** `chatgpt-web/gpt-5.6-sol-instant` (ChatGPT Web Sol pool).
- **Thí sinh A:** `ag-claude` (Claude Sonnet qua pool Antigravity).
- **Thí sinh B:** `ag-opus` (Claude Opus 4.6 Thinking qua pool Antigravity).
- **Harness:** HTTP POST trực tiếp, max_tokens 1000, đo thời gian thực tế bằng giây và token usage.

---

## 1. Đề thi từ Giám khảo Sol
Tình huống khẩn cấp vận hành Farm 160 điện thoại:
1. 10 máy cùng phát alert (app crash, mất mạng, worker đứng): Nêu ưu tiên và quyết định điều phối trong 5 phút đầu.
2. Thiết kế cách quan sát trạng thái farm theo tư duy O(1) (không quét toàn bộ 160 máy).
3. Viết một Patch Contract chuẩn giữa Coordinator và Worker (Input/Output, retry, rollback).
4. Cách chia worker, tránh nghẽn cổ chai và duy trì uptime.

---

## 2. Kết quả & Đo lường thực tế

| Tiêu chí | `ag-claude` (Sonnet) | `ag-opus` (Opus 4.6 Thinking) |
| :--- | :---: | :---: |
| **Thời gian phản hồi (Elapsed)** | **32.26s** | **40.75s** |
| **Tokens sinh ra** | 1,000 completion tokens (chạm cap) | 1,611 completion tokens (kèm Thinking block) |
| **Tư duy cốt lõi** | "Excellent Operator" — Triage theo Severity x Blast Radius, Redis Sorted Set heartbeat, YAML Patch contract với idempotency_key, Pull-queue per pool. | "Fleet Commander" — Cô lập node lỗi tránh nhiễm task, State Map O(1) Bucket, JSON Patch Contract có Pre-check (pin/dung lượng) & Rollback test 180s, chia 4 Zone x 37 máy kèm Canary rollout. |

---

## 3. Bảng điểm chi tiết do Giám khảo Sol chấm (Thang điểm 100)

| Hạng mục chấm | Sonnet (`ag-claude`) | Opus (`ag-opus`) | Nhận xét từ Giám khảo Sol |
| :--- | :---: | :---: | :--- |
| **1. Xử lý 5 phút đầu (25đ)** | 22 / 25 | **24 / 25** | Opus nổi bật ở triết lý: "Không bao giờ debug trong giờ chiến — chỉ thay thế hoặc cô lập", chặn máy lỗi tiếp tục nhận workload tránh cascade failure. |
| **2. Giám sát O(1) (25đ)** | 21 / 25 | **24 / 25** | Sol nhận định: Redis ZSET của Sonnet là O(log N + M), chưa đạt O(1) tuyệt đối. Opus dùng State Bucket đọc trực tiếp counter (healthy/dead/degraded) đạt O(1) chuẩn xác. |
| **3. Patch Contract (25đ)** | 20 / 25 | **24 / 25** | Opus áp đảo: Có Pre-check (battery >= 30%, storage >= 100MB), vòng đời backup state và rollback rõ ràng. Sonnet có điểm cộng ở `idempotency_key` nhưng thiếu rollback lifecycle. |
| **4. Phân bổ Fleet (25đ)** | **21 / 25** | 19 / 25 | Sonnet gỡ lại điểm nhờ thiết kế Quarantine Pool và Pull-model chống nghẽn. Opus chia 4 Zone x 37 máy + Canary rất chuẩn nhưng chưa xử lý rủi ro Zone Leader chết. |
| **TỔNG ĐIỂM CHUNG CUỘC** | **84 / 100** | **91 / 100 (WINNER)** | 🏆 **CLAUDE OPUS THẮNG CUỘC** |

---

## 4. Kết luận kiến trúc thực chiến cho Taadaa Farm
1. **Chất lượng kiến trúc:** Claude Opus thể hiện tư duy Fleet Management vượt trội, đặc biệt ở khâu containment (cô lập sự cố), bảo vệ an toàn thiết bị và rollout phân tầng.
2. **Kỷ luật vận hành:** Claude Sonnet phản ứng nhanh hơn (~32s vs ~41s), thiết kế hàng đợi và cơ chế idempotency thực tế.
3. **Mô hình khuyến nghị tối ưu:**
   - **Tư vấn kiến trúc / Thiết kế Plan / Audit sự cố lớn:** Dùng `ag-opus` (Opus) để đảm bảo độ bao quát và kiểm soát rủi ro cascade failure.
   - **Điều phối hằng ngày / Triage phản xạ nhanh:** Dùng `ag-claude` (Sonnet) hoặc kết hợp pool `chatgpt-web/gpt-5.6-sol` cho vai trò Reviewer để tối ưu tốc độ và quota.
