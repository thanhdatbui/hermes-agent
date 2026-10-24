# Forward Report Parsing & Watchdog Separation Invariant

## 1. Phân Biệt Giữa Farm Alert và Session Watchdog Report
- **🚨 [FARM ALERT] (Cảnh báo hạ tầng/lỗi hệ thống):**
  - **Kích hoạt:** Khi sập nguồn, đứt cáp, proxy chết hàng loạt, hoặc lỗi script Follow/Upload hệ thống (>= 8 máy dính lỗi cùng loại).
  - **Kênh đích:** Nhóm Alert riêng (`-5373649734`).
  - **Cấm:** Tuyệt đối không tự ý đổi tiêu đề báo cáo ca nuôi định kỳ thành `[FARM ALERT]` chỉ vì một số máy rớt mạng/mở app hỏng làm hoảng loạn và phân tán kênh nhận tin.
- **📊 Báo Cáo Phiên Định Kỳ (`[TIKTOK NUÔI ACC] Ca X hoàn tất...`):**
  - Gửi vào đúng nhóm nghiệp vụ Nuôi (`-5377611430`).
  - Toàn bộ máy fail được liệt kê minh bạch ở mục `+ Fail (N)` và các nhóm lỗi phân loại bên dưới.

---

## 2. Quy Tắc Vận Hành: Forward Report = Lệnh Fix Script O(1)
Khi User forward bất kỳ tin nhắn báo cáo nào từ bot watchdog vào chat:
- **Cấm hỏi lại:** Không được hỏi *"Bạn có muốn sửa không?"* hay chờ chỉ đạo thêm.
- **Bóc tách 4 trường thông tin O(1):**
  1. **Thẻ tiêu đề:** Xác định repo đích (`[TIKTOK NUÔI ACC]` -> `tiktok-luot nuoi acc`, `[TIKTOK FOLLOW]` -> `tiktok-follow`).
  2. **Cụm máy & Run ID:** `【Kibe Local】` / `【Farm Admin】` + `(Row X)` + `(Run: YYYYMMDD-HHMMSS)` -> Đường dẫn log tuyệt đối:
     `D:/Taadaa/runtime/{cluster}/live/{YYYY-MM-DD}/row-X-*/{run_id}/` (hoặc dòng `📁 Trace:`).
  3. **Map nhóm lỗi sang file code:**
     - `+ Lỗi mở/focus App TikTok` -> `flows/device_prepare.py` (`prepare_tiktok_app_for_automation`, `recover_systemui_occlusion`).
     - `+ Lỗi thao tác vuốt (Swipe)` -> `flows/feed_session.py`.
     - `+ Lệch Profile / Kẹt Switcher` -> `flows/account_switcher.py`.
     - `+ Chưa gán Proxy / Nghẽn 4G` -> `farm_network_gate.py` hoặc `automation_core/network/`.
  4. **Bốc 1 máy đại diện:** Chọn 1 máy trong danh sách lỗi `(M1, M2... Mx)` đọc log `log.jsonl` hoặc chạy `inspect_machine.py <N>`.
- **Thực thi dứt điểm:** Đọc log máy đại diện -> Sửa code trong script ($\le$ 30 dòng) -> Pytest focused -> Chạy Canary máy thật (`canary_runner.py`) -> Báo cáo bằng chứng (Diff + Pass Test + Screenshot nghiệm thu).

---

## 3. Kỷ Luật Tư Vấn Nhất Quán (Anti-Flipflop)
- Khi đưa ra khuyến nghị kỹ thuật, tuyệt đối không thay đổi qua lại giữa "revert" và "giữ nguyên" khi user hỏi.
- Phải phân biệt rõ ràng giữa logic cốt lõi nghiệp vụ và giải pháp thừa (over-engineering). Khi một đề xuất vi phạm quy ước thông báo của User, lập tức hoàn tác dứt khoát.
