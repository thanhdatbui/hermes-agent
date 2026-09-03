# Autonomous AI Recovery via Hermes Telegram Session Bot (2026-08-19)

## 1. Bản Chất Kiến Trúc Producer - Consumer
- **Producer (`automation_core/alerts.py`):**
  - Chạy trên 80 máy Android (0 token LLM).
  - Khi máy dừng phiên: Chụp ảnh hiện trường, vẽ Banner Đỏ `[MAY XX] - HH:MM DD/MM`, gửi Tin nhắn 1 vào Telegram `Farm Alerts` (`-5373649734`).
  - **Bảo toàn hiện trường:** Tuyệt đối không bấm Home, giữ nguyên màn hình kẹt trên máy.
- **Consumer (Session Bot Hermes trong nhóm Farm Alerts):**
  - Nhận tin nhắn alert kèm ảnh.
  - Sử dụng Mắt Vision AI của session để đọc ảnh, suy luận giải pháp và điều phối quy trình gỡ lỗi tự hành.

## 2. Thứ Tự Thực Thi Khép Kín 5 Bước (Bắt Buộc)
1. **AI Đọc Ảnh & Suy Luận:** Mắt Vision đọc ảnh hiện trường. Kẹt ở bước nào (Login, OTP, Captcha, DOB, Profile, Thẻ bạn bè, Popup, Live, Survey...) thì suy luận giải pháp tại đúng bước đó (không ép máy về Feed). Nếu gặp ca khó/mơ hồ -> Tag hỏi operator.
2. **Viết Code / Bổ Sung Rule Vào Script Trước:** Mở file repo (`feed_swipe_smoke.py`, `benign_popup.py`...) encode rule/handler trước. Tuyệt đối CẤM tap tay hay bắn lệnh ADB thô trước rồi mới viết code sau vì làm mất hiện trường lỗi và không kiểm chứng được code.
3. **Chạy Chính Hàm Vừa Code Lên Máy Kẹt Để Test:** Kích hoạt hàm vừa viết chạy trực tiếp trên máy đang lỗi tại hiện trường để kiểm chứng máy tự vượt qua bước kẹt.
4. **Plan-Review Audit & Commit:** Xuất git diff gọi Model Plan-Review audit (bắt buộc nhận `VERDICT: APPROVED`) -> Chạy `pytest` xác nhận không có lỗi hồi quy -> Push Git `master` đồng bộ 80 máy.
5. **Reply Báo Cáo Vào Nhóm Farm Alerts:**
   ```text
   🛠️ [AI AUTO-RECOVERY - MÁY XX]
   • Hướng sửa: <Giải thích lỗi kỹ thuật & logic đã vá vào script>
   • Kết quả: <Kết quả test thực tế máy đã vượt qua bước kẹt và tiếp tục luồng>
   • (Nếu đúng ý bạn im lặng bỏ qua, cần sửa cách khác hãy nhắn lại)
   ```

## 3. Cấu Hình Channel Overrides
- Nhóm `Farm Alerts` (`chat_id: -5373649734`) được gắn `system_prompt` chuyên trách trong `config.yaml` của Hermes Gateway.
- Khi nhận tin nhắn `🚨 [MÁY XX] DỪNG PHIÊN` kèm ảnh -> Bot tự động kích hoạt lượt xử lý theo đúng quy trình 5 bước.
