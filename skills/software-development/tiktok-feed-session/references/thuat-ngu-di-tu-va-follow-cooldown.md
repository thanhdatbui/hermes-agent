# Quy tắc giải mã ngữ cảnh câu hỏi Farm & "Đi tù"

## 1. Thuật ngữ vận hành: "Đi tù"
- Khi User hỏi về tài khoản nuôi TikTok "Đi tù" / "Bị đi tù gần hết rồi à":
  - **KHÔNG PHẢI** hỏi về nick bị cấm/ban/suspend hay checkpoint đăng nhập (văng nick).
  - **CHÍNH XÁC LÀ**: Nick bị TikTok phạt chặn hành động Follow (nhả follow / shadowban tính năng follow / `FOLLOW_FAILED` / `follow-released-daily-cooldown`).
  - Khi dính lỗi này, TikTok cho phép lướt feed, thả tim bình thường nhưng bấm follow thì không tăng số hoặc bị nhả lại sau vài giây.

## 2. Kiểm tra nhanh hiện trạng "Đi tù" của một phiên nuôi acc
- Kiểm tra báo cáo Follow trong artifact:
  - File `follow_result.json` của các máy trong thư mục run: `D:/Taadaa/runtime/kibe/live/<DATE>/<ROW_RUN_ID>/machines/machine_<M>/<RUN_ID>/follow_result.json`.
  - Phân loại rõ:
    + **Đang thụ án Cooldown 7 ngày** (`follow-released-daily-cooldown`): Hệ thống tự chủ động ngâm nick, chặn follow để chờ hết án phạt, bảo vệ nick khỏi bị TikTok gia hạn án.
    + **Bị bắt quả tang nhả follow trong phiên** (`FOLLOW_FAILED`): Vừa mới dính án nhả follow ở phiên hiện tại.
    + **Bị chặn do thiếu video** (`under-5-videos-follow-disabled`): Không đủ >= 5 video nên bot chủ động chưa cho follow.
    + **Lỗi UI verify tab Đã follow** (`MANUAL_REVIEW`).
    + **Thành công** (`OK` / `SUCCESS`).

## 3. Tránh hiểu nhầm khi trả lời User
- Tuyệt đối không trả lời vội vàng: "Nick không bị sao cả, 67/80 máy thành công" khi chưa bóc tách riêng số liệu của Hook Follow.
- Luôn tách bạch: Tỷ lệ Feed thành công (lướt video) vs Tỷ lệ Follow thành công / Cooldown nhả follow.
