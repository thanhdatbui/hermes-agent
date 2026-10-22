# Strike-3 Reviewer Hand-off & Claude Quota Guard Collision Protocol

## 1. Bản Chất Kiến Trúc: Phân Biệt Sol Review vs Sol Repair
- **Sol Review (`closeout_gate.py`)**: 
  - Là Reviewer thẩm định chất lượng code độc lập.
  - Theo chính sách User chốt: **Reviewer Tier 0 bắt buộc dùng Sonnet CLI (`--model claude-sonnet`)**, fallback Sol Web (`:20129`) khi offline. Khi User nói "bỏ Sol review", nghĩa là chuyển gate review sang Sonnet CLI, KHÔNG dùng Sol để chấm điểm.
- **Sol Repair (`sol_repair.py`)**:
  - Là công cụ First-Responder độc quyền tạo patch proposal O(1) khi `closeout_gate.py` trả về `REJECTED` ở Strike 1 & 2.
  - Sử dụng model `gpt-web-sol` qua port `:20129` để đọc scorecard và đề xuất diff tối thiểu.

## 2. Chu Trình Strike-3 Reviewer Hand-off
Khi `closeout_gate.py` từ chối 3 lần liên tiếp trên cùng một `scope_hash` (Strike 3):
1. **Dừng toàn bộ:** Coordinator, Worker thông thường và Sol Repair BẮT BUỘC DỪNG MỌI HÀNH ĐỘNG sửa code / suy đoán mò mẫm.
2. **Kích hoạt Hand-off:** Ghi cờ `handoff_lock_active.json` và bàn giao quyền chỉnh sửa trực tiếp cho Reviewer:
   - **Tier 1 (Ưu tiên):** Claude CLI Reviewer (`python D:/Taadaa/tools/claude_worker.py --role reviewer`).
   - **Tier 2 (Fallback):** Agy CLI Reviewer (`ag_cli.py fix`).
3. **Phạm vi khóa cứng (Scope-Locked):** Reviewer chỉ được phép can thiệp đúng các file trong danh sách `--files` của lần review gần nhất.

## 3. Xử Lý Va Chạm Quota Guard (Claude Quota Guard Collision)
Khi gọi Claude CLI trong pha Reviewer Hand-off mà gặp lỗi:
```text
⛔ [CLAUDE_QUOTA_GUARD_BLOCKED]
Lệnh gọi Claude CLI bị chặn để bảo vệ hạn mức tài khoản:
  • Quota 5 giờ: 85.0% (ngưỡng tối đa: 85.0%)
  • Quota tuần : 47.0% (ngưỡng tối đa: 90.0%)
```

### Kỷ luật bắt buộc của Coordinator:
1. **CẤM TỰ Ý BYPASS:** Tuyệt đối không tự ý gán `CLAUDE_USER_APPROVED=1` hoặc tự chạy `claude_quota_guard.py allow` nếu User chưa phê duyệt rõ ràng.
2. **CẤM DÙNG CLARIFY BỪA BÃI NẾU BỊ KHÓA:** Trong thời gian Hand-off Lock active, công cụ `clarify` có thể bị chặn bởi Hard Gate. Coordinator phải trình bày trực diện trong tin nhắn phản hồi thông thường.
3. **CẤU TRÚC BÁO CÁO 3 ĐIỂM RÕ RÀNG:**
   - **Hiện trạng kỹ thuật:** Báo cáo rõ code đã sửa gì, test suite pass bao nhiêu (ví dụ: 72/72 passed).
   - **Lý do dừng:** Nêu rõ chạm ngưỡng bảo vệ 85% và thời gian reset dự kiến (ví dụ: 03:49 AM).
   - **3 Phương án hành động cho User:**
     * *Phương án 1 (Khuyên dùng):* User cấp quyền tạm thời (`python D:/Taadaa/tools/claude_quota_guard.py allow 30`) để chạy nốt lần hand-off cuối.
     * *Phương án 2:* Giữ nguyên diff sạch và test pass, dừng phiên chờ sau giờ reset quota để chốt gate.
     * *Phương án 3:* Chốt phiên đặc cách nếu User xác nhận không cần Reviewer chấm tiếp.
