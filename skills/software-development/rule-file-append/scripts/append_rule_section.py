# -*- coding: utf-8 -*-
"""Rule-file append with EOL preservation: baseline -> backup -> append -> verify.

Edit TARGETS / SECTION / PREFIX at the top, then run with python3 (use a
C:/... or C:\\... path to the script, NOT /c/... which MSYS mangles after cd
to a D: drive). Prints baseline/backup paths and a PASS/FAIL table.
Does NOT commit anything.

Handles per file: pure-CRLF, pure-LF, MIXED (uses DOMINANT EOL so the
pre-existing minority-EOL count stays byte-identical), already-blank-line
ending (no extra separator), and unterminated last line (terminates it first
and flags it so the delta stays honest).
"""
import hashlib, os, shutil, datetime

# --- EDIT THESE -------------------------------------------------------------
TARGETS = [
    r"D:\Taadaa\AGENTS.md",
    # ... all assigned files (repo-root AGENTS.md / PROJECT_RULES.md only;
    #     exclude nested apps/node_modules AGENTS.md unless explicitly listed)
]

SECTION = [
    "## Merge / Cleanup Rule (bắt buộc, 2026-08-08)",
    "",
    "Khi thực hiện merge nhánh về main hoặc dọn nhánh/tree quan trọng:",
    "1. Lên PLAN bằng subagent TRƯỚC khi merge (không merge mù).",
    "2. Worker thực thi merge/resolve.",
    "3. Chạy AUDIT lại sau khi worker xong — lặp tới khi audit APPROVED mới xoá nhánh/tree.",
    "4. Xoá nhánh chỉ sau bằng chứng absorbed/superseded (merge-tree/reflog/fsck).",
]

PREFIX = "rule-merge"          # baseline/backup artifact prefix
WORKER_N = "2"                 # worker number for baseline2/backup2 naming
MARKER = "Merge / Cleanup Rule"  # must appear exactly once per file after append
# ----------------------------------------------------------------------------

def stats(b):
    crlf = b.count(b'\r\n')
    lf = b.count(b'\n')
    return crlf, lf - crlf, b.count(b'\r') - crlf, lf  # crlf, lone_lf, lone_cr, lines

def classify(crlf, lone_lf, lone_cr):
    if crlf > 0 and lone_lf == 0 and lone_cr == 0:
        return "CRLF"
    if lone_lf > 0 and crlf == 0 and lone_cr == 0:
        return "LF"
    return "MIXED"

def pick_eol(b, eol_class):
    # MIXED -> DOMINANT EOL (count CR vs LF bytes). Keeps the pre-existing
    # minority-EOL count byte-identical: e.g. LF-dominant mixed file with 2 CRLF
    # lines -> CR stays 2, only LF grows. Tail-EOL is the alternative (uniform
    # boundary, minority count balloons) - if you switch, update verify below.
    if eol_class == "CRLF":
        return b'\r\n'
    if eol_class == "LF":
        return b'\n'
    return b'\r\n' if b.count(b'\r') > b.count(b'\n') else b'\n'

def main():
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base_file = rf"D:\Taadaa\{PREFIX}-baseline{WORKER_N}-{ts}.txt"
    backup_dir = rf"D:\Taadaa\{PREFIX}-backup{WORKER_N}-{ts}"
    os.makedirs(backup_dir, exist_ok=True)

    baseline = []
    flags = {}
    for p in TARGETS:
        assert os.path.isfile(p), f"MISSING: {p}"
        b = open(p, 'rb').read()
        crlf, lone_lf, lone_cr, lines = stats(b)
        baseline.append(f"{hashlib.sha256(b).hexdigest()}  {classify(crlf, lone_lf, lone_cr)}  "
                        f"crlf={crlf} lone_lf={lone_lf} lone_cr={lone_cr} lines={lines}  {p}")
        # mirror repo-relative path to avoid AGENTS.md/PROJECT_RULES.md collisions
        dest = os.path.join(backup_dir, os.path.basename(p).replace(' ', '_')
                            + "__" + (os.path.basename(os.path.dirname(p)) or "ROOT"))
        shutil.copy2(p, dest)
    with open(base_file, 'w', encoding='utf-8', newline='') as f:
        f.write("\n".join(baseline) + "\n")
    print(f"BASELINE: {base_file}\nBACKUP:   {backup_dir}\n")

    # --- append -----------------------------------------------------------
    expected_delta = {}
    for p in TARGETS:
        b = open(p, 'rb').read()
        assert MARKER.encode('utf-8') not in b, f"ALREADY HAS SECTION: {p}"
        crlf, lone_lf, lone_cr, lines = stats(b)
        eol_class = classify(crlf, lone_lf, lone_cr)
        EOL = pick_eol(b, eol_class)
        out = b
        delta = 0
        if not out.endswith(EOL):          # unterminated last line -> terminate, flag
            out += EOL
            delta += 1
            flags[p] = "FIXED-UNTERMINATED-LAST-LINE"
        if not out.endswith(EOL + EOL):    # blank separator line before section
            out += EOL
            delta += 1
        out += EOL.join(s.encode('utf-8') for s in SECTION) + EOL
        delta += len(SECTION)
        expected_delta[p] = delta
        with open(p, 'wb') as f:
            f.write(out)

    # --- verify ------------------------------------------------------------
    bl = {}
    for line in open(base_file, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line:
            continue
        fields = line.split("  ")
        kv = " ".join(fields[2:-1]); path = fields[-1]
        d = {}
        for tok in kv.split():
            k, v = tok.split("="); d[k] = int(v)
        bl[path] = (fields[0], fields[1], d)

    all_ok = True
    for p in TARGETS:
        b = open(p, 'rb').read()
        crlf, lone_lf, lone_cr, lines = stats(b)
        eol = classify(crlf, lone_lf, lone_cr)
        bsha, beol, bd = bl[p]
        delta = lines - bd["lines"]
        EOL = pick_eol(b, beol)
        section = EOL.join(s.encode('utf-8') for s in SECTION) + EOL
        # byte-exact: appended block must be the section (separator presence
        # varies with original tail; expected_delta tracks the true line delta)
        byte_exact = b.endswith(section) and expected_delta[p] == delta
        if beol == "LF":
            eol_ok = (crlf == 0 and lone_cr == 0 and lone_lf == bd["lone_lf"] + delta)
        elif beol == "CRLF":
            eol_ok = (lone_lf == 0 and lone_cr == 0 and crlf == bd["crlf"] + delta)
        else:
            # MIXED: dominant-EOL policy — majority count grows, minority
            # stays byte-identical (a naive crlf+delta check here would FAIL
            # LF-dominant mixed files; a "CR unchanged" check would fail CRLF
            # files — compute per dominant side).
            dom_crlf = (bd["crlf"] + bd["lone_cr"]) > (bd["crlf"] + bd["lone_lf"])
            if dom_crlf:
                eol_ok = (crlf == bd["crlf"] + delta and lone_lf == bd["lone_lf"]
                          and lone_cr == bd["lone_cr"])
            else:
                eol_ok = (lone_lf == bd["lone_lf"] + delta and crlf == bd["crlf"]
                          and lone_cr == bd["lone_cr"])
        ok = (eol == beol and eol_ok and byte_exact)
        all_ok &= ok
        flag = " " + flags[p] if p in flags else ""
        print(f"{'PASS' if ok else 'FAIL'} | {beol}->{eol} | delta={delta} | byte_exact={byte_exact}{flag} | {p}")
    print("\nALL_PASS" if all_ok else "\nSOME_FAIL")
    print("\nArtifacts left: baseline + backup. NOT committed (by design).")

if __name__ == "__main__":
    main()