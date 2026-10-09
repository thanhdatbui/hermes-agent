# Benchmark Tournaments & Routing Analysis: Luna vs Terra vs Sol (27/09/2026)

## 1. Hierarchy & Năng lực thực tế
- **Sol (`chatgpt-web/gpt-5.6-sol-high` qua OmniRoute :20129)**: Top 1 về System Architecture, bóc tách edge cases sâu và audit gatekeeper. Tuy nhiên phản hồi chậm (~18-30s), chỉ chạy trên Web Pool (không hỗ trợ Native Tool Calling của Codex/Hermes subagent), KHÔNG thể làm worker hay coordinator, chỉ làm Planner ca khó và Giám khảo Closeout Gate.
- **Terra (`codex/gpt-5.6-terra-high` / `medium`)**: Top 2 (nằm giữa Sol và Luna). Mạnh hơn Luna về tư duy kiến trúc/logic hệ thống, nhanh và nhẹ hơn Sol rất nhiều (~3-5s). Chỉ có trên Codex Pool (không có trong pool `chatgpt-web`).
- **Luna (`codex/gpt-5.6-luna-high` / `medium`)**: Thợ vặn ốc cú pháp chuẩn xác từng chi tiết, ít lỗi syntax/typing. Tuy nhiên tư duy kiến trúc bao quát kém, dễ bị "tê liệt phòng thủ" (refusal khi gặp dirty repo) hoặc over-engineering nếu thả rông. Phải nhốt trong **Lồng Vô Trùng** (`cage_gate.py`, budget <= 30 dòng, 1 file, 1 focused test).

## 2. Vì sao CẤM bắt Sol lên plan cho MỌI task? (Claude CLI Advisory)
1. **Lãng phí & nghẽn Gateway**: Task vặt, đọc log, sửa hằng số mất 5 giây mà bắt Sol lên plan mất 20 giây sẽ làm đơ gateway và phình blast radius.
2. **Task đọc/khảo sát (Investigate)**: Không cần plan, cứ đọc rồi báo cáo.
3. **Chỉ dùng Sol Plan cho**: Logic code đa tiến trình, watchdog, lock, scheduler, hoặc khi cage_gate fail 2 lần.

## 3. Kiến trúc 2 Làn (Fast Lane & Standard Lane)
- **Fast Lane (Gemini Coordinator tự làm O(1))**:
  - Đọc log, inspect thiết bị farm, check proxy, bật/tắt script.
  - Sửa hằng số cấu hình <= 60 ký tự (port, timeout).
- **Standard Lane (Worker trong Lồng Vô Trùng)**:
  - Task sửa code 1 file -> Giao thẳng cho Worker (Terra hoặc Luna) thi công trong Lồng Vô Trùng.
  - Nghiệm thu bằng `python D:/Taadaa/tools/cage_gate.py --target-file <file> --test-cmd "<test>" --base <SHA>`.
- **Escalate lên Sol**:
  - Khi đụng file nhạy cảm: `watchdog`, `lock`, `gateway`, `semaphore`.
  - Hoặc khi `cage_gate.py` reject 2 lần liên tiếp.
  - Chốt phiên: `python D:/Taadaa/tools/closeout_gate.py` (Sol chấm điểm >= 85 mới APPROVED).

## 4. Kết quả Tournament 15 trận thực chiến (Luna vs Terra)
Đánh giá năng lực làm Worker trong Lồng Vô Trùng do Sol High (`chatgpt-web/gpt-5.6-sol-high`) chấm độc lập:
- **Bán kết 1 (Luna High vs Luna Medium)**:
  - T1 (UI Drift): Medium thắng (91.0 vs 93.0) — patch regex text ngắn hơn, không thêm logic thừa.
  - T2 (Reconcile Watchdog): Medium thắng (91.0 vs 93.0) — bám sát đúng 1 điều kiện bỏ qua máy fail.
  - T3 (Hotmail Clock Skew): High thắng áp đảo (94.0 vs 86.0) — xử lý timezone UTC vs Local cực chuẩn, Medium sót biên 5 phút.
  - T4 (GPM Teardown `finally`): High thắng (92.0 vs 88.0) — bọc `finally` toàn diện cả exception cấp executor.
  - T5 (Popup Misclick): High thắng (92.0 vs 88.0) — xử lý đúng cả 2 nhánh (nút 'Đóng' và fallback tọa độ).
  -> **Vô địch Luna: `codex/gpt-5.6-luna-high`** (460.0 vs 448.0 điểm).
- **Bán kết 2 (Terra High vs Terra Medium)**:
  - T1: Medium thắng (91.0 vs 93.0).
  - T2: High thắng áp đảo (92.0 vs 78.0) — Medium bị trừ nặng vì đổi signature hàm.
  - T3: High thắng (94.0 vs 88.0) — xử lý skew tolerance tốt hơn.
  - T4: High thắng (93.0 vs 91.0).
  - T5: Medium thắng (86.0 vs 89.0).
  -> **Vô địch Terra: `codex/gpt-5.6-terra-high`** (456.0 vs 439.0 điểm).
- **Chung kết Tối cao (Luna High vs Terra High)**:
  - T1 (TikTok UI Drift): **Terra High thắng** (94.0 vs 96.0) — thiết kế fallback mượt mà, code sạch hơn.
  - T2 (Watchdog Reconcile): **Luna High thắng** (92.0 vs 84.0) — bản chất "thợ vặn ốc chuẩn mực", sửa đúng 3 dòng `if all_follows[m].get("follow_failed"): continue`, không refactor ngoài lề; Terra High bị trừ điểm do xu hướng over-engineering refactor dict comprehension.

## 5. Khuyến nghị lựa chọn Worker (Luna High vs Terra High)
- **Cả 2 nhánh HIGH đều vượt trội hơn MEDIUM** ở các ca khó đòi hỏi tính chuẩn xác về logic thời gian/bảo vệ lỗi (460 vs 448 và 456 vs 439).
- **Khi cần Worker tuyệt đối không refactor bậy, chỉ vặn đúng ốc chỉ định**: Chọn **`codex/gpt-5.6-luna-high`**.
- **Khi cần Worker thông minh hơn, tự hiểu bug logic rộng hơn một chút**: Chọn **`codex/gpt-5.6-terra-high`**.
