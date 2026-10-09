# Triage & Troubleshooting Guide: TikTok Feed Session

## 1. Log-First Rule (CẤM đoán mò nguyên nhân)
- Khi một máy fail hoặc script thoát với exit code lỗi (1, 2, 3...):
  - **BƯỚC 1:** Mở trực tiếp file `summary.txt` và `log.jsonl` tại artifact directory của run đó:
    - Multi-machine summary: `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/<timestamp>/summary.txt`
    - Per-machine summary: `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/<timestamp>/machines/machine_<N>/<timestamp>/summary.txt`
  - **BƯỚC 2:** Đọc `stop_reason`, `reason`, `blocker_type` và error stack trace trong `log.jsonl`.
  - Tuyệt đối không phán đoán lỗi dựa trên exit code bên ngoài của PowerShell hay alert cũ (như `ATX_SESSION_UNAVAILABLE`) khi chưa đối chiếu log thực tế.

## 2. Lỗi Cohort Argument Binding (`_apply_cohort_identity`)
- **Triệu chứng:**
  `RuntimeError: cohort artifact and assignment manifest are both required for a live cohort child` hoặc `cohort-target-mismatch` (exit code 1).
- **Nguyên nhân:**
  Trong môi trường có sẵn `$env:TIKTOK_FEED_ASSIGNMENT_MANIFEST` và `$env:TIKTOK_FEED_WORKER_ID`. Nếu wrapper PowerShell (`run-feed-session.ps1`) truyền `--assignment-manifest` và `--worker-id` sang `run_tiktok.py` khi KHÔNG có `--cohort-artifact` (chạy lẻ/canary), Python runner hiểu nhầm là tiến trình con của frozen cohort và fail-closed.
- **Quy tắc xử lý:**
  - Trong `run-feed-session.ps1`: CHỈ truyền `--assignment-manifest` và `--worker-id` vào `run_tiktok.py` khi `$CohortArtifact` có giá trị.
  - Khi chạy canary/standalone: không truyền các cờ cohort vào python runner để chạy ở direct mode.

## 3. Lỗi Device Lock Conflict (`skipped-device-locked` / `status: manual-needed`)
- **Triệu chứng:**
  `summary.txt` báo:
  `final_status: skipped-device-locked`
  `stop_reason: device lock active: path=C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json pid=<PID> project=tiktok-follow ...`
- **Nguyên nhân:**
  Máy mục tiêu đang được tiến trình khác (ví dụ: `tiktok-follow` theo lịch) chiếm giữ lock độc quyền `machine_<N>.lock.json`.
- **Cách xử lý:**
  - Kiểm tra tiến trình đang giữ lock: `Get-Process -Id <PID>`.
  - Không kill tiến trình đang chạy hợp lệ. Chờ tiến trình hoàn tất nhả lock hoặc kiểm tra xem tiến trình có bị treo (zombie) hay không trước khi giải phóng lock.
