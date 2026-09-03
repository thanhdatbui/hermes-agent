# Auto-Recovery AI Architecture & Enforced Code-First Order (19/08/2026)

## 1. Bản chất phân định trách nhiệm trong Hệ Thống
1. **Producer (`automation_core.alerts.send_farm_machine_alert`)**:
   - Khi có máy dừng phiên/kẹt lỗi: Screencap, đóng dấu Banner Đỏ `[MAY XX] - HH:MM DD/MM`, gửi Telegram Message 1 (`Farm Alerts`).
   - Tự động spawn subprocess `ai_recovery.agent` (chặn khi chạy unit test bằng `PYTEST_CURRENT_TEST`).
   - Giữ nguyên màn hình và XML tại hiện trường lỗi, CẤM dọn app về Home trước khi recovery.

2. **AI Recovery Agent (`python_runner/ai_recovery/agent.py` & `vision_client.py`)**:
   - Dùng mô hình Vision thật `ag/gemini-3.7-flash-high` qua 9Router proxy (`http://127.0.0.1:20128/v1/chat/completions`).
   - Parse key từ `.env` bỏ qua dòng comment `#`.
   - Parse JSON từ model sạch sẽ, bóc tách Markdown code block ` ```json ... ``` `.
   - Default action khi không chắc chắn là `action_type: "none"` (CẤM default `"back"` mù quáng).

## 2. QUY TẮC BẮT BUỘC: CODE-FIRST ORDER (Vá Code Trước Khi Thao Tác Thiết Bị)
- **CẤM CHỮA CHÁY BẰNG LỆNH ADB TẠM THỜI MÀ BỎ QUA SỬA CODE**:
  - Prompt gửi lên AI Vision (`vision_client.py`) PHẢI ép chặt: Bất kỳ màn hình lạ nào (popup, live modal, search screen, product grid, survey...) BẮT BUỘC phải sinh ra đoạn `code_patch` và `target_file` tương thích với cấu trúc của repo (`feed_swipe_smoke.py` hoặc `benign_popup.py`).
  - Agent thực hiện: Phân tích ➔ Vá code vào repo ➔ Audit bằng `plan-review` ➔ Test chính hàm vừa vá lên máy kẹt tại hiện trường ➔ Pytest test suite ➔ Commit & Push Git ➔ Gửi Telegram Message 2 báo cáo chi tiết **Hướng sửa** & **Kết quả**.

## 3. Quản lý Cooldown Nhả Follow Riêng Từng Nick (Per-Account Isolation)
- Khi nick bị TikTok nhả nút follow sau cú vuốt kiểm tra (`pull-to-refresh`):
  - Ghi nhận `follow_failed = True` và `follow_failed_date = "YYYY-MM-DD"` vào riêng file state của nick đó: `follow_state_<machine>_row_<account_row_index>.json`.
  - Ở các phiên chạy sau cùng ngày, luồng Feed nuôi (`multi_machine_feed_session.py`) kiểm tra thấy nick đã dính nhả ➔ **Tự động SKIP bước Follow**, chỉ lướt Feed nuôi nick bình thường.
  - Các nick khác trên cùng máy đó (Row 1, Row 2, Row 4...) **hoàn toàn KHÔNG bị ảnh hưởng**, vẫn chạy lướt Feed và Follow bình thường.
  - Tự động reset cooldown khi sang ngày mới.

## 4. Các Quy Tắc Nhận Diện Màn Hình Mới Đã Bổ Sung
- **Popup Chính sách Live (`live_reward_policy_acknowledge`)**: Tap nút "Đã hiểu" (tọa độ tính toán hoặc $y \approx 1490$ trên màn 1080x1920) ➔ Chờ vài giây ➔ Tap X ($x=1020, y=78$) thoát phòng Live.
- **Trang Tìm Kiếm (`search_screen_back`)**: Nhận diện `tv_search_sug_word`, `zsc`, `bps` ➔ Gửi phím `BACK` để hạ bàn phím và đóng trang tìm kiếm về Feed.
- **Thẻ gợi ý kết bạn ("Người mà bạn có thể biết")**: Bấm nút **"Follow lại"** (`follow_back_suggestion`).
- **Lưới sản phẩm thương hiệu ("Vừa xem")**: Gửi phím `BACK` (`brand_product_grid_back`).
- **Popup quảng cáo Enfagrow A+ / CTA**: Bấm nút **"Đóng"** (`learn_more_dialog_dismiss`) hoặc swipe lướt qua.
