# Closeout Reviewer Pitfalls & Patterns: Metrics Lock, Lookbehind & Test Truncation

## 1. Thread-Safe Metrics & Immutable Snapshot Pitfall
Khi triển khai bộ đếm telemetry toàn cục (như `RECONCILE_METRICS`) dưới bảo vệ của `_METRICS_LOCK`:
- **Type Annotation:** Khai báo kiểu tường minh cho lock:
  ```python
  _METRICS_LOCK: threading.Lock = threading.Lock()
  ```
- **Getter độc lập (Immutable Snapshot):** Reviewer chấm điểm rất gắt nếu getter trả về dict trực tiếp hoặc nếu test không chứng minh tính độc lập:
  ```python
  def get_reconcile_metrics() -> dict[str, int]:
      """Lấy bản sao thread-safe của RECONCILE_METRICS dưới bảo vệ của lock."""
      with _METRICS_LOCK:
          return dict(RECONCILE_METRICS)
  ```
- **Test Assertion bắt buộc để pass Reviewer:**
  ```python
  snap = fsw.get_reconcile_metrics()
  assert snap is not fsw.RECONCILE_METRICS
  snap["buffer_applied"] = 999
  assert fsw.RECONCILE_METRICS["buffer_applied"] != 999
  ```
- **Auto-Reset Flag (`auto_reset_metrics`):**
  Trong các hàm đối soát / watchdog xử lý multi-cluster, caller cần kiểm soát việc reset metrics để tránh xóa nhầm metrics của cluster trước đó khi chạy đồng thời hoặc liên tiếp:
  ```python
  def reconcile_cluster_following(..., auto_reset_metrics: bool = True) -> list[str]:
      if auto_reset_metrics:
          reset_reconcile_metrics()
  ```
  Reviewer yêu cầu có cả test case truyền `auto_reset_metrics=False` để chứng minh counter tích lũy đúng qua 2 lần gọi.

## 2. Session Key Classification & Negative Lookbehind
Khi parse định danh phiên (`session_key`):
- Tránh false-positive với các key chứa chuỗi con như `ap1_cluster`, `3p1_session`, `xp1_p2`:
  Dùng negative lookbehind và negative lookahead chặt chẽ:
  ```python
  has_p1 = bool(re.search(r"(?<![a-z0-9])(?:phien|session|p)[\s_.-]*1(?![0-9])", s_lower))
  has_later = bool(re.search(r"(?<![a-z0-9])(?:phien|session|p)[\s_.-]*([2-9]|\d{2,})", s_lower))
  res = not (has_later and not has_p1)
  ```
- Thêm telemetry log cho mỗi lần phân loại: `logger.debug("[SESSION_KEY_CLASSIFY] key=%s -> is_p1_or_unknown=%s", session_key, res)`.

## 3. Truncation Trap Trong Closeout Gate Diff
- Closeout Gate có ngưỡng dung lượng diff tối đa (ví dụ 30.000 bytes). Nếu committed diff vượt quá, gate sẽ trả về `DIFF_TOO_LARGE` hoặc làm model reviewer truncate phần test (~100-200 dòng cuối).
- Khi bị truncate, Reviewer tự động trừ điểm nặng ở rubric `test_evidence` và từ chối duyệt ("phần bị lược KHÔNG được coi là đã review").
- **Giải pháp:**
  - Thu hẹp base ref (`--base HEAD~N` phù hợp) sao cho diff nằm trong khoảng 8KB - 25KB.
  - Tránh gộp các refactor cosmetic 1 dòng (single-line if-return) làm bẩn git diff và giảm điểm readability (PEP 8).
