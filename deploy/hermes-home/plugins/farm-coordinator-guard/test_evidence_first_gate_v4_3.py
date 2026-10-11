import os
import sys
import time
import uuid
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

import __init__ as guard_plugin


class TestEvidenceFirstGateV43(unittest.TestCase):
    """Bộ kiểm thử toàn diện cho Evidence-First Gate v4.3 (Round 9 Certified & 100% Hermetic)."""

    def setUp(self):
        guard_plugin._PARENT_SESSION_CACHE.clear()

    # --- 1. KIỂM THỬ _extract_media_paths ---
    def test_extract_media_paths_with_captions_and_markdown(self):
        text = (
            "Báo cáo hoàn thành:\n"
            "MEDIA:D:/Taadaa/tmp/screen%20shot.png — chú thích ảnh chụp M261\n"
            "![Ảnh minh chứng](D:/Taadaa/tmp/switcher_proof.png)\n"
            "MEDIA:C:/Screenshots/status.jpg, xem chi tiết."
        )
        paths = guard_plugin._extract_media_paths(text)
        self.assertEqual(len(paths), 3)
        self.assertIn("D:/Taadaa/tmp/screen shot.png", paths)
        self.assertIn("D:/Taadaa/tmp/switcher_proof.png", paths)
        self.assertIn("C:/Screenshots/status.jpg", paths)

    # --- 2. KIỂM THỬ _detect_completion_claims (ROUND 9: BẮT MỌI TỪ ĐỒNG NGHĨA & DẠNG CÂU) ---
    def test_detect_claims_natural_and_complex_expressions(self):
        self.assertTrue(guard_plugin._detect_completion_claims("Đã đăng nhập nick @my_user")[0])
        self.assertTrue(guard_plugin._detect_completion_claims("Đã đổi pass thành công")[0])
        self.assertTrue(guard_plugin._detect_completion_claims("Đã thay đổi mật khẩu")[0])
        self.assertTrue(guard_plugin._detect_completion_claims("2fa đã bật")[0])
        self.assertTrue(guard_plugin._detect_completion_claims("2FA: ON")[0])
        self.assertTrue(guard_plugin._detect_completion_claims("Trạng thái 2FA: đã bật")[0])
        self.assertTrue(guard_plugin._detect_completion_claims("Mật khẩu: đã đổi")[0])
        self.assertTrue(guard_plugin._detect_completion_claims("đã kích hoạt xác minh 2 bước")[0])
        self.assertTrue(guard_plugin._detect_completion_claims("Nick không bị lỗi đã đăng nhập")[0])
        self.assertTrue(guard_plugin._detect_completion_claims("thiết lập 2fa thành công")[0])
        self.assertTrue(guard_plugin._detect_completion_claims("xác thực 2 lớp đã bật")[0])

    def test_detect_claims_actual_failure_ignored(self):
        self.assertFalse(guard_plugin._detect_completion_claims("Chưa đăng nhập thành công")[0])
        self.assertFalse(guard_plugin._detect_completion_claims("Không bật được 2fa")[0])

    def test_detect_claims_false_positives_ignored(self):
        """Kiểm thử chống false positive: hội thoại bình thường hoặc mô tả lỗi không bị coi là hoàn tất."""
        false_positive_cases = [
            "Ủa mở gpm vào chatgpt login kiểm tra mấy acc die coi",
            "Tao bảo là mày cứ trả cái gate nhảm lồn này nè. Đéo làm cứ trả cái này vào output",
            "Sửa cái gate óc l này cho t",
            "Bực bội v",
            "đang login",
            "kiểm tra login",
            "đăng nhập thất bại",
            "login lỗi",
            "quy trình login",
            "em xin lỗi em sẽ kiểm tra login",
            "hướng dẫn đổi mật khẩu",
            "sẽ đổi pass",
            "đổi pass thất bại",
            "đang bật 2fa",
            "bật 2fa bị lỗi",
            "bật 2fa thất bại",
            "chưa bật 2fa",
            "có đăng nhập được không?",
            "đã đăng nhập được chưa?",
            "Gate bắt câu \"đã đăng nhập\" trong trích dẫn nên sai",
            "Regex trong `đã bật 2fa` là false positive",
            "> đã đăng nhập thành công",
            "Đã đăng nhập chatgpt bằng GPM, 3 acc die",
            "Gate này đã đăng nhập sai logic",
        ]
        for text in false_positive_cases:
            has_claim, claims = guard_plugin._detect_completion_claims(text)
            self.assertFalse(has_claim, f"False positive on: {text} -> {claims}")

    # --- 3. KIỂM THỬ PROVENANCE HÀM THỰC TẾ (CHỐNG PATH TRAVERSAL '..') ---
    def test_provenance_actual_function_behavior(self):
        # Hợp lệ
        self.assertTrue(guard_plugin._is_allowed_evidence_image_path(r"D:\Taadaa\tmp\screen.png"))
        self.assertTrue(guard_plugin._is_allowed_evidence_image_path(r"C:\Screenshots\shot.jpg"))
        # Bất hợp pháp: Path traversal '..' ra ngoài
        self.assertFalse(guard_plugin._is_allowed_evidence_image_path(r"D:\Taadaa\tmp\..\..\Windows\system32\cmd.exe"))
        self.assertFalse(guard_plugin._is_allowed_evidence_image_path(r"C:\Users\Kibe\Downloads\fake.png"))

    # --- 4. KIỂM THỬ G2 PROVENANCE & OCR WHITELIST (HERMETIC VIA TEMPDIR) ---
    def test_post_tool_call_ocr_provenance_hermetic(self):
        sess_id = f"test_ocr_{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory() as tmp_dir:
            valid_img = os.path.join(tmp_dir, "valid.png")
            unauthorized_img = os.path.join(tmp_dir, "unauthorized.png")
            with open(valid_img, "wb") as f:
                f.write(b"valid image")
            with open(unauthorized_img, "wb") as f:
                f.write(b"unauthorized image")

            real_ocr_script = sorted(list(guard_plugin._allowed_ocr_scripts()))[0]

            with patch("__init__._is_allowed_evidence_image_path", side_effect=lambda p: os.path.normcase(p) == os.path.normcase(valid_img)):
                # Unauthorized -> BỊ CHẶN!
                guard_plugin._on_post_tool_call(
                    tool_name="terminal",
                    args={"command": f'python "{real_ocr_script}" "{unauthorized_img}"'},
                    result={"output": "xác minh 2 bước đang bật", "exit_code": 0},
                    session_id=sess_id
                )
                state = guard_plugin._get_session_state(sess_id)
                self.assertNotIn(os.path.normcase(unauthorized_img), state.get("verified_media_paths", []))

                # Valid -> ĐƯỢC GHI NHẬN KÈM SHA-256!
                guard_plugin._on_post_tool_call(
                    tool_name="terminal",
                    args={"command": f'python "{real_ocr_script}" "{valid_img}"'},
                    result={"output": "xác minh 2 bước đang bật: trình xác thực bật", "exit_code": 0},
                    session_id=sess_id
                )
                state = guard_plugin._get_session_state(sess_id)
                norm_p = os.path.normcase(valid_img)
                self.assertIn(norm_p, state.get("verified_media_paths", []))
                self.assertEqual(len(state.get("verified_media_details", {})[norm_p]["sha256"]), 64)

    # --- 5. KIỂM THỬ BROWSER_VISION TỪ CHỐI HTML CỤC BỘ & LOCALHOST/DATA URL SPOOFING ---
    def test_browser_vision_screenshot_provenance_and_html_rejection(self):
        sess_id = f"test_vision_{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory() as tmp_dir:
            valid_sc = os.path.join(tmp_dir, "valid.png")
            with open(valid_sc, "wb") as f:
                f.write(b"valid")

            # Ca 1: Navigate từ file:///.../page.html -> BỊ TỪ CHỐI!
            guard_plugin._on_post_tool_call(
                tool_name="browser_navigate",
                args={"url": "file:///D:/Taadaa/tmp/page.html?v=1#hash"},
                result="navigated",
                session_id=sess_id
            )
            with patch("__init__._is_allowed_evidence_image_path", return_value=True):
                guard_plugin._on_post_tool_call(
                    tool_name="browser_vision",
                    args={},
                    result=f"Visual inspect ok. Screenshot path: {valid_sc}",
                    session_id=sess_id
                )
                state = guard_plugin._get_session_state(sess_id)
                self.assertNotIn(os.path.normcase(valid_sc), state.get("verified_media_paths", []))

            # Ca 2: Navigate từ http://127.0.0.1:8000/fake -> BỊ TỪ CHỐI!
            guard_plugin._on_post_tool_call(
                tool_name="browser_navigate",
                args={"url": "http://127.0.0.1:8000/fake"},
                result="navigated",
                session_id=sess_id
            )
            with patch("__init__._is_allowed_evidence_image_path", return_value=True):
                guard_plugin._on_post_tool_call(
                    tool_name="browser_vision",
                    args={},
                    result=f"Visual inspect ok. Screenshot path: {valid_sc}",
                    session_id=sess_id
                )
                state = guard_plugin._get_session_state(sess_id)
                self.assertNotIn(os.path.normcase(valid_sc), state.get("verified_media_paths", []))

            # Ca 3: Navigate sang web thật https://www.tiktok.com -> GHI NHẬN HỢP LỆ!
            guard_plugin._on_post_tool_call(
                tool_name="browser_navigate",
                args={"url": "https://www.tiktok.com"},
                result="navigated",
                session_id=sess_id
            )
            with patch("__init__._is_allowed_evidence_image_path", return_value=True):
                guard_plugin._on_post_tool_call(
                    tool_name="browser_vision",
                    args={},
                    result=f"Visual inspect ok. Screenshot path: {valid_sc}",
                    session_id=sess_id
                )
                state = guard_plugin._get_session_state(sess_id)
                self.assertIn(os.path.normcase(valid_sc), state.get("verified_media_paths", []))

    # --- 6. KIỂM THỬ BẢO VỆ SCRIPT OCR (F6) ---
    def test_ocr_scripts_are_protected_targets(self):
        self.assertTrue(guard_plugin._is_protected_target(r"D:\Taadaa\tools\ocr.py"))
        self.assertTrue(guard_plugin._is_protected_target(r"D:\Taadaa\tools\winrt_ocr.py"))
        self.assertTrue(guard_plugin._is_protected_target("tools/ocr.py"))

    # --- 7. KIỂM THỬ CHỐNG FILE TAMPERING (THỰC TẾ GHI ĐÈ FILE TRÊN ĐĨA KHÔNG MOCK HASH) ---
    @patch("__init__._is_worker_session", return_value=False)
    def test_fails_closed_when_file_tampered_hermetic_real_io(self, mock_is_worker):
        sess_id = f"test_tamper_{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_p = os.path.join(tmp_dir, "tamper_test.png")
            with open(img_p, "wb") as f:
                f.write(b"AUTHENTIC_ORIGINAL_SCREENSHOT")
            real_sha = guard_plugin._compute_file_sha256(img_p)

            state = {
                "verified_media_paths": [os.path.normcase(img_p)],
                "verified_media_details": {
                    os.path.normcase(img_p): {
                        "text": "xác minh 2 bước đang bật @user_tamper",
                        "sha256": real_sha,
                        "source": "ocr",
                    }
                }
            }

            with patch("__init__._get_session_state", return_value=state):
                text_claim = f"Đã bật 2fa thành công cho @user_tamper!\n\nMEDIA:{img_p}"
                # File nguyên vẹn -> PASS THRU
                self.assertIsNone(guard_plugin._enforce_evidence_first_gate(text_claim, sess_id))

                # Ghi đè file thật trên đĩa với nội dung khác mà KHÔNG patch hash!
                with open(img_p, "wb") as f:
                    f.write(b"TAMPERED_MALICIOUS_DIFFERENT_CONTENT_ON_DISK")

                # Gate tự tính SHA-256 mới từ đĩa và phát hiện không khớp -> FAIL-CLOSED!
                res_bad = guard_plugin._enforce_evidence_first_gate(text_claim, sess_id)
                self.assertIsNotNone(res_bad)
                assert res_bad is not None
                self.assertIn("TAMPERED MEDIA", res_bad)
                self.assertIn("SHA-256 MISMATCH", res_bad)

    # --- 8. KIỂM THỬ 2FA: CÓ CẢ "ĐANG BẬT" VÀ "TẮT" TRONG CÙNG 1 ẢNH ---
    @patch("__init__._is_worker_session", return_value=False)
    def test_2fa_rejects_when_both_active_and_disabled_in_same_image(self, mock_is_worker):
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_p = os.path.join(tmp_dir, "proof.png")
            with open(img_p, "wb") as f:
                f.write(b"bytes")
            file_sha = guard_plugin._compute_file_sha256(img_p)
            norm_p = os.path.normcase(img_p)

            state_conflict = {
                "verified_media_paths": [norm_p],
                "verified_media_details": {
                    norm_p: {
                        "text": "cài đặt bảo mật: xác minh 2 bước đang bật nhưng 2fa: off",
                        "sha256": file_sha,
                    }
                }
            }
            with patch("__init__._get_session_state", return_value=state_conflict):
                res = guard_plugin._enforce_evidence_first_gate(f"Đã bật 2fa!\n\nMEDIA:{img_p}", "c1")
                self.assertIsNotNone(res)
                assert res is not None
                self.assertIn("CONTENT MISMATCH", res)

    # --- 9. KIỂM THỬ PASSWORD TỪ CHỐI ẢNH BẢNG EXCEL VÀ FORM TRỐNG CHƯA SUBMIT ---
    @patch("__init__._is_worker_session", return_value=False)
    def test_password_rejects_plain_excel_proof(self, mock_is_worker):
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_p = os.path.join(tmp_dir, "excel.png")
            with open(img_p, "wb") as f:
                f.write(b"excel")
            file_sha = guard_plugin._compute_file_sha256(img_p)
            norm_p = os.path.normcase(img_p)

            # Ca A: Ảnh bảng Excel -> BỊ CHẶN!
            state_excel = {
                "verified_media_paths": [norm_p],
                "verified_media_details": {
                    norm_p: {
                        "text": "bảng đối soát excel stt tài khoản tik row 242",
                        "sha256": file_sha,
                    }
                }
            }
            with patch("__init__._get_session_state", return_value=state_excel):
                res = guard_plugin._enforce_evidence_first_gate(f"Đã đổi pass thành công!\n\nMEDIA:{img_p}", "c1")
                self.assertIsNotNone(res)
                assert res is not None
                self.assertIn("CONTENT MISMATCH", res)

            # Ca B: Ảnh chỉ là form nhập mật khẩu trống ('đặt lại mật khẩu', 'mật khẩu mới') chưa submit -> BỊ CHẶN!
            state_form = {
                "verified_media_paths": [norm_p],
                "verified_media_details": {
                    norm_p: {
                        "text": "cài đặt đặt lại mật khẩu: vui lòng nhập mật khẩu mới",
                        "sha256": file_sha,
                    }
                }
            }
            with patch("__init__._get_session_state", return_value=state_form):
                res_form = guard_plugin._enforce_evidence_first_gate(f"Đã đổi pass thành công!\n\nMEDIA:{img_p}", "c1")
                self.assertIsNotNone(res_form)
                assert res_form is not None
                self.assertIn("CONTENT MISMATCH", res_form)

    # --- 10. KIỂM THỬ PER-IMAGE ENTITY & ACTION BINDING (CHỐNG GHÉP ẢNH TRIỆT ĐỂ) ---
    @patch("__init__._is_worker_session", return_value=False)
    def test_strict_per_image_binding_blocks_collage_bypass(self, mock_is_worker):
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_a = os.path.join(tmp_dir, "img_a.png")
            img_b = os.path.join(tmp_dir, "img_b.png")
            with open(img_a, "wb") as f:
                f.write(b"a")
            with open(img_b, "wb") as f:
                f.write(b"b")
            sha_a = guard_plugin._compute_file_sha256(img_a)
            sha_b = guard_plugin._compute_file_sha256(img_b)

            # Kịch bản ghép ảnh tinh vi 2 claim:
            # Báo cáo: "@user_a đã đăng nhập và bật 2fa thành công"
            # Ảnh A: Màn hình Switcher chứa @user_a (có login nhưng không có 2FA)
            # Ảnh B: Màn hình 2FA đang bật của @user_other (không có tên @user_a)
            # ➔ STRICT PER-CLAIM PER-USER BINDING BẮT BUỘC CHẶN ĐỨNG VÌ THIẾU ẢNH 2FA CHO @user_a!
            state_collage = {
                "verified_media_paths": [os.path.normcase(img_a), os.path.normcase(img_b)],
                "verified_media_details": {
                    os.path.normcase(img_a): {"text": "chuyển đổi tài khoản switcher @user_a", "sha256": sha_a},
                    os.path.normcase(img_b): {"text": "xác minh 2 bước đang bật: trình xác thực bật @user_other", "sha256": sha_b},
                }
            }
            with patch("__init__._get_session_state", return_value=state_collage):
                text_collage = f"Nick @user_a đã đăng nhập và bật 2fa thành công!\n\nMEDIA:{img_a}\nMEDIA:{img_b}"
                res = guard_plugin._enforce_evidence_first_gate(text_collage, "c1")
                self.assertIsNotNone(res)
                assert res is not None
                self.assertIn("CONTENT MISMATCH", res)
                self.assertIn("@user_a", res)

    # --- 11. KIỂM THỬ SEND_MESSAGE GATE TRONG PRE_TOOL_CALL ---
    @patch("__init__._is_worker_session", return_value=False)
    def test_send_message_mid_turn_bypass_blocked(self, mock_is_worker):
        res = guard_plugin._on_pre_tool_call(
            tool_name="send_message",
            args={"text": "Em báo cáo Sếp: nick ngohuong0265 đã bật 2fa thành công rồi ạ!"},
            session_id="coord_send_msg"
        )
        self.assertIsNotNone(res)
        assert res is not None
        self.assertEqual(res.get("action"), "block")
        self.assertIn("EVIDENCE FIRST GATE — FAIL-CLOSED VIOLATION", res.get("reason", ""))

    # --- 12. KIỂM THỬ FAIL-CLOSED KHI GATE NỘI BỘ GẶP EXCEPTION ---
    def test_transform_output_hook_fail_closed_on_error(self):
        mock_ctx = MagicMock()
        guard_plugin.register(mock_ctx)
        hooks = {call[0][0]: call[0][1] for call in mock_ctx.register_hook.call_args_list}
        transform_hook = hooks.get("transform_llm_output")
        self.assertIsNotNone(transform_hook)
        assert transform_hook is not None

        with patch("__init__._enforce_evidence_first_gate", side_effect=RuntimeError("Lỗi hệ thống bất ngờ")):
            res = transform_hook(response_text="Báo cáo hoàn thành", session_id="c_err")
            self.assertIsNotNone(res)
            assert res is not None
            self.assertIn("EVIDENCE FIRST GATE — FAIL-CLOSED", res)


if __name__ == "__main__":
    unittest.main()
