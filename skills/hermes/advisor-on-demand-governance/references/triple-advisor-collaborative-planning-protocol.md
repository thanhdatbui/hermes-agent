# Triple Advisor Collaborative Planning Protocol (Gate B Multi-Model Deliberation)

## 1. Context & Architecture Consensus
- **Thực trạng Pipeline (`unified_patch_pipeline.py` & `gate_b_planner.py`)**:
  - Ban đầu chạy Fallback tuần tự: Gemini Web (Argon 4 Pool :20129) -> Sol Worker (`gpt-web-sol` :20129) -> Claude CLI (`claude -p`).
  - Hạn chế: Mô hình đầu tiên trả về anchor `count == 1` sẽ được chọn ngay mà không qua phản biện chéo (cross-examination).
- **Hội đồng 3 Cố vấn (Sol, Gemini, Claude) ngày 2026-11-01 đã bỏ phiếu đồng thuận (3/3) chọn: P3 (Dynamic)**.
- **Chỉ thị Tối cao từ User (Production Invariant - Cập nhật 2026-11-01)**:
  1. **100% MỌI TASK ĐỀU TRIỆU TẬP HỘI ĐỒNG (CẤM SKIP COUNCIL)**: Không dùng Fast Path bỏ qua Hội đồng. Mọi lượt lập plan đều bắn song song cả 3 bên.
  2. **PHÂN BỔ MODEL & TIMEOUT**:
     - 🔵 **Gemini Argon**: `:20129` `gemini-web` Argon 4 Pool (Timeout 90s).
     - 🟣 **Claude Sonnet**: Local CLI `claude --model sonnet -p` (Timeout 90s). Không dùng Haiku; nâng lên Sonnet để đảm bảo chất lượng tư duy phản biện.
     - 🟢 **Sol Web**: `:20129` `gpt-web-sol` (Timeout 90s).
  3. **THUẬT TOÁN CHỌN PLAN CHIẾN THẮNG (CÁCH D - HYBRID CONSENSUS)**:
     - *Bước 1 (Lọc nhóm đa số)*: Gom các plan theo vị trí/vùng hàm trong file (`_compute_plan_metric`). Nếu có >= 2 con trùng vị trí -> chọn nhóm đa số (loại trừ ngay con bị ảo giác lệch vị trí).
     - *Bước 2 (Tối ưu diff & Thứ tự ưu tiên)*: Trong nhóm đa số, chọn con có numstat nhỏ nhất. Nếu bằng nhau, áp dụng thứ tự ưu tiên chuẩn của User: **Argon (Gemini) -> Claude Sonnet -> Sol Web**.
  4. **BẮT BUỘC BÁO CÁO MINH BẠCH TIẾN ĐỘ ĐỒNG THUẬN CHO USER**: Kết quả đồng thuận phải xuất ngắn gọn tình trạng của từng con (e.g. `Argon: OK, Claude Sonnet: OK, Sol: OK -> ĐỒNG THUẬN 3/3 (Chọn gemini)`) trong `planner` và report pipeline để User biết chính xác từng model có đang hoạt động tốt hay không.

---

## 2. Đặc tả Kiến trúc Hội Đồng 3 Cố Vấn Thực Thi (Production Council Engine)

### A. Triệu tập Đồng thời & Cơ chế Báo cáo Minh bạch
- **Cơ chế triệu tập**: Chạy đa luồng song song qua `concurrent.futures.ThreadPoolExecutor(max_workers=3)`:
  * 🔵 **Gemini Argon**: `:20129` `gemini-web` Argon 4 Pool (Timeout 90s).
  * 🟣 **Claude Sonnet**: Local CLI `claude --model sonnet -p` (Timeout 90s).
  * 🟢 **Sol Web**: `:20129` `gpt-web-sol` (Timeout 90s).
- **Thẩm định cơ học độc lập**: Từng proposal của 3 bên đều phải qua cổng kiểm tra `validate_plan()`: `old_string` xuất hiện duy nhất 1 lần (`count == 1`) trên file thật.
- **Quy tắc chọn Plan ưu tiên (Cách D)**:
  * Lọc nhóm đa số trùng vị trí code/hàm để loại bỏ ảo giác.
  * Trong nhóm đa số: chọn con có numstat nhỏ nhất; tie-break theo thứ tự ưu tiên: **Gemini Argon -> Claude Sonnet -> Sol Web**.
  * Ghi nhận `council_details` đầy đủ vào `plan.json` gồm latency, edits_count, status của từng con.

### B. Quy tắc Biểu quyết & Quorum Suy Giảm (Degraded Quorum)
| Trạng thái Hội đồng | Cơ chế biểu quyết | Báo cáo hiển thị User | Hành động Pipeline |
| :--- | :--- | :--- | :--- |
| **Đầy đủ 3/3** | Cả 3 bên đều pass `validate_plan()`, 0 VETO | `Argon: OK, Claude Sonnet: OK, Sol: OK -> ĐỒNG THUẬN 3/3 (Chọn gemini)` | Sinh `plan.json`, chuyển S2 (Patch). |
| **Suy giảm 2/3** *(1 bên timeout/429/invalid)* | Chọn proposal hợp lệ từ bên thành công | `Argon: OK, Claude Sonnet: OK, Sol: TIMEOUT -> ĐỒNG THUẬN 2/3 (Chọn gemini)` | Sinh `plan.json`, ghi log DEGRADED. |
| **Suy giảm khẩn cấp 1/3** *(2 bên lỗi/chậm)* | Lấy proposal duy nhất pass validation để cứu pipeline | `Argon: OK, Claude Sonnet: FAIL, Sol: TIMEOUT -> SUY GIẢM KHẨN CẤP 1/3 (Chọn gemini)` | Sinh `plan.json`, cứu nguy pipeline. |
| **Bại liệt (0/3)** *(Cả 3 bên đều hỏng)* | **Fail-closed**, tuyệt đối CẤM tự PASS | `Argon: FAIL, Claude Sonnet: FAIL, Sol: FAIL -> THẤT BẠI 0/3` | Trả về REJECTED, pipeline dừng an toàn. |

### C. Luật Phủ Quyết (Veto / P0 Invariant)
- Bất kỳ Advisor nào phát hiện lỗi nghiêm trọng (vi phạm vùng cấm, breaking interface, hồi quy tiềm ẩn, rủi ro bypass guard) và giơ cờ **P0 / VETO** thì Plan đó **bị bác bỏ ngay lập tức**, kể cả khi 2 bên còn lại đồng ý.

---

## 3. Bài học Triển khai Kỹ thuật (Technical Implementation Notes)
1. **Claude CLI Invocation**:
   - Khi gọi tư vấn hoặc phản biện ngắn từ Claude, dùng trực tiếp lệnh in `claude -p "<prompt>"` (hoặc truyền qua `stdin` nếu prompt dài).
   - Tránh gọi qua `claude_worker.py --role reviewer` cho các turn phản biện tức thời vì wrapper này chạy multi-turn tương tác và có thể cắn vào quota / timeout vòng lặp.
2. **Schema & Anchor Invariant**:
   - Mọi bản Patch Plan do Hội đồng chốt bắt buộc phải tuân thủ nghiêm ngặt schema JSON:
     `{"edits": [{"file": "<path>", "old_string": "<exact>", "new_string": "<exact>"}]}`.
   - Bắt buộc kiểm tra `count == 1` trên file thật trước khi trả về.
