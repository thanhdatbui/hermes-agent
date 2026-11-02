---
name: rule-file-append
description: >-
  Append an approved text section (policy/rule block) to the END of rule files
  (AGENTS.md / PROJECT_RULES.md) across many repos while preserving each file's
  EOL byte-for-byte, with baseline+backup+verify discipline and NO commit.
  Trigger: user says "thêm section ... vào CUỐI tất cả AGENTS.md + PROJECT_RULES.md",
  "append rule to all repos", "chèn text duyệt vào cuối file", or any multi-file
  append where EOL preservation, verification, and worker-scope boundaries matter.
---
# Rule File Append (EOL-preserving, baseline+backup+verify, no commit)

Class of task: user approves a fixed text block and wants it appended verbatim to
the END of many rule files (often AGENTS.md + PROJECT_RULES.md in a fleet of repos),
where the same task may be split across multiple worker sessions. Success criteria:
byte-exact appended block, per-file EOL unchanged, verifiable delta, files backed
up, **nothing committed**, and no file outside the assigned list touched.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
