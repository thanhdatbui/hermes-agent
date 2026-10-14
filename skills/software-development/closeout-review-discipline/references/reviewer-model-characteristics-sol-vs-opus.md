# Reviewer Models in Closeout Gate: Sol High vs Opus Pool

## 1. Bản chất sự khác biệt giữa 2 Reviewer

Khi chạy thẩm định `closeout_gate.py` cho các repository của Phone Farm Taadaa:

### A. Sol High (`review` / `chatgpt-web/gpt-5.6-sol-high`)
- **Tư duy:** Thực dụng (Pragmatic), hiểu rõ ngữ cảnh tự động hóa thiết bị và công cụ nội bộ Farm (Phone Farm Internal Tooling).
- **Trọng tâm chấm:** Tính đúng đắn của logic, độ an toàn thiết bị, test coverage và xử lý timeout.
- **Mức điểm thường thấy:** **79 – 88 điểm**. Rất nhanh chóng phát hiện các lỗi bảo mật/vận hành cốt lõi và hướng dẫn sửa để đạt APPROVED.
- **Hạn chế duy nhất:** Chạy qua pool web cookie của OpenAI trên OmniRoute nên vào giờ cao điểm đôi khi bị nghẽn mạng gây timeout.

### B. Opus Pool (`ag-opus-pool`)
- **Tư duy:** Học thuật / Tiêu chuẩn Thung lũng Silicon (Academic Enterprise Purist).
- **Bệnh Over-Engineering:**
  1. Chê đường dẫn mặc định cá nhân Windows (`Path.home()` / `%APPDATA%`), đòi hỏi phải portable đa nền tảng tuyệt đối.
  2. Chê unit test dùng mock, đòi hỏi phải có integration test gọi live mạng thật.
  3. Đòi hỏi telemetry phải có Prometheus metrics, exporter, dashboarding cloud, canary deployment dù chỉ là script CLI chạy trên máy farm.
- **Mức điểm thường thấy:** Bị dìm xuống **62 – 72 điểm**, gây tắc nghẽn Closeout Gate đối với các script tiện ích đơn giản.

## 2. Quy tắc lựa chọn Reviewer chuẩn mực
1. **Mặc định Closeout Farm:** Ưu tiên **Sol High (`review`)**.
2. **Khi Sol High bị nghẽn timeout:** Tạm thời dùng `ag-opus-pool` nhưng phải chuẩn bị tâm lý code sẽ bị soi xét khắt khe theo chuẩn Enterprise (cần docstrings, type hints, hermetic tests không đụng file thật trên đĩa).
3. **Kỷ luật Git Pre-Push Hook:** Hook `hooks/pre-push.sh` chặn cứng mọi lệnh `git push` nếu entry gần nhất trong `gate_audit.jsonl` có `passed == false`. Không thể và không được tìm cách lách qua hook này khi Gate chưa APPROVED.
