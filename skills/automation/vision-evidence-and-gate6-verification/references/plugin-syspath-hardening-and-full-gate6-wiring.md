# Khắc Phục Lỗ Hổng Sys.Path Plugin, Bẫy ImportError Âm Thầm & Hoàn Thiện Wiring Gate 6

Tài liệu đúc kết sự cố lọt báo mồm, chụp láo và hoàn thiện wiring cơ học cho Gate 6 Visual Evidence trên Taadaa Farm.

---

## 1. Bản Chất Sự Cố & 3 Lỗ Hổng Kiến Trúc Bị Bóc Trần

Trong phiên chuẩn hóa và ghim video kênh Máy 42 & 43, Coordinator đã chạy script pin video, chụp screencap, gọi `browser_vision` xem ảnh nội bộ, nhưng khi trả lời User thì quên dán thẻ `MEDIA:`, chỉ báo mồm *"Video 8.856 view đã được ghim lên đầu thành công!"*. Mặc dù hệ thống đã có sẵn `guard_media_vision_gate.py`, tin nhắn vi phạm Gate 6 vẫn lọt qua 100%.

Điều tra sâu bóc tách 3 lỗ hổng chí mạng:

### Lỗ hổng 1: Bẫy `ImportError: pass` do thiếu `sys.path`
- Trong Coordinator Guard Plugin (`deploy/hermes-home/plugins`), hook `transform_output_hook` gọi:
  ```python
  try:
      import guard_media_vision_gate
      ok, guarded_text = guard_media_vision_gate.transform_llm_output_check(response_text)
      if not ok:
          return guarded_text
  except ImportError:
      pass
  ```
- File `guard_media_vision_gate.py` nằm ở `D:/Taadaa/tools/`. Nhưng môi trường runtime của Hermes (`venv`) **KHÔNG** có `D:/Taadaa/tools` trong `sys.path`.
- Lệnh import văng `ImportError: No module named 'guard_media_vision_gate'`.
- Khối `except ImportError: pass` nuốt sạch lỗi trong im lặng, khiến toàn bộ chốt chặn đầu ra bị vô hiệu hóa 100%!

### Lỗ hổng 2: `browser_vision` trên ảnh local không được cấp Sổ Khám (Receipt)
- Khi Coordinator xem ảnh cục bộ (`browser_navigate("file:///D:/...png")` rồi gọi `browser_vision`), kết quả trả về của tool là:
  `"Image loaded into your context — you can see it natively now..."`
- Trong `_on_post_tool_call`, code cũ chỉ tìm regex `"Screenshot path:\s*([^\r\n]+)"` (vốn chỉ sinh ra khi chụp màn hình web).
- Trên ảnh local, regex trả về `None`, dẫn đến việc ảnh dù đã được xem qua `browser_vision` vẫn **KHÔNG** được thêm vào `verified_media_paths` và **KHÔNG** được tạo receipt trong `vision_receipts.jsonl`.
- Hậu quả: Khi Agent dán thẻ `MEDIA:`, Gate lại coi là `NO_RECEIPT` (chưa soi ảnh), gây ra lỗi giả hoặc phải bypass.

### Lỗ hổng 3: Bộ claim `_detect_completion_claims` bỏ quên tác vụ Pin & Avatar
- Regex nhận diện hoàn thành chỉ có 3 nhóm: `2fa`, `login`, `password`.
- Hoàn toàn thiếu nhóm `pin` (`đã ghim`, `ghim lên đầu`, `pin to top`) và `profile` (`đổi avatar`, `đổi bio`, `chuẩn hóa`).
- Do đó, câu tuyên bố *"Video 8.856 view đã được ghim lên đầu thành công"* không bị coi là completion claim, lọt qua cửa sổ kiểm tra.

---

## 2. Giải Pháp Khắc Phục Cơ Học Triệt Để (100% Tested)

### A. Nạp `D:/Taadaa/tools` vào `sys.path` ngay đầu Plugin
Trong plugin `__init__.py`:
```python
_tools_dir = Path(r"D:\Taadaa\tools")
if _tools_dir.is_dir() and str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))
```
Đảm bảo `import guard_media_vision_gate` luôn thành công tuyệt đối trên mọi runtime.

### B. Hỗ trợ Local Image Path & Tự Động Ký Receipt cho `browser_vision`
Trong `_on_post_tool_call`:
```python
candidate_paths = []
m_sc = re.search(r"Screenshot path:\s*([^\r\n]+)", res_str)
if m_sc:
    candidate_paths.append(m_sc.group(1).strip().strip('"\''))
if last_f and last_f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
    candidate_paths.append(last_f)

for cand in candidate_paths:
    sc_p = os.path.normcase(os.path.normpath(cand))
    if os.path.isfile(sc_p) and _is_allowed_evidence_image_path(sc_p) and _validate_image_content(sc_p):
        sc_sha = _compute_file_sha256(sc_p)
        if sc_sha:
            if sc_p not in verified:
                verified.append(sc_p)
            details[sc_p] = {
                "text": res_str.lower(),
                "timestamp": time.time(),
                "sha256": sc_sha,
                "source": "browser_vision_screenshot",
            }
            try:
                import guard_media_vision_gate
                guard_media_vision_gate.create_vision_receipt(
                    image_path=sc_p,
                    tool_called="browser_vision",
                    ocr_raw_text=res_str,
                )
            except Exception as exc_receipt:
                logger.debug("[FARM_GUARD] Error creating vision receipt for browser_vision: %s", exc_receipt)
```

### C. Mở Rộng Regex Nhận Diện Claim Đầy Đủ
Thêm 2 nhóm `pin` và `profile` vào `_detect_completion_claims`:
- **`pin`**: `r"\bđã\s+ghim\b"`, `r"\bghim\s+(?:lên\s+đầu|thành\s+công|xong|hoàn\s+tất|ok)\b"`, `r"\b(?:pin|pinning)\s+(?:to\s+top|thành\s+công|xong|hoàn\s+tất|ok)\b"`, `r"✅\s*(?:đã\s+)?ghim\b"`.
- **`profile`**: `r"\bđã\s+(?:đổi|cập\s+nhật|thay\s+đổi)\s+(?:avatar|ảnh\s+đại\s+diện|ava|bio|tiểu\s+sử)\b"`, `r"\b(?:avatar|ảnh\s+đại\s+diện|ava|bio|tiểu\s+sử)\s*[:=]?\s*(?:đã\s+được\s+đổi|đã\s+đổi|đã\s+cập\s+nhật|thành\s+công|xong|hoàn\s+tất|ok)\b"`, `r"\bđã\s+chuẩn\s+hóa\s+(?:kênh|hồ\s+sơ|profile)\b"`.

### D. Chống Chụp Màn Hình Đối Phó Bằng `TEXT_CLAIM_RULES`
Trong `guard_media_vision_gate.py`:
- Thêm rule `avatar`:
  ```python
  (
      "avatar",
      re.compile(r"\b(?:da (?:doi|thay|cap nhat) (?:avatar|ava|anh dai dien)|doi avatar)\b"),
      re.compile(r"\b(?:sua ho so|chinh sua|edit profile|avatar|thay doi anh|anh dai dien)\b"),
  ),
  ```
- Nếu Agent chụp màn hình Launcher (chứa icon Tin nhắn, Cài đặt, Điện thoại) hoặc màn hình đen mà tuyên bố:
  + *"Đã ghim video"* $\to$ Bị chặn ngay: `UNGROUNDED_TEXT_CLAIM: pin`.
  + *"Đã đổi avatar"* $\to$ Bị chặn ngay: `UNGROUNDED_TEXT_CLAIM: avatar`.
- Chỉ khi OCR trên ảnh có chữ thuộc màn hình Profile (`sửa hồ sơ`, `edit profile`, `avatar`, `đã ghim`) thì mới được thông qua (`PASS`).

---

## 3. Quy Trình Xác Thực Kép (Verification Proof)

Sau khi chỉnh sửa, bắt buộc chạy kiểm thử cả 2 suite:
1. `pytest D:/Taadaa/Hermes/deploy/hermes-home/plugins/*guard*/test_evidence_first_gate_v4_3.py` (20/20 PASS).
2. `pytest D:/Taadaa/tools/tests/test_guard_media_vision_gate.py` (97/97 PASS).
