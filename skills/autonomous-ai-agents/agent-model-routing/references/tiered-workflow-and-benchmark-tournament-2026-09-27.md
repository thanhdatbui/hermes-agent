# LUNA VS TERRA BENCHMARK & TIERED WORKFLOW (2026-09-27)
*Thẩm định & Thiết kế bởi Senior Architect Claude CLI & Giám khảo GPT-5.6 Sol High*

---

## I. BỐI CẢNH & PHÂN TÍCH NỖI ĐAU CỦA USER
1. **Lợi thế & Điểm yếu của Gemini (Coordinator):**
   - *Lợi thế:* Xốc vác, bias for action, tìm mọi cách để làm, KHÔNG OVER-ENGINEER, tốc độ cực nhanh (5-15s).
   - *Điểm yếu:* Hay làm ẩu, chữa ngọn (Happy Path Coder), báo cáo "thành công" nhưng dễ sót edge cases (timeout, rớt mạng, lệch timezone) dẫn tới vài hôm sau lỗi lại.
2. **Lợi thế & Điểm yếu của Luna (Worker):**
   - *Lợi thế:* Cú pháp code chuẩn xác, ít bug vặt, cực kỳ tuân thủ phạm vi khi bị khóa.
   - *Điểm yếu:* "Thấy đèn đỏ là tắt máy ngồi khóc" (Tê liệt phòng thủ / Defensive Paralysis khi gặp repo dirty hoặc dính nhiều rule cấm), và hay over-engineer vẽ kiến trúc lớn nếu thả rông.
3. **Mục tiêu của Workflow:**
   - Bảo toàn 100% tốc độ và tính xốc vác hiện trường của Gemini.
   - Dùng Terra/Sol để soi trước góc chết (edge cases) cho các ca khó.
   - Nhốt Luna vào Lồng Vô Trùng để gõ code chuẩn mà không thể ngồi khóc nhè hay over-engineer.
   - Dùng Canary Gate trên máy thật để bắt thóp bệnh "báo cáo láo" của Gemini.

---

## II. KẾT QUẢ ĐẠI HỘI BENCHMARK 15 TRẬN THỰC CHIẾN (27/09/2026)
*Giám khảo: GPT-5.6 Sol High qua OmniRoute :20129*

1. **Bán kết 1 (Luna Derby):** `codex/gpt-5.6-luna-high` (460.0đ) thắng `codex/gpt-5.6-luna-medium` (448.0đ).
2. **Bán kết 2 (Terra Derby):** `codex/gpt-5.6-terra-high` (456.0đ) thắng `codex/gpt-5.6-terra-medium` (439.0đ).
3. **Chung kết Tối Cao (Luna High vs Terra High):**
   - *Trận 11 (TikTok UI Drift):* Terra High thắng (96 vs 94) — thiết kế fallback mượt mà, sáng sủa.
   - *Trận 12 (Watchdog Reconcile):* Luna High thắng (92 vs 84) — Luna sửa đúng 3 dòng `if follow_failed: continue`, Terra bị trừ điểm vì tài lanh refactor dict comprehension.
   - *Trận 13 (Hotmail OTP Clock Skew):* Terra High thắng (96 vs 94) — sliding window tự co giãn dung sai.
   - *Trận 14 (GPM Teardown finally):* Luna High thắng (91 vs 84) — Terra bị bắt lỗi leak window do đăng ký profile muộn sau start_profile().
   - *Trận 15 (Dropdown Misclick):* Terra High thắng (94 vs 91).
   - **TỔNG KẾT:** **`codex/gpt-5.6-luna-high` VÔ ĐỊCH TỔNG ĐIỂM (462.0đ)** nhờ tính ổn định và kỷ luật an toàn vượt trội.

---

## III. QUY CHUẨN ĐIỀU PHỐI TỨ TRỤ TAADAA FARM (TIERED WORKFLOW)

### 1. TẦNG 0 (T0) — VẬN HÀNH HIỆN TRƯỜNG (0 CODE DIFF)
- **Phạm vi:** Restart script, lệnh ADB trực tiếp, đọc log `inspect_machine.py`, check proxy, taskkill, đổi hằng số `.env`.
- **Thực thi:** Gemini Coordinator tự làm 100% trong 5–15 giây.

### 2. TẦNG 1 (T1) — VÁ HIỆN TRƯỜNG / SỬA ỐC LỎNG (GEMINI TỰ NỔ SÚNG)
- **Phạm vi:** Tăng timeout, đổi tọa độ, đổi selector text UI drift, thêm `try/except`, thêm `if... continue`.
- **Điều kiện O(1):** Đúng 1 file, tổng diff (thêm + xóa) <= 15 dòng, có 1 lệnh verify < 30s.
- **Quy trình:** Gemini tự sửa trực tiếp O(1) -> Chạy Canary trên máy thật. Sol High hậu kiểm ở Cổng Chốt Phiên.

### 3. TẦNG 2 (T2) — THI CÔNG KIẾN TRÚC LỚN (TERRA PLAN -> LUNA GÕ)
- **Phạm vi:** Tính năng mới, sửa >= 2 file, diff > 15 dòng, đụng chạm `watchdog`, `lock`, `semaphore`, `gateway`.
- **Quy trình 3 bước:**
  - *Bước 1 (Bản vẽ):* Terra High (`codex/gpt-5.6-terra-high`) lên plan 3–5s, chốt anchor $c==1$, soi edge cases.
  - *Bước 2 (Thi công):* Luna High (`codex/gpt-5.6-luna-high`) thi công trong Lồng Vô Trùng: <= 30 dòng, test focused.
  - *Bước 3 (Nghiệm thu):* Chạy `python D:/Taadaa/tools/cage_gate.py` (tối đa 2 vòng).

### 4. LÀN CỨU HỘ KHẨN CẤP (BREAK-GLASS)
- Khi >= 3 máy farm kẹt hoặc production dừng: Gemini được quyền hotfix trong 15 phút để thông đường trước.

### 5. CỔNG NGHIỆM THU CHỐNG BỆNH CỦA 2 MODEL
- **Chống Gemini báo cáo láo:** BẮT BUỘC Canary Gate trên máy/profile thật (ảnh `MEDIA:`, log ADB thật). Không nghiệm thu bằng mồm.
- **Chống Luna ngồi khóc:** Tước quyền từ chối (thấy dirty không được dừng; task rộng bắt buộc làm phần lõi <= 30 dòng và để lại 1 dòng `NOTE:`).
- **Chốt phiên:** `python D:/Taadaa/tools/closeout_gate.py` do Sol High chấm >= 85/100 mới được đóng phiên.
