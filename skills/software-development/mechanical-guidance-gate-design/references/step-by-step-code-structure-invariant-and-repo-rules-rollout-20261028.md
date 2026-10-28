# Cơ Giới Hóa Cấu Trúc Code Theo Bước & Phủ Toàn Bộ Rules.json Cho Farm Repos (28/10/2026)

## 1. Bài Học Về "Cam Kết Bằng Lời" vs "Cơ Giới Hóa (Mechanical Enforcement)"
- **Hiện tượng vi phạm:** AI và Worker có thói quen viết code "một tràng vô danh" (hundreds/thousands dòng không có comment phân bước hay định danh logic), khiến cho việc kiểm tra git diff, đối soát sự cố và review gần như bất khả thi.
- **Yêu cầu cốt lõi của User:** "Phong cách viết code đừng có cam kết. Cần cơ giới hóa vào GuardGate". Không tin vào lời hứa suông; mọi quy tắc về code style và bài học xương máu bắt buộc phải biến thành **Deterministic Invariant** được GuardGate kiểm tra tự động trước mỗi lần commit.

---

## 2. Rule Cơ Giới Hóa Cấu Trúc Code (`case_invariant_require_step_by_step_structure`)
- **Vị trí:** `D:/Taadaa/tools/guardgate/rules.json` & `predicates.py:check_step_by_step_structure`.
- **Phạm vi:** Toàn farm (`repos: ["*"]`, file `*.py`).
- **Ngưỡng kích hoạt:**
  - Khi diff thêm mới $\ge 15$ dòng code thực sự (đã loại trừ import, dòng trống, comment thuần, docstring).
  - BẮT BUỘC phải chứa ít nhất một comment định danh phân bước:
    * Khớp regex: `#.*(buoc|bước|step|phase|stage|checkpoint)` (case-insensitive)
    * Hoặc banner phân đoạn: `# ===`
- **Xử lý vi phạm:** Nếu $\ge 15$ dòng code thêm vào mà không có comment phân bước $\rightarrow$ GuardGate lập tức trả về **`DENY` (Exit code 1)**, chặn đứng Closeout Gate.

---

## 3. Kiến Trúc 2 Tầng GuardGate: Global vs Repo-Local `rules.json`
GuardGate (`D:/Taadaa/tools/guardgate`) được tích hợp tại **Step 2.5** của `closeout_gate.py`.
Cơ chế tự động nạp rules:
1. **Global Invariants (`D:/Taadaa/tools/guardgate/rules.json`):**
   - 8 luật chung cho toàn farm: cấm `uiautomator dump` (chống OOM S7), cấm quét đĩa diện rộng `D:/`, cấm gán IP domain vào Android, cấm bulk pre-reserve lock, cấm base64 terminal, cấm rogue Wi-Fi SSID, và bắt buộc comment phân bước $\ge 15$ dòng.
2. **Repo-Local Invariants (`<repo>/rules.json`):**
   - `runner.py` tự động nạp `<repo>/rules.json` khi chạy kiểm tra repo đó.
   - **Tất cả các repo farm bắt buộc phải có `rules.json` riêng** đúc kết các commit lịch sử:
     * `tiktok-luot nuoi acc`: Sàn timeout USB 20s (Case 162), trần follow popup = 0 (Case 161), cấm check compound pass, cấm pass ảo.
     * `tiktok-add-bao-mat-f2a`: Cấm bulk lock pre-reserve (Commit `4b55e51`), bắt buộc remote socket `192.168.110.119:5037` cho máy Admin $\ge 200$ (Commit `4d621c6`), bắt buộc `acquire_workbook_lock` có retry/backoff (Commit `ab7127b` & mã thoát 5), cấm gán pass ảo khi cột PASS trống.
     * `register gmail`: Bắt buộc `with device_lock(serial)` (Commit `a11decc`), cấm mật khẩu tĩnh hardcode.
     * `tiktok-follow`: Khóa cứng bậc thang cooldown Follow s1: 24h, s2: 3d, s3: 5d, s4+: 15d (Commit `2a7ff3d`), cấm tap tọa độ mù không qua WinRT OCR (Commit `32ecdcb`).
     * `automation-core`: So khớp chính xác tài khoản trong switcher chống nhầm đuôi số (Commit `989654f`), bắt buộc atomic write/file lock khi ghi file runtime dùng chung.
