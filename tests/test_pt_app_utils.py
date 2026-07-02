import unittest

from pt_app_utils import LAXITY_MAX_SCORE
from pt_app_utils import calculate_laxity_score
from pt_app_utils import classify_gemini_error
from pt_app_utils import detect_potential_personal_information
from pt_app_utils import format_grip_strength_items
from pt_app_utils import validate_ai_output


class PrivacyDetectionTests(unittest.TestCase):
    def assert_detected(self, value):
        findings = detect_potential_personal_information({"テスト欄": value})
        self.assertTrue(findings)

    def test_detects_phone_number(self):
        self.assert_detected("090-1234-5678")

    def test_detects_email_address(self):
        self.assert_detected("test@example.com")

    def test_detects_labeled_birth_date(self):
        self.assert_detected("生年月日: 1980/1/1")

    def test_does_not_detect_clinical_date(self):
        for value in (
            "2026/6/30から疼痛軽減",
            "発症日 2026/6/30",
            "手術日 2026年6月30日",
        ):
            with self.subTest(value=value):
                findings = detect_potential_personal_information({"テスト欄": value})
                self.assertEqual(findings, [])


class OutputValidationTests(unittest.TestCase):
    def test_detects_missing_initial_output_items(self):
        missing_items, _, _ = validate_ai_output("電子カルテ用 問題点", is_reevaluation=False)
        self.assertIn("短期目標", missing_items)
        self.assertIn("治療内容", missing_items)

    def test_detects_output_that_is_too_short(self):
        _, output_too_short, output_too_long = validate_ai_output("短い出力", is_reevaluation=False)
        self.assertTrue(output_too_short)
        self.assertFalse(output_too_long)


class LaxityScoreTests(unittest.TestCase):
    def test_calculates_partial_laxity_score(self):
        bilateral_results = {
            "手関節": {"右": True, "左": False},
            "肘関節": {"右": True, "左": True},
        }
        single_results = {"脊柱": True, "股関節": False}
        self.assertEqual(calculate_laxity_score(bilateral_results, single_results), 2.5)

    def test_laxity_score_has_seven_point_maximum(self):
        bilateral_results = {
            item: {"右": True, "左": True}
            for item in ("手関節", "肘関節", "肩関節", "膝関節", "足関節")
        }
        single_results = {"脊柱": True, "股関節": True}
        self.assertEqual(calculate_laxity_score(bilateral_results, single_results), LAXITY_MAX_SCORE)


class GripStrengthFormattingTests(unittest.TestCase):
    def test_zero_is_kept_distinct_from_unmeasured(self):
        self.assertEqual(format_grip_strength_items(None, None), [])
        self.assertEqual(format_grip_strength_items(0.0, None), ["右 0.0kg"])


class GeminiErrorClassificationTests(unittest.TestCase):
    @staticmethod
    def make_error(name, message):
        return type(name, (Exception,), {})(message)

    def assert_safe_classification(self, error, expected_level, expected_text):
        level, message = classify_gemini_error(error)
        self.assertEqual(level, expected_level)
        self.assertIn(expected_text, message)
        self.assertNotIn("secret-key-value", message)

    def test_classifies_authentication_error(self):
        self.assert_safe_classification(
            self.make_error("Unauthenticated", "API key not valid: secret-key-value"),
            "error",
            "認証",
        )

    def test_classifies_quota_error(self):
        self.assert_safe_classification(
            self.make_error("ResourceExhausted", "quota exceeded: secret-key-value"),
            "warning",
            "Quota",
        )

    def test_classifies_network_error(self):
        self.assert_safe_classification(
            self.make_error("DeadlineExceeded", "request timed out: secret-key-value"),
            "warning",
            "通信",
        )


if __name__ == "__main__":
    unittest.main()
