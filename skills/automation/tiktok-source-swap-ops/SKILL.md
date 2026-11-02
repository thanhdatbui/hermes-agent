---
name: tiktok-source-swap-ops
description: "Vận hành đổi nguồn video kênh TikTok, tự động push avatar lên máy thật, xử lý clip cũ và kỷ luật chống over-engineering."
---
# TikTok Source Swap Operations & Post-Swap Invariants

Sử dụng quy chuẩn này khi tài khoản TikTok trong farm cần chuyển đổi kênh nguồn (do dính tin tức/thời sự, flop view, hoặc vi phạm bản quyền).

## 1. INVARIANT BẮT BUỘC: ĐẨY VÀ SET AVATAR TRỰC TIẾP LÊN MÁY THẬT NGAY SAU KHI ĐỔI NGUỒN
- **Tín hiệu bắt lỗi từ User:** *"Đổi ava chưa?"*, *"Chuẩn hoá ava ms chưa"*
- **Nguyên nhân cốt lõi:**
  - Script pipeline (`swap_single_folder_pipeline.py`) chỉ sinh file `avatar.jpg` và lưu trên ổ đĩa máy tính (`D:\video goc\<raw>\avatar.jpg` và copy sang `D:\TIKTOK-videonuoinick\<render>\avatar.jpg`).
  - **Bẫy cờ `Avatar = OK` trong Excel:** Khi đổi nguồn cào mới cho kênh, cột `Avatar` trong bảng `Tik<N>.xlsx` vẫn đang mang cờ `OK` từ kênh cũ. Script tự động `resolve_avatar_pending_machines.py <Tik>` sẽ BỎ QUA máy này vì tưởng đã up rồi. Do đó, runner auto thông thường sẽ không bao giờ tự up avatar mới nếu không ép máy chỉ định.
  - **Bẫy mất context do `session_search`:** Khi User hỏi dồn/hỏi vắn tắt (*"Chuẩn hoá ava ms chưa?"*), Agent có thói quen xấu là gọi `session_search` bới lại session quá khứ, làm nhiễm chéo context máy khác (ví dụ bốc nhầm Máy 223/MikroTik của phiên cũ đè vào Máy 64), dẫn đến ảo giác và bị User phạt nặng: *"Mày mất hết context rồi hả"*.
  - Agent dừng lại và báo xong sau khi render mà bỏ quên thao tác nạp avatar vào máy thật. Để User phải hỏi lại "Đổi ava chưa?" hoặc báo cáo ảo "đã đổi" khi chưa chạy runner là vi phạm nghiêm trọng nhất.
- **Quy chuẩn thực thi tự động (Autonomous Push Flow):**
  Ngay sau khi hoàn thành render clip mới từ nguồn thay thế:
  1. Kiểm tra và soi mắt ảnh đại diện trên ổ đĩa: Dùng `browser_vision` soi trực tiếp `D:/video goc/<folder>/avatar.jpg` đảm bảo 100% sạch chữ, không dính logo/sub đè.
  2. Kích hoạt runner upload avatar cưỡng bức theo máy lẻ:
     ```bash
     python D:/Taadaa/tools/run_upload_avatar.py --tik <TIK_NUM> --machine <MACHINE_NUM>
     ```
     *(Lệnh này tự động kích hoạt `-ForceAvatarMachineList <MACHINE_NUM>` để vượt qua cờ `Avatar = OK` cũ của Excel).*
  3. Mở Profile TikTok trên máy thật, chụp màn hình và kéo về:
     ```bash
     python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> shell screencap -p /sdcard/m<N>_live_check.png && adb -s <SERIAL> pull /sdcard/m<N>_live_check.png D:/Taadaa/reports/m<N>_live_check.png
     ```
  4. BẮT BUỘC dùng `browser_vision` mở ảnh screenshot nghiệm thu kiểm tra vòng tròn avatar thực tế trên app ĐÃ ĐỔI SANG ẢNH MỚI CHƯA. Chưa đổi tuyệt đối CẤM báo xong.
  5. Khi phản hồi User, BẮT BUỘC đính kèm thẻ `MEDIA:D:/Taadaa/reports/m<N>_live_check.png` làm bằng chứng nghiệm thu thực tế.
  6. Tuyệt đối không gọi `session_search` bới lại session cũ khi User hỏi tiến độ. Bắt buộc đối soát trực tiếp hiện trường thực tế của máy đang làm.

---

## 2. KỶ LUẬT ẨN CLIP CŨ KHI ĐỔI NGUỒN (PRIVATE VS LEAVE ALONE)
- **Tín hiệu từ User:** *"có bắt buộc làm k hay kệ mẹ"* (sau khi nghe gợi ý ẩn clip cũ).
- **Nguyên lý phân phối thuật toán TikTok:**
  - Thuật toán TikTok phân phối theo từng video đơn lẻ (Video-level / Content-based Recommendation), không tính điểm phạt toàn kênh (Domain/Page-level) như Facebook Fanpage.
  - Video render mới (`start_seq = da_dang + 1`) mang metadata, âm thanh và hashtag của ngách mới sẽ được đẩy vào test pool độc lập.
- **Quy tắc quyết định:**
  - **Không bắt buộc ẩn (Kệ mẹ nó):** Nếu các clip cũ chỉ là nội dung không tối ưu (ví dụ tin tức/thời sự view thấp, bóp reach) nhưng **không dính vi phạm chính sách cộng đồng**. Cứ để nguyên như lịch sử người dùng bình thường, video mới sẽ đè lên và kéo kênh theo tệp mới mà không tốn công thao tác tay trên hàng trăm máy.
  - **Bắt buộc ẩn (Chuyển sang "Chỉ mình tôi"):** Duy nhất khi clip cũ bị dính cảnh báo vi phạm tiêu chuẩn cộng đồng, bản quyền âm thanh bị tắt tiếng, hoặc bị gậy "Không đủ điều kiện cho FYP" có nguy cơ kéo tụt trust score tài khoản.

---

## 3. CHỐNG OVER-ENGINEERING: CẤM CHÈN SCRIPT QUÉT GẬY VÀO CA NUÔI FEED
- **Bẫy tư duy:** Đề xuất chèn thêm script tự động mở Switcher $\to$ vào từng profile xem có bị dính gậy/cảnh báo vi phạm không để báo cáo về.
- **Lý do nghiêm cấm:**
  1. **Không có Actionable:** Kênh farm nuôi hàng loạt bằng video render preset. Nếu dính vi phạm từ TikTok thì farm cũng không thể kháng cáo thủ công hay sửa video đã đăng $\to$ Báo cáo về chỉ gây rác notification và nhiễu loạn vận hành.
  2. **Gây tắc nghẽn Hot-path Ca Nuôi:** Mỗi máy nuôi nhiều nick, lịch chạy ca cuốn chiếu 24/7. Chèn thêm luồng soi gậy làm tăng thời gian chiếm giữ máy thêm 30-60s/nick, gây đè lịch chạy (schedule collision) và treo farm.
  3. **Bộ lọc tự nhiên của Farm:** Nick dính gậy nhẹ vẫn lướt feed bình thường; nick bị ban nặng/văng nick thì cơ chế preflight/login tự nhiên sẽ phát hiện và loại bỏ khỏi pool.
