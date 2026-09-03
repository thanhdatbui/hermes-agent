# Windows host tooling gotchas (Taadaa repos, D:\Taadaa\... có dấu cách)

Nhận từ session sửa `NoneType.get` trong entrypoint multi-machine-feed-session (22/08). Áp dụng mọi lần thao tác repo trên host Windows này.

## 1. `search_files` bẻ gãy đường dẫn có dấu cách
- Convert `D:\Taadaa\tiktok-luot nuoi acc` → `/d/Taadaa/tiktok-luot nuoi acc`, rg trả `IO error: The system cannot find the path specified (os error 3)` DÙ file tồn tại.
- **KHÔNG dùng search_files với repo path này.** Thay thế:
  - `terminal` + `grep -n "pattern" path\file_cụ_thể.py` (Windows path nguyên bản, có ngoặc kép).
  - `read_file` với Windows path gốc — tool này hoạt động đúng.
- Nếu bắt buộc search_files: copy repo ra thư mục temp KHÔNG dấu cách rồi search. Nhưng đơn giản nhất là né nó.

## 2. `grep -r` / `rg` đệ quy treo (timeout 900s)
- Treo vì lặp vào `.ai-runs/`, `runs/`, `__pycache__/`.
- Luôn giới hạn: `grep -n "x" file.py` trên file đã biết, hoặc `grep -rln "x" core/ flows/ tests/` chỉ liệt kê thư mục nguồn. Đừng `grep -r .` từ gốc.
- Set timeout ngắn (30–60s) trên terminal call.

## 3. `cd` repo trong terminal
- Dùng Windows path nguyên bản có ngoặc kép: `cd "D:\Taadaa\tiktok-luot nuoi acc"`. Git/ls/grep qua bash MSYS đều nhận.

## Context áp dụng
- Repo: `D:\Taadaa\tiktok-luot nuoi acc` (python_runner/).
- Lỗi gốc (NoneType.get): `load_config` deep_merge để YAML `safety: null`/`timeouts: null` thay thế dict; fix tập trung tại `run_tiktok.py` + `core/device.py` + normalization tại load_config, fail-closed, không crash CLI entrypoint. (Xem diff session.)
