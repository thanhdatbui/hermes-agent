#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_advisor_orchestration.py
Bộ test offline độc lập, kiểm chứng toàn diện cơ chế điều phối và Intent Classifier của Advisor.
"""

import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Thêm đường dẫn scripts vào sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from advisor_consult import (
    classify_advice_intent,
    consult_advisor,
    ensure_dual_answer,
    redact_secrets,
    _call_stream_chat,
)


class TestAdvisorIntentClassification(unittest.TestCase):
    """Kiểm chứng khả năng phân loại Advice Intent vs Imperative Intent."""

    def test_positives_advice_intent(self):
        advice_cases = [
            # Câu hỏi nguyên nhân / đánh giá thuần túy
            "sao nhìn lệch v",
            "tại sao không chạy ca tối",
            "vì sao lại bị lỗi",
            "thấy sao về phương án này",
            "là sao cứ lệch hoài thế",
            "có nên đổi proxy cho máy 62 không",
            "đánh giá kiến trúc này giúp tao",
            "plan thế nào để xử lý triệt để",
            "sao bữa nay t đéo hề thấy mày gọi advisor nữa?",
            "theo mày nên dùng cách nào",
            "nhìn avatar thế nào có hợp không",
            "liệu làm vậy có bị ban nick ko nhỉ?",
            "hay là do MikroTik bị rớt mạng?",
            # Câu hỗn hợp (Mệnh lệnh + Hỏi tư vấn / nguyên nhân)
            "chạy batch rồi cho tao biết nên làm gì",
            "git log xem có gì lạ không",
            "kiểm tra log và phân tích xem nguyên nhân là do đâu",
        ]
        for msg in advice_cases:
            with self.subTest(msg=msg):
                self.assertTrue(
                    classify_advice_intent(msg),
                    f"Phải nhận diện '{msg}' là ADVICE_INTENT"
                )

    def test_negatives_imperative_and_status(self):
        imperative_cases = [
            # Mệnh lệnh thuần túy
            "chạy batch máy 2",
            "sửa file path_resolver.py",
            "fix đi đm đừng có lệch nữa",
            "làm đi",
            "làm luôn đi",
            "triển khai đi",
            "restart gateway",
            "upload avatar máy 62",
            "đăng ký bù 4 máy",
            "adb shell input keyevent 82",
            # Mệnh lệnh có chứa từ review/plan (False-positive prevention)
            "chạy review combo",
            "tạo plan cho phase 2",
            # Câu hỏi tiến độ / trạng thái (không phải xin ý kiến kiến trúc)
            "kiểm tra xem avatar máy 62 sao rồi",
            "tiến trình chạy ra sao rồi",
            # Câu phó từ ("sao cho")
            "sửa cái này sao cho nhanh",
            # Câu xin phép mệnh lệnh
            "Đăng ký bù, được không?",
        ]
        for msg in imperative_cases:
            with self.subTest(msg=msg):
                self.assertFalse(
                    classify_advice_intent(msg),
                    f"Phải nhận diện '{msg}' là IMPERATIVE_INTENT / STATUS"
                )


class TestStreamParserAndDeadline(unittest.TestCase):
    """Kiểm chứng parser SSE stream thật và xử lý deadline thời gian."""

    def test_sse_parser_success(self):
        sse_lines = [
            b"data: {\"choices\": [{\"delta\": {\"content\": \"Ki\xe1\xba\xbfn tr\xc3\xbac \"}}]}\n",
            b": keep-alive comment\n",
            b"data: {\"choices\": [{\"delta\": {\"content\": \"chu\xe1\xba\xa9n c\xe1\xba\xa7n ph\xe1\xba\xa3i th\xe1\xbb\xb1c thi.\"}}]}\n",
            b"data: [DONE]\n",
        ]
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = sse_lines

        with patch("urllib.request.urlopen", return_value=mock_resp):
            ok, text = _call_stream_chat("http://dummy", {}, {"model": "test"}, timeout_sec=10.0)
            self.assertTrue(ok)
            self.assertEqual(text, "Kiến trúc chuẩn cần phải thực thi.")

    def test_sse_premature_close_without_done_returns_false(self):
        # Stream bị đóng trước khi có marker [DONE] -> Bắt buộc coi là thất bại
        sse_lines = [
            b"data: {\"choices\": [{\"delta\": {\"content\": \"Text d\xe1\xbb\x9f dang ch\xc6\xb0a xong.\"}}]}\n",
        ]
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = sse_lines

        with patch("urllib.request.urlopen", return_value=mock_resp):
            ok, text = _call_stream_chat("http://dummy", {}, {"model": "test"}, timeout_sec=10.0)
            self.assertFalse(ok)
            self.assertIn("without [done]", text.lower())

    def test_deadline_abort_returns_false_not_truncated_text(self):
        def slow_generator():
            yield b"data: {\"choices\": [{\"delta\": {\"content\": \"Text d\xe1\xbb\x9f dang tr\xc6\xb0\xe1\xbb\x9bc deadline.\"}}]}\n"
            time.sleep(0.06)
            yield b"data: {\"choices\": [{\"delta\": {\"content\": \"Text sau deadline.\"}}]}\n"

        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = slow_generator()

        with patch("urllib.request.urlopen", return_value=mock_resp):
            ok, text = _call_stream_chat("http://dummy", {}, {"model": "test"}, timeout_sec=0.03)
            self.assertFalse(ok, "Khi vượt deadline, bắt buộc phải trả về False để kích hoạt fallback")
            self.assertIn("deadline exceeded", text.lower())

    def test_pseudo_200_limit_rejection(self):
        sse_lines = [
            b"data: {\"choices\": [{\"delta\": {\"content\": \"[Error: You've hit your limit for today]\"}}]}\n",
            b"data: [DONE]\n",
        ]
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = sse_lines

        with patch("urllib.request.urlopen", return_value=mock_resp):
            ok, text = _call_stream_chat("http://dummy", {}, {"model": "test"}, timeout_sec=10.0)
            self.assertFalse(ok, "Phải từ chối kết quả pseudo-200 chứa thông báo limit")
            self.assertIn("limit", text.lower())


class TestSecretRedaction(unittest.TestCase):
    """Kiểm chứng khả năng che giấu API keys, Bearer tokens, passwords, sessions."""

    def test_redact_all_sensitive_variants(self):
        raw = (
            "sk-1234567890abcdef1234567890, "
            "Bearer token1234567890abcdef, "
            "https://admin:super_secret@farm.net, "
            "password: my_password123, "
            "mật khẩu = secret_vn, "
            "token=xyz789, "
            "api_key=key_999, "
            "sessionid=sess_456"
        )
        cleaned = redact_secrets(raw)
        self.assertNotIn("sk-1234567890", cleaned)
        self.assertNotIn("token1234567890abcdef", cleaned)
        self.assertNotIn("super_secret", cleaned)
        self.assertNotIn("my_password123", cleaned)
        self.assertNotIn("secret_vn", cleaned)
        self.assertNotIn("xyz789", cleaned)
        self.assertNotIn("key_999", cleaned)
        self.assertNotIn("sess_456", cleaned)
        self.assertIn("[REDACTED_API_KEY]", cleaned)
        self.assertIn("[REDACTED_TOKEN]", cleaned)
        self.assertIn("[REDACTED_USER_PASS]", cleaned)


class TestAdvisorFallbackChain(unittest.TestCase):
    """Kiểm chứng fallback chain 3 tầng khi gặp timeout hoặc lỗi upstream."""

    @patch("advisor_consult._call_stream_chat")
    def test_tier1_success(self, mock_stream):
        mock_stream.side_effect = [(True, "Sol Tier 1 architectural advice.")]
        res = consult_advisor("Đánh giá phương án?")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["tier"], 1)
        self.assertIn("Sol / review", res["formatted"])
        self.assertIn("Sol Tier 1 architectural advice.", res["advice"])

    @patch("advisor_consult._call_stream_chat")
    def test_tier1_fail_fallback_tier2(self, mock_stream):
        mock_stream.side_effect = [
            (False, "timed out"),  # Tier 1 fails
            (True, "Gemini Fast Fallback advice.")  # Tier 2 succeeds
        ]
        res = consult_advisor("Đánh giá phương án?")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["tier"], 2)
        self.assertIn("gemini-3.7-flash-high fallback", res["formatted"])
        self.assertIn("Gemini Fast Fallback advice.", res["advice"])

    @patch("advisor_consult.os.environ.get")
    @patch("advisor_consult._call_stream_chat")
    def test_tier1_tier2_fail_fallback_tier3(self, mock_stream, mock_env):
        mock_env.return_value = "dummy_nine_key"
        mock_stream.side_effect = [
            (False, "timed out"),  # Tier 1 fails
            (False, "timed out"),  # Tier 2 fails
            (True, "9Router Tier 3 advice.")  # Tier 3 succeeds
        ]
        res = consult_advisor("Đánh giá phương án?")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["tier"], 3)
        self.assertIn("9Router :20128 backup", res["formatted"])
        self.assertIn("9Router Tier 3 advice.", res["advice"])

    @patch("advisor_consult.os.environ.get")
    @patch("advisor_consult._call_stream_chat")
    def test_all_tiers_fail_returns_unavailable(self, mock_stream, mock_env):
        mock_env.return_value = "dummy_key"
        mock_stream.side_effect = [
            (False, "timed out"),  # Tier 1 fails
            (False, "timed out"),  # Tier 2 fails
            (False, "HTTP 500 error"),  # Tier 3 fails
        ]
        res = consult_advisor("Đánh giá phương án?")
        self.assertEqual(res["status"], "unavailable")
        self.assertEqual(res["tier"], 0)
        self.assertIn("Advisor: unavailable", res["formatted"])


class TestMechanicalEnforcement(unittest.TestCase):
    """Kiểm chứng cơ chế bảo vệ cơ học ensure_dual_answer."""

    @patch("advisor_consult.consult_advisor")
    def test_enforces_advisor_when_missing_on_advice(self, mock_consult):
        mock_consult.return_value = {
            "status": "success",
            "formatted": "--- Advisor (Sol / review) ---\nLời khuyên từ Advisor."
        }
        msg = "Tại sao lại bị lệch avatar?"
        primary = "Do công thức toán học bị sai."
        enforced = ensure_dual_answer(msg, primary)
        self.assertIn("--- Advisor (Sol / review) ---", enforced)
        self.assertIn("Do công thức toán học bị sai.", enforced)

    def test_skips_when_advisor_already_present(self):
        msg = "Tại sao lại bị lệch avatar?"
        primary = "Câu trả lời chính.\n\n--- Advisor (Sol / review) ---\nÝ kiến độc lập."
        enforced = ensure_dual_answer(msg, primary)
        self.assertEqual(enforced, primary)

    def test_skips_on_imperative_command(self):
        msg = "Chạy batch máy 2"
        primary = "Đã khởi động máy 2."
        enforced = ensure_dual_answer(msg, primary)
        self.assertEqual(enforced, primary)


if __name__ == "__main__":
    unittest.main()
