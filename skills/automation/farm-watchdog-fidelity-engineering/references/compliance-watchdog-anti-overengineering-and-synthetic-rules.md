# Compliance Watchdog Anti-Overengineering & Synthetic Rule Elimination

## Bối Cảnh & Sự Cố
Trong báo cáo định kỳ 6h `farm-gate-compliance-6h-report` (`gate_compliance_watchdog.py`), hệ thống phát hiện 3 điểm over-engineering gây phiền hà và hiểu lầm cho Operator:
1. **Synthetic Rule Generation:** Watchdog tự động đếm các dòng `REJECTED` cũ trong cửa sổ 6h và tự sinh ra rule ảo `[Closeout] Unremediated-Rejection: 5 lần` nhét vào Top Quy Tắc Bị Chặn, dù không có hook hay rule nào tên như vậy.
2. **Actionable / Guidance Spam:** Báo cáo tự gắn thêm tiêu đề `(Cần Bổ Sung Guidance)` và thòng dòng kêu gọi `💡 Actionable: Operator/Agent cập nhật guidance chi tiết cho các hook/rule trên để Agent biết đường làm nhanh hơn, giảm tiêu hao token.`.
3. **Buzzword "Auto-rewire cứu nguy":** Watchdog đếm regex các từ khóa `Auto-clamped|rewrite` rồi chèn vào header `| 🔄 Auto-rewire cứu nguy: 2 lần`, khiến Operator thắc mắc về "cái gì auto chuyển hướng ấy".
4. **Stale Reviewer Scorecard Invariant:** Tên Gate G5 vẫn ghi là `Closeout Reviewer Gate` và chỉ soi verdict `APPROVED`/`REJECTED` kiểu cũ, trong khi hệ thống chốt phiên đã được tinh gọn sang mô hình cơ học O(1) (Pytest 100% pass + GuardEngine ALLOW, bãi bỏ chấm điểm Scorecard 85).

---

## Các Bất Biến Khắc Phục (Invariants)

### 1. Cấm Tự Bịa Synthetic Rules
Watchdog chỉ được thống kê các `rule_id`, `category`, `reason` thật sự được bắn ra từ các Gate và Hook có cấu trúc trong file log:
```python
# CHỈ ghi nhận rule_id thật từ log có cấu trúc:
r_id = d.get("rule_id") or d.get("route") or d.get("category") or d.get("reason") or d.get("event")
```
TUYỆT ĐỐI CẤM tự gán synthetic entry như:
```python
# CẤM:
blocked_rules["[Closeout] Unremediated-Rejection"] = g5_failed
```

### 2. Gọt Bỏ Noise & Buzzword Header
Dòng đối soát log chỉ cần trung thực, tối giản:
```python
# ĐÚNG:
f"📁 Đối soát: {files_scanned} log files ({lines_scanned} dòng)"

# CẤM:
f"📁 Đối soát: {files_scanned} log files ({lines_scanned} dòng | 🔄 Auto-rewire cứu nguy: {rewired} lần)"
```

### 3. Trả Về Báo Cáo Gọn Gàng (Không Rác Actionable)
Khi hiển thị danh sách quy tắc bị chặn, chỉ cần:
```markdown
🔥 *Top Quy Tắc Bị Chặn:*
1. `[Anti-Scan & Terminal] GUARD_SEARCH_FILES_ROOT`: 32 lần
2. `[Worker Dispatch] NO_DIFF`: 7 lần
```
Xóa bỏ hoàn toàn câu mời chào cập nhật guidance hay lời khuyên thừa thãi.

### 4. Đồng Bộ Closeout Gate Cơ Học O(1)
- Tên Gate: `Gate("G5", "Closeout Gate", ...)` (bỏ chữ *Reviewer*).
- Pattern pass: Hỗ trợ cả định dạng phê duyệt truyền thống và các cờ cơ giới hóa mới:
  `_rx(r"verdict\W+APPROVED\b|\[GuardEngine\s+ALLOW\]|CLOSEOUT_PASSED")`
