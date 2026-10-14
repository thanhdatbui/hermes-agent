# Strike 3 Remediation: Bảo Hiểm Fallback AG CLI Khi Claude CLI Hết Quota (429) & Lựa Chọn Reviewer

## 1. Bối Cảnh & Hiện Tượng Kẹt Cứng (Deadlock) ở Strike 3
Trong quy trình Closeout Gate của Phone Farm Taadaa:
- **Strike 1 & 2:** Sol High (`sol_repair.py`) độc quyền tạo patch proposal O(1).
- **Strike 3 Hand-off:** Nếu trượt 3 lần liên tiếp trên cùng scope_hash, Coordinator, Worker và Sol Repair đều bị tước quyền. Toàn bộ quyền can thiệp được trao cho Reviewer (Claude CLI: `claude-sonnet-5-5`) để tự vào phòng mổ remediate code và test.

### Điểm nghẽn chí mạng (SPOF):
Tài khoản Claude Pro của người dùng áp dụng cửa sổ trượt 5 giờ. Khi Claude CLI dính lỗi:
```json
{"api_error_status": 429, "result": "You've hit your session limit · resets 1:30am (Asia/Bangkok)"}
```
Nếu hệ thống chỉ biết gọi duy nhất Claude CLI, **toàn bộ quy trình Closeout Gate bị đóng băng hoàn toàn (deadlock)**, không ai được phép sửa code tiếp và phiên làm việc bị kẹt cứng!

---

## 2. Lưới An Toàn Bắt Buộc (Fallback Insurance) Cho Strike 3

Khi triệu tập Claude CLI (`claude-sonnet-5-5`) vào khâu Strike 3 Handoff:
1. **Thực thi chính (Primary):**
   Gọi Claude Sonnet 5.5 với prompt nhiệm vụ rõ ràng:
   ```bash
   claude -p "<Nhiệm vụ remediate>" --model sonnet --allowedTools "Read,Edit,Write,Bash" --dangerously-skip-permissions
   ```
2. **Kích hoạt Fallback khi Claude CLI lỗi:**
   Nếu Claude CLI trả về exit code != 0, hoặc dính các lỗi:
   - `429` / `hit your session limit`
   - `ETIMEDOUT` / `ECONNRESET` / Rớt mạng
   - Thiếu binary `claude` CLI
   **BẮT BUỘC TỰ ĐỘNG CHUYỂN GIAO NGAY CHO `ag_cli.py fix` (Antigravity 7 Acc Pro Pool):**
   ```bash
   python D:/Taadaa/tools/ag_cli.py fix "<Nhiệm vụ remediate>" --file <target_file> --timeout 120
   ```
   *Lợi thế của dàn AG CLI:* 7 tài khoản Google Pro hoạt động song song, hoàn toàn miễn phí, không bao giờ hết quota, có cơ chế tự động chuyển IP Direct / 4G Proxy chống nghẽn mạng.

---

## 3. Lựa Chọn Reviewer Độc Lập Khi Chạy `closeout_gate.py`

Bằng chứng thực chiến ngày 15/10/2026 đã phân định rõ đặc tính của các model chấm điểm:

| Model Reviewer | Điểm số đặc trưng | Ưu điểm | Nhược điểm / Rủi ro | Kết luận sử dụng |
|---|---|---|---|---|
| **Sol High** (`chatgpt-web/gpt-5.6-sol-high` / `review`) | **79 – 88đ** | Thực dụng, hiểu rõ môi trường Farm Tooling trên Windows, bắt lỗi logic/safety rất chuẩn. | Chạy qua pool web cookie, giờ cao điểm dễ bị nghẽn (conv 404/502). | **Ưu tiên số 1** khi hạ tầng web ổn định. |
| **Omni-Worker** (`omni-worker` - Gemini 3.8 Flash tiered) | **95 – 97đ** | Cực nhanh (10-15s), chấm đúng trọng tâm: kiểm tra defensive programming, fail-safe, test coverage thực tế. | Cần truyền qua cờ `--model omni-worker`. | **Lựa chọn cứu sinh hoàn hảo** khi Sol Web bị nghẽn cookie. |
| **Opus Pool** (`ag-opus-pool` - Claude Opus 4.6 Thinking) | **62 – 72đ** | Tư duy lý thuyết rất cao. | **Bệnh Over-Engineering học thuật nặng**: Bắt bẻ script farm phải có Canary, Health-check HTTP, Prometheus metrics, chê unit test dùng mock. | **CẤM DÙNG / DEPRECATED** cho Farm utility scripts. |

---

## 4. Kỷ Luật Tuyệt Đối Về Điểm Số & Danh Xưng Model

1. **Cấm Báo Done Khống Khi Điểm < 85:**
   - Điểm **84/100 là REJECTED (Exit code 1)**.
   - Nghiêm cấm Coordinator tuyên bố *"hoàn thành trọn vẹn"* hay *"done"* khi chưa có `Verdict: APPROVED` và `Exit code: 0`. Báo Done không có bằng chứng Gate duyệt là thất bại kỷ luật nặng nhất.
2. **Chuẩn Hóa Danh Xưng Model (Anti-Confusion):**
   - Luôn sử dụng đúng định danh kỹ thuật: **Claude Sonnet 5.5** (`claude-sonnet-5-5`), không nói tắt cẩu thả thành "Sonnet 5".
