# Closeout Scope Normalization & Downstream Integration Pitfalls

## 1. Bẫy Python `str.lstrip("./")` Khi Chuẩn Hóa Git Scope Binding
- **Ngữ cảnh:** Trong `closeout_gate.py:238`, hàm chuẩn hóa git scope `build_audit_binding` dùng cú pháp:
  ```python
  normalized = sorted(set(str(p).replace("\\", "/").lstrip("./") for p in scope))
  ```
- **Hiện tượng:** Khi commit chứa các file ẩn bắt đầu bằng dấu chấm như `.gitignore`, `.env`, `.github/...`, `closeout_gate.py` báo lỗi:
  ```text
  committed scope mismatch with git state: expected ['gitignore', ...], got ['.gitignore', ...]
  ```
- **Nguyên nhân:** Trong Python, `str.lstrip(chars)` nhận tham số là một tập hợp các ký tự cần bóc (`chars` as a set of characters), KHÔNG PHẢI chuỗi tiền tố cần cắt. Do đó:
  ```python
  ".gitignore".lstrip("./") -> "gitignore"  # Mất luôn dấu chấm hợp lệ của filename!
  ```
- **Giải pháp triệt để:** Sử dụng logic cắt tiền tố chính xác:
  ```python
  p_str = str(p).replace("\\", "/")
  normalized_path = p_str[2:] if p_str.startswith("./") else p_str
  ```

---

## 2. Hợp Đồng Consumer Downloader Proxy Pool (`argparse.Namespace`)
- **Ngữ cảnh:** Module `scripts/downloader/proxy.py` có hàm nạp danh sách proxy:
  ```python
  def load_proxy_pool(args: argparse.Namespace) -> list[str]:
      if not getattr(args, "proxy_pool", None):
          return []
      path = args.proxy_pool
      ...
  ```
- **Bẫy:** Nếu caller hoặc unit test truyền chuỗi đường dẫn string path trần `load_proxy_pool(path)`, hàm sẽ kiểm tra `getattr(str, 'proxy_pool', None)` -> trả về `None` -> danh sách rỗng `[]` mà không ném lỗi!
- **Giải pháp:** Luôn đóng gói qua `argparse.Namespace`:
  ```python
  import argparse
  from downloader.proxy import load_proxy_pool

  pool = load_proxy_pool(argparse.Namespace(proxy_pool=resolved_path))
  assert len(pool) in (67, 69)
  ```

---

## 3. Chống Bẫy Vacuous Truth Trong Pytest Closeout Verification
- **Vấn đề:** Khi viết test kiểm tra tích hợp dữ liệu thật của farm (ví dụ file proxy pool hoặc config):
  ```python
  p = Path(result)
  if p.exists():  # <-- NGUY HIỂM: VACUOUS PASS
      lines = p.read_text().splitlines()
      assert len(lines) > 0
  ```
  Nếu file không tồn tại, khối `if` bị bỏ qua hoàn toàn, pytest vẫn báo `PASSED` nhưng không hề kiểm tra gì. Closeout Gate Auditor Sol sẽ đánh trượt vì thiếu bằng chứng thực thi xác minh nội dung file.
- **Giải pháp:** Luôn dùng `assert p.exists()` trực tiếp:
  ```python
  p = Path(result)
  assert p.exists(), f"File {result} bắt buộc phải tồn tại"
  lines = [line.strip() for line in p.read_text().splitlines() if line.strip()]
  assert len(lines) in (67, 69)
  assert all(":" in line for line in lines)
  ```
