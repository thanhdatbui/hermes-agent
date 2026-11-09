#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
advisor_consult.py (Archived / Deprecated Forwarder)
---------------------------------------------------
File này đã được ARCHIVE và chuyển tiếp toàn bộ cuộc gọi sang Single Source of Truth chuẩn của Farm:
    D:/Taadaa/tools/consult_advisor.py

Đảm bảo luôn triệu hồi đầy đủ Hội đồng Cố vấn (Sol + Gemini + Claude).
"""

from __future__ import annotations

import os
import sys
import subprocess

CANONICAL_SCRIPT = r"D:\Taadaa\tools\consult_advisor.py"


def classify_advice_intent(*args, **kwargs) -> bool:
    return False


def ensure_dual_answer(response=None, *args, **kwargs):
    return response


def main():
    if not os.path.exists(CANONICAL_SCRIPT):
        sys.stderr.write(f"[ERROR] Canonical script not found: {CANONICAL_SCRIPT}\n")
        sys.exit(1)

    # Chuyển tiếp toàn bộ sys.argv sang consult_advisor.py
    cmd = [sys.executable, CANONICAL_SCRIPT] + sys.argv[1:]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)


if __name__ == "__main__":
    main()
