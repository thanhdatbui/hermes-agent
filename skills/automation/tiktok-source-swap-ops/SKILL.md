---
name: tiktok-source-swap-ops
description: "Vận hành đổi nguồn video kênh TikTok, tự động push avatar lên máy thật, xử lý clip cũ và kỷ luật chống over-engineering."
---
# TikTok Source Swap Operations & Post-Swap Invariants

Sử dụng quy chuẩn này khi tài khoản TikTok trong farm cần chuyển đổi kênh nguồn (do dính tin tức/thời sự, flop view, hoặc vi phạm bản quyền).

## Phân Tầng Kiểm Chứng: UI vs Backend / Database (Anti-Canary Illusions)
- **Tác vụ đổi nguồn & avatar máy thật:** Chạy script đổi nguồn, render video, push avatar vào máy thật và chạy `run_avatar_m1.py` để đổi avatar trên app TikTok. Bắt buộc nghiệm thu bằng ảnh UI thật qua WinRT OCR / Multimodal.
- **Tác vụ chuẩn hóa dữ liệu sang SQLite / DAL:** Thuần túy là tầng **Backend / Data Layer**. Tuyệt đối **CẤM** suy luận máy móc bật màn hình điện thoại chụp ảnh splash app TikTok đối phó. Nghiệm thu bằng **Focused Test < 30s** và **Read-back SQLite / DAL**. Cờ `--no-canary` phải được áp dụng với lý do cụ thể.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
