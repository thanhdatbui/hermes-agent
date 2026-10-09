# Bài Học Hiện Trường Máy 78: Tránh Ảo Giác Nguồn Popup (App Attribution Hallucination) & Chuẩn Hóa WORK_PACKAGE Cho Popup Allowlist

## 1. Hiện Trường Sự Cố & Diễn Biến
- **Máy:** 78 (Serial: `ce0916090a9d320a01`)
- **Quy trình:** Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`)
- **Triệu chứng Alert:** `popup is not in the shared TikTok allowlist; manual review required; swipe recovery (2 swipes) still stuck`
- **Hình ảnh hiện trường:** Giao diện TikTok bị che bởi một popup tiếng Việt:
  - Tiêu đề / Nội dung: *"Tự động tải video về qua Wi-Fi để xem ngoại tuyến?"*
  - Nút bấm: `"OK"`

## 2. Hai Sai Lầm Chí Mạng Trong Xử Lý

### Sai lầm 1: Ảo giác nguồn gốc Popup (App Attribution Hallucination) & Đổ lỗi rớt mạng
- **Hiện tượng:** Worker ban đầu và Coordinator suy diễn chủ quan rằng popup này thuộc về app ngoài (YouTube Smart Downloads hoặc notification hệ thống chen vào) hoặc nghi ngờ máy rớt Wi-Fi.
- **Phản ứng của User:** 
  > *"Có phải do máy rớt wifi k"*
  > *"Nghe vô lí vc đang ở trong tiktok mắc gì youtube nhảy vào. Đọc log kĩ coi"*
- **Bằng chứng thực tế (Ground Truth qua ADB O(1)):**
  - Mạng Wi-Fi: `wlan0` UP, IP `192.168.110.122`, Ping `8.8.8.8` packet loss **0%** (avg 54.9ms) $\rightarrow$ Hoàn toàn không rớt mạng.
  - Ứng dụng chiếm màn hình (`dumpsys window`):
    `mCurrentFocus: Window{... com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity}`
    $\rightarrow$ **100% nội bộ app TikTok (`com.ss.android.ugc.trill`)**. Đây là tính năng "Video ngoại tuyến" (Offline Videos auto-download) của chính TikTok hiển thị khi có kết nối Wi-Fi.
- **Bài học:** Tuyệt đối không suy đoán nguồn popup dựa trên cảm tính. Luôn kiểm tra `dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'` trước khi phát ngôn nguyên nhân.

### Sai lầm 2: Worker Runaway Loop (35 tool calls / 40+ phút) Do Giao Goal Mở Đa Repo
- **Hiện tượng:**
  - Logic popup TikTok nằm phân tán giữa `automation-core` (`src/automation_core/tiktok/benign_popup.py`) và `tiktok-luot nuoi acc` (`python_runner/flows/benign_popup.py`, `core/benign_popup.py`).
  - Khi Coordinator dispatch worker với goal điều tra chung chung ("tìm nguyên nhân và patch allowlist"), worker thực hiện chuỗi đọc, grep phân trang, đào sâu import giữa 2 repo, dẫn đến 3 subagents liên tiếp chạm trần `max_iterations = 35` (mỗi worker ngốn 40-45 phút) mà không hề ghi đĩa hay chạy test.
- **Bài học:** Các task bổ sung popup allowlist đã có sẵn screencap/text cụ thể BẮT BUỘC phải khóa cứng thành **WORK_PACKAGE Bounded (<= 8 tool calls)**, cấm để worker tự do khảo sát đa repo.

---

## 3. Quy Trình Chuẩn Xử Lý Popup Allowlist Mới (WORK_PACKAGE Bounded <= 8 Calls)

Khi gặp alert `popup is not in the shared TikTok allowlist` với ảnh/text hiện trường đã rõ:

1. **Xác thực O(1) Package & Network (Coordinator - 1 call):**
   - Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc direct ADB check `dumpsys window`.
   - Xác nhận đúng package đang chiếm focus (chống đổ lỗi app thứ 3 hoặc rớt mạng).

2. **Chỉ thị WORK_PACKAGE Đóng Gói (Giao Worker - Ngân sách <= 8 calls):**
   - **Bước 1 (1-2 calls):** Định vị nhanh hàm detector liên quan bằng `search_files` có chủ đích (ví dụ `pattern='offline_video'` trong `automation-core/.../benign_popup.py` và `tiktok-luot nuoi acc/python_runner/.../benign_popup.py`).
   - **Bước 2 (1 call):** Đọc hẹp $\pm 30$ dòng quanh hàm detector bằng `read_file`.
   - **Bước 3 (1 call):** Dùng `patch` tool bổ sung ngay text marker (`"tự động tải video về qua wi-fi để xem ngoại tuyến"`) và action button (`"OK"`).
   - **Bước 4 (1 call):** Chạy Canary Test B4:
     ```powershell
     powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
     ```
   - **Bước 5 (1 call):** Trích xuất `git diff` và output test, kết thúc nhiệm vụ.

Tuyệt đối không cấp quyền cho worker mở rộng điều tra sang các luồng đăng ký, login hay refactor code xung quanh.
