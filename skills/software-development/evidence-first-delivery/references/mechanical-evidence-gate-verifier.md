# Mechanical Evidence Gate Verifier (`evidence_gate_verifier.py`)

Công cụ kiểm chứng cơ học độc lập cho bằng chứng UI (Browser, GPM, Phone Farm, App):
Đường dẫn script: `D:/Taadaa/tools/evidence_gate_verifier.py`
Sổ cái audit: `D:/Taadaa/runtime/audit/audit_chain.jsonl`
Khóa tiến trình: `D:/Taadaa/runtime/audit/audit_chain.lock`

---

## 1. Các Bất Biến Cưỡng Chế Cơ Học (Hard Enforced Invariants)

1. **Unconditional Mandatory Pairing:**
   Mọi thao tác thay đổi trạng thái (state transition) BẮT BUỘC phải cung cấp cả cặp ảnh Pre-submit và Post-submit.
   - Cấm dùng mẹo chọn từ ngữ trong claim để né tránh Post-submit.
   - Cờ `--allow-single-inspection` CHỈ dùng cho tác vụ kiểm tra thụ động (read-only pre-action check).

2. **Anti-Same-File & Distinct Artifact Check:**
   - Pre-submit và Post-submit BẮT BUỘC là 2 file vật lý độc lập (`abspath(pre) != abspath(post)`).
   - Mã băm SHA256 BẮT BUỘC khác nhau (`pre_hash != post_hash`). Nghiêm cấm dùng ảnh clone hoặc rename cùng 1 ảnh.

3. **Anti-Replay Temporal Order & Freshness:**
   - `post_image` mtime BẮT BUỘC `>= pre_image` mtime.
   - Khoảng cách giữa 2 ảnh: `post_mtime - pre_mtime <= max_pair_interval` (mặc định 120s).
   - Tuổi thọ của ảnh: `now - mtime <= max_age` (mặc định 600s).

4. **Anti-Replay Claim Binding (Consumed Hash Protection):**
   - SHA256 của `post_image` sau khi được xác nhận PASS/FLAGGED_STALE_RESOLVED sẽ được lưu vào sổ cái audit ledger.
   - Nếu bất kỳ lượt chạy nào tái sử dụng lại `post_image` này cho claim khác -> Bị từ chối ngay lập tức với lỗi `ANTI_REPLAY_CLAIM_BINDING_VIOLATION`.

5. **Affirmative Positive Success Evidence Gating:**
   - Không chỉ kiểm tra vắng mặt tín hiệu lỗi, khi có cờ `--require-positive` hoặc `--expected-post-keywords`, verifier bắt buộc phải phát hiện tín hiệu thành công thực sự trên màn hình post-submit.
   - Nếu không có tín hiệu thành công -> Trả về `FAIL_NO_POSITIVE_EVIDENCE`.

6. **Cryptographic Hash-Chained Audit Ledger with FileLock:**
   - Ghi tuần tự từng lượt kiểm tra vào `audit_chain.jsonl` với liên kết mã băm `prev_hash -> block_hash` (SHA256).
   - Đồng bộ hóa đa tiến trình qua inter-process `FileLock` (`msvcrt.locking` trên Windows, `fcntl` trên Linux) chống race condition giữa các worker farm song song.
   - Xác minh toàn vẹn chuỗi độc lập: `python evidence_gate_verifier.py --verify-chain`.

---

## 2. CLI Usage Examples

### Xác thực thao tác thông thường (Pre + Post submit):
```bash
python D:/Taadaa/tools/evidence_gate_verifier.py \
  --pre-image "D:/path/to/pre.png" \
  --post-image "D:/path/to/post.png" \
  --claim "Đã đổi pass thành công" \
  --expected-post-keywords "success" "confirmed" "dashboard"
```

### Kiểm tra đơn lẻ cho tác vụ chỉ đọc (Read-only pre-inspection):
```bash
python D:/Taadaa/tools/evidence_gate_verifier.py \
  --pre-image "D:/path/to/screen.png" \
  --allow-single-inspection
```

### Hậu kiểm toàn vẹn sổ cái audit ledger:
```bash
python D:/Taadaa/tools/evidence_gate_verifier.py --verify-chain
```

---

## 3. Bảng Ý Nghĩa Verdict

- `PASS`: Cặp ảnh sạch hoàn toàn, có chứng cứ xác nhận thành công, mã băm độc lập, thời gian hợp lệ.
- `FLAGGED_STALE_RESOLVED`: Ảnh Pre-submit có vệt lỗi từ lần thử trước (stale error banner), nhưng ảnh Post-submit sạch 100% và thời gian chuyển đổi hợp lệ.
- `VETO_REJECT`: Màn hình chứa tín hiệu lỗi trực tiếp (Error, Failed, Invalid, Try again...). Cấm phát ngôn hoàn tất!
- `FAIL_NO_POSITIVE_EVIDENCE`: Thiếu tín hiệu thành công thực tế trên ảnh Post-submit khi có yêu cầu bằng chứng dương tính.
- `FAIL`: Vi phạm định dạng ảnh, ảnh thiếu, cùng một file (same-file), vi phạm replay (ảnh cũ hoặc đã dùng).
- `ESCALATE_L3_BLOCKED`: Quá thời gian (elapsed > 30s) hoặc quá số lần (attempts >= 3). Chuyển ngay sang L3 BLOCKED.
