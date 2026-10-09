# Đại Hội Benchmark Codex GPT (Luna & Terra) vs Gemini & Sonnet — Thẩm Định Bởi Sol High (21/09/2026)

## 1. Bối cảnh & Thiết lập Thẩm định
- **Giám khảo độc lập:** BẮT BUỘC dùng `chatgpt-web/gpt-5.6-sol-high` (Sol High có thinking sâu, thời gian chấm 15s–35s/trận). TUYỆT ĐỐI KHÔNG dùng `sol-instant` cho các bài toán audit, plan review hay chấm thi vì sol-instant thiếu thinking tokens ngầm, dễ bị đánh lừa bởi từ ngữ đao to búa lớn (như Airplane Mode hay Kill Switch) mà bỏ qua an toàn tài sản farm.
- **Hạ tầng thi đấu:** Gọi trực tiếp qua cụm OmniRoute `http://localhost:20129/v1/chat/completions`.
- **Model tham gia:**
  - `cx/gpt-5.6-luna-medium`, `cx/gpt-5.6-luna-high`, `cx/gpt-5.6-luna-max` (Codex upstream)
  - `cx/gpt-5.6-terra-medium`, `cx/gpt-5.6-terra-high` (Codex upstream)
  - `antigravity/gemini-3.8-flash-tiered` (medium & high)
  - `antigravity/claude-sonnet-4-6-medium` & `antigravity/claude-sonnet-4-6-high`

---

## 2. Kết Quả Giải Đấu Chi Tiết (18 Trận Đấu Thật)

### A. Nhánh Thợ Gõ (Worker Subagent)
1. **Bán kết nội bộ Codex Luna (3 trận):**
   - Trận 1 (Refactor Hook & Rollback): Luna High thắng (91 vs 82) — Atomic write file tạm `temp + os.replace`, kiểm tra SHA-256 byte stream.
   - Trận 2 (Watchdog XML ATX & MEDIA): Luna High thắng (91 vs 86) — Parse đúng node hierarchy XML thay vì match chuỗi thô.
   - Trận 3 (Redis Stream Consumer): Luna Medium thắng (82 vs 76) — Flow đơn giản, ít lỗi contract.
   - 👉 **Luna Worker High** thắng (2 - 1).
2. **Chung kết Worker: Luna Worker High vs Gemini Worker Medium (3 trận):**
   - Trận 1: Luna High 92đ vs Gemini Medium 63đ 🏆
   - Trận 2: Luna High 91đ vs Gemini Medium 58đ 🏆
   - Trận 3: Luna High 86đ vs Gemini Medium 62đ 🏆
   - 👉 **GPT-5.6 Luna Worker High VÔ ĐỊCH TUYỆT ĐỐI (3 - 0)**.
   - *Nhận xét Sol High:* Gemini Medium code prototype còn nhiều lỗi (dùng regex dễ phá hỏng file 3.000 dòng, không dump XML thực tế, lock task trước khi chạy dẫn đến mất task). Luna High code chuẩn Senior production (atomic fsync/replace, monotonic watchdog, consumer group + DLQ hoàn chỉnh).

---

### B. Nhánh Tổng Tư Lệnh (Coordinator)
1. **Vòng loại Luna (Medium vs High):** Luna High toàn thắng (3 - 0) — Điểm số 96, 91, 92.
2. **Vòng loại Terra (Medium vs High):** Terra High thắng (2 - 1) — Điểm số 96, 96, 82.
3. **Bán kết Codex (Luna High vs Terra High):**
   - Trận 1 (Proxy Outage): Terra High thắng (94 vs 90) — Lệnh O(1) dạng action chuẩn chỉ.
   - Trận 2 (Monolith Hook c=1): Luna High thắng (94 vs 88) — Anchor c=1 gọn, giữ 140 máy lành.
   - Trận 3 (Trễ lịch Nuôi/Reg): Luna High thắng (94 vs 84) — Ưu tiên đúng ca Nuôi đang chạy, dùng epoch/lease chặn race.
   - 👉 **Luna Coord High** thắng (2 - 1).
4. **Chung kết Tổng Tư Lệnh Tối Thượng: Luna Coord High vs Gemini Coord High (3 trận):**
   - Trận 1 (Sập Proxy 35 máy): Luna High 94đ vs Gemini High 86đ 🏆
   - Trận 2 (Monolith 3.5k dòng 5 Gates): Luna High 93đ vs Gemini High 84đ 🏆
   - Trận 3 (Trễ lịch Nuôi/Reg SQLite): Luna High 94đ vs Gemini High 72đ 🏆
   - 👉 **GPT-5.6 Luna Coord High VÔ ĐỊCH TỔNG TƯ LỆNH (3 - 0)**.
   - *Nhận xét Sol High:* Gemini High có xu hướng "hành động thái quá" (over-reacting) nguy hiểm: bật Airplane Mode và pkill -STOP làm văng session/cookie của 35 nick đang nuôi; tự ý đảo thứ tự Reg > Nuôi làm đứt gãy tài sản chính. Trong khi đó, Luna High tuân thủ tuyệt đối tôn chỉ Farm: **Bảo vệ tài sản nick lên hàng đầu (PAUSE, giữ session/cookie)**, chia rạch ròi 5 Gates, anchor c=1 tuyệt đối và quản trị rủi ro mẫu mực.

---

## 3. Đối Đầu Nội Bộ Đỉnh Cao: GPT-5.6 Luna High vs Luna Max (Sol High Chấm 6 Trận)

### A. Nhánh Thợ Gõ (Worker): Luna High vs Luna Max (3 trận)
- Trận 1 (Hook Scope Lock & Rollback): Luna High thắng (91 vs 84) — Scope Lock thực dụng bằng unique match, atomic replace. Luna Max bị over-constrain cứng nhắc.
- Trận 2 (Watchdog XML ATX & MEDIA): Luna High thắng (88 vs 84) — Bám scope rất chặt, watchdog tuyến tính, không thêm layer thừa.
- Trận 3 (Redis Stream & DLQ): Luna Max thắng (72 vs 58) — Max xử lý retry nội bộ đúng chuẩn, giữ message pending không ACK cho đến khi commit.
👉 **Kết quả Worker: Luna Worker High chiến thắng (2 - 1)**.
*Nhận xét Sol High:* Ở vai trò Worker, Luna Max đốt 6.000–8.000 reasoning tokens ngầm, latency lên tới 110s–160s, dẫn đến over-engineering và tự đặt ra các ràng buộc quá ngặt nghèo. Luna High thực dụng, code sạch và an toàn cho production.

### B. Nhánh Tổng Tư Lệnh (Coordinator): Luna High vs Luna Max (3 trận)
- Trận 1 (Proxy Outage & Forensic): Luna Max thắng (94 vs 88) — Khóa toàn bộ forensic state (disk/RAM/log), kiểm soát gateway allowlist chống bão request.
- Trận 2 (Monolith 3k dòng & 5 Gates): Luna Max thắng (95 vs 91) — Kiểm soát blast radius hoàn hảo, có bước reproduce trước patch, rollout canary chi tiết.
- Trận 3 (Trễ lịch Nuôi/Reg & SQLite): Luna High thắng (92 vs 78) — Quyết định O(1) giữ nguyên ca Nuôi (tài sản lớn nhất). Max mắc lỗi chiến lược dồn Standby cho Reg.
👉 **Kết quả Coordinator: Luna Coord Max chiến thắng (2 - 1)**.
*Nhận xét Sol High:* Ở vai trò Tổng tư lệnh, tư duy Max phát huy sức mạnh tối đa ở khâu khoanh vùng rủi ro (Containment) và thiết lập hàng rào bảo vệ (Gates). Điểm trừ của Max là thời gian suy nghĩ lâu (35s–68s).

---

## 4. Kiến Trúc Phân Vai & Cấu Hình Hermes Chốt Hạ
1. **Tổng Tư Lệnh (Coordinator Session Chính):**
   - Vô địch toàn diện: `cx/gpt-5.6-luna-max` (khi cần bao quát rủi ro tối đa) hoặc `cx/gpt-5.6-luna-high` (tốc độ nhanh 15–25s, điểm TB 94/100).
   - Tùy chọn kinh tế / fallback: `omni-worker` với `agent.reasoning_effort: high`.
2. **Thợ Gõ (Worker Subagents):**
   - Vô địch toàn diện: `cx/gpt-5.6-luna-high` (Điểm TB 90/100, code sạch chuẩn Senior, atomic write).
   - Cấu hình Hermes: `delegation.reasoning_effort: medium` (nếu dùng pool free) hoặc `high` khi cần code production chuẩn mực.
3. **Lưu Ý Endpoint & Timeout Bắt Buộc:**
   - Model ID Codex: Dùng tiền tố `cx/` (ví dụ `cx/gpt-5.6-luna-high`, `cx/gpt-5.6-luna-max`) để gọi thẳng backend Codex trên OmniRoute `:20129` mà không bị nghẽn timeout upstream.
   - Timeout client: Luna High sinh 1.000–3.000 reasoning tokens ngầm $\to$ timeout $\ge 120s$. Luna Max sinh 4.000–8.000 reasoning tokens ngầm $\to$ timeout BẮT BUỘC $\ge 240s$ để tránh rớt kết nối giữa chừng!
