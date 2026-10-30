---
name: tiktok-channel-standardization
description: "Use when standardizing TikTok profiles (bio, pin, avatar)."
---
# TikTok Channel Standardization (5-in-1 Protocol)

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
> - `references/avatar-no-text-discipline-and-launcher-trap.md`: Kỷ luật trích xuất Avatar sạch chữ 100% & Bẫy chụp lộn màn hình Launcher khi Watchdog hoàn tất.
> - `references/username-vs-display-name-and-cross-registry-sync.md`: Quy chuẩn chuẩn hóa Username (@handle) vs Display Name và kỷ luật đồng bộ nguyên tử đa tầng dữ liệu (Excel + SQLite).
> - `references/false-positive-anchor-drop-and-profile-unlock-20261030.md`: Điều tra lỗi nhả follow ảo 35 máy do race condition nút Anchor & Quy trình mở khóa trang Sửa hồ sơ để đổi Username trên layout Profile mới.
> - `references/tiktok-profile-missing-edit-button-and-username-trap-20261030.md`: Bẫy giao diện TikTok khuyết nút Sửa hồ sơ (chỉ có Thêm tiểu sử) và hạn chế đổi Username trực tiếp.
> - `references/tiktok-follow-drop-verification-and-profile-edit-20261030.md`: Cơ chế kiểm tra nhả follow qua vuốt reload (pull-to-refresh + sleep 3.5s), tỷ lệ xem video mồi (30-35%) và quy trình mở khóa đổi Username @.
> - `references/cohort-analysis-and-follow-drop-mechanics-20261030.md`: Kỷ luật phân tách cohort tuổi (±15 ngày) và loại mail (Gmail vs Hotmail), bản chất TikTok cấm chiều Cho Đi (Following) và thực trạng đàn nick 25/08.
> - `references/username-change-variant-and-fleet-partitioning-20261029.md`: Quy chuẩn đổi Username khi UI ẩn nút Sửa hồ sơ, đối soát trust threshold follow và hiệu quả phân nhóm Chẵn/Lẻ.
> - `references/o1-proposal-canvas-and-fast-lookup-protocol.md`: Quy trình tra cứu toạ độ kênh O(1), trích xuất avatar sạch chữ và kết xuất Proposal Canvas 5-in-1 chuẩn mực.
> - `references/pa4-execution-discipline-and-lockdown.md`: Kỷ luật thực thi chuẩn hoá khi User chọn PA 4, bẫy lệch ảnh Card 4 trên Canvas vs app thật, quy trình force upload avatar và đồng bộ khóa media đa tầng.
> - `references/tiktok-unhide-private-videos-and-tab2-shift-flow-20261030.md`: Quy trình mở công khai video bị ẩn (Tab 2 - icon khóa 🔒), cơ chế tự dịch chuyển hàng đợi (queue shift) tại toạ độ cố định (540, 1200) và toạ độ chuẩn Privacy Settings.
> - `references/tiktok-lifo-pin-ordering-and-enforce-slot1.md`: Quy tắc ghim video theo cơ chế LIFO TikTok, hàm tự động giữ top 1 view ở Ô 1 (_enforce_top_pin_at_slot1) và lọc candidate sort giảm dần tránh chọn nhầm bài rác.

