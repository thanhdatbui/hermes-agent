# VPN Preflight Gate + Antidetect Jitter — Tiktok_Reg (verify 2026-08-18)

Trạng thái đã verify trên branch `reg-stable-0722` (HEAD `3890613`), dùng **production
interpreter** `D:\Taadaa\python-envs\automation\Scripts\python.exe` (editable install của
`D:\Taadaa\automation-core`).

## VPN Preflight Gate — fail-closed (commit c465eb9 + 3890613)

- Nằm trong `preflight_concurrency_gate()` (`social_reg_v1.py` ~dòng 763-791), sau
  source-workbook gate, trước `if blockers:` chung.
- Flow:
  1. `mapping_path = resolve_proxy_mapping_path()` — fail-closed: raise
     `ConsumerPreflightError` nếu thiếu `TAADAA_HOST_CONFIG`, `workbook_root` invalid,
     hoặc file mapping missing. KHÔNG fallback sang workbook host khác.
  2. `vpn_required = serial_is_mapped_in_workbook(mapping_path, device_id,
     serial_headers=("phoneId", "deviceId", "serial"))` — device có trong mapping
     workbook → bắt buộc VPN.
  3. `require_android_vpn(AdbClient(adb_path=ADB_PATH, serial=device_id,
     default_timeout=20), required=vpn_required)`.
- Blocker codes (cả hai đều fail-closed, raise qua gate chung):
  - `VPN_PREFLIGHT_BLOCKED(<exc>)` — `ConsumerPreflightError`: VPN required nhưng
    không connected (evidence: `interface=tun0 tun_up=... vpn_connected=...`), hoặc
    mapping workbook không đọc được.
  - `VPN_PREFLIGHT_ERROR(<exc>)` — bất kỳ exception nào khác. LƯU Ý: trước 3890613
    nhánh này fail-open ("skipped non-fatal") — đã sửa thành fail-closed theo review.
- Host config máy kibe: `TAADAA_HOST_CONFIG=D:\Taadaa\machine-config\kibe.yaml` →
  `workbook_root: D:/OneDrive/TaadaaData/kibe` → mapping file `PROXYgandienthoai.xlsx`.
- Workbook thật: sheet `Proxy`, header `['Máy', 'device ID', 'proXy']`. Alias khớp nhờ
  normalization: `device ID` → `deviceid` == `deviceId` → `deviceid`. Serial mẫu:
  `9885b64957334f5a46` (mapped=True), `99999999` (mapped=False).

## Diagnose khi batch bị block

- `VPN_PREFLIGHT_BLOCKED`: check (1) device có trong mapping workbook không (cột
  `device ID`), (2) VPN trên máy có connected không
  (`adb -s <serial> shell dumpsys connectivity | grep -i vpn`), (3) mapping workbook
  có đọc được không (file bị khóa/missing → fail-closed chặn luôn).
- `VPN_PREFLIGHT_ERROR`: đọc exc — thường do `AdbClient`/`ADB_PATH` hoặc bản
  automation-core không có `resolve_proxy_mapping_path` (xem mục Verify bên dưới).

## Antidetect jitter (commit 3643327 + 3890613)

- `tap()` và `swipe()` helper jitter tọa độ ±4-6px (`_jitter(coord, max_offset=6)`;
  swipe dùng `_jitter(x, 4)`).
- 100% swipe đã chuyển qua `swipe()` helper — `grep -n '"input", "swipe"'` chỉ còn
  **1 hit duy nhất** (dòng bên trong chính helper, ~261).
- Còn 7 raw tap chưa jitter (clear-X ~322, `hide_keyboard` 335, dismiss-ad 1653/1736/1766,
  play-store 1771) — ngoài scope review swipe, ghi nhận follow-up.
- `calibrate.py`: UI capture `default_timeout` 45→60s, capture timeout 40→50s.

## Verify pattern (tái sử dụng)

- KHÔNG dùng `python` bare: system Python 3.12 site-packages chứa automation_core CŨ
  (thiếu `resolve_proxy_mapping_path`) → false `AttributeError`. Luôn probe bằng
  production interpreter:
  ```
  /d/Taadaa/python-envs/automation/Scripts/python.exe -c "import automation_core.preflight as p; print(p.resolve_proxy_mapping_path())"
  ```
- Trace xóa constant: `git log -S VICHANGER_PROXY_MAPPING_PATH --oneline -- social_reg_v1.py`
  → chỉ còn commit thêm (c465eb9) + xóa (3890613); grep hiện tại = 0 hit.
