# Quy tắc Phân tầng Tỉ lệ Like & Cơ chế Swipe theo từng Tab (Chốt 2026-09-18)

## 1. Bản chất Phân tầng Tương tác giữa các Tab
- **Tab Đề xuất (For You - 70% thời lượng session):**
  - Cơ chế lướt: **Fast Swipe mạnh** (2–4 video lướt nhanh 2–5s, 1 video Deep Inspect soi XML).
  - Tỉ lệ Like: **8% – 12%** trên tổng video For You (Deep inspect like rate 40% bù trừ qua nhịp fast swipe).
  - Mục đích: Giữ trust người dùng giải trí bình thường, không spam like người lạ, giải phóng 70% CPU cho dàn máy farm.
- **Tab Bạn bè (Friends - 15% thời lượng session):**
  - Cơ chế lướt: **Fast Swipe nhẹ xen kẽ** (1 video lướt qua làm Noise tự nhiên, 1–2 video Deep Inspect).
  - Tỉ lệ Like: **45% – 55%** trên tổng video Bạn bè (Deep inspect like rate 65%).
  - Bản chất: Tab Bạn bè thực tế chỉ hiện video của mutual friends (các nick farm chéo nhau). Thả tim đậm đà (60-70% ở nhịp xem) vừa tự nhiên theo tâm lý ủng hộ bạn bè, vừa **tối đa hóa sản lượng buff tim chéo tự nhiên cho video farm** mà không cần viết thêm script buff riêng cồng kềnh.
- **Tab Đang theo dõi (Following - 15% thời lượng session):**
  - Cơ chế lướt: **Fast Swipe nhẹ** (1 lướt nhanh, 1 soi).
  - Tỉ lệ Like: **25% – 30%** trên tổng video Following (Deep inspect like rate 35%).

## 2. Quy chuẩn Báo cáo Đối soát Telegram Watchdog (`feed_session_watchdog.py`)
- Báo cáo % thả tim của từng tab **BẮT BUỘC tính theo số lượt xem của chính tab đó**, tuyệt đối không chia gộp cho toàn bộ phiên chạy:
  `Thả tim: 185 tim / 1480 video (12.5%) [Đề xuất: 110 (9.8%) | Bạn bè: 45 (48.4%) | Following: 30 (27.3%)]`
- Công thức: `tot_tab_likes / tot_tab_swipes * 100.0`.
- Operator nhìn vào là kiểm soát tức thì hiệu quả đẩy tim nội bộ cho farm.
