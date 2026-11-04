import os
import sys
import json
import pytest
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import post_morning_gmail_2fa_watchdog as watchdog


def test_watchdog_exports():
    assert callable(watchdog.get_gpm_candidates)
    assert callable(watchdog.save_state_results)
    assert callable(watchdog.is_feed_ca1_finished)
