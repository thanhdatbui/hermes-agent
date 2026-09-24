# Kỷ Luật Phân Lớp 3 Tầng (3-Tier Architecture) & Vá Lỗ Hổng Hook Guard — Claude Opus 2026-09-25

Được đúc rút từ đợt audit gắt gao của Claude Code CLI Opus High (`claude -p --model opus --effort high`) sau sự cố Coordinator vi phạm nghiêm trọng: gộp 2 tính năng lớn trên monolith `tiktok_dashboard.py` (1.876 dòng) vào 1 subagent dispatch, dính timeout 600s liên tiếp 2 lần, đốt sạch quota và thời gian của user mà kết quả trả về `0 files modified`.

---

## 1. Bản Chất Sự Cố: "Subagent Overhead Death Loop"

Khi Coordinator hành xử máy móc theo giáo điều cứng nhắc *"Session chính cấm tự sửa code, mọi việc phải tống ra worker qua delegate_task"*, hệ thống rơi vào bẫy nghịch lý:
- **Patch cơ học đã biết rõ anchor (Lớp D):** Nếu tự sửa bằng công cụ kiểm chứng tất định (`apply_patch.py`), chỉ mất **15 – 30 giây**, vài trăm token và kiểm thử `pytest` ngay.
- **Đẩy sang Subagent ngầm:** Tốn **600 giây (10 phút)**, đốt 25.000 – 90.000 tokens chỉ để worker "học lại từ đầu" cấu trúc file 1.876 dòng, vật lộn với lỗi escape ký tự `{}` trong template string, rồi timeout trả về 0 kết quả!
- **Nguyên lý cốt lõi:** Delegate subagent có chi phí cố định (overhead) rất lớn để chuyển context. Nó chỉ kinh tế khi **chi phí khám phá (exploration) lớn hơn chi phí chuyển context, và kết quả có thể nén thành báo cáo ngắn**. Với patch cơ học đã rõ toạ độ, delegate là hành vi "trả tiền để worker học lại thứ Coordinator đã biết" — lỗ vốn hoàn toàn.

---

## 2. Bảng Phân Loại Công Việc 3 Lớp (3-Tier Task Classification)

| Lớp | Điều kiện (Thỏa mãn TẤT CẢ) | Ai thực hiện & Cơ chế thi hành |
| :--- | :--- | :--- |
| **Lớp D: Deterministic Patch**<br>*(Sửa cơ học đã biết rõ)* | • Biết chính xác file và anchor duy nhất (`grep -o ... \| wc -l == 1`).<br>• Diff $\le$ 80 dòng mỗi patch, $\le$ 3 files.<br>• Có lệnh verify tất định (`pytest`, `py_compile`, `node --check`).<br>• Không can thiệp ADB, máy thật hay thiết bị farm. | **Coordinator tự apply ngay qua `tools/apply_patch.py`.**<br>• Tự động tạo backup `.bak`.<br>• Tự động rollback nếu verify thất bại.<br>• **CẤM TUYỆT ĐỐI dispatch sang subagent ngầm.** |
| **Lớp S: Scoped Build**<br>*(Viết logic mới trong file)* | • Biết file, nhưng cần viết logic mới > 80 dòng hoặc có thử-sai nhỏ.<br>• Có acceptance test cụ thể, rõ ràng. | **Worker subagent**, bắt buộc cấp sẵn Anchor Map, budget cứng $\le$ 240s (cấm để 600s). |
| **Lớp E: Exploratory**<br>*(Khám phá & Hiện trường Farm)* | • Phải thao tác thiết bị thật, ADB, OCR, 160 máy farm.<br>• Debug sự cố chưa rõ nguyên nhân gốc rễ.<br>• Dự kiến > 15 tool calls, kết quả nén được thành báo cáo. | **Bắt buộc Worker subagent** độc lập trong context riêng. |

---

## 3. Bộ Quy Tắc R1 – R10 Điều Phối & Ngân Sách

```text
R1  PHÂN RÃ TRƯỚC, LÀM SAU: Mỗi prompt phải qua Gate 0–3. Prompt có >1 tính năng -> mỗi tính năng
    là một pipeline riêng biệt. Gộp 2 tính năng vào 1 dispatch = VI PHẠM NGHIÊM TRỌNG.
R2  CẤM BLIND DISPATCH: Chưa có anchor map (file + toạ độ duy nhất + lệnh verify) -> CẤM dispatch.
R3  LỚP D DO COORDINATOR LÀM: Patch <= 80 dòng, anchor duy nhất, verify tất định, không đụng
    thiết bị -> Coordinator apply ngay (dùng tools/apply_patch.py). Đẩy việc lớp D sang worker = VI PHẠM.
R4  COORDINATOR KHÔNG KHÁM PHÁ: Tối đa 3 Read/Grep để lập anchor map. Vượt -> chuyển lớp S/E.
R5  LỚP E BẮT BUỘC WORKER: ADB, máy thật, OCR, tái hiện lỗi, debug chưa rõ nguyên nhân.
R6  NGÂN SÁCH CỨNG: Timeout worker <= 240s, <= 20 tool calls, bắt buộc checkpoint progress.md.
R7  CẦU DAO (CIRCUIT BREAKER): Timeout 1 lần -> cấm retry cùng hình dạng, phải chia nhỏ lại hoặc
    tự làm phần lớp D. 2 timeout/phiên -> chuyển sang chế độ trực tiếp và báo cáo sếp.
R8  MINH BẠCH QUOTA: Trước khi thực thi, báo sếp 1 dòng: số unit, lớp, ước lượng thời gian.
R9  MƠ HỒ THÌ HỎI: Nghiệp vụ chưa rõ -> hỏi sếp ở Gate 0, không để worker tự đoán.
R10 NỢ KIẾN TRÚC: File monolith > 800 dòng trộn nhiều ngôn ngữ -> tách file theo kiểu chuyển
    nguyên văn (Lớp D) trước khi thêm tính năng lớn.
```

---

## 4. Công Cụ Thi Hành Exact Patch Contract: `tools/apply_patch.py`

Cơ chế thực thi patch nguyên tử (atomic), tự động backup và rollback:
```python
# tools/apply_patch.py — usage: python tools/apply_patch.py patch.json
# patch.json: {"patches": [{"file": .., "old": .., "new": ..}], "verify": "pytest tests/x.py", "timeout": 120}
import json, pathlib, shutil, subprocess, sys

spec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
backups = {}
try:
    for p in spec["patches"]:
        f = pathlib.Path(p["file"])
        src = f.read_bytes().decode("utf-8")
        eol = "\r\n" if "\r\n" in src else "\n"
        old, new = (p[k].replace("\r\n", "\n").replace("\n", eol) for k in ("old", "new"))
        n = src.count(old)
        if n != 1:
            raise SystemExit(f"ANCHOR_FAIL {f}: {n} matches")
        if f not in backups:
            backups[f] = f.with_suffix(f.suffix + ".bak")
            shutil.copy2(f, backups[f])
        f.write_bytes(src.replace(old, new, 1).encode("utf-8"))
    rc = subprocess.run(spec["verify"], shell=True, timeout=spec.get("timeout", 120)).returncode
    if rc:
        raise SystemExit(f"VERIFY_FAIL rc={rc}")
    print("PATCH_OK")
except BaseException:
    for f, bak in backups.items():
        shutil.copy2(bak, f)
    print("ROLLED_BACK")
    raise
```

---

## 5. Hai Lỗ Hổng Tử Huyệt Từng Gây Tê Liệt Hook `guard_dispatch_contract.py`

Khi kiểm tra log thực tế (từ 21/09 đến 25/09 không có Sol Plan nào được sinh ra), phát hiện 2 nguyên nhân kỹ thuật:

1. **Lỗ hổng 1: Bẫy Regex phân loại (False-Investigate Bypass)**
   - Regex cũ `edit_intent` chỉ bắt các từ tiếng Việt (`sửa code`, `chỉnh sửa`). Khi prompt dùng tiếng Anh (`Implement feature... Target files: ...`), hook không khớp `edit_intent`.
   - Kết hợp với việc có nhãn `Budget: <= 10 calls`, hook lầm tưởng đây là task **INVESTIGATE (đọc mã thuần túy)** và cho qua (`sys.exit(0)`), bỏ qua bước gọi Sol Planner!
   - **Vá dứt điểm:**
     * Bắt các cụm từ hành động cụ thể (`patch`, `sửa code`, `refactor`, `fix code`, `viết code`, `modify code`, `implement feature`, `thay thế code`).
     * Loại bỏ các từ chung chung (`add`, `update`, `feature`) đứng đơn lẻ.
     * Cụm từ đọc mã (`inspect`, `investigate`, `audit`, `review`, `trace`, `chỉ đọc`, `soi log`) được xếp ưu tiên vào Investigate route, nhưng **ràng buộc cứng budget $\le$ 5 calls**. Budget $> 5$ calls tự động bị BLOCK.

2. **Lỗ hổng 2: Lệch Timeout vật lý trong `config.yaml`**
   - Trong `config.yaml`: hook `guard_dispatch_contract.py` được cấu hình `timeout: 5` (5 giây).
   - Trong code hook: lệnh gọi `sol_planner.py` sang OmniRoute `:20129` cần 15 – 25 giây để Sol High suy luận (`timeout=25`).
   - Hậu quả: Cứ sau 5 giây là Hermes Agent kill hook do timeout, và mặc định bỏ qua lỗi để thả cho dispatch chạy mù!
   - **Vá dứt điểm:** Nâng timeout trong `config.yaml` lên `timeout: 30`.

3. **Nguyên tắc Quad-Location Parity cho Hooks:**
   Mọi cập nhật trên hook `guard_dispatch_contract.py` bắt buộc đồng bộ đủ 4 vị trí với cùng mã băm SHA256:
   1. `D:/Taadaa/tools/hooks/guard_dispatch_contract.py`
   2. `C:/Users/Kibe/AppData/Local/hermes/hooks/guard_dispatch_contract.py`
   3. `D:/OneDrive/Taadaa_Sync_Shared/hermes-sync/hooks/guard_dispatch_contract.py`
   4. `D:/Taadaa/Hermes/deploy/hermes-home/hooks/guard_dispatch_contract.py`
