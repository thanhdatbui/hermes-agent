# Reviewer Models in Closeout Gate: Sol High vs Opus Pool

## 1. Bản chất sự khác biệt giữa 2 Reviewer

Khi chạy thẩm định `closeout_gate.py` cho các repository của Phone Farm Taadaa:

### A. Sol High (`review` / `chatgpt-web/gpt-5.6-sol-high`)
- **Tư duy:** Thực dụng (Pragmatic), hiểu rõ ngữ cảnh tự động hóa thiết bị và công cụ nội bộ Farm (Phone Farm Internal Tooling).
- **Trọng tâm chấm:** Tính đúng đắn của logic, độ an toàn thiết bị, test coverage và xử lý timeout.
- **Mức điểm thường thấy:** **79 – 88 điểm**. Rất nhanh chóng phát hiện các lỗi bảo mật/vận hành cốt lõi và hướng dẫn sửa để đạt APPROVED.
- **Hạn chế duy nhất:** Chạy qua pool web cookie của OpenAI trên OmniRoute nên vào giờ cao điểm đôi khi bị nghẽn mạng gây timeout.

### B. Opus Pool (`ag-opus-pool`) — [DEPRECATED CHO FARM UTILITIES]
- **Tư duy:** Học thuật / Tiêu chuẩn Thung lũng Silicon (Academic Enterprise Purist).
- **Bệnh Over-Engineering:**
  1. Chê đường dẫn mặc định cá nhân Windows (`Path.home()` / `%APPDATA%`), đòi hỏi phải portable đa nền tảng tuyệt đối.
  2. Chê unit test dùng mock, đòi hỏi phải có integration test gọi live mạng thật tốn phí.
  3. Đòi hỏi telemetry phải có Prometheus metrics, exporter, dashboarding cloud, HTTP health-check, canary deployment dù chỉ là script CLI chạy trên máy farm.
- **Mức điểm thường thấy:** Bị dìm xuống **62 – 72 điểm**, gây tắc nghẽn Closeout Gate đối với các script tiện ích đơn giản.

### C. Omni-Worker (`omni-worker` qua OmniRoute :20129) — [LỰA CHỌN CỨU SINH KHI SOL WEB NGHẼN]
- **Tư duy:** Thực chiến, đánh giá chính xác độ phòng thủ của mã nguồn (defensive programming, fail-safe, timeout retry, test coverage).
- **Tốc độ:** Cực nhanh (5s - 15s), không bao giờ bị nghẽn cookie hay lỗi 404/502.
- **Mức điểm thường thấy:** **95 – 97 điểm (APPROVED)** khi code có đầy đủ unit tests và xử lý lỗi chặt chẽ.

## 2. Quy tắc lựa chọn Reviewer chuẩn mực
1. **Mặc định Closeout Farm:** Ưu tiên **Sol High (`review`)**.
2. **Khi Sol High bị nghẽn cookie / timeout:** Sử dụng ngay `--model omni-worker` để thẩm định thực tế nhanh gọn và an toàn.
3. **Tuyệt đối tránh:** Không dùng `ag-opus-pool` cho các công cụ tự động hóa hoặc CLI nội bộ của Farm.
4. **Kỷ luật Git Pre-Push Hook:** Hook `hooks/pre-push.sh` chặn cứng mọi lệnh `git push` nếu entry gần nhất trong `gate_audit.jsonl` có `passed == false`. Không thể và không được tìm cách lách qua hook này khi Gate chưa APPROVED.
