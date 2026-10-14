# Chu Kỳ 4 Ngày & Quy Luật Chọn Row Dưỡng Sinh Động (Taadaa Farm)

Tài liệu này tổng hợp cấu trúc chu kỳ nuôi acc TikTok 4 ngày, quy luật chọn row cố định và thuật toán chọn row dưỡng sinh động (`healing_selector.py`), cùng các bẫy đường dẫn khi deploy runner.

---

## 1. Cấu Trúc Chu Kỳ 4 Ngày (96h Parity)

Farm vận hành theo chu kỳ cố định 4 ngày (96 giờ) để đảm bảo mỗi row được quay lại nuôi đúng nhịp, tránh hiện tượng starve (bỏ đói > 108h):

- **Ngày 1 (cycle_day = 0):**
  - Ca 1 (Sáng: 06h, 08h): Row 1
  - Ca 2 (Trưa: 12h, 14h): Row 3
  - Ca 3 (Tối: 18h, 20h): Row 5
- **Ngày 2 (cycle_day = 1):**
  - Ca 1 (Sáng: 06h, 08h): Row 2
  - Ca 2 (Trưa: 12h, 14h): Row 4
  - Ca 3 (Tối: 18h, 20h): Row 6
- **Ngày 3 (cycle_day = 2):**
  - Ca 1 (Sáng: 06h, 08h): Row 7
  - Ca 2 (Trưa: 12h, 14h): Row 8
  - Ca 3 (Tối: 18h, 20h): Ca dưỡng sinh tối (chọn Row 3 hoặc 4 pure feed)
- **Ngày 4 (cycle_day = 3) — DƯỠNG SINH ĐỘNG TOÀN FARM:**
  - Cả 3 ca (Ca 1, Ca 2, Ca 3) đều là slot dưỡng sinh (`target_row is None`).
  - Runner BẮT BUỘC gọi `healing_selector.py` để chấm điểm và chọn Row acc yếu nhất cần phục hồi.

---

## 2. Thuật Toán Chọn Row Dưỡng Sinh Động (`healing_selector.py`)

Công thức tính điểm ưu tiên hồi phục cho từng row:
$$\text{Score} = 100 \times p_{\text{fail}} + 20 \times p_{\text{young}}$$

Trong đó:
- $p_{\text{fail}}$: Tỷ lệ tài khoản bị dính cooldown hoặc lỗi follow (`follow_failed`) lấy từ `D:/Taadaa/tiktok-follow/runs/state`.
- $p_{\text{young}}$: Tỷ lệ tài khoản non (< 10 video) lấy từ `snapshots` trong `D:/Taadaa/data/tiktok_tracker.db`.

### Các Ràng Buộc Điều Phối Bắt Buộc:
1. **S2 bám S1 (Session Pairing):** Phiên 2 (08h, 14h, 20h) LUÔN LUÔN chạy cùng Row với Phiên 1 (06h, 12h, 18h) trong cùng một ca.
2. **Chống kẹp ca (Anti-consecutive):** Phiên 1 của ca sau loại trừ `last_row` của ca liền trước, không để 1 row chạy 2 ca liên tiếp.
3. **N4 3 ca 3 row (Rest Day Diversity):** Trong Ngày 4, các ca tiếp theo trong ngày loại trừ các Row đã được chọn dưỡng sinh trước đó trong cùng ngày (`today_runs`).
4. **Cache & Audit:** Cache tỷ lệ 60s; ghi nhận quyết định vào `D:/Taadaa/runtime/audit_logs/healing_decision_audit.jsonl` (schema 1.0, tự rotate khi > 5MB).

---

## 3. Bẫy Triển Khai Runner Ngoại Vi (Deploy Path & Fallback Trap — 2026-10-14)

### Hiện Tượng:
Ngày 4 dưỡng sinh nhưng hệ thống lại chạy cố định **Row 3 (Sáng) - Row 4 (Trưa) - Row 5 (Tối)**, lặp lại cùng một mẫu tĩnh ngày này qua ngày khác.

### Nguyên Nhân Gốc Rễ:
- Script `tiktok_runner.py` khi chạy qua Cron nằm ở thư mục deploy trên ổ `C:` ngoài git repo.
- Hàm `_load_determine_healing_row()` chỉ tìm kiếm `healing_selector.py` bằng cách duyệt các thư mục cha `Path(__file__).resolve().parents`. Vì script nằm trên `C:`, các thư mục cha không bao giờ trỏ tới `D:/Taadaa/tools`.
- Đồng thời `env.json` chưa gán `HERMES_CRON_TOOLS_DIR`.
- Kết quả: văng `ImportError: healing_selector.py not found`, code nhảy vào khối `except` kích hoạt **fallback tĩnh định sẵn** (Ca 1 -> Row 3, Ca 2 -> Row 4, Ca 3 -> Row 5).

### Giải Pháp Khắc Phục Bắt Buộc:
1. Trong `tiktok_runner.py`:
   - Hàm `_load_determine_healing_row()` phải đọc `repo_env_overrides().get("HERMES_CRON_TOOLS_DIR")`.
   - Nếu chưa có, quét các candidate roots chuẩn (`D:/Taadaa/tiktok-luot nuoi acc/tools`, `D:/Taadaa/tools`, `D:/Taadaa/automation-core/tools`).
2. Trong `runtime/hermes-cron/env.json`: Khai báo tường minh `"HERMES_CRON_TOOLS_DIR": "D:/Taadaa/tools"`.
3. Kích hoạt `cron_sync_watchdog` để đồng bộ ngay lập tức sang runtime.
