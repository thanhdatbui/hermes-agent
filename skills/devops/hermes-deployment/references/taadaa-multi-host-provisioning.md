# Taadaa multi-host provisioning — Kibe (1–80) ↔ Admin (200+)

Session 2026-08-23: setup máy Admin từ đầu qua RDP/screenshots. Toàn bộ quy trình đã chạy thành công — bản chuẩn hóa để tái sử dụng cho host thứ 3 trở đi.

## Bố cục host (đã verify hoạt động)

```
D:\Taadaa\                       ← thư mục cha KHÔNG phải git repo
├── <15 consumer repos>          ← git clone riêng từng repo (branch riêng, xem bảng)
├── machine-config\{kibe,admin}.yaml   ← host config (junction OneDrive)
├── tools\                       ← shared scripts (junction OneDrive)
├── python-envs\automation\      ← venv CHUNG (tạo mới per-host, KHÔNG copy venv)
├── runtime\<host>\              ← state/lock/log per-host (KHÔNG bao giờ copy chéo host)
├── AGENTS.md / HANDOFF.md / HERMES_SUBAGENT_RULES.md
└── HUONG_DAN_CAI_DAT_MAY_ADMIN.md

D:\OneDrive\TaadaaData\<host>\   ← data workbook PER HOST (kibe/, admin/)
D:\OneDrive\Taadaa_Sync_Shared\  ← junction sync realtime: machine-config + tools + rules + .bat scripts
TAADAA_HOST_CONFIG = D:\Taadaa\machine-config\admin.yaml  (User env var)
```

## Branch map (git clone -b)

| Repo | Branch |
|---|---|
| automation-core, Hotmail, tiktok-follow, tiktok-luot-nuoi-acc, open-claw | `master` |
| Tiktok_Reg | `reg-stable-0722` |
| còn lại (tiktok-video, tiktok-log-in, register-gmail, add-mail-khoi-phuc, AI-Tools, gan-proxy, site-ban-hang-clone) | `main` |
| Hermes | upstream `NousResearch/hermes-agent`, `main` |

## Data workbooks: template rỗng, giữ header

Tạo file data cho host mới = **copy structure từ kibe rồi xóa hết rows từ row 2** (giữ nguyên header + toàn bộ sheet). Đã làm cho: PROXYgandienthoai, taikhoan_dat_v2_updated, taikhoan_run_safe, gmail_clean_v2, Tik1–4. Proxy mapping là FILE RIÊNG per host (serial/device ID khác hẳn giữa 2 dàn máy).

## Venv per-host (không copy venv giữa máy)

```powershell
python -m venv D:\Taadaa\python-envs\automation
D:\Taadaa\python-envs\automation\Scripts\python.exe -m pip install -U pip setuptools wheel PyYAML requests openpyxl pillow tzdata pytest
D:\Taadaa\python-envs\automation\Scripts\python.exe -m pip install -e D:\Taadaa\automation-core
```

## Verify cuối (chạy trên host mới)

```powershell
$env:TAADAA_HOST_CONFIG = "D:\Taadaa\machine-config\admin.yaml"
D:\Taadaa\python-envs\automation\Scripts\python.exe -c "import automation_core.preflight as pf; print(pf.resolve_proxy_mapping_path())"
```
→ Lỗi `proxy mapping workbook missing for host` nghĩa là thiếu file xlsx trong `TaadaaData\<host>\` (fail-closed đúng thiết kế, không phải lỗi config).

## Pitfalls gặp thật trong session này

1. **`.bat` double-click trong OneDrive im lặng không chạy** → luôn hướng dẫn paste lệnh PowerShell trực tiếp thay vì batch file.
2. **Private repos cần auth**: `gh` CLI thường chưa cài trên máy mới → dùng 1 lệnh `git clone` thủ công đầu tiên để Git Credential Manager bật browser flow; sau đó clone hàng loạt OK.
3. **User copy lệnh hay mất `-m`** (`python venv` thay vì `python -m venv`; `git clone main URL` thay vì `git clone -b main URL`) → khi user báo lỗi lạ, kiểm tra trước câu hỏi có phải lệnh bị dính/drop token khi copy.
4. **Branch name sai**: plan cũ ghi Tiktok_Reg = `reg-stable-0722` nhưng remote chỉ còn `master`/`main` → luôn check `git ls-remote --heads <url>` trước khi đưa lệnh clone.
5. **Junction OneDrive tạo từ python subprocess `cmd /c mklink`** hoạt động tốt; tạo bằng bash quoting thì fail syntax — dùng python subprocess với list args.
6. **9Router key**: xem skill `9router-proxy-ops` → `references/remote-lan-access-auth.md` (dummy key luôn bị reject, lấy key thật từ sqlite).
7. **Firewall LAN**: Test-NetConnection từ chính host server luôn True (loopback) — không chứng tỏ rule mở. Rule firewall cần tạo bằng PowerShell RunAs trên máy chủ; nếu TCP vẫn thông mà chưa thấy rule, kiểm tra rule allow sẵn của process node.exe trước khi kết luận firewall chặn.
8. **Hermes CLI trên máy mới chưa có**: các bước `hermes config set ...` yêu cầu cài Hermes trước (`pip install -e D:\Taadaa\Hermes` hoặc setup-admin.ps1 trong repo deploy/).
