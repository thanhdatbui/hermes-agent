# Farm Shift Structure, Follow Budget Math, and Avatar Failure Mechanics

## 1. Farm Shift Structure & Follow Budget Math
- **Farm Execution Hierarchy:**
  - **1 Ngày = 3 Ca:**
    - Ca 1: Row 1 (ngày lẻ) / Row 2 (ngày chẵn)
    - Ca 2: Row 3 (ngày lẻ) / Row 4 (ngày chẵn)
    - Ca 3: Row 5 (ngày lẻ) / Row 6 (ngày chẵn)
  - **1 Ca = 3 Phiên (Sessions):** Mỗi ca máy chạy lần lượt 3 phiên (Sáng - Chiều - Tối / cữ cách nhau $\ge 2-4h$).
- **Follow Budget Calculation:**
  - Khi cấu hình `budget_per_session` trong `config.yaml`:
    $$\text{Tổng Follow/ngày/nick} = \text{budget\_per\_session} \times 3\text{ phiên}$$
  - **Ví dụ:**
    - Nếu đặt `budget_per_session: 15-20` $\rightarrow$ Tổng follow trong ca là $45 - 60\text{ follow/ngày}$.
    - Để giữ ngưỡng an toàn $30 - 36\text{ follow/ngày}$ (tránh TikTok shadow drop / rate-limit), cấu hình chuẩn là `budget_per_session: 10-12` (hoặc `budget_per_session_min: 10`, `budget_per_session_max: 12`).

## 2. Avatar Upload & Post Pipeline Interaction (Tiktok-video)
- **Quy trình State Machine Upload (`run_post.py` / `state_machine.py`):**
  $$\text{POST} \rightarrow \text{VERIFY\_POST} \rightarrow \text{UPDATE\_WORKBOOK} \rightarrow \mathbf{ENSURE\_AVATAR} \rightarrow \text{DELETE\_REMOTE\_MEDIA} \rightarrow \text{RELEASE}$$
- **Khi Video thành công nhưng Up Avatar thất bại:**
  - `VERIFY_POST` & `UPDATE_WORKBOOK` đã hoàn thành $\rightarrow$ Workbook ghi nhận `Video Đã Đăng` tăng lên (không bị đăng trùng video khi chạy lại).
  - Bước `ENSURE_AVATAR` ném ngoại lệ `AVATAR_WORKFLOW_FAILED` / `AVATAR_SOURCE_MISSING` / `AVATAR_EDIT_OPEN_FAILED`.
  - Workflow chuyển sang `FAILED` / `MANUAL_REVIEW` $\rightarrow$ Parent runner bắn Telegram Farm Alert banner đỏ `[MÁY N] GIỮ HIỆN TRƯỜNG UPLOAD`.
  - **Cách xử lý / Targeted Repair:**
    - Không chạy lại batch upload video.
    - Chạy script chuyên biệt up avatar tách rời:
      ```powershell
      & powershell.exe -File run_tiktok_upload_avatar.ps1 `
          -Tik <N> -ForceAvatarMachineList "<M>" -WorkerId hermes-kibe-avatar `
          -AssignmentManifest <manifest.json>
      ```
