# Unified Gate Pipeline & Windows CLI Length Enforcement (2026-10-22)

## 1. Bẫy Windows CLI Length Limit: `The command line is too long`

### Hiện tượng:
Khi chạy `dispatch_worker.py` có kích hoạt `skill_injector.py`, subprocess gọi `claude_worker.py` hoặc `ag_cli.py` bị văng lỗi ngay lập tức:
```text
The command line is too long.
[DISPATCH] Haiku Attempt 1 failed (NO_DIFF) -> Haiku Attempt 2
The command line is too long.
[DISPATCH] All worker attempts failed.
```

### Nguyên nhân gốc (Root Cause):
Trên Windows, hàm API Win32 `CreateProcessW` áp đặt giới hạn cứng độ dài chuỗi dòng lệnh là **8.191 ký tự**.
Khi `inject_skill_context` dùng `max_context_chars=15000` nhồi nhiều skill cùng lúc (VD: 5 skills chiếm 14.423 ký tự) vào argument dòng lệnh `sys.argv`, Windows từ chối tạo tiến trình và trả về lỗi trên.

### Khắc phục:
1. Trong `dispatch_worker.py`: Hạ trần `max_context_chars=2500` khi nhồi argument dòng lệnh, đảm bảo tổng chiều dài command luôn $< 4000$ ký tự (an toàn dưới 8.191).
2. Thêm tham số `--no-skill-injection` vào `dispatch_worker.py` để các bộ điều phối programmatic (như `gate_pipeline.py` hay test runner) có thể tắt injection tự động khi đã có context xác định.

---

## 2. Giao Thức Cơ Học 3 Cổng: `gate_pipeline.py`

### Động lực:
Hai sự cố gần đây cho thấy nếu để Coordinator tự tay gọi rời rạc Gate A $\rightarrow$ Gate B $\rightarrow$ Worker $\rightarrow$ Gate C:
1. **TikTok Rename Incident:** Coordinator tự đọc và tự sửa 395 dòng trên 3 files, sau đó commit với nhãn dối trá `[L2-surgery]` (quy định L2 tối đa $\le 30$ dòng, $\le 2$ files).
2. **Warcraft Incident:** Coordinator tự gọi `claude_worker.py --role planner`, copy đoạn text markdown thủ công rồi nhồi vào `ag_cli.py fix` mà không hề qua xác thực mật mã HMAC của Gate B.

### Giải pháp `gate_pipeline.py`:
Đóng gói quy trình thành **1 lệnh duy nhất**:
```bash
python D:/Taadaa/tools/gate_pipeline.py \
  --file <target_file> \
  --goal "<goal>" \
  --evidence-source <path_or_cmd> \
  --acceptance-cmd "<test_command>"
```

### Quy trình tự động bên dưới:
- **Gate A**: Chốt hiện trường bằng `plan_exec_gate.py A`, kiểm tra file/cmd/ocr/log claim.
- **Gate B**: Ký `plan.json` có HMAC bí mật, xác nhận scope $\le 2$ files, $\le 30$ dòng, có lệnh rollback rõ ràng.
- **Gate C**: Gọi `dispatch_worker.py` thi công theo plan, sau đó chạy `plan_exec_gate.py C` để đo diff thật và chạy acceptance test.

### Kỷ luật "Không khóc lóc":
- Trả về JSON 1 dòng: `{"status": "FAIL", "failed_gate": "...", "error": "...", "next_action": "..."}`.
- Có hành động khắc phục cụ thể (`next_action`), cấm tuyệt đối sinh văn mẫu xin xỏ clarify hoặc đóng băng session.
