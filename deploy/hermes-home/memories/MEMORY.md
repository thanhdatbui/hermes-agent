MikroTik Web (:2310) chỉ quản lý PPPoE Đà Nẵng; R3G Thái Bình quản lý native tại Dashboard :1905.
§
Niche TikTok: Video là Ground Truth. CẤM cào/đăng tin tức/VTV (dính bóp reach); ưu tiên ngách Câu chuyện (cauchuyen).
§
Gate 6: dùng watchdog retry, evidence tự tính từ diff. S4 canary_plan.py truyền --plan. Cấm hứa hẹn suông. Pipeline trích dẫn ngắn kết quả Advisor nếu có. Fallback provider bắt buộc hỗ trợ Vision, không dính 429 tránh văng lỗi retry.
§
Canary: phân tầng UI vs Backend (backend ko ép screencap). Lock repo: nhường single-writer. Flop scanner: chỉ xét 3 snapshot gần nhất (snapshots_history[-3:]). SQLite lưu metrics; Tik1..Tik8 Excel là sổ cái routing sequence upload. S7 kẹt 'offline' do micro-drop USB phải kick bằng 'adb reconnect offline' toàn cục daemon (kibe & admin), cấm dùng lệnh đơn lẻ. M10/30/35/41 Kibe và M255 Admin rớt USB vật lý. M270 trắng phiên.
§
Lỗ hổng Gate Bánh Xe: ui_policy_check.py cần body_patterns quét chuỗi đặc thù trong thân hàm; thiếu canonical import (account_switcher) -> REJECT ngay.
§
Gateway: .pth & Watchdog ghim D:\Taadaa\Hermes\.venv, cô lập C:. Cấm restart mù. Khi user hỏi tiến độ ('còn gì k', 'xong chưa'), CẤM session_search quét chéo session khác làm loãng context; chỉ báo cáo đúng task phiên hiện tại. Model Native Vision (ag-gemini-pool-3) đọc ảnh trực tiếp qua turn prompt, CẤM gọi browser_vision mở ảnh local làm màu đối phó.
§
User gửi `?` hoặc tin nhắn cực ngắn trích dẫn lại đoạn chat cũ của Agent là tín hiệu chất vấn/bắt lỗi mâu thuẫn (Contradiction Alert), cấm hiểu nhầm là yêu cầu phân tích tiếp hay lặp lại báo cáo hiện trường cũ.
§
Đổi nguồn video: Dọn 2 đầu, giữ cursor posted và render nối tiếp posted+1; BẮT BUỘC up avatar mới lên app ngay qua run_avatar_m1.py <M> <Tik>, cấm để User hỏi 'Đổi ava chưa?'. Clip cũ ko gậy kệ mẹ ko cần ẩn. Cấm chèn script quét gậy vào ca nuôi feed tránh nghẽn hotpath. Chuẩn hoá: O(1) `lookup_channel.py`, ghim top LIFO qua `pin_top_videos.py`. Gate 6 soi mắt browser_vision rồi cập nhật Tik<N>.xlsx.