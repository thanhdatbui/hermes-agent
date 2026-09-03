# In-Feed Ad / TopView Ad Triggers False "TikTok focus lost"

## Hiện tượng
- Bot/Runner dừng phiên với lý do: `TikTok focus lost` và trạng thái `GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`.
- Ảnh chụp màn hình cho thấy ứng dụng TikTok vẫn đang mở ở foreground tại tab Đề xuất (For You), nhưng hiển thị video quảng cáo thương hiệu (TopView/In-Feed Ad, ví dụ: La Roche-Posay).

## Nguyên nhân
- Video quảng cáo dạng này thường ẩn hoặc thay đổi cụm điều khiển tiêu chuẩn (Like, Comment, Share bên phải), khiến bộ phân loại màn hình (`classifier.py` / `safety.py`) không tìm thấy đủ marker của feed thông thường.
- Do không khớp với các pattern feed/popup chuẩn, `safety_check()` coi đây là trạng thái mất focus và kích hoạt dừng an toàn.

## Hướng xử lý
- Không can thiệp sửa tài khoản hay reset app/thiết bị vì TikTok không bị lỗi/crash hay checkpoint.
- Thực hiện vuốt (swipe) qua video quảng cáo để chuyển sang video feed tiếp theo.
