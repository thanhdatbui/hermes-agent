#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""php_verify_no_runtime.py — mechanical verification for PHP edits when `php` is unavailable.

Usage:
    python php_verify_no_runtime.py file1.php file2.php ...

Checks (deterministic, on the real files):
  1. brace/paren/bracket balance (strings + comments stripped crudely)
  2. LF-only EOL check (byte-level; grep/file can lie)
  3. inline <script> blocks parse under `node --check` (PHP template tags substituted)

Exit code 0 = all checks passed. This is AD-HOC verification, NOT a php -l equivalent.
"""
import re
import subprocess
import sys
import os

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (("  " + detail) if (not cond and detail) else ""))
    if not cond:
        failures.append(name)


def strip_comments_strings(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                i += 1
            continue
        if c in ('"', "'"):
            q = c
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == q:
                    i += 1
                    break
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def rendered_js(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    blocks = re.findall(r"<script>(.*?)</script>", src, flags=re.S)
    rendered = []
    for b in blocks:
        b = re.sub(r'"<\?=.*?\?>"', '"TEMPLATE"', b, flags=re.S)  # url: "<?=...?>" -> url: "TEMPLATE"
        b = re.sub(r"<\?=.*?\?>", "TEMPLATE", b, flags=re.S)
        b = re.sub(r"<\?php.*?\?>", "", b, flags=re.S)
        rendered.append(b)
    return "\n;\n".join(rendered)


def main(files):
    if not files:
        print(__doc__)
        return 2
    for f in files:
        if not os.path.exists(f):
            check(f"exists {f}", False, "file not found")
            continue
        raw = open(f, "rb").read()
        s = strip_comments_strings(raw.decode("utf-8", errors="replace"))
        bal = (s.count("{") == s.count("}") and s.count("(") == s.count(")")
               and s.count("[") == s.count("]"))
        check(f"balanced braces {f}", bal)
        check(f"LF-only EOL {f}", b"\r\n" not in raw)
        js = rendered_js(f)
        if js.strip():
            tmp = os.path.join(os.environ.get("TEMP", "."), "hermes-verify-rendered.js")
            with open(tmp, "w", encoding="utf-8") as tf:
                tf.write(js)
            r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
            if os.path.exists(tmp):
                os.unlink(tmp)
            check(f"node --check rendered JS {f}", r.returncode == 0, r.stderr[:300])
    print()
    if failures:
        print("VERIFY FAILED:", len(failures), "checks")
        return 1
    print("VERIFY OK (ad-hoc; php -l BLOCKED unless a runtime exists)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))