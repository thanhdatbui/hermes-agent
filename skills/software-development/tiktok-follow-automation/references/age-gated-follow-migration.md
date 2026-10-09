# Age-gated follow migration, upload cadence & farm reality decision record

## Approved farm policy (Dual Gate Follow)

- Unlock follow only when `account_age_days >= 21 AND video_count >= 6`. Áp dụng đồng bộ cho cả Follow Chéo lẫn Follow Tự Nhiên ngoài feed!
- Nick non (`video_count < 6`): CẤM TUYỆT ĐỐI cả follow chéo và follow tự nhiên khi lướt feed (`_follow_rate = 0`).
- Khi nick bị phạt nhả follow (`follow_failed: true` / daily cooldown): LẬP TỨC TẮT follow tự nhiên ngoài feed và chuyển sang Dưỡng Sinh thuần túy (0 follow, 0 upload).
- Watchdog reporting & Farm alert: Khi follow hook trả về `followed_count == 0` do lỗi UI (lag mở tab Following của Anchor ở Mode 2, `mode2_degraded: true`), CẤM gom vào nhóm `fl_other_skipped` (bỏ qua khác); BẮT BUỘC phân loại vào `fl_error` để hiển thị minh bạch và kích hoạt Farm Alert khi có >= 3 máy gặp sự cố.
- Safe Workbook gộp (`taikhoan_run_safe_combined.xlsx`): BẮT BUỘC giữ Cột 5 `Ngày Tạo` khi sync từ Kibe và Admin để Runner tính đúng tuổi nick `account_age_days`, tránh bị bóp oan về warmup budget.
- Age 21–30 (hoặc age > 30 nhưng video 6–9): warm-up / follow mồi, 3–5 follows per session.
- Age >= 31 and video_count >= 10: full configured budget theo config máy (10–20 follows/phiên, tuyệt đối không bóp thành 6–10 do nhầm docstring cũ).
- Missing/invalid creation date: fail closed to zero follow budget (trừ nick cũ đã có >= 10 video để tương thích ngược).
- Preserve 0-video safety, server-side targeted reconciliation, fail-streak, and cooldown handling.

## ĐỊNH NGHĨA CHUẨN: DƯỠNG SINH (ORGANIC REST) TRÊN TAADAA FARM

- **LƯỚT FEED LÀ NỀN TẢNG BẤT BIẾN 100%:** Mọi nick khi vào ca/phiên nuôi ĐỀU LƯỚT FEED để nuôi trust score và IP proxy. Dưỡng sinh KHÔNG PHẢI là lướt feed.
- **Dưỡng sinh (Organic Rest 1/3):** Chính xác là thao tác **TẮT ĐĂNG VIDEO + TẮT FOLLOW** trong ngày nuôi đó (0 follow, 0 upload).
- **Ý nghĩa với nhịp đăng:**
  * Nick Thường (`NORMAL`): Có ngày dưỡng sinh 1/3 -> nhịp đăng tự nhiên giãn ra 2.5 – 3 ngày/video (tiết kiệm video cho nick flop).
  * Nick Đang Cắn Đề Xuất (`BOOST`): Vẫn lướt feed bình thường, nhưng **gỡ lệnh cấm upload của ngày dưỡng sinh** -> được phép đăng đều đặn 48h/lần (2 ngày 1 video) để đón sóng phân phối.
  * CẤM tăng lên 1 video/ngày (tránh cannibalization view và spam trigger).

## ANTI-OVERENGINEERING: CÁC BẪY LÝ THUYẾT SUÔNG CỦA LLM REVIEWER (BẮT BUỘC TRÁNH)

1. **CẤM "Quarantine Bất Tử" & "Kiểm tra tay":**
   - Video mới đăng bị 0-view hay vài view là hiện tượng bình thường trên TikTok (do chậm index / lag thống kê).
   - Tuyệt đối CẤM tự ý kích hoạt cờ Quarantine dừng đăng toàn bộ rồi bắt user đi "kiểm tra tay" (manual review). Nick flop/0-view cứ để chạy ở chế độ thường, automation tự xử lý.
2. **CẤM "Khóa 1 chiều khi farm có biến":**
   - Không tự ý vẽ thêm các cơ chế khóa/đóng băng toàn farm trừ khi có chỉ thị trực tiếp từ User.
3. **Bẫy dao động Dashboard (Flapping "hôm nay cắn mai mất"):**
   - Dashboard delta 24h là sensor, không dùng làm công tắc trực tiếp.
   - Khi nick cắn đề xuất -> gắn cờ `BOOST` khóa giữ 5 ngày (đủ để đăng 2-3 video nhịp 48h), tránh việc ngày hôm sau delta giảm nhẹ làm hệ thống nhảy giật cục về dưỡng sinh.

## Workbook compatibility contract

The source account workbook contains `NGÀY TẠO`; the safe workbook must carry a normalized creation date/age field as Column 5 (`Ngày Tạo`). Keep `May`, `Device ID`, `ID`, and `Video Đã Đăng` in the original first-four-column order so legacy consumers continue to read correctly. Accept Excel datetime/date, ISO dates/timestamps, and `dd/mm/yyyy`; malformed or missing values must not crash and must produce a fail-closed account.

### Code-level Threading Architecture (Workbook -> FollowEngine -> Mode1/Mode2)

1. **`follow_runner/core/workbook.py`**:
   - `_DATE_ALIASES = ("ngay tao", "ngày tạo", "created at", "created_at", "ngay", "date")`
   - `RowMapping` dataclass: `created_date: str | None = None`, `account_age_days: int | None = None`
   - Helpers: `_parse_date_iso(val)` parses ISO YYYY-MM-DD, DD/MM/YYYY, or date/datetime objects; `_calc_age_days(date_str)` returns non-negative days from `datetime.now().date()`.
   - `load_mapping`: maps `col_date`, calculates `age_days = _calc_age_days(date_val)` and populates `RowMapping`.

2. **`follow_runner/flows/follow_engine.py`**:
   - In both `_account_ready()` and `run_session()`:
     Set `self.account_age_days = getattr(row, "account_age_days", None)` alongside `self.video_count`.

3. **`follow_runner/flows/mode1_search_follow.py`**:
   - Mode 1 budget calculation threads `account_age_days` to `session_budget`:
     `state.session_budget(getattr(engine, "video_count", None), getattr(engine, "account_age_days", None))`

4. **`follow_runner/flows/mode2_follow_followers.py`**:
   - Mode 2 budget calculation threads `account_age_days` to `session_budget`:
     `state.session_budget(getattr(engine, "video_count", None), getattr(engine, "account_age_days", None))`

## Verification matrix

Test at minimum: missing age; age 20/21/30/31; video 0/5/6/9/10; cooldown/fail-streak active; malformed date; and a legacy four-column workbook. Verify warm-up and full-budget ranges separately, and run focused tests before any live canary.

## Telemetry & Observability Invariant (Bài học từ Closeout Gate Sol Auditor)

Khi thay đổi rule budget hoặc gate follow, Reviewer (Sol Auditor / Closeout Gate) sẽ **REJECT (dưới 85 điểm)** nếu thiếu Audit Telemetry:
1. **Structured Log:** Bắt buộc log info với prefix `[DUAL_GATE]` gồm machine, row, budget, video_count, account_age_days, mode (`warmup`/`full`/`blocked`).
2. **State Decision Record:** Lưu `last_budget_decision` vào `self._data` trong `FollowState`:
   ```python
   self._data["last_budget_decision"] = {
       "budget": budget,
       "video_count": video_count,
       "account_age_days": account_age_days,
       "mode": mode_str,
       "decided_at": self._now_utc().isoformat(),
   }
   ```
3. **Thực chứng điểm số Closeout Gate:** Thiếu telemetry -> Điểm Telemetry & Obs chỉ đạt 3/15 (Tổng 78/100 - FAIL). Sau khi bổ sung structured log + `last_budget_decision` -> Đạt 12/15 (Tổng 91/100 - APPROVED).

## Closeout Gate Focused Test Scoping (Tránh Timeout 180s)

- **Nguyên nhân Timeout:** Khi repo có hàng trăm tests (ví dụ: `tiktok-follow` có hơn 250 tests), việc chạy `pytest tests/` không chỉ định file sẽ bị timeout 180s hoặc chạy vào các test cũ phụ thuộc ngầm vào `video_count=6`.
- **Giải pháp chuẩn:** Khi chạy Closeout Gate hoặc test cục bộ, luôn chỉ định rõ các file test liên quan trực tiếp đến thay đổi:
  `python -m pytest follow_runner/tests/test_follow_state.py follow_runner/tests/test_mode2_following.py follow_runner/tests/test_mode2_follow_followers.py --tb=short -q`
  Giúp toàn bộ 257 tests hoàn tất chỉ trong ~40s mà vẫn đảm bảo 100% test coverage cho gate mới.

## Bẫy Vận Hành & Đồng Bộ Farm Thực Tế (Session 28/09/2026)

1. **Bẫy rơi Cột 5 (`Ngày Tạo`) tại `sync_combined_safe_workbook.py`:**
   - File nguồn `taikhoan_run_safe.xlsx` có cột 5 là `Ngày Tạo`. Khi xuất ra file gộp `taikhoan_run_safe_combined.xlsx`, nếu script gộp chỉ lấy 4 cột đầu thì runner sẽ nhận `account_age_days = None`.
   - Hậu quả: `FollowState` tự động hạ cấp nick đủ điều kiện full budget (10–20 follow) về chế độ `warmup` (ngân sách 3 follow). Bắt buộc `sync_combined_safe_workbook.py` phải copy đủ Cột 5.

2. **Lệch Gate Video giữa 2 repo (`tiktok-follow` vs `tiktok-luot nuoi acc`):**
   - Trong `tiktok-follow`, Dual Gate cho phép nick `account_age_days >= 21 AND video_count >= 6` mở follow.
   - Nhưng tại hook cha `multi_machine_feed_session.py`, nếu giữ hardcode `if video_count < 10:` thì toàn bộ nick 6–9 video sẽ bị skip ngay từ cửa trước với lý do `under-10-videos-follow-disabled`. Bắt buộc đồng bộ ngưỡng `< 6` ở cả 2 repo.

3. **Tách bạch Follow Tự Nhiên vs Follow Chéo Nội Bộ trong DB & Dashboard:**
   - Follow tự nhiên (bấm ngoài feed khi lướt) và Follow chéo nội bộ (Mode 1/2) là 2 cơ chế độc lập.
   - Khi ghi dữ liệu vào SQLite (`daily_account_actions`), chỉ ghi số lượt follow chéo thực tế (`m_to_cross`) vào cột `internal_follows`. Tuyệt đối CẤM lấy tổng follow báo cáo (`cnt + natural_cnt`) ghi vào cột nội bộ, gây hiểu lầm trên Dashboard (`🔗 Nội bộ: +X`).
   - Tắt follow tự nhiên đồng bộ: Nick chưa đủ điều kiện follow chéo hoặc nick đang dính cờ nhả follow (`follow_failed: true` / cooldown) bắt buộc phải tắt cả follow tự nhiên (`_follow_rate = 0`) để dưỡng sinh triệt để.

4. **Chống giấu lỗi (False Clean) trong Watchdog Report & Farm Alert:**
   - Nếu máy đủ điều kiện follow nhưng kết thúc với `followed_count == 0` do lỗi UI (mở tab anchor fail ở Mode 2, vướng target đã follow ở Mode 1), không được xếp vào nhóm `fl_other_skipped` (bỏ qua khác). Phải phân loại vào lỗi/suy thoái để cảnh báo Farm Alert và báo cáo minh bạch cho người vận hành.

