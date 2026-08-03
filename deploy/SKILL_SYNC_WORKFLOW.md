# Skill Sync Workflow — Hermes orchestration skills auto-sync via git

Cơ chế để 2 skill điều phối (`agent-review-loops`, `hermes-orchestration-dispatcher`)
tự động sync lên git repo này, và máy khác chỉ cần pull là dùng được.

## Kiến trúc

```
C:\Users\<user>\AppData\Local\hermes\skills\<skill>
        │  (junction → trỏ thẳng vào git working tree)
        ▼
D:\Taadaa\Hermes\skills\<skill>      ← repo này (git)
        │  (cron mỗi 30 phút chạy script sync)
        ▼
git commit + push → GitHub (thanhdatbui/hermes-agent.git)
        ▼
Máy khác: git pull → skill tự đổi → dùng luôn
```

## Trên máy MỚI (setup 1 lần)

### 1. Junction skill local → repo git

```powershell
# Thay <USER> bằng tên user máy đó
mklink /J "C:\Users\<USER>\AppData\Local\hermes\skills\autonomous-ai-agents\agent-review-loops" "D:\Taadaa\Hermes\skills\autonomous-ai-agents\agent-review-loops"
mklink /J "C:\Users\<USER>\AppData\Local\hermes\skills\software-development\hermes-orchestration-dispatcher" "D:\Taadaa\Hermes\skills\software-development\hermes-orchestration-dispatcher"
```

Lưu ý: xóa folder local cũ trước nếu đã tồn tại (đã có skill cũ).

### 2. Cài script sync vào Hermes scripts dir

```powershell
copy D:\Taadaa\Hermes\deploy\sync-orchestration-skills.ps1  C:\Users\<USER>\AppData\Local\hermes\scripts\sync-hermes-skills.ps1
copy D:\Taadaa\Hermes\deploy\sync-hermes-skills.py        C:\Users\<USER>\AppData\Local\hermes\scripts\sync-hermes-skills.py
```

### 3. Tạo cron job (chạy mỗi 30 phút, silent khi không đổi)

```powershell
hermes cron add --name sync-hermes-skills-to-git --schedule "30m" --repeat forever --no-agent --script sync-hermes-skills.py
```

Hoặc trong Hermes chat, ra lệnh:
> "Tạo cron job `sync-hermes-skills-to-git` chạy mỗi 30 phút, lặp vĩnh viễn, no_agent, script `sync-hermes-skills.py` trong `~/hermes/scripts/`. Script tự commit+push skill nếu có thay đổi, silent nếu không."

### 4. Restart / reset

`/reset` hoặc mở session mới để Hermes load skill qua junction.

## Hoạt động

- Sửa skill ở local (bất kỳ máy nào) → junction → git working tree thấy ngay
- Cron 30 phút chạy `sync-hermes-skills.py`:
  - Có thay đổi → commit + push lên GitHub
  - Không có → silent
- Máy khác: `git pull` trong `D:\Taadaa\Hermes` → skill tự đổi → dùng luôn

## File liên quan

- `deploy/sync-orchestration-skills.ps1` — script commit+push (chỉ stage 2 skill, không đụng code Hermes khác)
- `deploy/sync-hermes-skills.py` — cron wrapper (silent khi không đổi, in khi push)
- 2 skill junction: `skills/autonomous-ai-agents/agent-review-loops/`, `skills/software-development/hermes-orchestration-dispatcher/`

## Lưu ý

- Chỉ stage 2 skill điều phối — KHÔNG tự commit code Hermes khác (apps/, gateway/...) đang modified.
- Nếu 2 máy sửa cùng skill gần nhau → git merge conflict bình thường, resolve như mọi conflict.
- `FETCH_HEAD` bị lỗi "Permission denied" nếu bị ghi đè tay — xóa file `.git/FETCH_HEAD` là git tự tạo lại.
