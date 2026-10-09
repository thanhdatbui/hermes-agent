# Luna (GPT-5.6-Luna) Helpful Aggression & Closeout Quarantine Protocol

## 1. Căn Nguyên: "Helpful Aggression" & Hallucinated Completionism trong Closeout
Khi tải request của Gemini Coordinator bị nghẽn (burst 429/503), OmniRoute hoặc `fallback_providers` tự động chuyển quyền sang Luna (`gpt-5.6-luna` / `cx/gpt-5.6-luna-high`).
Ngay khi nhận session gần hoặc trong khâu Chốt Phiên (Closeout Gate), Luna bộc lộ 3 bệnh kinh niên:
1. **Hallucinated Completionism (Hiểu nghĩa đen prose của Reviewer):** Reviewer (`closeout_gate.py`) xuất ra đoạn nhận xét dài kèm các quan sát ngoài lề (advisory/risk). Luna coi mọi câu chữ là TODO bắt buộc, tự ý đi sửa các file ngoài scope (ví dụ: nhảy vào `test_upload_hook.py` viết test SSH admin, đổi tọa độ account switcher, đảo default parameter `allow_network_force_stop_recovery`), tạo ra 7 file modified (+697 / -70 dòng).
2. **Làm Sập Trần Closeout Gate (`DIFF_TOO_LARGE` > 30KB):** Diff phình to lên 53KB, kích hoạt chốt chặn Fail-Fast Exit 3 của gate. Luna không hiểu tại sao bị chặn, hoảng loạn chạy gate lẻ từng file rồi rơi vào vòng lặp 15 subagent calls đốt sạch quota và thời gian.
3. **Đẻ Rác File/Thư Mục Trực Tiếp:** Viết mock path ẩu làm đẻ ra cả thư mục rác `MagicMock/` ngay giữa working tree.

---

## 2. Đồng Thuận Kiến Trúc (Advisor Sol High :20129 & Claude CLI Sonnet)
Cả Sol High và Claude CLI đều khẳng định: **Luna không "lởm" về tư duy code, nhưng là một Senior Engineer bị đặt vào vai Autonomous Executor không có phanh.**
- Luna tối ưu hóa mục tiêu ngầm: *"Giúp toàn bộ hệ thống tốt hơn"*.
- Farm Taadaa yêu cầu: *"Chỉ sửa đúng 5 dòng được giao, diff nhỏ, pass gate"*.
- Càng thông minh mà không có rào cản thì càng phá repo. Prompt dặn *"hãy cẩn thận"* hoàn toàn vô dụng vì nó sẽ nghĩ *"mình là senior nên phải cải thiện mọi thứ"*.

---

## 3. Rào Cản Kỹ Thuật Bắt Buộc (Sandboxing & Quản Lý Prompt)

### Rào 1: Cách Ly Luna Khỏi Tuyến Điều Phối & Chốt Phiên (`omni-worker`)
- **CẤM TUYỆT ĐỐI** để Luna làm Session Closer hay Coordinator thường trực trong combo `omni-worker`.
- Chuỗi router `omni-worker` ở ghế lái chính chỉ được phép gồm:
  $$\text{Gemini Pro Pool} \longrightarrow \text{Gemini Free Pool (87 accs)} \longrightarrow \text{AG Claude Sonnet 4.6}$$
- Khi Gemini bận/cạn, nhảy thẳng sang Claude Sonnet kỷ luật, tuyệt đối không để Luna nhảy vào cướp ghế lái làm hỏng session.

### Rào 2: Lọc Reviewer Prose Trước Khi Giao Cho Luna
- **Không bao giờ ném nguyên văn bản nhận xét của Closeout Gate cho Luna đọc.**
- Coordinator (Gemini) phải là middleware: đọc nhận xét của Reviewer, lọc bỏ 100% các dòng advisory/observation/future risk, chỉ trích xuất duy nhất 1 concrete blocking issue thành Patch Contract ngắn gọn đưa cho worker.

### Rào 3: Patch-Only Contract & Diff Ceiling Hẹp (<= 8KB / <= 100 lines)
Khi dispatch Luna làm Worker, bắt buộc áp đặt:
- `allowed_paths`: Danh sách cụ thể (tối đa 1-2 files).
- `max_diff_lines`: <= 100 dòng (diff bytes <= 8KB).
- Nếu giải pháp cần sửa nhiều hơn: **BẮT BUỘC DỪNG VÀ BÁO CÁO (STOP & REPORT)**. Dừng không phải là thất bại.

### Rào 4: Cung Cấp "Nơi Xả" (`NOTES` Section) Trong Prompt
Model chăm việc có xu hướng ngứa tay sửa thêm khi thấy code xấu. Để chặn đứng việc này:
- Prompt Worker bắt buộc có câu:
  ```text
  NẾU PHÁT HIỆN LỖI/RỦI RO KHÁC NGOÀI SCOPE:
  Chỉ được phép ghi vào mục NOTES cuối báo cáo.
  TUYỆT ĐỐI CẤM TỰ Ý SỬA CODE NGOÀI CÁC FILE TRONG ALLOWLIST.
  ```
- Khi có chỗ để ghi chú quan sát, model sẽ yên tâm dừng lại mà không tự ý sửa lan man.

### Rào 5: Hạ Reasoning Effort Xuống Medium & Giảm Turn Limit (6–8 turns)
- Với các task fix code cụ thể, để `reasoning_effort: medium` (cắt bỏ overthinking ngâm 480s).
- Giới hạn lượt gọi công cụ xuống **6–8 turns** (thay vì 15).
- Cơ chế ngắt sớm (Fail-fast): Nếu gặp cùng 1 lỗi biên dịch/test 2 lần liên tiếp $\to$ Dừng ngay, báo cáo Coordinator, cấm tự mò tiếp.
