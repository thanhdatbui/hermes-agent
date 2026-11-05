# Quy Chuẩn Dọn Lock Rác Pipeline & Kỷ Luật Vận Hành Khóa Cơ Học (Anti-Stale-Lock)

## 1. Bản Chất Bẫy Stale Repo Lock Trong `unified_patch_pipeline.py`
- Khi pipeline cơ giới hóa chạy trên một repo (ví dụ `tools`, `AI-Tools`), `RepoLock` tạo ra file `D:/Taadaa/runtime/locks/pipeline_repo_<digest>.lock`.
- Nếu phiên trước bị ngắt đột ngột (User ngắt turn, gateway crash, reboot PC), file `.lock` vẫn tồn tại trên đĩa nhưng tiến trình giữ lock (PID) đã chết (`psutil.pid_exists(pid) == False`).
- Trước đây, pipeline chỉ kiểm tra sự tồn tại của file lock và ném lỗi `PRECHECK ERROR` chặn họng mọi lượt chạy sau.

## 2. Giải Pháp Cơ Giới Hóa Tự Động (Dead Lock Reap O(1))
- Nâng cấp trực tiếp trong `RepoLock.acquire()`:
  ```python
  if self.path.exists():
      try:
          content = self.path.read_text(encoding="utf-8").strip()
          if content:
              data = json.loads(content)
              pid = data.get("pid")
              if pid and isinstance(pid, int):
                  import psutil
                  if not psutil.pid_exists(pid):
                      try:
                          self.path.unlink()
                      except OSError:
                          pass
      except Exception:
          pass
  ```
- **Kỷ luật vận hành:** Không bao giờ viện cớ lock đang bị giữ để từ chối chạy pipeline hoặc tự ý bypass pipeline sửa code trực tiếp (trừ Emergency Surgery L2). Bắt buộc cơ chế `RepoLock` phải tự dọn lock rác nếu tiến trình cũ đã chết.

## 3. Kỷ Luật Phân Vai Sửa Code vs Thao Tác Mạng
- Sửa code/script trong repo git: BẮT BUỘC dùng `unified_patch_pipeline.py` có hội đồng duyệt plan, worker sửa và test pass.
- Cấu hình thiết bị mạng ngoại vi (MikroTik RouterOS REST API, OpenWrt ubus): Thao tác trực tiếp qua API, không đẻ thêm lock nhảm trên repo code.
