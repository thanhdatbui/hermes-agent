#!/usr/bin/env python3
"""
flush_dpapi_journal_to_workbook.py
Flush các Secret Key 2FA đang nằm an toàn trong Windows DPAPI Journal vào file Excel
taikhoan_dat_v2_updated .xlsx (Cột E) và transition journal sang trạng thái WRITTEN.
"""

import argparse
import sys
from pathlib import Path

DEFAULT_JOURNAL_DIR = Path(r"C:\Users\Kibe\AppData\Local\codex_gmail_debug-tiktok-add-bao-mat-f2a\journals")
DEFAULT_WORKBOOK_PATH = Path(r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx")
DEFAULT_SHEET = "Tài Khoản"

def flush_journals(
    journal_dir: Path,
    workbook_path: Path,
    sheet_name: str = DEFAULT_SHEET,
    dry_run: bool = False,
) -> int:
    f2a_path = Path(r"D:\Taadaa\tiktok-add-bao-mat-f2a")
    if str(f2a_path) not in sys.path:
        sys.path.insert(0, str(f2a_path))
    if str(f2a_path / "python_runner") not in sys.path:
        sys.path.insert(0, str(f2a_path / "python_runner"))

    try:
        from core.journal import JournalStore, PhaseBState
        from core.workbook import write_2fa, read_2fa_value
    except ImportError as e:
        print(f"[ERROR] Cannot import core modules from {f2a_path}: {e}")
        return 0

    if not journal_dir.exists():
        print(f"[ERROR] Journal dir not found: {journal_dir}")
        return 0

    store = JournalStore(journal_dir)
    resumable_states = {
        PhaseBState.AUTHENTICATOR_CONFIRMED,
        PhaseBState.WRITTEN,
    }

    count = 0
    matched = 0

    print(f"Scanning journals in: {journal_dir}")
    print(f"Target workbook: {workbook_path} [Sheet: {sheet_name}] (dry_run={dry_run})")

    for f in journal_dir.glob("*.dpapi"):
        h = f.stem
        try:
            rec = store.load(h)
        except Exception as exc:
            print(f"  [WARN] Failed to load journal {h}: {exc}")
            continue

        if not rec or not rec.secret_key:
            continue

        if rec.state in resumable_states and rec.source_row:
            matched += 1
            cur_val = None
            try:
                cur_val = read_2fa_value(workbook_path, rec.source_row, sheet_name=sheet_name)
            except Exception as exc:
                print(f"  [WARN] Failed to read row {rec.source_row}: {exc}")

            if cur_val == rec.secret_key:
                print(f"  [SKIP] Row {rec.source_row} ({rec.username}): Already has matching 2FA secret")
                if rec.state != PhaseBState.WRITTEN and not dry_run:
                    store.transition(rec, PhaseBState.WRITTEN)
                continue

            if dry_run:
                print(f"  [DRY-RUN] Would write Row {rec.source_row} ({rec.username}) -> Secret: {rec.secret_key[:6]}...{rec.secret_key[-4:]}")
                count += 1
                continue

            try:
                write_2fa(workbook_path, rec.source_row, rec.secret_key, sheet_name=sheet_name)
                verified = read_2fa_value(workbook_path, rec.source_row, sheet_name=sheet_name)
                if verified == rec.secret_key:
                    store.transition(rec, PhaseBState.WRITTEN)
                    count += 1
                    print(f"  [OK] Row {rec.source_row} ({rec.username}): Flushed and verified successfully")
                else:
                    print(f"  [FAIL] Row {rec.source_row} ({rec.username}): Verification mismatch after write!")
            except Exception as exc:
                print(f"  [ERROR] Row {rec.source_row} ({rec.username}): Write failed: {exc}")

    print(f"\nCompleted: {matched} matched journals, {count} records written/verified.")
    return count

def main() -> None:
    parser = argparse.ArgumentParser(description="Flush DPAPI journal 2FA secrets to workbook")
    parser.add_argument("--journal-dir", type=Path, default=DEFAULT_JOURNAL_DIR, help="Path to journal folder")
    parser.add_argument("--workbook-path", type=Path, default=DEFAULT_WORKBOOK_PATH, help="Path to workbook .xlsx")
    parser.add_argument("--sheet", type=str, default=DEFAULT_SHEET, help="Workbook sheet name")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    flush_journals(args.journal_dir, args.workbook_path, args.sheet, args.dry_run)

if __name__ == "__main__":
    main()
