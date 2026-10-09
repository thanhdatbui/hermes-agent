# User-Locked Devices Teardown on Session Close (2026-09-25)

## 1. Quy tắc Tự động Giải phóng Lock khi Chốt phiên
- **Vấn đề:** Trong phiên làm việc, User yêu cầu can thiệp khẩn cấp trên một số máy (ví dụ Máy 52), Agent thiết lập `OPERATOR_PREEMPT` và giữ lock `pinned=True`, `user_authorized=True` để miễn nhiễm hoàn toàn với cronjob dọn dẹp/healer.
- **Kỷ luật vận hành:** User không cần và không muốn phải tự gõ lệnh `release` thủ công. Trách nhiệm dọn dẹp thuộc về bước Closeout Gate của phiên.
- **Quy trình khi nhận lệnh Chốt phiên (`chốt phiên`, `đóng phiên`, `kết thúc phiên`):**
  1. Chạy thẩm định độc lập `closeout_gate.py` đạt score >= 85.
  2. Git commit & push.
  3. **Teardown Device Locks:** Quét thư mục `~/.codex/device-locks/` và dọn dẹp/release các lock do phiên làm việc của User tạo ra (đặc biệt là lock `project='operator_intervention'` hoặc lock máy can thiệp khẩn cấp), đưa app TikTok về HOME (`input keyevent 3`) và trả máy về trạng thái rảnh cho scheduler farm.
