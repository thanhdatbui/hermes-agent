# Cron no_agent cwd root cause + verify artifact (18/08 sáng, 2026)

## Vấn đề
Cron picker tick 06:00 `last_status: ok` nhưng manifest 18/08 KHÔNG tồn tại.
Tay chạy wrapper (cả automation python lẫn hermes python, kể cả env sạch) LUÔN tạo được manifest.
`cronjob action=run` thủ công CŨNG silent ("empty stdout — silent run").

## Root cause
Hermes cron `no_agent` script KHÔNG chạy với `workdir` của job — `scheduler._run_job_script`
(hermes venv `cron/scheduler.py` ~dòng 2106) spawn script với `cwd=str(path.parent)`
= `%LOCALAPPDATA%\hermes\scripts` (thư mục chứa script). `workdir` job chỉ dùng cho
agent-job, không cho script-only.

→ Deployed wrapper chạy từ hermes/scripts → `repo_root()` walk `__file__`/cwd lên .git
không thấy (hermes không phải repo) → fallback `parents[1]` = `C:\Users\Kibe\AppData\Local\hermes`
→ permit `hermes/runtime/...` không tồn tại → `is_activated` False → exit 0 im lặng.

## Chẩn đoán (thứ tự)
1. `cronjob list` → `last_status: ok` nhưng `cron/output/<job_id>/*.md` ghi `Status: silent (empty output)`.
2. Chạy tay deployed wrapper từ cwd=repo → tạo artifact → không phải lỗi wrapper env.
3. Chạy đúng cron: hermes python + cwd=hermes/scripts → silent + repo_root()=hermes (sai).
4. `import importlib.util; spec_from_file_location(...)` debug repo_root/permit/is_activated.

## Fix (đã deploy 18/08)
`repo_root()` thứ tự: `HERMES_CRON_REPO` env → probe list cố định
(`"D:/Taadaa/tiktok-luot nuoi acc"`, `"D:/Taadaa/tiktok-follow"`, `"D:/Taadaa/automation-core"`)
→ cwd → walk `__file__` → fallback parents[1]. Dùng FORWARD SLASH (xem escape pitfall dưới).

## Escape path Windows trong Python source (3 lần sai cùng session)
- `r"D:\\Taadaa\\tiktok-luot nuoi acc"` → raw string giữ NGUYÊN 2 backslash → path sai.
- `"D:\Taadaa\automation-core"` → `\a` thành bell 0x07, `\t` thành tab.
- `\v` trong `WindowsPowerShell\v1.0` → vertical tab.
- **Fix: forward slash `"D:/Taadaa/..."`** — Windows chấp nhận, không escape.
Verify: `ast.literal_eval` + `Path(r).exists()` đọc từ file sau patch (đừng tin grep).

## Audit độc lập session 17/08 (7/8 APPROVED, 1 NEEDS_FIX P2)
- Lệnh: `codex exec --ephemeral --sandbox read-only -c 'model_provider="9router"' --model ag/claude-opus-4-6-thinking < prompt.txt > transcript.txt`
  (60818 Codex API down → 9router; lỗi `could not lock .gitconfig` transient → retry với
  `HOME=<temp>` + `GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=""`).
- Verdict đọc `tail -c 4000` transcript. Audit bắt P2: xpath "Không quan tâm" có thể match
  context menu khác → fix `@class="android.widget.Button"`; "Follow bạn" và "Không quan tâm"
  là 2 nhánh cây khác nhau → KHÔNG dùng following-sibling.

## Cron mai chạy — verify thật
Sau fix: giả lập cron (hermes python, cwd=hermes/scripts) → runner tạo `runner-live-lease/2026-08-18.json`
+ spawn `run-feed-session.ps1 -Row 1 -Machines <74 máy>` (đúng hành vi cron tick).

## 🔴 Quy tắc CHỐT sau session này (bài học lớn nhất)
1. **`last_status: ok` của no_agent cron ≠ script đã làm việc** — `cron/output/<id>/*.md`
   ghi `Status: silent (empty output)` là dấu hiệu script exit 0 vô tác dụng; PHẢI verify
   ARTIFACT thật (manifest file sinh chưa, state mới chưa, lease spawn chưa), không tin status.
2. **User đính chính thiết kế 18/08: "Làm đéo có chuyện 1 ngày chạy 6 row thiết kế bị ngu à"**
   — row-slot 17/08 (1 entry/acc theo 6 row cố định = 6 lần/ngày) là HIỂU SAI ý user.
   Thiết kế CHÍNH THỐNG = plan 16/08: **3 ca/ngày (06:00/12:30/19:00) × 3 phiên/ca = 9 phiên/ngày**;
   mỗi ca 1 acc; phiên 2/3 reactive; lane chọn acc (chẵn rows 1-3, lẻ 4-6); máy thiếu acc row → bỏ ca.
   Khi user phủ định 1 model, ĐỐI CHIẾU plan APPROVED gốc trước khi viết lại picker.
3. **Verify cron đúng cách**: chạy deployed wrapper bằng hermes python với cwd = hermes/scripts
   (đúng cách scheduler spawn) + kiểm tra ARTIFACT (manifest/lease/spawn log), không chỉ RC=0.
4. **Skip-identity-verify cho follow hook (user chốt 17/08)**: feed preflight đã chọn nick chuẩn
   → follow chạy liền không verify; flag `--skip-identity-verify` default False (chạy tay vẫn verify
   an toàn) — feed hook truyền flag, engine bỏ `switch_account_and_verify` khi bật.
5. **Popup "Follow bạn" policy (user chốt 17/08, máy 33)**: bấm "Không quan tâm", TUYỆT ĐỐI
   không "Follow lại"; xpath action thêm `@class="android.widget.Button"` (tránh context menu khác);
   "Follow bạn" và "Không quan tâm" ở 2 nhánh cây khác nhau nên KHÔNG dùng following-sibling.