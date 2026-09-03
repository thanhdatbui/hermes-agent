"""Regenerate avatar.jpg for a set of machines using the workbook's `video gốc` column.

2026-08-15 lesson: for Tik2 machines 40-74 the `Folder Video` column is a RENDER ID
(314/322/586...) — D:\\video goc\\<that> does NOT exist. The real source folder is
`video gốc` (120..154). The folder logged in execution.log is ALSO unreliable for
those machines (latest run may be a Tik1 run, off-by-one from the Tik2 mapping).

Usage:
  python regenerate_avatars_from_workbook.py --workbook D:\\OneDrive\\TaadaaData\\kibe\\Tik2.xlsx --machines 40,41,42,43
  python regenerate_avatars_from_workbook.py --workbook ... --machines all-except 38
"""
import argparse
import subprocess
import time
from pathlib import Path

VENV = r"D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe"
MAKE_AVATAR = r"D:\Taadaa\Tiktok-video\scripts\_make_avatar.py"
SOURCE_ROOT = Path(r"D:\video goc")


def load_machine_folder_map(workbook: str) -> dict[int, int]:
    """Read (Máy -> video gốc) from the active sheet. Never reads credentials."""
    import openpyxl

    wb = openpyxl.load_workbook(workbook, data_only=True, read_only=True)
    ws = wb.active
    m2g: dict[int, int] = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[0] is None:
            continue
        try:
            machine = int(r[0])
        except (TypeError, ValueError):
            continue
        try:
            video_goc = int(r[4])  # column E = 'video gốc'
        except (TypeError, ValueError):
            continue
        if machine > 0 and video_goc > 0:
            m2g[machine] = video_goc
    return m2g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", required=True,
                    default=r"D:\OneDrive\TaadaaData\kibe\Tik2.xlsx")
    ap.add_argument("--machines", help="comma list, or 'all-except <N,M>'")
    args = ap.parse_args()

    m2g = load_machine_folder_map(args.workbook)
    if not m2g:
        print("No machine->video_gốc rows found (check column E).")
        return 2

    if args.machines and args.machines.lower().startswith("all-except"):
        exclude = {int(x) for x in args.machines.split()[-1].split(",") if x.strip()}
        targets = sorted(m for m in m2g if m not in exclude)
    elif args.machines:
        targets = [int(x) for x in args.machines.split(",") if x.strip()]
    else:
        targets = sorted(m2g)
    targets = [m for m in targets if m in m2g]
    if not targets:
        print("No target machines in workbook.")
        return 2

    out = []
    start = time.time()
    for i, m in enumerate(targets, 1):
        folder = m2g[m]
        src = SOURCE_ROOT / str(folder)
        if not src.is_dir():
            print(f"[{i}/{len(targets)}] máy={m} video_gốc={folder} MISSING "
                  f"(D:\\video goc\\{folder} not a dir)", flush=True)
            out.append((m, folder, False))
            continue
        t0 = time.time()
        try:
            r = subprocess.run([VENV, MAKE_AVATAR, str(folder)],
                               capture_output=True, text=True, timeout=300)
            last = (r.stdout or "").strip().splitlines()
            last = last[-1] if last else "(no stdout)"
            ok = r.returncode == 0 and "AVATAR OK" in (r.stdout or "")
            print(f"[{i}/{len(targets)}] máy={m} video_gốc={folder} rc={r.returncode} "
                  f"ok={ok} {last} ({time.time()-t0:.0f}s)", flush=True)
        except subprocess.TimeoutExpired:
            print(f"[{i}/{len(targets)}] máy={m} video_gốc={folder} TIMEOUT (>300s)", flush=True)
            ok = False
        except Exception as exc:
            print(f"[{i}/{len(targets)}] máy={m} video_gốc={folder} EXC {exc}", flush=True)
            ok = False
        out.append((m, folder, ok))

    fails = [(m, f) for m, f, ok in out if not ok]
    print(f"DONE {time.time()-start:.0f}s: {len(out)-len(fails)}/{len(out)} OK; "
          f"FAILED: {fails}")
    print("RED FLAG: eyeball any avatar.jpg < ~10KB with vision_analyze before upload "
          "(blank/flat frame may have won).")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
