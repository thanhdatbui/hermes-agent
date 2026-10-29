# Zero-Overengineering Bulkhead Clamp & ADB False-Positive Elimination (2026-10-29)

## 1. Operator Mandate: Anti-Overengineering & Anti-Whining
- **Vấn đề xuất phát:** Khi đối soát Farm Gate Compliance 6h, Coordinator ban đầu chỉ cập nhật văn bản Guidance trong SKILL.md. Operator chất vấn: *"K auto wire à, cái m sửa là ở tầng guidance à"*.
- **Cạm bẫy Over-Engineering từ Advisor:** Khi hỏi Claude CLI lần đầu, advisor vẽ ra một cấu trúc đồ sộ (Normalizer v0, Registry đóng, Shadow mode 24h, Property tests, tool `locate`...). Operator lập tức chỉnh đốn: *"mày hội ý lại vs claude cho nó k khóc lóc k over engineer đi"*.
- **Kỷ luật O(1) Tối giản:** Khống chế tuyệt đối diff $\le 30$ dòng, 1 file duy nhất, 0 thêm framework, chia pha thi công dứt điểm: *"Xong phase nào gọi reviewer sửa phase đó đạt thì qua phase tiếp theo"*.

---

## 2. Root Cause & Bản Vá O(1) Cho `guard_device_bulkhead.py`

### A. Bug Bắt Nhầm `GUARD_AMBIGUOUS_ADB_COMMAND` (False Positive)
- **Triệu chứng:** Hơn 29 lần chặn trong 6h đối với các lệnh vô hại như:
  - `git commit -m "fix(dual-cluster): route Admin machines via adb"`
  - `grep -n "Adb" python_runner/run_batch_live_2fa.py`
  - `echo "--- LOCAL ADB ---"`
  - `cat adb.log`
- **Nguyên nhân gốc rễ kép:**
  1. `is_adb = bool(re.search(r'(?:^|[\s"\'&])(?:[^\s]*[/\\])?adb(?:\.exe)?(?:[\s"\'$]|$)', stmt))` quét toàn bộ câu lệnh, bắt dính từ khóa `"adb"` nằm trong chuỗi nháy kép của git commit hay grep.
  2. `is_device_cmd` soi tên script `run_*.py` trên toàn bộ chuỗi lệnh, biến `grep ... run_batch_2fa.py` thành "lệnh điều khiển thiết bị" và ném lỗi thiếu timeout!
- **Giải pháp O(1):**
  ```python
  # Step 1: Detect actual ADB invocation (chống bắt nhầm git commit / grep)
  _ADB_EXES = {'adb', 'adb.exe', 'fastboot', 'fastboot.exe'}
  _WRAP_EXES = {'timeout', 'env', 'nohup', 'sudo', 'bash', 'sh', 'cmd', 'powershell', 'pwsh'}

  def _is_actual_adb_call(stmt: str) -> bool:
      s = stmt.strip()
      if not s or not re.search(r'\b(adb|fastboot)(?:\.exe)?\b', s, re.IGNORECASE):
          return False
      tokens = re.findall(r'(?:[^\s"\'|&;]+|"[^"]*"|\'[^\']*\')+', s)
      if not tokens:
          return False
      idx = 0
      while idx < len(tokens) and '=' in tokens[idx] and not tokens[idx].startswith('-'):
          idx += 1
      if idx >= len(tokens):
          return False
      exe = tokens[idx].strip('\'"').replace('\\', '/').split('/')[-1].lower()
      return (exe in _ADB_EXES) or (exe in _WRAP_EXES)
  ```
  Và loại trừ lệnh kiểm tra:
  ```python
  is_inspection = bool(re.match(r'^\s*(?:grep|git|cat|echo|rm|ls|diff|head|tail)\b', cmd))
  is_device_cmd = (bool(machine_matches) or is_device_script) and not is_inspection
  ```

### B. Auto-Clamp `GUARD_DEVICE_FOREGROUND_TIMEOUT` (0-Turn Friction)
- **Triệu chứng:** Lệnh foreground điều khiển thiết bị chạy với `timeout > 60s` hoặc không đặt timeout bị ném lỗi `block` thụ động, ép Coordinator tốn 1 turn gõ lại.
- **Giải pháp O(1):** Thay `_block(...)` bằng in-place rewrite:
  ```python
  # 4.2 BULKHEAD: CẤM FOREGROUND CHẠY DÀI TRÊN SESSION CHÍNH -> AUTO-CLAMP VỀ 60s
  if not is_bg and (timeout is None or timeout > 60):
      updated_args = dict(args)
      updated_args["timeout"] = 60
      print(json.dumps({
          "action": "rewrite",
          "rule_id": "GUARD_DEVICE_FOREGROUND_TIMEOUT_AUTO_CLAMPED",
          "updated_args": updated_args,
          "notice": f"Auto-clamped timeout {timeout}s -> 60s (policy: foreground device cap 60s).",
      }))
      sys.exit(0)
  ```

---

## 3. Bài Học GuardGate: Invariant `check_step_by_step_structure`
- **Quy tắc cứng:** Trong `predicates.py`, mọi diff Python có số dòng code thêm mới $\ge 15$ lines bắt buộc phải có comment định danh bước khớp `r"#.*(buoc|bước|step|phase|stage|checkpoint)|#\s*={3,}"`.
- **Pitfall:** Thiếu comment bước sẽ bị GuardGate từ chối ở Step 2 của Closeout Gate (`predicate_failed:check_step_by_step_structure`).
- **Khắc phục:** Luôn đặt comment dạng `# Step 1: <Mô tả hành động>` trước khối logic bổ sung.

---

## 4. Bằng Chứng Nghiệm Thu Reviewer (Closeout Gate)
- **Phase 1 (Fix False Positive ADB):** 23/23 tests pass, Reviewer Sol chấm **86/100 (APPROVED)**, commit `19ac48d`.
- **Phase 2 (Auto-Clamp Timeout):** 23/23 tests pass, Reviewer Sol chấm **87/100 (APPROVED)**, commit `95c69bf`.
- **G5 Watchdog:** Đạt trạng thái `PASS (0 vi phạm, 7 remediations)`.
