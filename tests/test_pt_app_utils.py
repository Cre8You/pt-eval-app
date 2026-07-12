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
    REEVALUATION_OUTPUT = """
【疼痛について】疼痛軽減
【筋力について】筋力改善
【感覚異常について】しびれ残存
【可動域について】可動域改善
【優先的問題点】
1. 動作時痛の残存
2. 下肢筋力低下
3. 歩行耐久性低下
【短期目標】屋内歩行の安定
【長期目標】買い物動作の再獲得
【治療方針】筋力と歩行能力の改善
【実施プログラム】
・股関節・下肢筋群のストレッチ
・殿筋群・体幹筋群の筋力エクササイズ
・下肢筋群の筋力エクササイズ
・立ち上がり・歩行動作練習
・自主トレーニング指導
【参加制限に対する具体的な対応方針】外出機会を段階的に増やす
【機能障害に対する具体的な対応方針】筋力訓練を実施する
"""

    def test_detects_missing_initial_output_items(self):
        missing_items, _, _ = validate_ai_output("電子カルテ用 問題点", is_reevaluation=False)
        self.assertIn("短期目標", missing_items)
        self.assertIn("治療内容", missing_items)

    def test_detects_output_that_is_too_short(self):
        _, output_too_short, output_too_long = validate_ai_output("短い出力", is_reevaluation=False)
        self.assertTrue(output_too_short)
        self.assertFalse(output_too_long)

    def test_accepts_reevaluation_priority_problems_and_program_heading(self):
        missing_items, _, _ = validate_ai_output(self.REEVALUATION_OUTPUT, is_reevaluation=True)
        self.assertNotIn("優先的問題点", missing_items)
        self.assertNotIn("優先的問題点（3項目）", missing_items)
        self.assertNotIn("実施プログラム", missing_items)
        self.assertNotIn("実施プログラム（5行以内）", missing_items)

    def test_detects_missing_reevaluation_priority_problems(self):
        response_text = self.REEVALUATION_OUTPUT.replace(
            "【優先的問題点】\n1. 動作時痛の残存\n2. 下肢筋力低下\n3. 歩行耐久性低下\n",
            "",
        )
        missing_items, _, _ = validate_ai_output(response_text, is_reevaluation=True)
        self.assertIn("優先的問題点", missing_items)

    def test_detects_priority_problem_count_other_than_three(self):
        response_text = self.REEVALUATION_OUTPUT.replace("3. 歩行耐久性低下\n", "")
        missing_items, _, _ = validate_ai_output(response_text, is_reevaluation=True)
        self.assertIn("優先的問題点（3項目）", missing_items)

    def test_detects_missing_reevaluation_program_heading(self):
        program_section = self.REEVALUATION_OUTPUT.split("【実施プログラム】", 1)[1].split(
            "【参加制限に対する具体的な対応方針】",
            1,
        )[0]
        response_text = self.REEVALUATION_OUTPUT.replace(f"【実施プログラム】{program_section}", "")
        missing_items, _, _ = validate_ai_output(response_text, is_reevaluation=True)
        self.assertIn("実施プログラム", missing_items)

    def test_accepts_fewer_than_five_reevaluation_programs(self):
        response_text = self.REEVALUATION_OUTPUT.replace(
            "・下肢筋群の筋力エクササイズ\n・立ち上がり・歩行動作練習\n・自主トレーニング指導\n",
            "",
        )
        missing_items, _, _ = validate_ai_output(response_text, is_reevaluation=True)
        self.assertNotIn("実施プログラム（5行以内）", missing_items)

    def test_detects_more_than_five_reevaluation_programs(self):
        response_text = self.REEVALUATION_OUTPUT.replace(
            "・自主トレーニング指導\n",
            "・自主トレーニング指導\n・バランス練習\n",
        )
        missing_items, _, _ = validate_ai_output(response_text, is_reevaluation=True)
        self.assertIn("実施プログラム（5行以内）", missing_items)

    def test_counts_supported_reevaluation_program_bullets(self):
        program_section = self.REEVALUATION_OUTPUT.split("【実施プログラム】", 1)[1].split(
            "【参加制限に対する具体的な対応方針】",
            1,
        )[0]
        mixed_bullet_section = """
・ストレッチ
- 筋力エクササイズ
* 可動域練習
1. 動作練習
① バランス練習
② 自主トレーニング指導
"""
        response_text = self.REEVALUATION_OUTPUT.replace(program_section, mixed_bullet_section)
        missing_items, _, _ = validate_ai_output(response_text, is_reevaluation=True)
        self.assertIn("実施プログラム（5行以内）", missing_items)

    def test_initial_validation_does_not_require_reevaluation_additions(self):
        response_text = "電子カルテ用 評価結果 問題点 短期目標 長期目標 治療方針 治療内容"
        missing_items, _, _ = validate_ai_output(response_text, is_reevaluation=False)
        self.assertNotIn("優先的問題点", missing_items)
        self.assertNotIn("優先的問題点（3項目）", missing_items)
        self.assertNotIn("実施プログラム", missing_items)
        self.assertNotIn("実施プログラム（5行以内）", missing_items)


class LaxityScoreTests(unittest.TestCase):
    def test_no_positive_findings_score_zero(self):
        bilateral_results = {"手関節": {"右": False, "左": False}}
        single_results = {"脊柱": False, "股関節": False}
        self.assertEqual(calculate_laxity_score(bilateral_results, single_results), 0.0)

    def test_unilateral_positive_scores_half_point(self):
        bilateral_results = {"手関節": {"右": True, "左": False}}
        self.assertEqual(calculate_laxity_score(bilateral_results, {}), 0.5)

    def test_bilateral_positive_scores_one_point(self):
        bilateral_results = {"手関節": {"右": True, "左": True}}
        self.assertEqual(calculate_laxity_score(bilateral_results, {}), 1.0)

    def test_spine_and_hip_score_one_point_each(self):
        with self.subTest(item="脊柱"):
            self.assertEqual(calculate_laxity_score({}, {"脊柱": True, "股関節": False}), 1.0)
        with self.subTest(item="股関節"):
            self.assertEqual(calculate_laxity_score({}, {"脊柱": False, "股関節": True}), 1.0)

    def test_laxity_score_has_seven_point_maximum(self):
        bilateral_results = {
            item: {"右": True, "左": True}
            for item in ("手関節", "肘関節", "肩関節", "膝関節", "足関節")
        }
        single_results = {"脊柱": True, "股関節": True}
        self.assertEqual(calculate_laxity_score(bilateral_results, single_results), LAXITY_MAX_SCORE)

    def test_calculate_laxity_score_is_importable(self):
        from pt_app_utils import calculate_laxity_score as imported_function

        self.assertIs(imported_function, calculate_laxity_score)


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
