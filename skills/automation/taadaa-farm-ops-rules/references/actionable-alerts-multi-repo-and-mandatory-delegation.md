# Multi-Repo Actionable Alert & Mandatory Delegation Protocol

## 1. Chuẩn Hóa Actionable Alert Đa Repo (Phone Farm 160 Máy)
Mọi script nghiệp vụ khi phát sinh dừng phiên / exception đều phải gửi Telegram Farm Alert theo format Actionable Alert động, chứa sẵn 4 dòng payload thực thi đích danh:

```text
🚨 [FARM ALERT: MÁY {machine}] DỪNG PHIÊN
• Máy: {machine} | Serial: {serial} | Nick: {account}
• Triệu chứng: {error_reason}

📋 BẮT BUỘC THỰC THI (KHÔNG GREP / KHÔNG TÌM KIẾM):
1. Lệnh lấy hiện trường: python D:/Taadaa/tools/inspect_machine.py {machine}
2. File flow phụ trách: {flow_file}
3. File log run: {log_path}
4. Lệnh canary test lại máy {machine}:
{canary_cmd}
```

### Bảng Ánh Xạ Repo & Payload Phụ Trách:
| Repo | Entrypoint | File Flow (`flow_file`) | File Log (`log_path`) | Lệnh Canary (`canary_cmd`) |
| :--- | :--- | :--- | :--- | :--- |
| **Nuôi Acc / Lướt Feed** (`tiktok-luot nuoi acc`) | `multi_machine_feed_session.py` | `python_runner/flows/feed_swipe_smoke.py` | `.ai-runs/latest/summary.txt` | `run-feed-session.ps1 -Machines <N> ...` |
| **Follow Tự Động** (`tiktok-follow`) | `multi_machine_feed_session.py` (hook) | `python_runner/flows/follow_engine.py` | `runs/latest/summary.txt` | `run-follow.ps1 -Machines <N> ...` |
| **Upload Video** (`Tiktok-video`) | `run_post.py` | `scripts/tiktok_workflow/run_post.py` | `D:/CodexRuntime/tiktok-video/runs` | `python -m scripts.tiktok_workflow ...` |
| **Đăng Ký Nick** (`Tiktok_Reg`) | `social_reg_v1.py` | `D:/Taadaa/Tiktok_Reg/social_reg_v1.py` | `D:/Taadaa/Tiktok_Reg/social_reg_log.txt` | `python social_reg_v1.py <STT> --ss --email <mail>` |
| **Bật 2FA** (`tiktok-add-bao-mat-f2a`) | `run_batch_live_2fa.py` | `python_runner/run_batch_live_2fa.py` | `runtime/kibe/reports` | `python python_runner/run_batch_live_2fa.py --live --limit 1` |

---

## 2. Kỷ Luật Phân Vai Bắt Buộc (Coordinator vs Worker Delegation)

### Vấn Đề Gốc Rễ Đã Khắc Phục:
- **Hiện tượng cũ**: Coordinator tự mở file, tự patch code và tự chạy test trên session chính làm phình to context (>150 tool calls), dễ bị timeout/interrupted.
- **Hiện tượng bấm tay chữa cháy**: Dùng `adb shell input tap/keyevent` để giải phóng máy tạm thời thay vì sửa handler codebase.

### Quy Trình Chuẩn 5 Bước Khi Nhận [FARM ALERT: MÁY N]:
1. **Turn 1 - BẮT BUỘC Spawn Worker Subagent**:
   - Coordinator gọi ngay `delegate_task(role='leaf', model='ag-worker', goal=..., context=...)`.
   - Cung cấp đầy đủ đường dẫn `flow_file`, `log_path`, `canary_cmd` cho worker.
2. **Worker Subagent Thực Thi Độc Lập**:
   - Worker chạy `inspect_machine.py <N>`, đọc log, sửa file code flow và chạy unit test/canary trong môi trường riêng.
3. **CẤM TUYỆT ĐỐI Bấm Tay ADB**:
   - Máy lỗi là **HIỆN TRƯỜNG** để đọc UI XML và viết code tự động vượt qua lỗi. CẤM gõ lệnh tap/swipe thủ công qua ADB.
4. **Coordinator Xác Minh & Chốt Phiên**:
   - Khi worker hoàn thành, Coordinator chạy canary test lại máy N, review code diff và thực hiện quy trình chốt phiên 6 Gate.

---

## 3. Quản Lý & Sao Lưu Cấu Hình Hermes
- Mọi thay đổi về cấu hình Hermes (`config.yaml`, `SOUL.md`, `cron/jobs.json`, scripts vận hành, skills) bắt buộc phải được đồng bộ vào `D:/Taadaa/Hermes/deploy/hermes-home/` và `skills/`, sau đó commit và push lên remote `fork/main`.
