# Strike 3 Reviewer Hand-off & Claude CLI Model Invariant

## 1. Bối cảnh & Nguyên tắc Tối Cao
Khi Closeout Gate gặp tín hiệu `[REVIEWER_HANDOFF_TRIGGERED: 3 consecutive rejections reached...]` theo quy định tại `D:/Taadaa/HERMES_SUBAGENT_RULES.md` (`3-STRIKE-REVIEWER-HANDOFF-2026-10-08`), Coordinator/Worker/Sol Repair BẮT BUỘC DỪNG tự sửa và chuyển giao bàn phím trực tiếp cho Claude CLI đóng vai trò Reviewer-with-write-access.

## 2. Invariant Model Claude CLI (BẮT BUỘC)
- **Model chuẩn duy nhất:** **Sonnet 5.5** (chỉ định cờ `--model sonnet`).
- **CẤM TUYỆT ĐỐI:** Không bao giờ được gọi tên, suy diễn hay ghi vào log/báo cáo là "Sonnet 3.5". Trong toàn bộ hệ sinh thái Phone Farm Taadaa, Claude CLI hiện đại luôn sử dụng Sonnet 5.5. Bất kỳ sự nhầm lẫn nào về model 3.5 cũ đều bị coi là lỗi ngớ ngẩn gây phản cảm nghiêm trọng cho người dùng.

## 3. Lệnh Điều Hành Chuẩn
Trước khi gọi Claude CLI, kiểm tra quota an toàn:
```bash
python D:/Taadaa/tools/claude_quota_guard.py status
# Đảm bảo Quota 5h < 85% và Quota Weekly < 90%
```

Lệnh thực thi background với event-driven wakeup:
```bash
claude -p "$(< /d/Taadaa/logs/claude_handoff_prompt.txt)" \
  --model sonnet \
  --allowedTools "Read,Edit,Write,Bash" \
  --dangerously-skip-permissions \
  --max-turns 15
```
*Lưu ý:* Bắt buộc chạy background với `notify_on_complete=True` và `timeout=300` trong công cụ `terminal` của Hermes để tránh timeout foreground 60s.

## 4. Cấu Trúc Prompt Giao Quyền (`claude_handoff_prompt.txt`)
Prompt bàn giao phải chứa đủ 5 phần:
1. **Vai trò:** Reviewer-with-write-access theo `HERMES_SUBAGENT_RULES.md`.
2. **Scope Lock Allowlist:** Danh sách chính xác các file được phép sửa (tuyệt đối không đụng file ngoài scope).
3. **Mục tiêu của Operator:** Nêu rõ kỳ vọng nghiệp vụ (ví dụ: gỡ bỏ nghỉ ngẫu nhiên, mở upload, v.v.).
4. **Findings cần khắc phục:** Trích xuất verbatim nhận xét của Reviewer (thiếu telemetry, thiếu regression test, thiếu fail-closed gate).
5. **Acceptance Test:** Lệnh pytest cụ thể phải pass 100% trước khi kết thúc.
