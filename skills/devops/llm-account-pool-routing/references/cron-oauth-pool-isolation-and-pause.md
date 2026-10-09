# Cron OAuth Pool Isolation & Safe Pause

## Bối cảnh phân định các Cron Job nạp Pool trên OmniRoute (:20129)

Hệ thống OmniRoute duy trì nhiều upstream account pool độc lập. Khi có yêu cầu dừng hoặc cô lập một pool (ví dụ: dừng nạp OAuth Antigravity nhưng giữ Codex và ChatGPT Web), cần phân loại chính xác từng cron job để tránh tắt nhầm.

### 1. Phân loại Cron Job theo Upstream Provider

| Nhóm Provider | Job Name | Script | Vai trò |
|---|---|---|---|
| **Antigravity / Google OAuth** | `gpm-oauth-full-pool-feeder` | `cron_gpm_oauth_full_pool.py` | Quét GPM profiles, giải captcha, nạp OAuth Google/Antigravity lên `:20129` |
| **Antigravity / Google OAuth** | `gpm-oauth-pool-6h-report` | `cron_gpm_oauth_pool_6h_report.py` | Báo cáo 6h về sản lượng và trạng thái nạp Antigravity |
| **Codex OAuth** | `omni-activate-soaked-codex` | `cron_omni_activate_soaked_codex.py` | Kích hoạt (`is_active = 1`) tài khoản Codex đã ngâm đủ điều kiện |
| **Codex OAuth** | `gpm-5profiles-lifecycle-supervisor` | `gpm_5profiles_supervisor_wrapper.py` | Quét lifecycle Hotmail -> ChatGPT -> Codex OAuth (`codex_5sim_auto_verify.py`) |
| **Codex OAuth** | `hotmail-gpm-lifecycle-6h-report` | `cron_hotmail_gpm_lifecycle_6h_report.py` | Báo cáo 6h vòng đời Hotmail/ChatGPT/Codex |
| **ChatGPT Web Pool** | `chatgpt-web-pool-healer-watchdog` | `cron_chatgpt_web_pool_watchdog.py` | Giám sát liveness và hồi sinh pool ChatGPT Web |
| **ChatGPT Web Pool** | `omni-free-pool-auto-updater` | `cron_omni_free_pool_updater.py` | Quét liveness OpenRouter & ChatGPT Web để duy trì Free pool |

### 2. Nguyên tắc Thao tác An toàn khi Dừng Cron Pool

1. **Ưu tiên `pause` hơn `remove`**:
   - Sử dụng `cronjob(action='pause', job_id=...)`.
   - Giữ nguyên cấu hình, schedule, script binding và lịch sử chạy; có thể `resume` tức thì khi cần mở lại pool.
2. **Kiểm tra Script Target trước khi thao tác**:
   - Luôn đọc `prompt_preview` và `script` của job trong `cronjob(action='list')`.
   - Không đoán theo tên job nếu chưa đối chiếu mã nguồn script để xác nhận upstream đích.
3. **Cơ chế Đồng bộ Tự động (3-Way Sync Contract)**:
   - Runtime `jobs.json` tại `~\AppData\Local\hermes\cron\jobs.json` là Source of Truth khi agent gọi `cronjob`.
   - `cron-sync-watchdog` (`cron_sync_watchdog.py`) chạy định kỳ mỗi 15 phút sẽ tự động phát hiện thay đổi và sync bản copy sang:
     - Git deploy: `D:\Taadaa\Hermes\deploy\hermes-home\cron\jobs.json`
     - OneDrive Shared: `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\jobs.json`
   - Không cần can thiệp thủ công vào file `jobs.json` trên đĩa hay các bản sync.
