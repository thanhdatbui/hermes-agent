# Cronjob LLM Hang vs Anti-Destructive Remediation Invariant

> Bối cảnh: Khi một cronjob chạy chế độ LLM (`no_agent: false`) bị timeout trên API provider dẫn đến kẹt gateway Hermes (`stuck on tool cronjob`), nghẽn luồng xử lý và gửi cảnh báo "No activity for 60 min".

## 1. Bản chất cơ chế gây nghẽn (RCA)
- Khi cronjob có `no_agent: false`, mỗi tick định kỳ runtime Hermes sẽ spawn một subagent/LLM session độc lập để xử lý prompt.
- Nếu model hoặc provider (OmniRoute, OpenRouter, direct upstream) bị treo socket, rate limit 429, hoặc exhaustion fallback chain:
  - Tiến trình LLM không trả về kết quả và ngậm cứng slot thực thi của tool `cronjob`.
  - Sau 3600 giây (60 phút), hệ thống phát cảnh báo:
    `⚠️ No activity for 60 min. If the agent does not respond soon, it will be timed out in 1 min.`
    `The agent appears stuck on tool cronjob (<N>s since last activity, iteration X/100).`
  - Tin nhắn của User gửi vào lúc này sẽ bị chặn hoặc drop do gateway dính timeout/stop.

## 2. Kỷ luật BẤT KHẢ XÂM PHẠM: Sửa Code (Fix), CẤM Phá Hoại (Anti-Destructive)
- **Hành vi phá hoại cấm tuyệt đối:**
  - Tuyệt đối CẤM Coordinator tự ý gọi `cronjob action='remove'` để xóa job của hệ thống sản xuất khi User yêu cầu sửa/điều tra lỗi ("Fix đi", "Tại sao treo").
  - Xóa job vận hành khi gặp lỗi bị coi là hành vi phá hoại hệ thống và trốn việc nghiêm trọng nhất.
- **Quy trình chuẩn hóa kỹ thuật:**
  1. **Khóa cứng `no_agent: true` (Autonomous Script Standard):**
     - Mọi watchdog/dispatcher/healer định kỳ phải chạy bằng script Python nền độc lập (`script='<tên_script>.py'`), KHÔNG thông qua agent loop/LLM.
     - Cập nhật an toàn: `cronjob(action='update', job_id='<id>', no_agent=True, script='<tên_script>.py')`.
  2. **Thực thi kiểm chứng O(1):**
     - Sau khi đã cập nhật `no_agent: true`, kích hoạt chạy thử đúng 1 lần: `cronjob(action='run', job_id='<id>')`.
     - Tuyệt đối CẤM trigger `cronjob action='run'` lặp đi lặp lại khi job vẫn đang ở trạng thái `no_agent: false` vì sẽ tiếp tục giam gateway vào vòng lặp timeout 60 phút mới.
