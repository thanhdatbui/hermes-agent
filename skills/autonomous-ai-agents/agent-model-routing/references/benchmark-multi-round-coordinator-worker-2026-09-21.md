# Benchmark Đa Tầng Coordinator & Worker (Gemini 3.8 vs Claude Sonnet vs Claude Opus - 21/09/2026)

**Hạ tầng thực nghiệm:** Cụm proxy OmniRoute (`localhost:20129`) trên Windows host Kibe Master (Farm 160 máy).  
**Hội đồng giám khảo ra đề & chấm độc lập:** `chatgpt-web/gpt-5.6-sol-instant` (ChatGPT Web Sol pool 5+ accs).

---

## 1. Phát hiện gốc rễ cấu hình Thinking trong OmniRoute & Hermes
- **Sự cố:** Mặc dù user đã yêu cầu bật Thinking cho Sonnet và Gemini, trong dashboard log OmniRoute bấy lâu nay toàn bộ request `ag-claude` và `ag-gemini` đều chạy No-Thinking (Flash mode).
- **Nguyên nhân:**
  + Trong Antigravity/OmniRoute, `ag-opus` có target `antigravity/claude-opus-4-6-thinking` nên luôn có thinking.
  + Trong khi `ag-claude` trỏ target `antigravity/claude-sonnet-4-6` và `ag-gemini-pool-3` trỏ `antigravity/gemini-3.8-flash-tiered`. Đây là các base ID chạy No-Thinking trừ khi được gán cờ `reasoning_effort` / `thinking: {type: 'enabled'}` hoặc trỏ thẳng vào target suffix (`-medium` / `-high`).
  + Core Hermes Agent (`provider: omni`) khi gửi request qua `/v1/chat/completions` không tự động mapping thinking parameters đặc thù nếu không cấu hình explicit.

---

## 2. Phần 1: Benchmark Thợ Gõ (Worker) — Gemini 3.8 High vs Medium
- **Task 1 (Code Surgery & Rollback Invariant):** 
  + Gemini Medium: **86/100** (18.3s)
  + Gemini High: **78/100** (30.0s)
  + *Nhận xét Sol:* Medium thắng vì rollback thực tế (tạo backup trước khi `os.replace`), bám sát scope lock. High bị overthinking, regex quá rộng và rollback lý thuyết.
- **Task 2 (UI Bug Hunting & Lưu MEDIA Evidence):**
  + Gemini Medium: **92/100** (17.3s)
  + Gemini High: **90/100** (21.3s)
  + *Nhận xét Sol:* Medium thực dụng, watchdog đúng hạn, lưu folder MEDIA chuẩn. High bị over-engineering, tự ý thêm package `pillow` không cần thiết.
- 👑 **Kết luận Worker:** **Gemini 3.8 Flash Medium** là Worker tối ưu nhất: nhanh, code sạch, không vẽ vời dependency thừa.

---

## 3. Phần 2 & 3: Phân Hạng Điều Phối (Coordinator) Theo Mức Reasoning (3 Vòng Mỗi Cặp)

### Nhánh 1: Claude Sonnet Medium vs Claude Sonnet High (3 bài test điều phối)
- **Trận 1 (Fleet Proxy Failure):** Sonnet High 92đ vs Sonnet Medium 86đ (High thắng ở cơ chế Circuit Breaker).
- **Trận 2 (Monolith Hook Regression & 5 Gates):** Sonnet Medium 88đ vs Sonnet High 84đ (Medium thắng ở SITREP rõ, anchor c=1, rollback thực chiến).
- **Trận 3 (Schedule Conflict & Standby Borrowing):** Sonnet Medium 86đ vs Sonnet High 82đ (Medium thắng nhờ biết pause thay vì kill, không over-engineer).
- 🏆 **Chung cuộc Nhánh Claude:** **Claude Sonnet Medium THẮNG (2 - 1)**.
  * *Lý do:* Sonnet High bị bệnh "overthinking/lo xa", dễ ra quyết định quá tay làm lan rộng blast radius (như kill switch hoặc rate limit toàn farm).

### Nhánh 2: Gemini 3.8 Medium vs Gemini 3.8 High (3 bài test điều phối)
- **Trận 1 (Fleet Proxy Failure):** Gemini High 91đ vs Gemini Medium 86đ (High thắng ở trạng thái `DRAINING`, Quarantine VLAN).
- **Trận 2 (Monolith Hook Regression):** Gemini High 95đ vs Gemini Medium 92đ (High thắng ở Patch Contract đóng và điều kiện Abort Gate 1).
- **Trận 3 (Schedule Conflict & Standby):** Gemini High 86đ vs Gemini Medium 82đ (High thắng ở logic checkpoint/yield và hoàn trả node).
- 🏆 **Chung cuộc Nhánh Gemini:** **Gemini 3.8 High TOÀN THẮNG (3 - 0)**.
  * *Lý do:* Gemini High kiểm soát Control Plane và State Machine (`DRAINING`, `QUARANTINE_LANE`) vượt trội.

---

## 4. Phần 4: Trận Chung Kết Tổng Tư Lệnh (3 Trận Tử Chiến)
### ⚔️ Claude Sonnet Medium vs Gemini 3.8 High ⚔️

- **Chung kết 1 (Incident Triage & Cascading Failure):**
  + Gemini High: **91/100** (9.3s) — Ổn định hệ thống trước, cắt tải tức thì, event-driven log nhẹ, không đụng vào máy lành.
  + Sonnet Medium: **86/100** (19.7s) — Bị trừ điểm vì vội vàng đòi rollback cả 110 máy đang chạy bình thường.
- **Chung kết 2 (Code-Surgery Dispatch Monolith 3.5k dòng):**
  + Gemini High: **92/100** (10.7s) — Anchor c=1 dứt khoát, cấm đọc full file, tiêu chí nghiệm thu kiểm chứng được.
  + Sonnet Medium: **86/100** (15.3s) — Grep còn quá rộng, rollback sơ sài.
- **Chung kết 3 (Closeout Gate & Reviewer 82/100):**
  + Gemini High: **92/100** (7.4s) — Có state `CLOSEOUT_BLOCKED`, truy vết node lỗi, phân luồng vá nóng và tái nghiệm thu.
  + Sonnet Medium: **88/100** (13.2s) — Đúng kỷ luật nhưng nặng về checklist lý thuyết, thiếu cơ chế chuyển trạng thái.

👑 **TỔNG TƯ LỆNH TỐI THƯỢNG TOÀN FARM:** **GEMINI 3.8 FLASH THINKING HIGH (THẮNG TUYỆT ĐỐI 3 - 0)**.

---

## 5. Quy Chuẩn Routing Vàng Cho Farm Taadaa
1. **Tổng Tư Lệnh (Coordinator):** `Gemini 3.8 Flash (Thinking High)` — phản ứng quân sự dứt khoát (7-10s), O(1) kỷ luật thép, không bị compliance filter chặn đứng phản xạ chỉ huy.
2. **Thợ Gõ (Omni-Worker):** `Gemini 3.8 Flash (Thinking Medium)` — thực dụng, bám Scope Lock, zero side-effects, tốc độ 15-18s, không tốn quota Claude.
3. **Kiến Trúc Sư / Reviewer Độc Lập:** `Claude Sonnet 4.6 Medium` hoặc `Opus Thinking` / `Sol Web` — chuyên gia soi bug logic, race condition SQLite, và kiểm định 5 Gates trước khi chốt phiên.
