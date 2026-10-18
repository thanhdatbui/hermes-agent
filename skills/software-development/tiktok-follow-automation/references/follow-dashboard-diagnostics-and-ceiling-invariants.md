# Follow Dashboard Diagnostics & Health Ceiling Invariants

## 1. Dashboard Modal vs TikTok External Link Invariant
- **Vấn đề**: Người dùng bấm vào username tài khoản trong header "Sổ Bệnh Án" nhưng không bung ra kênh TikTok.
- **Nguyên nhân**: Trong `tools/dashboard/follow_detail_component.py`, danh sách các UID con được follow (`followed_list`) có gắn thẻ `<a href="https://www.tiktok.com/@${encodeURIComponent(item.uid)}" target="_blank">`. Tuy nhiên ở header modal (`fdModalTitle`), username `@username` lại được render dạng `<span style="color:#38bdf8;">` không có thẻ `<a>`, khiến nó chỉ đổi màu mà không thể click mở trang cá nhân.
- **Giải pháp chuẩn hóa**:
  * Tạo hàm helper `fdModalTitleHtml(username)`:
    ```javascript
    function fdModalTitleHtml(username) {
        if (!username || username === '-') return `📜 Sổ Bệnh Án: <span style="color:#38bdf8;">Chưa gán username</span>`;
        return `📜 Sổ Bệnh Án: <a href="https://www.tiktok.com/@${encodeURIComponent(username)}" target="_blank" rel="noopener" style="color:#38bdf8;text-decoration:none;">@${fdEsc(username)}</a>`;
    }
    ```
  * Áp dụng đồng bộ trong cả `loadFdDetail` (lúc bắt đầu nạp) và `renderFollowDetailModal` (sau khi có data API).

## 2. Cơ chế lưu và hiển thị "Gãy Gần Nhất" (Last Failed Ceiling)
- **Vấn đề**: Ở tab "Hồi phục 1" hoặc "Hồi phục 2", ô "Gãy Gần Nhất" thường hiển thị "Chưa từng" hoặc rỗng dù nick đang có `fail_streak > 0` và từng bị đưa vào cooldown.
- **Nguyên nhân cốt lõi trong code**:
  1. **Chỉ ghi nhận khi nick đã tốt nghiệp (`graduated`)**:
     Trong `tiktok-follow/follow_runner/core/follow_state.py` (hàm `set_follow_failed`), trường `last_failed_ceiling` chỉ được tính toán và lưu vào JSON khi nick đó có cờ `graduated: True` bị thu hồi (revoked):
     ```python
     if self._data.pop("graduated", None):
         failed_ceiling = attempted if attempted is not None else (used + 1)
         self._data["last_failed_ceiling"] = failed_ceiling
     ```
     Nếu tài khoản bị nhả khi đang ở diện Tân binh (rookie), Warmup, hoặc đang trong quá trình Hồi phục (probation clean days < 2), trường này không được ghi nhận trong file state JSON.
  2. **Giải pháp fallback mốc trần ca gãy (`follow_health_helper.py`)**:
     Trong `get_account_follow_detail(machine, row)`:
     ```python
     last_failed_ceiling = _to_int(d.get("last_failed_ceiling"))
     last_failed_date = d.get("last_failed_date") or (d.get("last_failed_at") or "")[:10] or None
     if not last_failed_date and isinstance(d.get("last_cooldown_decision"), dict):
         last_failed_date = (d["last_cooldown_decision"].get("decided_at") or "")[:10] or None
     if last_failed_ceiling is None and last_failed_date:
         last_b = d.get("last_budget_decision")
         if isinstance(last_b, dict) and last_b.get("budget") is not None:
             last_failed_ceiling = _to_int(last_b.get("budget"))
     ```
  3. **Hiển thị thông minh tại Frontend (`follow_detail_component.py`)**:
     ```javascript
     const hasCeiling = data.last_failed_ceiling !== null && data.last_failed_ceiling !== undefined && data.last_failed_ceiling !== '' && data.last_failed_ceiling !== '-';
     const failedDate = data.last_failed_date ? String(data.last_failed_date).slice(5) : '';
     let lastFailedText = 'Chưa từng (sạch)';
     if (hasCeiling) {
         lastFailedText = `${data.last_failed_ceiling} lượt` + (failedDate ? ` · ${failedDate}` : '');
     } else if (failedDate) {
         lastFailedText = `Gãy ${failedDate}`;
     } else if (data.fail_streak > 0) {
         lastFailedText = `Streak ${data.fail_streak}`;
     }
     document.getElementById('fdLastFailed').textContent = lastFailedText;
     ```

## 3. Bản chất 967 nick ở tab "Hồi phục 1" (Probation Tier 1)
- Trong `tools/follow_health_helper.py` (hàm `get_follow_health_data`):
  Hệ thống query toàn bộ tài khoản từ bảng `farm_account_info` trong `tiktok_tracker.db`. Các nick chưa từng chạy flow follow hoặc chưa có file `follow_state_<machine>_row_<row>.json` (khoảng 967 nick) sẽ được gán mặc định:
  ```python
  "tier": "probation_tier1",
  "tier_label": "🟠 Mới / Đang dưỡng",
  "fail_streak": 0
  ```
- Trên giao diện dashboard, nhóm `probation_tier1` được gán tab label là `🌱 Hồi phục 1`.
- Do phần lớn 967 nick này là nick mới hoặc đang dưỡng chưa chạy follow, fail streak = 0 và chưa từng bị fail, nên chỉ số "Gãy Gần Nhất" hiển thị "Chưa từng (sạch)" là hoàn toàn chính xác theo dữ liệu thực tế.

## 4. Quy trình nạp lại Dashboard sau khi sửa code UI/Helper
- Sau khi chỉnh sửa `dashboard/*.py` hoặc `follow_health_helper.py`, tiến trình dashboard trên port 1905 giữ template HTML cũ trong memory.
- Lệnh reload chuẩn:
  1. Dò và tắt PID cũ: `taskkill /PID <pid> /F`.
  2. Relaunch: `python D:/Taadaa/tools/tiktok_dashboard.py --port 1905` (hoặc qua hidden VBS).
  3. Kiểm chứng live:
     - `http://localhost:1905/api/follow-detail?machine=12&row=1`
     - Kiểm tra string `fdModalTitleHtml` và `lastFailedText` trong HTML root `/`.
