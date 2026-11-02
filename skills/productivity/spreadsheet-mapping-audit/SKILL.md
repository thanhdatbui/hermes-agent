---
name: spreadsheet-mapping-audit
description: Audit and safely synchronize IDs, keys, folder mappings, and row-level relationships across Excel workbooks and filesystem-backed media manifests.
version: 1.0.0
category: productivity
metadata:
  hermes:
    tags: [xlsx, mapping, reconciliation, filesystem, audit]
---
# Spreadsheet Mapping Audit

Use this class-level skill whenever multiple Excel files represent the same accounts/assets, especially when one workbook maps records to folders or files on disk.

## Core rule

Never infer a key's meaning from its label, apparent sequence, or row position. A column named `Tik`, `STT`, or `ID` may be a global asset/folder key rather than a per-machine ordinal. Determine the contract from headers, workflow code/docs, representative rows, and the target filesystem before editing.

## Authority and synchronization direction

- Declare one authoritative master before editing. For this workbook class, the registration workbook (`taikhoan_dat_v2`) is the master; `Tik1.xlsx`, `Tik2.xlsx`, and `tik3.xlsx` are derived slot views.
- Synchronization is **one-way: master → derived**. A correction or deletion in a derived workbook must not be written back to the master automatically. If a value exists only in a derived file, report it as orphan/stale derived data and clear it by rebuilding from the master only after the user requests the repair.
- When the user defines Tik1/Tik2/Tik3 as account slots, select source rows by **machine-local row position** (slot k = the k-th REG row of that machine, including empty rows → empty slot), then copy both `ID` and the folder value into the derived row. Do not skip empty-ID rows when counting slots — row position is the contract, and skipping shifts later slots (observed: Tik3 rows got IDs from slot 4+ of REG).
- **REG's folder column is not automatically authoritative.** Historical manual edits can corrupt it (machine 2 read `12,10,11,13,14,15` instead of `9,10,11,12,13,14`). When a proven workbook exists (one whose videos were actually posted), anchor the folder allocation on it and normalize REG to the derived rule, with user confirmation.
- For this class, the folder allocation rule is `Folder Video(machine m, slot k) = (m-1)*8 + k` (Tik1 k=1 → 1,9,17...; Tik2 k=2 → 2,10,18...; Tik3 k=3 → 3,11,19...). Verify the rule against the posted workbook and D-folder existence before mass-rewriting.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
