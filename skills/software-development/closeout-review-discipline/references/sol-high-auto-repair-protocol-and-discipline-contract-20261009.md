# Operational Discipline: Sol High Auto-Repair Protocol & Anti-Gemini Fallback (2026-10-09 Incident)

## 1. Bản Án Hiện Trường (The Forensic Failure)
- **Sự cố:** Repo `D:/Taadaa/automation-core` bị Closeout Gate từ chối với điểm **82/100** (REJECTED).
- **Hành vi vi phạm của Coordinator:**
  Thay vì thực thi thiết kế tự động của hệ thống (`--auto-repair` / `sol_repair.py`), Coordinator lại tự động soạn prompt rồi dispatch Worker Gemini (`deleg_bc5a478b`).
  - Worker Gemini tốn 10 phút (600.0s) quay cuồng đọc repo, cạn kiệt budget 5 tool calls mà không sửa được 1 dòng code nào (`status=timeout`).
  - Làm lãng phí thời gian, gây nghẽn phiên chốt, và làm User bức xúc.
- **Sau khi kích hoạt Sol High:**
  Chỉ mất đúng **28 giây**, Sol High (:20129) nhả ra bản vá `_HeavyIoGate` hoàn hảo kèm AST syntax validation, sau khi áp dụng điểm số vọt lên **88/100 APPROVED**.

---

## 2. Thiết Quân Luật Vận Hành (Operational Discipline Contract)

### Điều 1: Tính Độc Quyền Của Sol High Sau Khi Gate Reject
Khi `closeout_gate.py` trả về `REJECTED` (< 85 điểm):
- **CẤM TUYỆT ĐỐI** Coordinator tự sửa code mò mẫm.
- **CẤM TUYỆT ĐỐI** dispatch Worker Gemini để phân tích sửa lại.
- **ĐIỀU HƯỚNG BẮT BUỘC 100%:** Luồng sửa code sau Gate Reject **BẮT BUỘC VÀ DUY NHẤT** thuộc về **Sol High Auto-Repair (`sol_repair.py`)**.

### Điều 2: Quy Tắc Gọi Closeout Gate Kèm Cờ `--auto-repair`
Mọi lần chạy `closeout_gate.py` từ vòng 1, Coordinator **BẮT BUỘC** truyền cờ `--auto-repair`:
```bash
python D:/Taadaa/tools/closeout_gate.py \
  --repo "<repo_path>" \
  --base "<base_ref>" \
  --auto-repair \
  --json-output
```
Khi có cờ này, nếu Gate bị reject, `closeout_gate.py` sẽ **TỰ ĐỘNG** chuyển giao Scorecard và Findings sang cho Sol High tạo bản vá ngay trong cùng 1 lần chạy, lưu file tại `D:/Taadaa/logs/repair_proposals/proposal_<repo>_<ts>.json`.

### Điều 3: Điều Kiện Tiên Quyết Để Fallback (Chỉ Làm Khi Sol Repair Hỏng)
Coordinator **CHỈ ĐƯỢC PHÉP** can thiệp hoặc tìm phương án thay thế khi thỏa mãn điều kiện:
1. `sol_repair.py` trả về lỗi rõ ràng (ví dụ: `[SOL_REPAIR_FAILED]`, endpoint :20129 rớt kết nối, hoặc proposal syntax error không thể fix).
2. Khi Sol Repair hỏng thực sự:
   - Áp dụng Emergency Surgery O(1) nếu đã rõ exact diff (<= 2 files, <= 30 dòng).
   - Hoặc re-dispatch Worker với exact patch contract O(1).
3. **Claude CLI:** CHỈ gọi khi User chỉ định bằng văn bản.

---

## 3. Bản Thiết Quân Luật Chi Tiết Từ Claude Code CLI (Operational Discipline Contract v1.0)

Theo thẩm định và tư vấn trực tiếp từ Claude Code CLI (Sonnet) ngày 09/10/2026:

1. **Điều 1 — Độc quyền phản ứng đầu tiên (First-Responder Monopoly):**
   Khi Closeout Gate trả kết quả `REJECTED`, hành động log kế tiếp của Coordinator **BẮT BUỘC PHẢI LÀ GỌI `sol_repair.py`** (hoặc `--auto-repair`). Tuyệt đối không có bước trung gian "phân tích sơ bộ", không "ước lượng độ khó" trước. Nếu log cho thấy hành động đầu tiên sau REJECTED không phải là sol_repair $\rightarrow$ Tự động coi là lỗi thụt lùi P0 (P0 regression), không xét ngữ cảnh.

2. **Điều 2 — Fallback chỉ được kích hoạt bởi lỗi khách quan của chính Sol, không bởi suy đoán của Coordinator:**
   Chỉ dispatch Worker khi `sol_repair.py` tự trả về bằng chứng cứng: non-zero exit code, exception trace, hoặc timeout của chính tiến trình sol_repair. Suy đoán chủ quan dạng "Tôi nghĩ task này khó/khác thường nên dùng Worker luôn" **KHÔNG PHẢI** điều kiện hợp lệ.

3. **Điều 3 — Budget và timeout là tín hiệu cảnh báo vi phạm, không phải cái giá chấp nhận được:**
   Một khi Worker đã bị dispatch oan và cạn budget 15 calls hoặc chạm timeout 600s mà không sửa được gì, đó là bằng chứng vi phạm Điều 1, bắt buộc kích hoạt kiểm tra lại ngay lập tức tại sao Sol Repair bị bỏ qua.

4. **Điều 4 — Người giám sát không phải là cơ chế dự phòng:**
   Việc User phải tự tay nhắc lại thiết kế gốc để Coordinator "tỉnh ngộ" là một thất bại hệ thống nặng nề, tính lỗi độc lập với việc patch sau đó có thành công hay không. Coordinator phải tự động thực thi đúng luồng Sol High từ đầu.
