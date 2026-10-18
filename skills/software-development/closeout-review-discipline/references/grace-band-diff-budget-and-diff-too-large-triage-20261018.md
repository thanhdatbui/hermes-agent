# Grace Band Line Budget, Diff Ceiling (30KB) & State Machine Scoring Rubric (2026-10-18)

## 1. Giới Hạn Kích Thước Diff Của Closeout Gate (Diff Ceiling 30KB)
- **Cơ chế Fail-Fast:** `closeout_gate.py` giới hạn toàn bộ candidate diff tối đa 30,000 bytes (`DIFF_TOO_LARGE`).
- **Hiện tượng:** Khi tích lũy nhiều file sửa đổi dở dang (ví dụ 8-9 files gồm cả core, flows, tests), lệnh chạy gate toàn repo sẽ văng:
  `[Gate Fail-Fast: DIFF_TOO_LARGE] targeted diff quá lớn (31728 > 30000 bytes). Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.`
- **Giải pháp chuẩn:** Phân rã theo ngữ nghĩa thành các cụm task độc lập, sử dụng tham số `--files <file_logic> <file_test>` để giới hạn diff dưới 30KB cho mỗi lần thẩm định.

## 2. Điều Kiện Kích Hoạt Token Của Grace Band (80–84 Điểm)
- **Ngưỡng Ngân Sách Theo `closeout_policy.json`:**
  ```json
  {"strict_threshold": 85, "grace_threshold": 80, "budget": {"max_files": 2, "max_lines": 80}}
  ```
- **Bẫy Ngộ Nhận Điểm 82:**
  - Điểm 80–84 được ghi nhận `APPROVED` và `grace_band: True` trong scorecard.
  - TUY NHIÊN, hàm `_grace_ok(evidence, policy["budget"])` trong `gate_common.py` kiểm tra chặt chẽ:
    `0 <= diff_files <= 2` VÀ `0 <= diff_lines <= 80`.
  - Nếu diff vượt quá 80 dòng (ví dụ 348 dòng do có nhiều test bổ sung), gate sẽ in:
    `[CLOSEOUT_TOKEN_SKIPPED: score 82 rejected: grace_conditions_unmet]`
  - **Quy tắc bắt buộc:** Với các diff tính năng lớn (> 80 dòng), KHÔNG THỂ dựa vào Grace Band để push, mà BẮT BUỘC phải đạt điểm khắt khe `STRICT_APPROVED` ($\ge 85/100$) từ Sol Auditor.

## 3. Tiêu Chí Khắc Phục Để Đạt Điểm $\ge 85$ Cho Logic Quota / Adaptive Ceiling
Khi thẩm định các tính năng dò trần thích ứng, điều chỉnh quota, hay máy trạng thái (state machine), Sol Auditor trừ điểm rất nặng (rơi về 78-79) nếu thiếu các bằng chứng sau:
1. **Toàn Vẹn Tín Hiệu Thành Công:** Không được tăng ceiling chỉ dựa vào `budget_used >= base_max`. Bắt buộc kiểm tra phiên không bị đánh dấu thất bại (`follow_failed` hoặc `last_session_failed`).
2. **Chuẩn Hóa Đường Biên Cấu Hình:** Xử lý triệt để trường hợp cấu hình dị thường (`base_min > base_max`, giá trị âm, None).
3. **Phòng Ngự Dữ Liệu Rác / Sai Kiểu:** Ép kiểu an toàn không ném Exception khi gặp `video_count`, `account_age_days` là chuỗi, boolean, None hoặc âm.
4. **Kiểm Thử Persistence:** Có unit test xác nhận các trường trạng thái (`proven_safe_ceiling`, `active_ceiling`, cohort) được bảo toàn nguyên vẹn qua chu kỳ lưu và nạp lại từ disk.

## 4. Bẫy Rút Cạn Hàng Đợi XML Trong Mock Adapter (`xml_queue`)
- Khi viết unit test cho các flow có bước phụ (như `pull_to_refresh_profile` hay `_screen_size`), các hàm này nếu gọi `adapter.dump_ui()` sẽ nuốt mất một XML dump trong `fake.xml_queue`.
- Hậu quả: Flow chính ở các bước tiếp theo nhận sai XML hoặc văng `RuntimeError: FakeAdapter: xml_queue rỗng`.
- Khắc phục: Trong các hàm helper kiểm tra `is_mock` hoặc `hasattr(adapter, "xml_queue")`, truyền sẵn `xml_text=mock_xml` để không kích hoạt `dump_ui()` ngầm.
