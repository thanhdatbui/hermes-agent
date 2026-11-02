MikroTik Web (:2310) chỉ quản lý PPPoE Đà Nẵng; R3G Thái Bình quản lý native tại Dashboard :1905.
§
Niche TikTok: Video là Ground Truth. CẤM cào/đăng tin tức/VTV/phóng sự (dính bóp reach); phát hiện nguồn tin tức phải đổi nguồn triệt để (dọn render -> dọn gốc -> cào/render mới). Ưu tiên ngách hot sạch chữ (Ẩm thực, Bếp Việt, Câu chuyện, Thú cưng). Chuẩn hoá kênh tra cứu O(1) lookup_channel.py; ghim top video bằng pin_top_videos.py.
§
Gate 6: dùng watchdog retry, evidence tự tính từ diff. S4 canary_plan.py truyền --plan. Cấm hứa hẹn suông. Pipeline trích dẫn ngắn kết quả Advisor nếu có. Fallback provider bắt buộc hỗ trợ Vision, không dính 429 tránh văng lỗi retry.
§
Canary: phân tầng UI vs Backend (backend ko ép screencap). Lock repo: nhường single-writer. Flop scanner: xét 3 snapshot gần nhất. SQLite SSOT: bảng `tiktok_workflow_state` trong `farm_master.db` thay thế dần Tik1..Tik8 Excel (DAL `farm_sqlite_dal.py`, WAL mode, fallback khi lock). S7 kẹt offline kick 'adb reconnect offline' toàn cục daemon. M10/30/35/41 Kibe và M255 Admin rớt USB vật lý.
§
Gateway: .pth & Watchdog ghim D:\Taadaa\Hermes\.venv, cô lập C:. Cấm restart mù. Khi user hỏi tiến độ ('còn gì k', 'xong chưa'), CẤM session_search quét chéo session khác; chỉ báo đúng task phiên. Native Vision (ag-gemini-pool-3) đọc ảnh trực tiếp, CẤM gọi browser_vision local làm màu đối phó. Telegram Proxy: Viettel LAN :10001 primary, WARP :40000 fallback, Heartbeat 30s chống ngâm socket.
§
Nén ngữ cảnh: BẮT BUỘC duy trì ở Hermes (threshold 0.6 = 600k tokens, protect_last_n 50, protect_first_n 3); CẤM chế cháo nén ở proxy router (OmniRoute/9Router) gây lỗi 400 đa phương thức. OmniRoute: CẤM dùng npm run build:backend vì cơ chế stub làm mất 126 trang giao diện Dashboard web; build production bắt buộc cấp đủ RAM Node và bảo toàn full frontend. Multimodal Native: Gemini đọc pixel trực tiếp, cấm mở browser_vision đối phó. Cấm quét chéo session khác khi user hỏi tiến độ.
§
Quy chuẩn Canary: Task chuẩn hoá SQLite/backend logic CẤM gọi canary máy thật chụp splash TikTok làm màu; bắt buộc nghiệm thu bằng focused test <30s và read-back DB thật. Pipeline bắt buộc chấp thuận --no-canary khi diff là backend.