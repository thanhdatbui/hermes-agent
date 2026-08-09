# Audit loop: prompt lớn + nhiều vòng REJECT (verified 2026-08-09)

Kinh nghiệm chạy thật: audit 3 vòng REJECT (14 → 12 → 6 findings) cho cùng 1 change-set
(state_machine.py + tests + core contract/validator). Mỗi vòng sửa hết findings → re-audit
(slot mới, evidence mới — hợp lệ theo one-slot rule).

## 1. Prompt > ~40KB: argv là BẪY — luôn dùng stdin/file

| Cách sai | Cách đúng |
|---|---|
| `claude -p "$(cat prompt.txt)"` → **`Argument list too long`** (bash argv limit, ~47KB) | `claude -p "..." --append-system-prompt-file <path>` (đọc nội dung từ file) |
| `codex exec ... "<prompt dài>"` → cùng lỗi argv | `cat prompt.txt \| codex exec ...` — codex đọc stdin khi không có `[PROMPT]` positional |
| AG qua wrapper `invoke-ag-audit.ps1` với prompt 47KB+ → **timeout 505s+, file 0 bytes, không có verdict** | Smoke-test AG model trước (2.2s OK) rồi nhớ: AG + prompt lớn + reasoning high = treo. Prompt lớn → dùng Sol/CLI qua stdin |

## AG (9router) bền với prompt nhỏ

- Smoke test model (prompt nhỏ): 200 OK trong ~2s — model khỏe, đường connect tốt.
- CÙNG model với prompt 47–100KB + reasoning high: `TimeoutSeconds` 480–600 không đủ → wrapper
  hoặc kill thủ công, file result 0 bytes (chưa có verdict). Không phải lỗi connect/quota.
- Kết luận: AG dành cho prompt ≤ ~30KB (spec ngắn, smoke). Prompt lớn → `codex exec` stdin
  hoặc Claude CLI `--append-system-prompt-file`.

## Claude CLI transient 500

- `--append-system-prompt-file` chạy đúng, nhưng có thể trả `API Error: Internal server error`
  (transient). Không có gì mất: lần chạy cùng evidence là PROCESSED rồi — chuyển route theo ladder.

## Worker chết mid-run (iteration limit) — TIẾP NỐI TẠI SESSION, không re-dispatch

Pattern lặp lại trong session: worker sửa code xong hết (21 edit), nhưng hết vòng tool-calling
(50 calls) TRƯỚC khi: sửa test cũ + viết test mới + docs + full suite. Xảy ra 3 lần liên tiếp
với cùng file 11K dòng.

- **Quy tắc**: worker mid-run = LÀM DỞ → session verify diff, rồi CONTINUE phần dở TẠI SESSION
  (không re-dispatch worker mới — worker mới lại đọc cả file lớn, lặp đúng fail).
- **Cách cứu nhanh khi test chết**:
  1. Chạy full suite, liệt kê lỗi FAILED cụ thể (4 fail = test cũ mock sai API mới).
  2. Đọc SIGUATURE hàm mới trong code (không đoán): `src.find("def name")`, in vùng report.
  3. Sửa test bằng python binary (không patch tool — EOL rules), anchor theo string chính xác
     (đã dính sai literal escape 2 lần — dùng `print(repr(segment))` để nhìn bytes thật).
  4. `sed`/`cat` hiển thị escape gây mắc — dùng `python -c "open('f','rb').read()"` + repr.
  5. Python scoping: class attribute của test class KHÔNG visible trong nested class body trong
     method → inline literal thay vì `EMPTY_EDIT_CAPTION` tham chiếu.
  6. Kiểm tra EOL sau mỗi edit (đếm CRLF/bareLF); đã từng tạo 1 bareLF trong file CRLF.

## Validator "OK 9/9" có thể fail-open — có audit thật mới phát hiện

- `check_ui_compatibility.py` trình OK 9/9 khi check cũ pass, nhưng chưa từng parse từng record.
- Sol tìm thấy: substring marker trong prose đếm như concept (fail-open), bullet rỗng
  `- **Evidence:**` coi như value (regex parse thành "**"), record mới nhưng ngày không parse
  → bị hạ legacy (fail-open).
- Fix đúng: parser chung bullet-label strict (strip Markdown decoration, mỗi concept 1 bullet,
  value != "") cho core 9 concepts + registry 7 legacy; record mới (≥ 2026-08-09) thiếu → FAIL,
  cũ → warning (không retroactive); owner/date nhận cả `YYYYMMDD` + `YYYY-MM-DD`.

## Test gãy newline (bug write)

- Khi thêm test mới với chuỗi `"\n"` bị lưu thành newline thật → 2 dòng (syntax ERROR).

  Ví dụ: trong file CRLF, chuỗi bị gãy trình cụ thể → regex `\r?\n` trong chuỗi source-thật
  + đọc repr để xác định vị trí; giữ CRLF (`.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")`
  khi ghi lại file CRLF).

- Anchor trong file đôi khi lệch (thay `\r\n` ↔ `\n`); luôn đọc bytes/decode trước khi replace.

## User preferences confirmed (không hỏi giữa chừng)

- Khi dispatch-fix đang chạy: KHÔNG dừng hỏi "tiếp không" — user hỏi "sao k làm nốt cho xong
  mà dừng lại hỏi t". Làm nốt, báo khi xong.
- Mọi write qua worker — nhưng worker chết mid-run thì session tự tiếp nối phần dở
  (đây là ngoại lệ được chấp nhận).
- Model audit 1 task = 1 model xuyên suốt (không đổi giữa các vòng same task);evidence mới (sau
  sửa) = slot audit mới hợp lệ.
- Sol audit cho 1 task: cứ REJECT → fix bằng worker → RE-audit (cùng Sol), LẶP tới APPROVED.
  User chốt 2026-08-09: Sol xuyên suốt, muốn Claude phải nhắc lại. (Session này chạy tới vòng
  6: 14 → 12 → 6 → 8 → 7 → chờ vòng 6.)

## Số findings REJECT KHÔNG giảm đều — đừng kết luận "đang tới đích" khi số tăng

Session 2026-08-09: vòng 4 Sol REJECT lại TĂNG từ 6 lên 8 findings (vòng 5 thêm 7). Bình thường —
auditor đọc diff MỚI (worker sửa đúng findings cũ nhưng sinh đường bug mới):
- Vòng 5 bắt: `_load_checkpoint` chỉ retry khi `status==FAILED` bỏ sót RECOVERY_RESERVED/RECOVERING
  dở → thêm reconcile crash; guard tap chỉ chặn `is False` không chặn `None` → đổi `is not True`;
  sanitizer whitelist giữ `\s` (tab/newline lọt `input text`) → literal space chuẩn hóa; tokenized
  path residue-append → clear hoặc cấm fallback; early visual accept không truyền artifact path.
- KẾT LUẬN: tăng/giảm findings KHÔNG phải tín hiệu hội tụ; chỉ APPROVED mới là điếm kết. Prompt
  re-audit phải liệt kê findings vòng trước + CÁCH ĐÃ SỬA từng cái → auditor verify diff MỚI.

## Validator báo finding trên file SESSION KHÁC đang sửa dở (dirty, chưa commit) — không phải regression

- Triệu chứng: validator workspace exit 1 với `registry_record_incomplete: <consumer>#Sponsored-ad
  ... (2026-08-09) missing=6 concepts` — record MỚI đúng ngày ≥ cutoff thiếu concept.
- Phân biệt: `git status` file → `M` (dirty) = **session/agent khác đang ghi dở CHƯA commit** →
  nó sẽ hoàn thiện record; validator fail-closed là chạy ĐÚNG (tính năng), không phải regression.
- Xử lý đúng: verify diff của MÌNH độc lập (pytest + EOL của mình); finding ngoài phạm vi (file
  dirty thuộc session khác) → báo user rõ lý do, KHÔNG tự sửa record ngoài trong (wait cho session
  đó commit), để user quyết chờ hay xử lý đồng thời. Validator "OK 9/9" là điều kiện cần nhưng
  findings trên file dirty không đổ vào đợt của mình.