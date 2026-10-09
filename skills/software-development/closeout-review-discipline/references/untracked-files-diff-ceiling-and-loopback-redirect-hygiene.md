# Untracked Files Diff Ceiling, Zero-Change Exclusion, and Loopback Redirect Hygiene

## 1. Untracked Files Diff Ceiling (`DIFF_TOO_LARGE` <= 30,000 bytes)

### Cơ chế bẫy `DIFF_TOO_LARGE` trong `closeout_gate.py`
`closeout_gate.py` quy định trần cứng `MAX_DIFF_BYTES_GATE = 30_000` (30KB).
Khi truyền danh sách file qua `--files <target1> <target2> ...`:
- Với file đã tracked trong Git: Git chỉ trích xuất diff giữa HEAD và working-tree (thường chỉ vài chục đến vài trăm dòng thay đổi thực tế).
- **Với file MỚI (untracked)**: Git trích xuất toàn bộ nội dung file từ `/dev/null` (`git diff --no-index -- /dev/null <file>`). Toàn bộ 100% dung lượng file mới (cả code lẫn test) được tính vào raw diff bytes!
- Nếu tổng raw bytes của tất cả file trong `--files` vượt quá 30,000 bytes, Gate kích hoạt **Fail-Fast**:
  ```text
  [Gate Fail-Fast: DIFF_TOO_LARGE] targeted diff quá lớn (39532 > 30000 bytes).
  Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.
  ```
  Script lập tức thoát với `exit code 3` mà **không chạy test hay gọi Reviewer**.

### Chiến lược xử lý & nén diff (Compression Strategy)
Khi thêm module mới kèm bộ test lớn (ví dụ: tool mới + 25 unit tests):
1. **Kiểm tra trước khi gọi Gate**:
   ```python
   import sys; sys.path.insert(0, 'D:/Taadaa/tools')
   from closeout_gate import targeted_candidate
   from pathlib import Path
   mode, scope, raw = targeted_candidate(Path(repo), targets, base_ref='HEAD~1')
   print('Raw bytes:', len(raw), 'Ceiling: <= 30000')
   ```
2. **Kỹ thuật nén code & test không làm mất logic**:
   - Loại bỏ docstrings dài dòng và chú thích lặp lại trong test.
   - Viết gọn các fixture / mock setup dùng chung (ví dụ: helper `_seam(...)` thay vì copy paste 5 dòng gọi helper).
   - Rút gọn các chuỗi payload test mẫu dài bất thường (ví dụ: `'q' * 2000` thay vì `'question ' * 5000` lặp nhiều lần).
   - Gom các assertion tương đồng trên cùng một dòng hoặc dùng tuple loop ngắn gọn.
   - BẮT BUỘC giữ nguyên 100% số lượng hàm test (`def test_*`) và đầy đủ các điều kiện assert logic/safety.

---

## 2. Zero-Change Exclusion: Loại bỏ file không có diff khỏi `--files`

### Bẫy `targets without working-tree changes`
Nếu một file được liệt kê trong `--files` nhưng sau quá trình sửa chữa hoặc revert lại giống hệt `HEAD` (0 dòng thay đổi), `targeted_candidate` sẽ raise exception:
```text
Failed to extract diff: targets without working-tree changes: ['toolsets.py']
```
### Quy tắc:
Trước khi chạy `closeout_gate.py`, bắt buộc chạy:
```bash
git status --short -- <targets>
```
Chỉ giữ lại trong `--files` những file có cờ `M` (modified) hoặc `??` (untracked có nội dung). File nào sạch diff phải loại ngay khỏi tham số `--files`.

---

## 3. Loopback Redirect Protection cho Egress an toàn

### Rủi ro SSRF qua HTTP 302 Redirect
Khi cấu hình công cụ gọi dịch vụ local/loopback (ví dụ: `http://127.0.0.1:20129`):
- Chỉ kiểm tra hostname ban đầu `urlparse(endpoint).hostname in {'localhost', '127.0.0.1'}` là **chưa đủ**.
- Mặc định `urllib.request.urlopen` sẽ tự động follow HTTP redirect (301/302). Nếu dịch vụ local redirect sang host ngoài (`http://evil.com/leak`), toàn bộ payload (kèm prompt/current_state/evidence) sẽ bị gửi ra ngoài internet.

### Giải pháp chuẩn hóa `_LoopbackRedirectHandler`:
```python
class _LoopbackRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _loopback_endpoint(newurl):
            raise urllib.error.HTTPError(req.full_url, code, "Advisor redirect target is not loopback", headers, None)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

_ADVISOR_OPENER = urllib.request.build_opener(_LoopbackRedirectHandler())
```
*Lưu ý khi viết unit test:*
- Phải mock `_ADVISOR_OPENER.open` thay vì `urllib.request.urlopen`.
- Hàm mock `open` phải nhận `*args, **kwargs` vì `timeout` được truyền dưới dạng keyword argument (`timeout=b_to`).

---

## 4. Giao tiếp khi gặp nghẽn / Timeout (Chống báo ẩu "không treo")

- Khi user gửi ảnh Telegram chỉ ra mốc thời gian cách nhau 10-15 phút: **Tuyệt đối thừa nhận latency / nghẽn ngay lập tức**, không cãi bướng "không có treo".
- Lệnh chạy Gate với Reviewer qua mạng suy nghĩ sâu (Sol/Terra) có thể mất từ 40s - 120s. BẮT BUỘC:
  - Chạy background: `terminal(background=True, notify_on_complete=True, timeout=300)`.
  - Cấm chạy foreground với timeout 60s vì guard terminal sẽ kill tiến trình (`exit code 124`).
