# Case Study: Dashboard UI Telemetry, Empty-State Edge Cases & 84→86 Closeout Remediation (2026-10-08)

## 1. Context & Problem Statement
- **User Request:** Tiếp tục xử lý một session bị treo/lỗi từ ảnh chụp Telegram ("Ủa k làm nốt ở session này đc à" kẹt ở iteration 7/200 do lỗi Gemini HTTP 400 turn order mismatch).
- **Phạm vi công việc:**
  - Chuẩn hóa nhãn hiển thị từ `Nấc 1 / 2 Thử Thách` sang `Hồi phục 1` và `Hồi phục 2` trên `tiktok_dashboard.py`.
  - Bổ sung hiệu ứng tương tác bấm thẻ (`.fleet-kpi.clickable`): hover lift (`translateY(-3px)`), active press (`translateY(-1px)`), và trạng thái active highlight (`linear-gradient` + accent border + indicator dot) đồng bộ với dàn thẻ KPI chính.
  - Tự động đồng bộ class `.active` trong JavaScript khi người dùng click lọc danh sách Follow Health (`filterFollowHealth`).

---

## 2. Reviewer 84/100 Scorecard Plateau Diagnosis
Khi chạy Closeout Gate lần đầu sau khi sửa UI và thêm test render HTML cơ bản, Sol Auditor (:20129) chấm **84 / 100 (Threshold >= 85) — REJECTED** với các phát hiện:
1. **Deduction ở tiêu chí `Telemetry & Obs: 8/15`:**
   Reviewer đánh giá: *"Thay đổi chủ yếu tập trung vào dashboard presentation và trạng thái active của KPI; chưa thấy bổ sung telemetry mới hoặc metric giúp theo dõi hành vi người dùng/chẩn đoán lỗi."*
2. **Thiếu kiểm thử dữ liệu biên / Edge Cases:**
   Reviewer đánh giá: *"Cần bổ sung test cho các nhánh tương tác JavaScript filterFollowHealth, trạng thái chuyển đổi active KPI giữa nhiều nhóm, và dữ liệu bất thường/missing state để tránh lỗi runtime phía client."*

---

## 3. Remediation Pattern: Breaking the 84 Plateau to 86 APPROVED

### A. Frontend Defensive Logging & Diagnostics
Không chỉ render template thụ động, bổ sung structured diagnostic logging và cảnh báo khi thiếu DOM element trong handler:
```javascript
const fhKpiMap = {
    'healthy': 'kpi-fh-healthy',
    'probation_tier1': 'kpi-fh-t1',
    'probation_tier2': 'kpi-fh-t2',
    'cooldown_s1': 'kpi-fh-cooldown'
};
document.querySelectorAll('.fleet-kpi.clickable').forEach(el => el.classList.remove('active'));
const activeKpi = document.getElementById(fhKpiMap[group]);
if (activeKpi) {
    activeKpi.classList.add('active');
} else {
    console.warn(`[FollowHealth] KPI element not found for group: ${group}`);
}
console.log(`[FollowHealth] Filter applied: ${group}, autoRefresh: ${isAutoRefresh}`);
```

### B. Backend Telemetry Contract Verification
Trong `test_tiktok_dashboard_history.py`, bổ sung kiểm thử xác nhận hợp đồng telemetry có cấu trúc ở tầng backend API (`/api/follow-health`):
- `status_code: 200`
- `duration_ms: float` (đo độ trễ thực thi endpoint)
- `total_accounts: int`
- `healthy_count: int`
- `error: None`

### C. Exhaustive Edge Cases & State Transition Tests
Viết thêm các unit test hermetic dùng `tmp_path`:
1. **Empty / Missing State Test (`test_follow_health_helper_missing_and_empty_state`):**
   - Kiểm tra database SQLite rỗng không có snapshot.
   - Thư mục state rỗng không có file `follow_state_*.json`.
   - Xác nhận hàm helper xử lý an toàn không văng exception, trả về `total_tracked: 0`, `healthy_full: 0`, `accounts: []`.
2. **Multi-Tier Transition Test (`test_follow_health_backend_telemetry_and_transitions`):**
   - Tạo fixtures cho 2 máy với `clean_days` lần lượt ở ngưỡng Hồi phục 1 (2 ngày sạch) và Hồi phục 2 (4 ngày sạch).
   - Xác nhận nhãn `tier_label` chuyển đổi chính xác, hoàn toàn sạch chữ "Thử Thách".

### D. Kết Quả Sau Remediation
- `pytest test_tiktok_dashboard_history.py`: **12/12 passed (100%)**.
- `closeout_gate.py` re-run: Score tăng vọt lên **86 / 100 — APPROVED (Pass)**.
- Telemetry & Obs tăng từ `8/15` lên `11/15`.
- Farm Safety & Anti-Regression tăng lên `14/15`.

---

## 4. Key Takeaways Cho Closeout Dashboard / UI
1. **Tránh chỉ test HTML string matching:** Reviewer Sol Auditor coi việc chỉ kiểm tra `assert "text" in html` là shallow testing. Luôn phải ghép đôi với:
   - Test kiểm chứng cấu trúc dữ liệu backend & helper.
   - Test telemetry runtime & đo thời gian thực thi.
   - Test dữ liệu biên (rỗng, thiếu file, DB trống).
2. **Staged Candidate Binding Discipline:** Khi sửa file theo remediation findings, bắt buộc chạy `git add <target_files>` trước khi re-run `closeout_gate.py` để audit log ghi nhận chính xác `staged_diff_sha256` khớp với git index.
3. **Zero Manual Push Friction:** Khi gate chuyển sang APPROVED (86/100), Coordinator lập tức thực thi `git commit` và `git push origin main` tự động mà không dừng lại xin phép hay bắt người dùng kiểm tra thủ công.
