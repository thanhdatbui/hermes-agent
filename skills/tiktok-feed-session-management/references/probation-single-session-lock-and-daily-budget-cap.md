# Cơ chế PROBATION_SINGLE_SESSION_LOCK & Daily Budget Cap

## Ngữ cảnh & Triệu chứng
Trong ca chạy có nhiều phiên trong ngày (ví dụ Ca 2 gồm Phiên 1/2 và Phiên 2/2):
- Phiên 1: Một số máy (vd: M5, M68) thực hiện follow thành công (2-4 lượt follow thật, đối soát khớp 100%).
- Phiên 2: Cũng các máy đó, follow runner chạy hoàn tất với `status: OK` nhưng `followed: 0`, không follow thêm nick nào.

## Nguyên nhân gốc (Root Cause)
Tài khoản đang trong diện **Probation** (Hồi phục sau vi phạm/cooldown, `is_graduated = False`):
- Khi tài khoản mới hết hạn cooldown nhả follow, nó bước vào chu kỳ dưỡng Probation Tier 1 (`clean_days = 0`) hoặc Tier 2 (`clean_days = 1`).
- Trong `follow_runner/core/follow_state.py`:
  ```python
  def _probation_budget(clean: int) -> tuple[int, str]:
      tier = f"probation_tier{1 if clean < tier1_threshold else 2}"
      cap = t1_cap if clean < tier1_threshold else t2_cap
      if _safe_int(self._data.get("budget_used", 0), 0) > 0:
          logger.info("[PROBATION_SINGLE_SESSION_LOCK] machine=%s row=%s tier=%s", self.machine, self.account_row_index, tier)
          return 0, tier
  ```
- **Quy tắc Single Session Lock:** Tài khoản Probation chỉ được phép follow tối đa **1 phiên duy nhất mỗi ngày**.
- Khi Phiên 1 đã thực hiện follow và ghi nhận `budget_used > 0`, sang Phiên 2 `session_budget` lập tức kích hoạt khóa an toàn `PROBATION_SINGLE_SESSION_LOCK` và trả về `budget = 0`.
- Runner vẫn chạy feed bình thường và kết thúc hook follow an toàn với `status: OK, followed: 0`.

## Triage Checklist khi máy báo 0 Follow
1. Kiểm tra `follow_state_{machine}_row_{row}.json`:
   - `is_graduated`: nếu `false`, tài khoản thuộc diện probation.
   - `budget_used`: nếu `> 0`, tài khoản đã cắn quota ngày ở phiên trước.
2. Xác nhận log: Tìm log `[PROBATION_SINGLE_SESSION_LOCK]`.
3. Kết luận: Đây là cơ chế fail-safe chủ động bảo vệ nick sau phạt, tuyệt đối không phải lỗi script, không phải treo socket ADB hay lỗi thiếu anchor.
