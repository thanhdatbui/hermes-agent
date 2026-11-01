# Pitfall & Quy chuẩn: Bốc Nick Trong Dynamic Shift-Pool (Chống Kẹt Nick Đi Tù & Cooldown)

## 1. Bản Chất Nghiệp Vụ Về Cooldown & Đi Tù (Fail Streak)
- **Tài khoản bị nhả (Follow Drop) hoặc fail streak là THẤT BẠI THỰC TẾ (FAIL)**, đang chịu án phạt kỷ luật của hệ thống hoặc TikTok.
- **TUYỆT ĐỐI CẤM** ngụy biện hoặc coi trạng thái skip follow do Cooldown / Dưỡng sinh là "đã hoàn thành nuôi để nhường lượt".
- **QUY TẮC CỐT LÕI KHI BỐC NICK TRONG POOL `{Row A, Row B, Row C}`**:
  * Nick đang ngồi tù / dính án phạt cooldown (`follow_failed=True`, `is_in_cooldown=True`, `fail_streak > 0`, hoặc `today <= cooldown_until_date`) **BẮT BUỘC BỊ ĐẨY XUỐNG RANK CUỐI CÙNG (`Rank 99`)**.
  * Máy **TUYỆT ĐỐI KHÔNG ĐƯỢC BỐC** nick đang đi tù ra chạy nếu trong Pool vẫn còn các Row sạch khác!
  * Phải bốc các Row sạch khỏe ra chạy nuôi và follow, để nick đi tù nằm yên dưỡng thương đúng số ngày án phạt.

---

## 2. Bẫy Logic Phân Hạng Ngược (_follow_rank Inversion Trap)
- **Điểm nổ đã phát hiện:** Trước đây hàm `_follow_rank` trong `shift_pool_selector.py` từng xếp:
  * `fail_streak > 0` lên **Rank 4** (với tư duy sai lệch là "ưu tiên dưỡng thương").
  * Trong khi nick bình thường sạch cờ lại nằm ở **Rank 6**.
- **Hậu quả nghiêm trọng:**
  * Máy ngày nào cũng bốc đúng cái nick đang bị đi tù/cooldown ra chạy feed.
  * Đến bước follow hook bị cổng chặn -> trả về `skipped` -> không được gọi `mark_shift_account_cycle_completed`.
  * Hôm sau kiểm tra thấy Row đó chưa xong chu kỳ, lại thấy nó ở Rank 4 (cao hơn Rank 6 của các nick sạch khác) -> **LẠI TIẾP TỤC BỐC ĐÚNG NICK ĐÓ RA**.
  * Tạo thành **vòng lặp kẹt vô tận (Deadlock Trap)**: 70/72 máy ngày nào cũng chạy lặp lại đúng 1 Row, các Row sạch khác trong Pool (như Row 4, Row 8) bị bỏ đói không bao giờ tới lượt!

---

## 3. Thứ Tự Phân Hạng Chuẩn Hóa Của `_follow_rank`
```python
def _follow_rank(machine, row: int, today: date) -> int:
    state = _load_state(FOLLOW_STATE_DIR / f'follow_state_{machine}_row_{row}.json')
    cooldown_until = state.get('cooldown_until_date')
    try:
        fail_streak = int(state.get('fail_streak') or 0)
    except (ValueError, TypeError):
        fail_streak = 0

    # 1. BẤT KỲ ROW NÀO ĐANG BỊ PHẠT / COOLDOWN / FAIL ĐỀU BỊ HẤT CẲNG XUỐNG BÉT BẢNG (RANK 99)
    if (
        state.get('follow_failed')
        or state.get('is_in_cooldown')
        or fail_streak > 0
        or (cooldown_until and today.isoformat() <= str(cooldown_until))
    ):
        return 99

    # 2. CÁC ROW SẠCH SẼ ĐƯỢC ƯU TIÊN THEO THỨ TỰ:
    if state.get('graduated') or state.get('healthy'):
        return 1
    if is_account_boosted is not None and is_account_boosted(machine, row):
        return 2
    try:
        probation = int(state.get('probation_clean_days') or 0)
    except (ValueError, TypeError):
        probation = 0
    if probation >= 1:
        return 3
    return 4  # Row bình thường sạch cờ
```

---

## 4. Xả Án Cooldown Hết Hạn Định Kỳ
- Khi ngày lịch đã vượt quá `cooldown_until_date` hoặc timestamp `cooldown_until_at`, hệ thống có tool `python D:/Taadaa/tools/reconcile_expired_cooldowns.py` để quét và gỡ cờ `is_in_cooldown=False`, `follow_failed=False`, đưa nick trở về trạng thái sạch sẽ tự nhiên.
