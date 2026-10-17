import io
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

REPO_SCRIPTS = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(REPO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REPO_SCRIPTS))

import cron_hotmail_gpm_lifecycle_6h_report as report_mod


def _profile(stage, status="PENDING", login=None, reg=None, **extra):
    data = {"stage": stage, "status": status}
    if login:
        data["hotmail_login_at"] = login
    if reg:
        data["chatgpt_registered_at"] = reg
    data.update(extra)
    return data


TS = "2026-10-01T00:00:00Z"


class ReportTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.kibe_path = self.tmp / "kibe.json"
        self.admin_path = self.tmp / "admin.json"
        self.db_path = self.tmp / "omni.sqlite"
        self.write_state(self.kibe_path, {})
        self.write_state(self.admin_path, {})

    # ── helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def write_state(path, profiles):
        path.write_text(json.dumps({"profiles": profiles}), encoding="utf-8")

    def make_db(self, connections=None, combos=None, schema=True):
        """connections: list[(provider, is_active)]; combos: list[(name, data)]."""
        conn = sqlite3.connect(self.db_path)
        if schema:
            conn.execute("CREATE TABLE provider_connections (id INTEGER PRIMARY KEY, provider TEXT, is_active)")
            conn.execute("CREATE TABLE combos (id INTEGER PRIMARY KEY, name TEXT, data TEXT)")
        for provider, active in connections or []:
            conn.execute("INSERT INTO provider_connections (provider, is_active) VALUES (?, ?)", (provider, active))
        for name, data in combos or []:
            conn.execute("INSERT INTO combos (name, data) VALUES (?, ?)", (name, data))
        conn.commit()
        conn.close()

    def make_default_db(self):
        self.make_db(
            connections=[("chatgpt-web", 1), ("chatgpt-web", 1), ("chatgpt-web", 0), ("other", 1)],
            combos=[("chatgpt-web-pool", json.dumps({"models": [{"id": "m1"}, {"id": "m2"}]}))],
        )

    def run_report(self):
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(report_mod, "KIBE_STATE_PATH", self.kibe_path), \
             patch.object(report_mod, "ADMIN_STATE_PATH", self.admin_path), \
             patch.object(report_mod, "DB_PATH", self.db_path), \
             redirect_stdout(out), \
             redirect_stderr(err):
            rc = report_mod.main()
        text = out.getvalue()
        events = [json.loads(line) for line in err.getvalue().splitlines() if line.startswith("{")]
        return rc, text, events

    def run_snapshot(self):
        tel = report_mod.Telemetry()
        out = io.StringIO()
        with patch.object(report_mod, "KIBE_STATE_PATH", self.kibe_path), \
             patch.object(report_mod, "ADMIN_STATE_PATH", self.admin_path), \
             patch.object(report_mod, "DB_PATH", self.db_path), \
             redirect_stdout(out):
            snap = report_mod.collect_snapshot(tel)
        return snap, tel

    @staticmethod
    def find_events(events, name):
        return [e for e in events if e["event"] == name]


class TestAggregation(ReportTestCase):
    def test_report_aggregates_chatgpt_and_change_hotmail_progress(self):
        self.write_state(self.kibe_path, {
            "M01:acc1@hotmail.com": _profile("WAIT_7D", "WAITING", login="2026-09-25T00:00:00Z", reg=TS),
            "M02:acc2@hotmail.com": _profile("CHANGE_INFO", "PENDING", reg="2026-10-02T00:00:00Z"),
            "M03:acc3@hotmail.com": _profile("DONE", "DONE", reg="2026-09-27T00:00:00Z"),
        })
        self.write_state(self.admin_path, {
            "M201:acc201@hotmail.com": _profile("WAIT_7D", "WAITING", reg="2026-10-05T00:00:00Z"),
        })
        self.make_default_db()

        rc, text, _ = self.run_report()

        self.assertEqual(rc, 0)
        for expected in (
            "BÁO CÁO 6H: VÒNG ĐỜI HOTMAIL -> GPM -> CHATGPT TOÀN FARM",
            "TIẾN ĐỘ HOTMAIL LOGIN:",
            "TIẾN ĐỘ CHATGPT REG:",
            "Toàn Farm Đã Reg Thành Công : 4/4",
            "TIẾN ĐỘ CHANGE HOTMAIL & BẢO MẬT:",
            "Đã Hoàn Tất Đổi Pass (DONE) : 1/4",
            "Hàng đợi đổi pass (CHANGE_INFO): 1 (Kibe: 1 | Admin: 0)",
            "Đang ngâm 7 ngày chờ đổi (WAIT_7D): 2 (Kibe: 1 | Admin: 1)",
            "CHATGPT WEB POOL (OMNIRoute :20129):",
            "3 connections (2 Active | 1 Soaking 48h)",
            "Models trong Web Pool      : 2 accounts",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("{", text)
        self.assertNotIn("Lỗi / Kẹt cần cứu", text)

    def test_full_multi_farm_lifecycle_stages(self):
        self.write_state(self.kibe_path, {
            "M01:a": _profile("HOTMAIL_LOGIN", "PENDING"),
            "M02:b": _profile("HOTMAIL_LOGIN", "BLOCKED"),
            "M03:c": _profile("CHATGPT_REG", "RUNNING", login=TS),
            "M04:d": _profile("WAIT_7D", "WAITING", login=TS, reg=TS),
            "M05:e": _profile("CHANGE_INFO", "PENDING", login=TS, reg=TS),
            "M06:f": _profile("DONE", "DONE", login=TS, reg=TS),
            "M07:g": _profile("CHANGE_INFO", "FAILED", login=TS, reg=TS),
        })
        self.write_state(self.admin_path, {
            "M201:a": _profile("HOTMAIL_LOGIN", "PENDING"),
            "M202:b": _profile("BLOCKED", "BLOCKED"),
            "M203:c": _profile("CHATGPT_REG", "QUARANTINE", login=TS),
            "M204:d": _profile("WAIT_7D", "WAITING", login=TS, reg=TS),
        })
        self.make_default_db()

        snap, _ = self.run_snapshot()
        kibe, admin, totals = snap["farms"]["kibe"], snap["farms"]["admin"], snap["totals"]

        self.assertEqual(kibe["total"], 7)
        self.assertEqual(kibe["buckets"], {
            "HOTMAIL_LOGIN": 1, "CHATGPT_REG": 1, "WAIT_7D": 1, "CHANGE_INFO": 1,
            "DONE": 1, "BLOCKED": 2, "UNKNOWN": 0,
        })
        self.assertEqual((kibe["login_pending"], kibe["login_blocked"]), (1, 1))
        self.assertEqual(kibe["login_ok"], 5)
        self.assertEqual(kibe["chatgpt_ok"], 4)
        self.assertEqual((admin["total"], admin["blocked"], admin["wait_7d"]), (4, 2, 1))
        self.assertEqual(admin["buckets"]["CHATGPT_REG"], 0)
        self.assertEqual(totals["total"], 11)
        self.assertEqual(totals["done"], 1)
        self.assertEqual(totals["blocked"], 4)
        self.assertEqual(totals["login_pending"], 2)
        # bucket loại trừ lẫn nhau => tổng bucket == tổng profile
        self.assertEqual(sum(totals["buckets"].values()), totals["total"])
        for farm in (kibe, admin):
            self.assertEqual(sum(farm["buckets"].values()), farm["total"])

        _, text, _ = self.run_report()
        self.assertIn("Lỗi / Kẹt cần cứu (BLOCKED): 4 (Kibe: 2 | Admin: 2)", text)
        self.assertIn("Đang Chờ Login (PENDING)   : 2 (Kibe: 1 | Admin: 1)", text)

    def test_stage_and_status_are_case_and_whitespace_insensitive(self):
        self.write_state(self.kibe_path, {
            "M01:a": _profile(" wait_7d ", "waiting", login=TS, reg=TS),
            "M02:b": _profile("done", "done", login=TS, reg=TS),
            "M03:c": _profile("change_info", " blocked "),
        })
        snap, _ = self.run_snapshot()
        buckets = snap["farms"]["kibe"]["buckets"]
        self.assertEqual((buckets["WAIT_7D"], buckets["DONE"], buckets["BLOCKED"]), (1, 1, 1))

    def test_empty_states_do_not_divide_by_zero(self):
        self.make_default_db()
        rc, text, _ = self.run_report()
        self.assertEqual(rc, 0)
        self.assertIn("Tổng số tài khoản trong Queue: 0 (Kibe: 0 | Admin: 0)", text)
        self.assertIn("0/0 (0.0%)", text)

    def test_chatgpt_ok_edge_cases(self):
        # (fields, expected chatgpt_ok, expected done_without_chatgpt)
        cases = [
            ({"stage": "BLOCKED", "status": "DONE", "bucket": "DONE", "has_chatgpt": False}, 0, 1),
            ({"stage": "HOTMAIL_LOGIN", "status": "PENDING", "bucket": "HOTMAIL_LOGIN", "has_chatgpt": False}, 0, 0),
            ({"stage": "BLOCKED", "status": "BLOCKED", "bucket": "BLOCKED", "has_chatgpt": True}, 0, 0),
            ({"stage": "CHATGPT_REG", "status": "RUNNING", "bucket": "CHATGPT_REG", "has_chatgpt": True}, 1, 0),
            ({"stage": "DONE", "status": "DONE", "bucket": "DONE", "has_chatgpt": False}, 1, 1),
            ({"stage": "DONE", "status": "DONE", "bucket": "DONE", "has_chatgpt": True}, 1, 0),
            ({"stage": "CHANGE_INFO", "status": "DONE", "bucket": "DONE", "has_chatgpt": False}, 1, 1),
        ]
        records = [{"key": f"k{i}", "status": "PENDING", "has_login": False, **fields}
                   for i, (fields, _, _) in enumerate(cases)]

        for rec, (_, exp_ok, exp_flag) in zip(records, cases):
            tel = report_mod.Telemetry(stream=io.StringIO())
            agg = report_mod.aggregate_records([rec], tel, "kibe")
            self.assertEqual(agg["chatgpt_ok"], exp_ok, rec)
            self.assertEqual(agg["done_without_chatgpt"], exp_flag, rec)
            events = self.find_events(tel.events, "done_without_chatgpt")
            self.assertEqual(len(events), exp_flag, rec)
            if exp_flag:
                self.assertEqual(events[0]["error_class"], "DONE_WITHOUT_CHATGPT_REG")
                self.assertEqual(events[0]["level"], "warning")
                self.assertEqual(events[0]["farm"], "kibe")
                self.assertEqual(events[0]["sample"], [rec["key"]])

        tel = report_mod.Telemetry(stream=io.StringIO())
        agg = report_mod.aggregate_records(records, tel, "admin")
        expected_ok = sum(c[1] for c in cases)
        expected_flag = sum(c[2] for c in cases)
        expected_keys = [r["key"] for r, c in zip(records, cases) if c[2]]
        self.assertEqual(agg["total"], len(cases))
        self.assertEqual(agg["chatgpt_ok"], expected_ok)
        self.assertEqual(agg["done_without_chatgpt"], expected_flag)
        self.assertLessEqual(agg["done_without_chatgpt"], agg["done"])
        self.assertLessEqual(agg["chatgpt_ok"], agg["total"])
        self.assertEqual(sum(agg["buckets"].values()), agg["total"])
        events = self.find_events(tel.events, "done_without_chatgpt")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["count"], expected_flag)
        self.assertEqual(events[0]["farm"], "admin")
        self.assertEqual(events[0]["sample"], expected_keys)

        merged = report_mod.merge_metrics(agg, agg)
        self.assertEqual(merged["chatgpt_ok"], 2 * expected_ok)
        self.assertEqual(merged["done_without_chatgpt"], 2 * expected_flag)

    def test_chatgpt_ok_consistency_through_normalize(self):
        profiles = {
            "E1:done_no_reg": {"stage": "DONE", "status": "DONE"},
            "E2:change_failed_with_reg": {"stage": "CHANGE_INFO", "status": "FAILED", "chatgpt_registered_at": TS},
            "E3:blocked_done_status": {"stage": "BLOCKED", "status": "DONE", "chatgpt_registered_at": TS},
            "E4:failed_stage_with_reg": {"stage": "FAILED", "status": "PENDING", "chatgpt_registered_at": TS},
            "E5:login_stage_done_status": {"stage": "HOTMAIL_LOGIN", "status": "DONE"},
            "E6:wait_with_reg": {"stage": "WAIT_7D", "status": "WAITING", "chatgpt_registered_at": TS},
            "E7:chatgpt_reg_running": {"stage": "CHATGPT_REG", "status": "RUNNING",
                                       "hotmail_login_at": TS, "chatgpt_registered_at": TS},
        }
        # key -> (bucket, chatgpt_ok, done_without_chatgpt)
        expected = {
            "E1:done_no_reg": ("DONE", 1, 1),
            "E2:change_failed_with_reg": ("BLOCKED", 1, 0),
            "E3:blocked_done_status": ("BLOCKED", 0, 0),
            "E4:failed_stage_with_reg": ("BLOCKED", 0, 0),
            "E5:login_stage_done_status": ("DONE", 1, 1),
            "E6:wait_with_reg": ("WAIT_7D", 1, 0),
            "E7:chatgpt_reg_running": ("CHATGPT_REG", 1, 0),
        }

        tel = report_mod.Telemetry(stream=io.StringIO())
        records = report_mod.normalize_profiles(profiles, tel, "kibe")
        self.assertEqual(tel.warnings(), [])
        by_key = {r["key"]: r for r in records}
        for key, (bucket, exp_ok, exp_flag) in expected.items():
            self.assertEqual(by_key[key]["bucket"], bucket, key)
            single = report_mod.aggregate_records([by_key[key]])
            self.assertEqual(single["chatgpt_ok"], exp_ok, key)
            self.assertEqual(single["done_without_chatgpt"], exp_flag, key)

        tel = report_mod.Telemetry(stream=io.StringIO())
        agg = report_mod.aggregate_records(records, tel, "kibe")
        flagged = [k for k, (_, _, f) in expected.items() if f]
        self.assertEqual(agg["total"], len(profiles))
        self.assertEqual(agg["done"], sum(1 for b, _, _ in expected.values() if b == "DONE"))
        self.assertEqual(agg["chatgpt_ok"], sum(ok for _, ok, _ in expected.values()))
        self.assertEqual(agg["done_without_chatgpt"], len(flagged))
        self.assertEqual(sum(agg["buckets"].values()), agg["total"])
        self.assertLessEqual(agg["done_without_chatgpt"], agg["done"])
        self.assertLessEqual(agg["done_without_chatgpt"], agg["chatgpt_ok"])
        events = self.find_events(tel.events, "done_without_chatgpt")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["count"], len(flagged))
        self.assertEqual(events[0]["sample"], flagged)
        self.assertEqual(events[0]["error_class"], "DONE_WITHOUT_CHATGPT_REG")


class TestStateRobustness(ReportTestCase):
    def test_corrupted_state_json_fails_safe(self):
        self.kibe_path.write_text("{broken json", encoding="utf-8")
        self.admin_path.write_text("{broken json", encoding="utf-8")
        self.make_default_db()

        rc, text, events = self.run_report()

        self.assertEqual(rc, 0)
        warnings = self.find_events(events, "state_parse_warning")
        self.assertTrue(any(w["event"] == "state_parse_warning" for w in warnings))
        self.assertEqual({w["farm"] for w in warnings}, {"kibe", "admin"})
        for w in warnings:
            self.assertEqual(w["error_class"], "STATE_INVALID_JSON")
            self.assertIn("duration_ms", w)
        self.assertIn("Tổng số tài khoản trong Queue: 0", text)
        self.assertIn("STATE_INVALID_JSON", text)

    def test_corrupted_state_does_not_hide_healthy_farm(self):
        self.kibe_path.write_text("{broken json", encoding="utf-8")
        self.write_state(self.admin_path, {"M201:a": _profile("DONE", "DONE", login=TS, reg=TS)})
        snap, _ = self.run_snapshot()
        self.assertEqual(snap["farms"]["kibe"]["total"], 0)
        self.assertEqual(snap["farms"]["admin"]["done"], 1)

    def test_invalid_utf8_state_is_classified_as_io_error(self):
        self.kibe_path.write_bytes(b"\xff\xfe\x00bad")
        _, _, events = self.run_report()
        classes = {e["error_class"] for e in self.find_events(events, "state_parse_warning") if e["farm"] == "kibe"}
        self.assertEqual(classes, {"STATE_IO_ERROR"})

    def test_missing_state_file_is_reported_not_silent(self):
        self.kibe_path.unlink()
        rc, _, events = self.run_report()
        self.assertEqual(rc, 0)
        missing = self.find_events(events, "state_missing")
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["error_class"], "STATE_NOT_FOUND")
        self.assertEqual(missing[0]["farm"], "kibe")

    def test_state_schema_invalid_variants(self):
        variants = {
            "list_top_level": json.dumps([1, 2]),
            "profiles_missing": json.dumps({"other": {}}),
            "profiles_is_list": json.dumps({"profiles": [{"stage": "DONE"}]}),
            "profiles_is_null": json.dumps({"profiles": None}),
        }
        for name, content in variants.items():
            with self.subTest(name):
                self.kibe_path.write_text(content, encoding="utf-8")
                snap, tel = self.run_snapshot()
                self.assertEqual(snap["farms"]["kibe"]["total"], 0)
                kibe_warn = [e for e in tel.events if e["event"] == "state_parse_warning" and e["farm"] == "kibe"]
                self.assertEqual([e["error_class"] for e in kibe_warn], ["STATE_SCHEMA_INVALID"])

    def test_malformed_profile_dicts_are_counted_as_unknown(self):
        self.write_state(self.kibe_path, {
            "M01:none": None,
            "M02:string": "oops",
            "M03:list": ["x"],
            "M04:int_stage": {"stage": 7, "status": ["BLOCKED"]},
            "M05:bad_ts": {"stage": "WAIT_7D", "status": "WAITING",
                           "hotmail_login_at": "not-a-date", "chatgpt_registered_at": 12345},
            "M06:unknown_stage": {"stage": "TELEPORT", "status": "PENDING"},
            "M07:good": _profile("DONE", "DONE", login=TS, reg=TS),
        })
        snap, tel = self.run_snapshot()
        kibe = snap["farms"]["kibe"]

        self.assertEqual(kibe["total"], 7)
        self.assertEqual(kibe["buckets"]["UNKNOWN"], 5)
        self.assertEqual(kibe["buckets"]["WAIT_7D"], 1)
        self.assertEqual(kibe["buckets"]["DONE"], 1)
        self.assertEqual(sum(kibe["buckets"].values()), 7)
        # timestamp hỏng không được tính là đã login/reg
        self.assertEqual(kibe["chatgpt_ok"], 1)
        self.assertEqual(kibe["login_ok"], 2)  # M05 (stage sau login) + M07 (có hotmail_login_at)

        schema = [e for e in tel.events if e["event"] == "profile_schema_warning"]
        self.assertEqual(len(schema), 1)
        self.assertEqual(schema[0]["error_class"], "PROFILE_SCHEMA_INVALID")
        issues = schema[0]["issues"]
        self.assertEqual(issues["non_dict_profile"], 3)
        self.assertEqual(issues["invalid_stage_type"], 1)
        self.assertEqual(issues["invalid_status_type"], 1)
        self.assertEqual(issues["unknown_stage"], 1)
        self.assertEqual(issues["invalid_timestamp:hotmail_login_at"], 1)
        self.assertEqual(issues["invalid_timestamp:chatgpt_registered_at"], 1)
        self.assertLessEqual(len(schema[0]["samples"]["non_dict_profile"]), 5)

    def test_unknown_profiles_are_visible_in_report(self):
        self.write_state(self.kibe_path, {"M01:x": None})
        _, text, _ = self.run_report()
        self.assertIn("Stage không nhận diện (UNKNOWN): 1 (Kibe: 1 | Admin: 0)", text)

    def test_duplicate_json_keys_within_file_are_flagged(self):
        self.kibe_path.write_text(
            '{"profiles": {"M01:a": {"stage": "HOTMAIL_LOGIN", "status": "PENDING"},'
            ' "M01:a": {"stage": "DONE", "status": "DONE"}}}',
            encoding="utf-8",
        )
        snap, tel = self.run_snapshot()
        dup = [e for e in tel.events if e["event"] == "duplicate_json_keys"]
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0]["count"], 1)
        self.assertEqual(dup[0]["sample"], ["M01:a"])
        self.assertEqual(dup[0]["error_class"], "STATE_DUPLICATE_KEYS")
        self.assertEqual(snap["farms"]["kibe"]["total"], 1)
        self.assertEqual(snap["farms"]["kibe"]["done"], 1)  # bản ghi cuối thắng, như json.loads

    def test_cross_farm_duplicate_keys_are_not_silently_merged(self):
        self.write_state(self.kibe_path, {"M01:a": _profile("DONE", "DONE", login=TS, reg=TS)})
        self.write_state(self.admin_path, {"M01:a": _profile("WAIT_7D", "WAITING", login=TS, reg=TS)})
        snap, tel = self.run_snapshot()
        self.assertEqual(snap["totals"]["total"], 2)
        self.assertEqual(snap["totals"]["done"], 1)
        self.assertEqual(snap["totals"]["wait_7d"], 1)
        dup = [e for e in tel.events if e["event"] == "duplicate_profile_keys"]
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0]["error_class"], "PROFILE_KEY_COLLISION")
        self.assertEqual(dup[0]["sample"], ["M01:a"])


class TestDatabaseRobustness(ReportTestCase):
    def test_missing_database_fails_safe(self):
        rc, text, events = self.run_report()
        self.assertEqual(rc, 0)
        missing = self.find_events(events, "db_missing")
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["error_class"], "DB_NOT_FOUND")
        self.assertIn("không đọc được OmniRoute DB", text)
        self.assertNotIn("0 connections", text)

    def test_connect_error_is_reported(self):
        self.make_default_db()
        out = io.StringIO()
        tel = report_mod.Telemetry()
        with patch.object(report_mod.sqlite3, "connect", side_effect=sqlite3.Error("mid-query")), \
             redirect_stdout(out):
            pool = report_mod.collect_omni_pool(self.db_path, tel)
        self.assertFalse(pool["connections_ok"])
        warn = [e for e in tel.events if e["event"] == "db_parse_warning"]
        self.assertEqual(len(warn), 1)
        self.assertEqual(warn[0]["error_class"], "DB_ERROR")
        self.assertEqual(warn[0]["query"], "connect")

    def test_main_survives_connect_error_and_reports_telemetry(self):
        self.make_default_db()
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(report_mod, "KIBE_STATE_PATH", self.kibe_path), \
             patch.object(report_mod, "ADMIN_STATE_PATH", self.admin_path), \
             patch.object(report_mod, "DB_PATH", self.db_path), \
             patch.object(report_mod.sqlite3, "connect", side_effect=sqlite3.Error("mid-query")), \
             redirect_stdout(out), \
             redirect_stderr(err):
            rc = report_mod.main()
        self.assertEqual(rc, 0)
        self.assertIn("correlation_id", out.getvalue())
        self.assertIn("db_parse_warning", err.getvalue())

    def test_missing_tables(self):
        self.make_db(schema=False)
        _, _, events = self.run_report()
        warns = self.find_events(events, "db_parse_warning")
        self.assertEqual({(w["query"], w["error_class"]) for w in warns},
                         {("provider_connections", "DB_MISSING_TABLE"), ("combos", "DB_MISSING_TABLE")})

    def test_missing_column_does_not_break_other_query(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE provider_connections (id INTEGER PRIMARY KEY, provider TEXT)")
        conn.execute("CREATE TABLE combos (id INTEGER PRIMARY KEY, name TEXT, data TEXT)")
        conn.execute("INSERT INTO combos (name, data) VALUES ('chatgpt-web-pool', ?)",
                     (json.dumps({"models": [1, 2, 3]}),))
        conn.commit()
        conn.close()

        pool = self._collect()
        self.assertFalse(pool["connections_ok"])
        self.assertTrue(pool["combo_ok"])
        self.assertEqual(pool["models"], 3)
        _, text, events = self.run_report()
        warns = self.find_events(events, "db_parse_warning")
        self.assertEqual([(w["query"], w["error_class"]) for w in warns], [("provider_connections", "DB_MISSING_COLUMN")])
        self.assertIn("không đọc được OmniRoute DB", text)
        self.assertIn("Models trong Web Pool      : 3 accounts", text)

    def test_file_that_is_not_a_database(self):
        self.db_path.write_bytes(b"this is definitely not sqlite" * 50)
        rc, _, events = self.run_report()
        self.assertEqual(rc, 0)
        classes = {w["error_class"] for w in self.find_events(events, "db_parse_warning")}
        self.assertEqual(classes, {"DB_CORRUPT"})

    def test_database_is_opened_read_only(self):
        self.make_default_db()
        before = self.db_path.read_bytes()
        self._collect()
        self.assertEqual(self.db_path.read_bytes(), before)
        with closing(sqlite3.connect(report_mod._readonly_uri(self.db_path), uri=True)) as conn:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("INSERT INTO combos (name, data) VALUES ('x', '{}')")

    def test_malformed_combos(self):
        cases = {
            "invalid_json": ("{not json", "COMBO_INVALID_JSON"),
            "null_data": (None, "COMBO_INVALID_JSON"),
            "list_not_object": (json.dumps([1, 2]), "COMBO_SCHEMA_INVALID"),
            "models_not_list": (json.dumps({"models": "abc"}), "COMBO_SCHEMA_INVALID"),
            "models_missing": (json.dumps({}), "COMBO_SCHEMA_INVALID"),
        }
        for name, (data, expected) in cases.items():
            with self.subTest(name):
                self.db_path.unlink(missing_ok=True)
                self.make_db(connections=[("chatgpt-web", 1)], combos=[("chatgpt-web-pool", data)])
                tel = report_mod.Telemetry()
                out = io.StringIO()
                with redirect_stdout(out):
                    pool = report_mod.collect_omni_pool(self.db_path, tel)
                self.assertTrue(pool["connections_ok"])
                self.assertFalse(pool["combo_ok"])
                self.assertEqual(pool["total"], 1)
                warn = [e for e in tel.events if e["event"] == "combo_parse_warning"]
                self.assertEqual([e["error_class"] for e in warn], [expected])

    def test_missing_combo_row_is_flagged(self):
        self.make_db(connections=[("chatgpt-web", 1)], combos=[("other-combo", "{}")])
        _, text, events = self.run_report()
        self.assertEqual(self.find_events(events, "combo_missing")[0]["error_class"], "COMBO_NOT_FOUND")
        self.assertIn("Models trong Web Pool      : 0 accounts", text)

    def test_duplicate_combo_rows_use_first_and_warn(self):
        self.make_db(combos=[("chatgpt-web-pool", json.dumps({"models": [1, 2]})),
                             ("chatgpt-web-pool", json.dumps({"models": [1]}))])
        tel = report_mod.Telemetry()
        with redirect_stdout(io.StringIO()):
            pool = report_mod.collect_omni_pool(self.db_path, tel)
        self.assertEqual(pool["models"], 2)
        self.assertEqual([e["error_class"] for e in tel.events if e["event"] == "combo_duplicate"],
                         ["COMBO_DUPLICATE_ROWS"])

    def test_invalid_is_active_values_are_counted_as_unknown(self):
        self.make_db(
            connections=[("chatgpt-web", 1), ("chatgpt-web", "1"), ("chatgpt-web", 0), ("chatgpt-web", None),
                         ("chatgpt-web", 7), ("chatgpt-web", "yes")],
            combos=[("chatgpt-web-pool", json.dumps({"models": []}))],
        )
        pool = self._collect()
        self.assertEqual((pool["total"], pool["active"], pool["soaking"], pool["unknown"]), (6, 2, 1, 3))
        _, text, events = self.run_report()
        self.assertEqual(self.find_events(events, "db_row_warning")[0]["error_class"], "DB_INVALID_IS_ACTIVE")
        self.assertIn("6 connections (2 Active | 1 Soaking 48h | 3 Không rõ)", text)

    def _collect(self):
        tel = report_mod.Telemetry()
        with redirect_stdout(io.StringIO()):
            return report_mod.collect_omni_pool(self.db_path, tel)


class TestTelemetry(ReportTestCase):
    def test_every_event_carries_one_correlation_id_and_timestamp(self):
        self.write_state(self.kibe_path, {"M01:a": _profile("DONE", "DONE", login=TS, reg=TS)})
        self.make_default_db()
        rc, _, events = self.run_report()
        self.assertEqual(rc, 0)
        self.assertGreaterEqual(len(events), 4)
        ids = {e["correlation_id"] for e in events}
        self.assertEqual(len(ids), 1)
        self.assertRegex(ids.pop(), r"^[0-9a-f]{12}$")
        for e in events:
            self.assertIn("timestamp", e)
            self.assertIn("level", e)
            self.assertTrue(e["timestamp"].endswith("+00:00"))

    def test_correlation_id_differs_between_runs(self):
        _, _, first = self.run_report()
        _, _, second = self.run_report()
        self.assertNotEqual(first[0]["correlation_id"], second[0]["correlation_id"])

    def test_snapshot_event_ok_status(self):
        self.write_state(self.kibe_path, {"M01:a": _profile("WAIT_7D", "WAITING", login=TS, reg=TS)})
        self.make_default_db()
        _, text, events = self.run_report()
        snap = self.find_events(events, "lifecycle_report_snapshot")
        self.assertEqual(len(snap), 1)
        snap = snap[0]
        self.assertEqual(snap["status"], "ok")
        self.assertEqual(snap["level"], "info")
        self.assertEqual(snap["warning_count"], 0)
        self.assertEqual(snap["error_classes"], [])
        self.assertEqual(snap["total"], 1)
        self.assertEqual(snap["buckets"]["WAIT_7D"], 1)
        self.assertEqual(snap["pool_connections"], 3)
        self.assertEqual(snap["pool_models"], 2)
        self.assertGreaterEqual(snap["duration_ms"], 0)
        self.assertNotIn("cảnh báo", text)

    def test_snapshot_event_degraded_lists_error_classes(self):
        self.kibe_path.write_text("{oops", encoding="utf-8")
        self.admin_path.unlink()
        _, text, events = self.run_report()
        snap = self.find_events(events, "lifecycle_report_snapshot")[0]
        self.assertEqual(snap["status"], "degraded")
        self.assertEqual(snap["level"], "warning")
        self.assertEqual(snap["error_classes"],
                         sorted(["DB_NOT_FOUND", "STATE_INVALID_JSON", "STATE_NOT_FOUND"]))
        self.assertEqual(snap["warning_count"], 3)
        self.assertIn(f"correlation_id={snap['correlation_id']}", text)

    def test_load_events_record_latency(self):
        self.make_default_db()
        _, _, events = self.run_report()
        for e in self.find_events(events, "state_loaded"):
            self.assertGreaterEqual(e["duration_ms"], 0)
        for e in self.find_events(events, "db_query_ok"):
            self.assertGreaterEqual(e["duration_ms"], 0)
        self.assertEqual({e["query"] for e in self.find_events(events, "db_query_ok")},
                         {"provider_connections", "combos"})

    def test_explicit_correlation_id_is_preserved(self):
        tel = report_mod.Telemetry(correlation_id="abc123")
        with redirect_stdout(io.StringIO()):
            rec = tel.emit("x", level="warning", error_class="E", extra=1)
        self.assertEqual((rec["correlation_id"], rec["error_class"], rec["extra"]), ("abc123", "E", 1))
        self.assertEqual(tel.error_classes(), ["E"])


class TestHelpers(unittest.TestCase):
    def test_classify_sqlite_error(self):
        cases = {
            "no such table: x": "DB_MISSING_TABLE",
            "no such column: y": "DB_MISSING_COLUMN",
            "unable to open database file": "DB_OPEN_FAILED",
            "database is locked": "DB_LOCKED",
            "file is not a database": "DB_CORRUPT",
            "database disk image is malformed": "DB_CORRUPT",
            "something else": "DB_ERROR",
        }
        for msg, expected in cases.items():
            with self.subTest(msg):
                self.assertEqual(report_mod.classify_sqlite_error(sqlite3.Error(msg)), expected)

    def test_parse_time(self):
        parsed = report_mod._parse_time("2026-10-01T00:00:00Z")
        self.assertEqual(parsed.utcoffset().total_seconds(), 0)
        self.assertEqual(report_mod._parse_time("2026-10-01T00:00:00").tzinfo, report_mod.timezone.utc)
        for bad in (None, "", "garbage", 123, ["x"]):
            self.assertIsNone(report_mod._parse_time(bad))

    def test_hours_ago(self):
        now = report_mod._parse_time("2026-10-02T00:00:00Z")
        self.assertEqual(report_mod._hours_ago(report_mod._parse_time("2026-10-01T12:00:00Z"), now), 12.0)
        self.assertIsNone(report_mod._hours_ago(None, now))

    def test_merge_metrics_sums_all_fields(self):
        a = report_mod.aggregate_records([{"key": "a", "stage": "DONE", "status": "DONE", "bucket": "DONE",
                                           "has_login": True, "has_chatgpt": True}])
        b = report_mod.aggregate_records([{"key": "b", "stage": "BLOCKED", "status": "BLOCKED", "bucket": "BLOCKED",
                                           "has_login": False, "has_chatgpt": False}])
        merged = report_mod.merge_metrics(a, b)
        self.assertEqual((merged["total"], merged["done"], merged["blocked"]), (2, 1, 1))
        self.assertEqual(sum(merged["buckets"].values()), 2)


if __name__ == "__main__":
    unittest.main()
