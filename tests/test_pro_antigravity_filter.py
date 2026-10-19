import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
deploy_scripts = repo_root / "deploy" / "hermes-home" / "scripts"
if str(deploy_scripts) not in sys.path:
    sys.path.insert(0, str(deploy_scripts))

import cron_chatgpt_web_pool_watchdog as w


class TestProAntigravityFilter(unittest.TestCase):
    def test_is_pro_antigravity_accepts_g1_pro_tier(self):
        c = {"name": "pro_user@gmail.com", "providerSpecificData": {"tier": "g1-pro-tier"}}
        self.assertTrue(w.is_pro_antigravity(c))

    def test_is_pro_antigravity_rejects_free_and_standard_tier(self):
        c_free = {"name": "free_user@gmail.com", "providerSpecificData": {"tier": "free-tier"}}
        c_std = {"name": "std_user@gmail.com", "providerSpecificData": {"tier": "standard-tier"}}
        self.assertFalse(w.is_pro_antigravity(c_free))
        self.assertFalse(w.is_pro_antigravity(c_std))

    def test_is_pro_antigravity_rejects_excluded_accounts_regardless_of_casing(self):
        c1 = {"name": "ThanhDatBui19951@GMAIL.COM", "providerSpecificData": {"tier": "g1-pro-tier"}}
        c2 = {"email": "jinrakal@gmail.com", "providerSpecificData": {"tier": "g1-pro-tier"}}
        self.assertFalse(w.is_pro_antigravity(c1))
        self.assertFalse(w.is_pro_antigravity(c2))

    def test_is_pro_antigravity_fail_closed_on_missing_or_corrupt_data(self):
        # Fail-closed: thiếu metadata hoặc cấu trúc không hợp lệ -> loại bỏ lập tức
        self.assertFalse(w.is_pro_antigravity({}))
        self.assertFalse(w.is_pro_antigravity(None))
        self.assertFalse(w.is_pro_antigravity("not a dict"))
        self.assertFalse(w.is_pro_antigravity({"name": "legacy_acc@gmail.com"}))
        self.assertFalse(w.is_pro_antigravity({"name": "legacy@gmail.com", "providerSpecificData": None}))
        self.assertFalse(w.is_pro_antigravity({"name": "legacy@gmail.com", "providerSpecificData": "string_not_dict"}))
        self.assertFalse(w.is_pro_antigravity({"name": "legacy@gmail.com", "providerSpecificData": {"tier": None}}))
        self.assertFalse(w.is_pro_antigravity({"name": "", "providerSpecificData": {"tier": "g1-pro-tier"}}))

    def test_omniroute_real_schema_contract(self):
        # Xác minh hợp đồng schema dữ liệu thực tế từ OmniRoute API
        real_pro_conn = {
            "id": "5a1e3685-3e28-4ef6-b223-fa349bc9a6e1",
            "name": "ninhvan04061999@gmail.com",
            "provider": "antigravity",
            "isActive": True,
            "testStatus": "active",
            "providerSpecificData": {
                "tier": "g1-pro-tier",
                "plan": "Pro",
                "subscriptionTier": "Google AI Pro"
            }
        }
        self.assertTrue(w.is_pro_antigravity(real_pro_conn))

    def test_antigravity_scan_telemetry_and_counts_on_success(self):
        mock_ag_conns = [
            # Pro account broken -> should be picked up and recovered
            {"id": "c1", "name": "pro_broken@gmail.com", "isActive": True, "testStatus": "expired", "providerSpecificData": {"tier": "g1-pro-tier"}},
            # Free account broken -> must be SKIPPED
            {"id": "c2", "name": "free_broken@gmail.com", "isActive": True, "testStatus": "expired", "providerSpecificData": {"tier": "free-tier"}},
            # Pro account healthy -> no recovery needed
            {"id": "c3", "name": "pro_healthy@gmail.com", "isActive": True, "testStatus": "active", "providerSpecificData": {"tier": "g1-pro-tier"}},
            # Excluded account -> must be SKIPPED
            {"id": "c4", "name": "thanhdatbui19951@gmail.com", "isActive": True, "testStatus": "expired", "providerSpecificData": {"tier": "g1-pro-tier"}},
            # Standby/inactive Pro account -> must be SKIPPED (respect user standby)
            {"id": "c5", "name": "pro_standby@gmail.com", "isActive": False, "testStatus": "expired", "providerSpecificData": {"tier": "g1-pro-tier"}},
        ]

        def fake_get_conns(prov):
            if prov == "antigravity":
                return mock_ag_conns
            return []

        mock_gpm = [{"id": "pid_1", "name": "pro_broken@gmail.com"}]
        with patch.object(w, "get_connections_by_provider", side_effect=fake_get_conns), \
             patch.object(w, "get_gpm_profiles", return_value=mock_gpm), \
             patch.object(w, "load_accounts_credentials", return_value={"pro_broken@gmail.com": {}}), \
             patch.object(w, "refresh_antigravity_account_via_gpm", return_value=(True, "OK")) as mock_refresh, \
             patch.object(w, "save_telemetry_metrics") as mock_save_telem:
            w.main()
            self.assertEqual(mock_refresh.call_count, 1)
            self.assertEqual(mock_refresh.call_args[0][1], "pro_broken@gmail.com")

            mock_save_telem.assert_called_once()
            telem = mock_save_telem.call_args[0][0]
            # Xác minh chính xác số lượng Pro active sau khi quét:
            self.assertEqual(telem["recovered_ag"], ["pro_broken@gmail.com"])
            # c1 (isActive=True) + c3 (isActive=True) -> total pro active conns = 2
            self.assertEqual(telem["antigravity"]["total"], 2)

    def test_antigravity_scan_failure_telemetry_recording(self):
        # Kiểm chứng khi refresh thất bại: ghi nhận telemetry failure đầy đủ
        mock_ag_conns = [
            {"id": "c1", "name": "pro_fail@gmail.com", "isActive": True, "testStatus": "expired", "providerSpecificData": {"tier": "g1-pro-tier"}},
        ]

        def fake_get_conns(prov):
            if prov == "antigravity":
                return mock_ag_conns
            return []

        mock_gpm = [{"id": "pid_1", "name": "pro_fail@gmail.com"}]
        with patch.object(w, "get_connections_by_provider", side_effect=fake_get_conns), \
             patch.object(w, "get_gpm_profiles", return_value=mock_gpm), \
             patch.object(w, "load_accounts_credentials", return_value={"pro_fail@gmail.com": {}}), \
             patch.object(w, "refresh_antigravity_account_via_gpm", return_value=(False, "OAuth token rejected")) as mock_refresh, \
             patch.object(w, "save_telemetry_metrics") as mock_save_telem:
            w.main()
            self.assertEqual(mock_refresh.call_count, 1)

            mock_save_telem.assert_called_once()
            telem = mock_save_telem.call_args[0][0]
            self.assertEqual(telem["recovered_ag"], [])
            self.assertGreaterEqual(telem["total_failures"], 1)
            failures_accounts = [f["account"] for f in telem.get("failures", [])]
            self.assertIn("pro_fail@gmail.com", failures_accounts)


if __name__ == "__main__":
    unittest.main()
