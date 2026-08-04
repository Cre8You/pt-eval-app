import unittest

from pt_app_utils import LAXITY_MAX_SCORE
from pt_app_utils import MMT_MYOTOME_MAP
from pt_app_utils import NECK_MMT_ITEMS
from pt_app_utils import PLAN_TRANSLATION_LANGUAGES
from pt_app_utils import ROM_REFERENCE_VALUES
from pt_app_utils import build_balance_assessment_lines
from pt_app_utils import build_plan_translation_prompt
from pt_app_utils import build_pt_free_text_instruction
from pt_app_utils import calculate_laxity_score
from pt_app_utils import calculate_sebt_anterior_asymmetry
from pt_app_utils import calculate_sebt_composite_score
from pt_app_utils import classify_sebt_asymmetry_reference
from pt_app_utils import classify_sebt_composite_reference
from pt_app_utils import classify_gemini_error
from pt_app_utils import classify_single_leg_stance_reference
from pt_app_utils import classify_tug_reference
from pt_app_utils import detect_potential_personal_information
from pt_app_utils import contains_bullet_only_content
from pt_app_utils import count_fullwidth_priority_problem_items
from pt_app_utils import count_priority_problem_items
from pt_app_utils import extract_colon_heading_body
from pt_app_utils import extract_rehabilitation_plan_section
from pt_app_utils import format_grip_strength_items
from pt_app_utils import format_mmt_display_name
from pt_app_utils import format_rom_display_name
from pt_app_utils import is_plan_translation_usable
from pt_app_utils import normalize_pt_free_text
from pt_app_utils import validate_ai_output
from pt_app_utils import validate_physical_therapy_evaluation


class RomAndMmtDisplayTests(unittest.TestCase):
    def test_formats_rom_reference_values(self):
        self.assertEqual(format_rom_display_name("屈曲", 125), "屈曲（125°）")
        self.assertEqual(format_rom_display_name("伸展", 0), "伸展（0°）")

    def test_rom_items_without_references_have_no_parentheses(self):
        for item in ("SLR", "CV角", "内旋(結帯)"):
            with self.subTest(item=item):
                self.assertEqual(format_rom_display_name(item, None), item)

    def test_zero_reference_is_not_treated_as_none(self):
        self.assertEqual(format_rom_display_name("伸展", 0), "伸展（0°）")
        self.assertNotEqual(format_rom_display_name("伸展", 0), "伸展")

    def test_updated_official_rom_references(self):
        self.assertEqual(ROM_REFERENCE_VALUES["腰部"]["右側屈"], 50)
        self.assertEqual(ROM_REFERENCE_VALUES["腰部"]["左側屈"], 50)
        self.assertEqual(ROM_REFERENCE_VALUES["腰部"]["右回旋"], 40)
        self.assertEqual(ROM_REFERENCE_VALUES["腰部"]["左回旋"], 40)
        self.assertEqual(ROM_REFERENCE_VALUES["手指"]["MP伸展"], 45)

    def test_hip_rom_contains_knee_ankle_and_slr_items(self):
        hip_rom = ROM_REFERENCE_VALUES["股関節"]
        for item in (
            "膝関節屈曲",
            "膝関節伸展",
            "足関節背屈",
            "足関節底屈",
            "SLR",
        ):
            with self.subTest(item=item):
                self.assertIn(item, hip_rom)
        self.assertIsNone(hip_rom["SLR"])

    def test_knee_rom_contains_hip_ankle_and_slr_items(self):
        knee_rom = ROM_REFERENCE_VALUES["膝関節"]
        for item in (
            "股関節屈曲",
            "股関節伸展",
            "股関節外転",
            "股関節内転",
            "股関節外旋",
            "股関節内旋",
            "足関節背屈",
            "足関節底屈",
            "SLR",
        ):
            with self.subTest(item=item):
                self.assertIn(item, knee_rom)

    def test_formats_mmt_myotome_labels(self):
        self.assertEqual(
            format_mmt_display_name("上腕二頭筋"),
            "上腕二頭筋（C5-C6、主にC5）",
        )
        self.assertEqual(
            format_mmt_display_name("上腕三頭筋"),
            "上腕三頭筋（C6-C8、主にC7）",
        )
        self.assertEqual(
            format_mmt_display_name("大腿四頭筋"),
            "大腿四頭筋（L2-L4、主にL3）",
        )

    def test_unknown_muscle_keeps_original_name(self):
        self.assertEqual(format_mmt_display_name("未登録筋"), "未登録筋")

    def test_myotome_labels_do_not_change_internal_muscle_keys(self):
        self.assertIn("上腕三頭筋", MMT_MYOTOME_MAP)
        self.assertNotIn("上腕三頭筋（C6-C8、主にC7）", MMT_MYOTOME_MAP)

    def test_neck_mmt_contains_bilateral_triceps_item(self):
        self.assertIn("上腕三頭筋", NECK_MMT_ITEMS)
        self.assertNotEqual(NECK_MMT_ITEMS[0], "上腕三頭筋")


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
＃1 動作時痛の残存
＃2 下肢筋力低下
＃3 歩行耐久性低下
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

    def test_accepts_old_and_new_initial_chart_layouts(self):
        plan_section = (
            "【計画書用】\n【短期目標】疼痛軽減\n【長期目標】屋外歩行\n"
            "【治療方針】機能改善\n【治療内容】可動域練習"
        )
        assessment_section = (
            "理学療法評価：\n　" + ("あ" * 150) + "\n"
            "優先的問題点：\n　＃1 疼痛\n　＃2 筋力低下\n　＃3 歩行制限\n"
        )
        old_layout = (
            "【電子カルテ用】\n疼痛：安静時0\n関節可動域：制限なし\n"
            f"筋力：MMT5\nADL：自立\n{assessment_section}{plan_section}"
        )
        new_layout = (
            "【電子カルテ用】\n疼痛：\n　安静時0\n関節可動域：\n　制限なし\n"
            f"筋力：\n　MMT5\nADL：\n　自立\n{assessment_section}{plan_section}"
        )
        for response_text in (old_layout, new_layout):
            with self.subTest(response_text=response_text):
                missing_items, _, _ = validate_ai_output(response_text, is_reevaluation=False)
                self.assertEqual(missing_items, [])

    def test_accepts_reevaluation_priority_problems_and_program_heading(self):
        missing_items, _, _ = validate_ai_output(self.REEVALUATION_OUTPUT, is_reevaluation=True)
        self.assertNotIn("優先的問題点", missing_items)
        self.assertNotIn("優先的問題点（3項目）", missing_items)
        self.assertNotIn("実施プログラム", missing_items)
        self.assertNotIn("実施プログラム（5行以内）", missing_items)

    def test_detects_missing_reevaluation_priority_problems(self):
        response_text = self.REEVALUATION_OUTPUT.replace(
            "【優先的問題点】\n＃1 動作時痛の残存\n＃2 下肢筋力低下\n＃3 歩行耐久性低下\n",
            "",
        )
        missing_items, _, _ = validate_ai_output(response_text, is_reevaluation=True)
        self.assertIn("優先的問題点", missing_items)

    def test_detects_priority_problem_count_other_than_three(self):
        response_text = self.REEVALUATION_OUTPUT.replace("＃3 歩行耐久性低下\n", "")
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

    def test_initial_validation_requires_three_priority_problems(self):
        response_text = "電子カルテ用 評価結果 問題点 短期目標 長期目標 治療方針 治療内容"
        missing_items, _, _ = validate_ai_output(response_text, is_reevaluation=False)
        self.assertIn("優先的問題点（3項目）", missing_items)
        self.assertNotIn("実施プログラム", missing_items)
        self.assertNotIn("実施プログラム（5行以内）", missing_items)


class PhysicalTherapyEvaluationTests(unittest.TestCase):
    INITIAL_OUTPUT_PREFIX = (
        "【電子カルテ用】\n理学療法評価：\n　" + ("あ" * 150) + "\n"
    )
    INITIAL_OUTPUT_SUFFIX = """優先的問題点：
　＃1 動作時痛
　＃2 筋力低下
　＃3 歩行能力低下
【標準算定期限】：2026/12/28
【リハビリ期限】：2026/12/28
【計画書用】
【疼痛について】動作時痛あり
【短期目標】屋内歩行安定
【長期目標】屋外歩行獲得
【治療方針】機能改善
【治療内容】①歩行練習
"""

    def initial_output(self, extra_sections=""):
        return self.INITIAL_OUTPUT_PREFIX + extra_sections + self.INITIAL_OUTPUT_SUFFIX

    def validate_initial(self, extra_sections="", has_pt_free_text=True):
        missing_items, _, _ = validate_ai_output(
            self.initial_output(extra_sections),
            is_reevaluation=False,
            has_pt_free_text=has_pt_free_text,
        )
        return missing_items

    def test_extracts_supplemental_findings_body(self):
        body = extract_colon_heading_body(
            "補足評価結果：\n　右立脚期の短縮を認めた。\nPT推論：\n　疼痛回避の可能性がある。",
            "補足評価結果",
        )
        self.assertEqual(body, "右立脚期の短縮を認めた。")

    def test_extracts_pt_reasoning_body(self):
        body = extract_colon_heading_body(
            "PT推論：\n　疼痛回避の可能性がある。\n優先的問題点：\n　・歩行能力低下",
            "PT推論",
        )
        self.assertEqual(body, "疼痛回避の可能性がある。")

    def test_extracts_fullwidth_indented_multiline_body(self):
        body = extract_colon_heading_body(
            "補足評価結果：\n　右片脚立位時間は3.2秒であった。\n　右股関節外転筋力はMMT4であった。",
            "補足評価結果：",
        )
        self.assertEqual(
            body,
            "右片脚立位時間は3.2秒であった。\n　右股関節外転筋力はMMT4であった。",
        )

    def test_extraction_stops_at_next_colon_heading(self):
        text = "補足評価結果：\n　右立脚期短縮。\nPT推論：\n　疼痛回避と考える。"
        self.assertEqual(
            extract_colon_heading_body(text, "補足評価結果"),
            "右立脚期短縮。",
        )

    def test_extraction_stops_at_plan_heading(self):
        text = "PT推論：\n　疼痛回避の可能性がある。\n【計画書用】\n【短期目標】疼痛軽減"
        self.assertEqual(
            extract_colon_heading_body(text, "PT推論"),
            "疼痛回避の可能性がある。",
        )

    def test_extraction_supports_halfwidth_colon_headings(self):
        text = "補足評価結果:\n　右立脚期の短縮を認めた。\nPT推論:\n　疼痛回避の可能性がある。"
        self.assertEqual(
            extract_colon_heading_body(text, "補足評価結果"),
            "右立脚期の短縮を認めた。",
        )
        self.assertEqual(
            extract_colon_heading_body(text, "PT推論"),
            "疼痛回避の可能性がある。",
        )

    def test_body_colon_is_not_misidentified_as_heading(self):
        text = (
            "補足評価結果：\n"
            "　TUG：12.3秒であった。\n"
            "PT推論：\n"
            "　歩行能力低下に影響している可能性がある。"
        )
        self.assertEqual(
            extract_colon_heading_body(text, "補足評価結果"),
            "TUG：12.3秒であった。",
        )

    def test_extracts_empty_heading_as_empty_string(self):
        self.assertEqual(
            extract_colon_heading_body("補足評価結果：\nPT推論：\n　仮説あり。", "補足評価結果"),
            "",
        )

    def test_missing_heading_returns_none(self):
        self.assertIsNone(extract_colon_heading_body("理学療法評価：\n　所見あり。", "PT推論"))
        self.assertIsNone(extract_colon_heading_body(None, "PT推論"))

    def test_detects_bullet_only_content(self):
        for text in (
            "・疼痛回避\n・筋力低下の影響",
            "- 疼痛回避\n* 筋力低下",
            "1. 疼痛回避\n2. 筋力低下",
            "①疼痛回避\n②筋力低下",
        ):
            with self.subTest(text=text):
                self.assertTrue(contains_bullet_only_content(text))

    def test_natural_text_and_decimal_are_not_bullet_only(self):
        self.assertFalse(contains_bullet_only_content("右立脚期の短縮を認めた。"))
        self.assertFalse(contains_bullet_only_content("3.2秒であった。"))
        self.assertFalse(contains_bullet_only_content(None))

    def test_pt_free_text_normalization_is_safe_for_empty_and_none(self):
        for value in (None, "", "   ", "　"):
            with self.subTest(value=value):
                self.assertEqual(normalize_pt_free_text(value), "")
                self.assertFalse(bool(normalize_pt_free_text(value)))
        self.assertEqual(normalize_pt_free_text(" 右立脚期短縮 "), "右立脚期短縮")

    def test_deprecated_findings_heading_warns(self):
        warnings = self.validate_initial("補足評価結果：\n　右立脚期の短縮を認めた。\n")
        self.assertIn("補足評価結果（廃止見出し）", warnings)

    def test_deprecated_pt_reasoning_heading_warns(self):
        warnings = self.validate_initial("PT推論：\n　疼痛回避の可能性がある。\n")
        self.assertIn("PT推論（廃止見出し）", warnings)

    def test_both_deprecated_headings_warn(self):
        warnings = self.validate_initial(
            "補足評価結果：\n　右立脚期の短縮を認めた。\n"
            "PT推論：\n　疼痛回避の可能性がある。\n"
        )
        self.assertIn("補足評価結果（廃止見出し）", warnings)
        self.assertIn("PT推論（廃止見出し）", warnings)

    def test_deprecated_headings_are_not_required(self):
        warnings = self.validate_initial()
        self.assertEqual(warnings, [])

    def test_empty_deprecated_findings_heading_warns(self):
        warnings = self.validate_initial(
            "補足評価結果：\nPT推論：\n　疼痛回避の可能性がある。\n"
        )
        self.assertIn("補足評価結果（廃止見出し）", warnings)

    def test_empty_deprecated_reasoning_heading_warns(self):
        warnings = self.validate_initial("PT推論：\n")
        self.assertIn("PT推論（廃止見出し）", warnings)

    def test_deprecated_heading_after_plan_still_warns(self):
        response_text = self.initial_output() + "PT推論：\n　疼痛回避の可能性がある。\n"
        warnings, _, _ = validate_ai_output(
            response_text,
            is_reevaluation=False,
            has_pt_free_text=True,
        )
        self.assertIn("PT推論（廃止見出し）", warnings)

    def test_deprecated_bullet_reasoning_heading_warns(self):
        warnings = self.validate_initial("PT推論：\n　・疼痛回避\n　・筋力低下の影響\n")
        self.assertIn("PT推論（廃止見出し）", warnings)

    def test_deprecated_natural_reasoning_heading_still_warns(self):
        warnings = self.validate_initial(
            "PT推論：\n　疼痛回避により歩幅が短縮している可能性がある。\n"
        )
        self.assertIn("PT推論（廃止見出し）", warnings)

    def test_no_free_text_and_no_new_headings_does_not_warn(self):
        self.assertEqual(self.validate_initial(has_pt_free_text=False), [])

    def test_no_free_text_still_warns_for_deprecated_findings(self):
        warnings = self.validate_initial(
            "補足評価結果：\n　右立脚期の短縮を認めた。\n",
            has_pt_free_text=False,
        )
        self.assertIn("補足評価結果（廃止見出し）", warnings)

    def test_no_free_text_still_warns_for_deprecated_reasoning(self):
        warnings = self.validate_initial(
            "PT推論：\n　疼痛回避の可能性がある。\n",
            has_pt_free_text=False,
        )
        self.assertIn("PT推論（廃止見出し）", warnings)

    def test_physical_therapy_assessment_alone_is_allowed_without_free_text(self):
        warnings = self.validate_initial(has_pt_free_text=False)
        self.assertNotIn("理学療法評価", warnings)

    def test_reevaluation_does_not_require_new_headings(self):
        warnings, _, _ = validate_ai_output(
            OutputValidationTests.REEVALUATION_OUTPUT,
            is_reevaluation=True,
            has_pt_free_text=True,
        )
        self.assertNotIn("補足評価結果（廃止見出し）", warnings)
        self.assertNotIn("PT推論（廃止見出し）", warnings)

    def test_none_and_empty_output_are_safe(self):
        for response_text in (None, ""):
            with self.subTest(response_text=response_text):
                warnings, _, _ = validate_ai_output(
                    response_text,
                    is_reevaluation=False,
                    has_pt_free_text=True,
                )
                self.assertIn("理学療法評価", warnings)

    def test_extracts_physical_therapy_evaluation_body(self):
        text = "理学療法評価：\n　疼痛と歩行制限の関連が考えられる。\n優先的問題点：\n　＃1 疼痛"
        self.assertEqual(
            extract_colon_heading_body(text, "理学療法評価"),
            "疼痛と歩行制限の関連が考えられる。",
        )

    def test_physical_therapy_evaluation_length_boundaries(self):
        for length in (150, 200, 250):
            with self.subTest(length=length):
                warnings = validate_physical_therapy_evaluation(
                    f"理学療法評価：\n　{'あ' * length}\n【計画書用】\n【短期目標】改善"
                )
                self.assertNotIn("理学療法評価（150～250文字）", warnings)

    def test_physical_therapy_evaluation_length_outside_range_warns(self):
        for length in (149, 251):
            with self.subTest(length=length):
                warnings = validate_physical_therapy_evaluation(
                    f"理学療法評価：\n　{'あ' * length}\n【計画書用】\n【短期目標】改善"
                )
                self.assertIn("理学療法評価（150～250文字）", warnings)

    def test_empty_or_missing_physical_therapy_evaluation_warns(self):
        empty_warnings = validate_physical_therapy_evaluation(
            "理学療法評価：\n【計画書用】\n【短期目標】改善"
        )
        self.assertIn("理学療法評価（本文なし）", empty_warnings)
        self.assertIn("理学療法評価", validate_physical_therapy_evaluation(""))

    def test_physical_therapy_evaluation_after_plan_warns(self):
        warnings = validate_physical_therapy_evaluation(
            "【計画書用】\n【短期目標】改善\n理学療法評価：\n　" + ("あ" * 150)
        )
        self.assertIn("理学療法評価（計画書部分より前）", warnings)

    def test_bullet_only_physical_therapy_evaluation_warns(self):
        warnings = validate_physical_therapy_evaluation(
            "理学療法評価：\n　・疼痛\n　・筋力低下\n【計画書用】\n【短期目標】改善"
        )
        self.assertIn("理学療法評価（文章形式）", warnings)

    def test_natural_physical_therapy_evaluation_does_not_warn_for_format(self):
        warnings = validate_physical_therapy_evaluation(
            "理学療法評価：\n　" + ("疼痛と歩行制限の関連が考えられる。" * 10) + "\n【計画書用】"
        )
        self.assertNotIn("理学療法評価（文章形式）", warnings)

    def test_clinical_reasoning_deprecated_heading_warns(self):
        warnings = self.validate_initial("臨床推論：\n　疼痛回避の可能性がある。\n")
        self.assertIn("臨床推論（廃止見出し）", warnings)

    def test_inline_deprecated_heading_warns(self):
        warnings = self.validate_initial("PT推論：疼痛回避の可能性がある。\n")
        self.assertIn("PT推論（廃止見出し）", warnings)

    def test_priority_problem_formats_are_counted_for_backwards_compatibility(self):
        for items in (
            "＃1 疼痛\n＃2 筋力低下\n＃3 歩行制限",
            "#1 疼痛\n#2 筋力低下\n#3 歩行制限",
            "1. 疼痛\n2. 筋力低下\n3. 歩行制限",
            "① 疼痛\n② 筋力低下\n③ 歩行制限",
            "・疼痛\n・筋力低下\n・歩行制限",
        ):
            with self.subTest(items=items):
                response_text = f"優先的問題点：\n{items}\n【計画書用】"
                self.assertEqual(count_priority_problem_items(response_text), 3)

    def test_new_priority_problem_format_requires_fullwidth_hash(self):
        fullwidth_text = "優先的問題点：\n＃1 疼痛\n＃2 筋力低下\n＃3 歩行制限\n【計画書用】"
        legacy_text = "優先的問題点：\n1. 疼痛\n2. 筋力低下\n3. 歩行制限\n【計画書用】"
        self.assertEqual(count_fullwidth_priority_problem_items(fullwidth_text), 3)
        self.assertEqual(count_fullwidth_priority_problem_items(legacy_text), 0)

    def test_duplicate_fullwidth_priority_numbers_warn(self):
        response_text = self.initial_output().replace(
            "＃1 動作時痛\n　＃2 筋力低下\n　＃3 歩行能力低下",
            "＃1 動作時痛\n＃1 筋力低下\n＃1 歩行能力低下",
        )
        warnings, _, _ = validate_ai_output(response_text, is_reevaluation=False)
        self.assertIn("優先的問題点（＃1～＃3形式）", warnings)

    def test_two_or_four_priority_problems_warn(self):
        for items in (
            "＃1 疼痛\n＃2 筋力低下",
            "＃1 疼痛\n＃2 筋力低下\n＃3 歩行制限\n＃4 ADL制限",
        ):
            with self.subTest(items=items):
                response_text = self.initial_output().replace(
                    "＃1 動作時痛\n　＃2 筋力低下\n　＃3 歩行能力低下",
                    items,
                )
                warnings, _, _ = validate_ai_output(response_text, is_reevaluation=False)
                self.assertIn("優先的問題点（3項目）", warnings)

    def test_prompt_instructions_cover_initial_and_reevaluation_modes(self):
        initial_instruction = build_pt_free_text_instruction(is_reevaluation=False)
        self.assertIn("該当する既存の評価項目へ統合", initial_instruction)
        self.assertIn("独立見出しは出力してはいけません", initial_instruction)
        self.assertIn("理学療法評価", initial_instruction)
        self.assertIn("原則150～250文字", initial_instruction)
        self.assertIn("患者申告", initial_instruction)
        self.assertIn("重複して記載しない", initial_instruction)
        self.assertIn("箇条書きや短文メモ", initial_instruction)
        self.assertIn("数値、単位、左右", initial_instruction)
        self.assertIn("＃1", initial_instruction)

        reevaluation_instruction = build_pt_free_text_instruction(is_reevaluation=True)
        self.assertIn("指定された11項目だけ", reevaluation_instruction)
        self.assertIn("独立見出しを追加せず", reevaluation_instruction)
        self.assertIn("＃1", reevaluation_instruction)


class PlanTranslationTests(unittest.TestCase):
    def test_extracts_plan_section_from_initial_output(self):
        response_text = (
            "【電子カルテ用】\n評価結果\n"
            "【計画書用】\n【疼痛について】動作時痛あり\n【短期目標】屋内歩行安定"
        )
        expected = "【計画書用】\n【疼痛について】動作時痛あり\n【短期目標】屋内歩行安定"
        self.assertEqual(extract_rehabilitation_plan_section(response_text), expected)

    def test_new_chart_layout_does_not_change_plan_extraction(self):
        plan_text = "【計画書用】\n【疼痛について】動作時痛あり\n【短期目標】屋内歩行安定"
        response_text = (
            "【電子カルテ用】\n疼痛：\n　動作時痛あり\n関節可動域：\n　右膝屈曲90°\n"
            f"{plan_text}"
        )
        self.assertEqual(extract_rehabilitation_plan_section(response_text), plan_text)

    def test_pt_free_text_sections_are_excluded_from_plan_extraction(self):
        plan_text = "【計画書用】\n【疼痛について】動作時痛あり\n【短期目標】屋内歩行安定"
        response_text = (
            "【電子カルテ用】\n"
            "補足評価結果：\n　右立脚期の短縮を認めた。\n"
            "PT推論：\n　疼痛回避の可能性がある。\n"
            f"{plan_text}"
        )
        extracted = extract_rehabilitation_plan_section(response_text)
        self.assertEqual(extracted, plan_text)
        self.assertNotIn("補足評価結果", extracted)
        self.assertNotIn("PT推論", extracted)

    def test_physical_therapy_evaluation_is_excluded_from_plan_extraction(self):
        plan_text = "【計画書用】\n【疼痛について】動作時痛あり\n【短期目標】屋内歩行安定"
        response_text = (
            "【電子カルテ用】\n"
            "理学療法評価：\n　疼痛が歩行へ影響している可能性がある。\n"
            f"{plan_text}"
        )
        self.assertEqual(extract_rehabilitation_plan_section(response_text), plan_text)

    def test_stops_before_next_major_heading(self):
        response_text = (
            "【リハビリテーション実施計画書案】\n【疼痛について】軽減\n"
            "【長期目標】屋外歩行\n【臨床推論】筋力低下が影響"
        )
        expected = "【リハビリテーション実施計画書案】\n【疼痛について】軽減\n【長期目標】屋外歩行\n"
        self.assertEqual(extract_rehabilitation_plan_section(response_text), expected)

    def test_extracts_plan_at_end_of_response(self):
        response_text = "前文\n【計画書案】\n【治療方針】歩行能力を改善する"
        self.assertEqual(
            extract_rehabilitation_plan_section(response_text),
            "【計画書案】\n【治療方針】歩行能力を改善する",
        )

    def test_accepts_plan_heading_variations_without_changing_source(self):
        for heading in (
            "リハビリテーション実施計画書案",
            "リハビリテーション計画書案",
            "リハビリ実施計画書案",
            "計画書案",
        ):
            with self.subTest(heading=heading):
                plan_text = f"【{heading}】\n【短期目標】疼痛軽減"
                self.assertEqual(extract_rehabilitation_plan_section(plan_text), plan_text)

    def test_returns_none_without_plan_heading(self):
        self.assertIsNone(extract_rehabilitation_plan_section("【電子カルテ用】\n評価結果"))

    def test_returns_none_for_empty_text(self):
        self.assertIsNone(extract_rehabilitation_plan_section(""))

    def test_extracts_reevaluation_output(self):
        response_text = (
            "【疼痛について】軽減\n【優先的問題点】\n1. 疼痛\n2. 筋力\n3. 歩行\n"
            "【実施プログラム】\n・歩行練習"
        )
        self.assertEqual(extract_rehabilitation_plan_section(response_text), response_text)

    def test_translation_prompt_contains_language_and_safety_instructions(self):
        prompt = build_plan_translation_prompt("【計画書用】\n右膝屈曲90°", "English")
        self.assertIn("English", prompt)
        self.assertIn("追加・削除・要約・推測しない", prompt)
        self.assertIn("左右、数値、単位", prompt)
        self.assertIn("【計画書用】\n右膝屈曲90°", prompt)

    def test_language_settings_include_spanish_and_no_translation(self):
        self.assertEqual(PLAN_TRANSLATION_LANGUAGES["スペイン語"], "Spanish")
        self.assertIsNone(PLAN_TRANSLATION_LANGUAGES["翻訳なし"])

    def test_translation_validation_rejects_empty_identical_and_short_results(self):
        source = "【計画書用】\n【疼痛について】右膝痛あり"
        self.assertFalse(is_plan_translation_usable(source, ""))
        self.assertFalse(is_plan_translation_usable(source, source))
        self.assertFalse(is_plan_translation_usable(source, "Too short"))
        self.assertTrue(
            is_plan_translation_usable(
                source,
                "Pain: The patient has pain in the right knee during movement.",
            )
        )

    def test_existing_japanese_validation_is_unchanged(self):
        response_text = OutputValidationTests.REEVALUATION_OUTPUT
        before = validate_ai_output(response_text, is_reevaluation=True)
        extract_rehabilitation_plan_section(response_text)
        after = validate_ai_output(response_text, is_reevaluation=True)
        self.assertEqual(after, before)


class BalanceAssessmentTests(unittest.TestCase):
    INITIAL_COMPLETE_OUTPUT = (
        "電子カルテ用 評価結果 問題点 短期目標 長期目標 治療方針 治療内容"
    )

    def test_tug_unmeasured_is_none(self):
        self.assertIsNone(classify_tug_reference(None))
        self.assertEqual(build_balance_assessment_lines(tug_seconds=None), [])

    def test_tug_zero_is_a_measured_value(self):
        lines = build_balance_assessment_lines(tug_seconds=0.0)
        self.assertEqual(lines, ["TUG：0.0秒"])

    def test_tug_cutoff_boundary(self):
        self.assertIn("13.5秒未満", classify_tug_reference(13.4))
        self.assertIn("13.5秒以上", classify_tug_reference(13.5))

    def test_tug_reference_does_not_make_definitive_risk_claim(self):
        for seconds in (13.4, 13.5):
            with self.subTest(seconds=seconds):
                result = classify_tug_reference(seconds)
                for prohibited_text in ("正常", "異常", "転倒リスクあり"):
                    self.assertNotIn(prohibited_text, result)

    def test_tug_condition_is_included(self):
        lines = build_balance_assessment_lines(
            tug_seconds=16.2,
            tug_condition="T字杖使用",
            include_references=True,
        )
        self.assertIn("TUG：16.2秒、T字杖使用", lines[0])

    def test_single_leg_stance_cutoff_boundary(self):
        self.assertIn("5秒未満", classify_single_leg_stance_reference(4.9))
        self.assertIn("5秒以上", classify_single_leg_stance_reference(5.0))

    def test_single_leg_stance_supports_one_measured_side_and_zero(self):
        lines = build_balance_assessment_lines(
            single_leg_right=0.0,
            single_leg_left=None,
        )
        self.assertEqual(lines, ["片脚立位時間（開眼）：右0.0秒"])

    def test_single_leg_stance_handles_right_and_left_independently(self):
        lines = build_balance_assessment_lines(
            single_leg_right=15.0,
            single_leg_left=3.2,
            include_references=True,
        )
        self.assertIn("右15.0秒、左3.2秒", lines[0])
        self.assertIn("左：参考値5秒未満", lines[0])

    def test_calculates_sebt_composite_score(self):
        self.assertEqual(calculate_sebt_composite_score(60.0, 70.0, 80.0, 80.0), 87.5)

    def test_sebt_composite_rounds_to_one_decimal_place(self):
        raw_score = (62.3 + 70.2 + 74.4) / (80.1 * 3) * 100
        self.assertEqual(
            calculate_sebt_composite_score(62.3, 70.2, 74.4, 80.1),
            round(raw_score, 1),
        )

    def test_sebt_composite_requires_all_values(self):
        self.assertIsNone(calculate_sebt_composite_score(None, 70.0, 80.0, 80.0))
        self.assertIsNone(calculate_sebt_composite_score(60.0, None, 80.0, 80.0))
        self.assertIsNone(calculate_sebt_composite_score(60.0, 70.0, None, 80.0))
        self.assertIsNone(calculate_sebt_composite_score(60.0, 70.0, 80.0, None))

    def test_sebt_composite_rejects_nonpositive_limb_length(self):
        self.assertIsNone(calculate_sebt_composite_score(60.0, 70.0, 80.0, 0.0))
        self.assertIsNone(calculate_sebt_composite_score(60.0, 70.0, 80.0, -1.0))

    def test_sebt_composite_accepts_zero_reach_distances(self):
        self.assertEqual(calculate_sebt_composite_score(0.0, 0.0, 0.0, 80.0), 0.0)

    def test_sebt_composite_reference_boundary(self):
        self.assertIn("94%未満", classify_sebt_composite_reference(93.9))
        self.assertIn("94%以上", classify_sebt_composite_reference(94.0))

    def test_calculates_sebt_anterior_asymmetry(self):
        self.assertEqual(calculate_sebt_anterior_asymmetry(60.0, 55.9), 4.1)

    def test_sebt_anterior_asymmetry_rounds_to_one_decimal_place(self):
        self.assertEqual(calculate_sebt_anterior_asymmetry(60.04, 55.95), 4.1)

    def test_sebt_anterior_asymmetry_requires_both_sides(self):
        self.assertIsNone(calculate_sebt_anterior_asymmetry(None, 55.9))
        self.assertIsNone(calculate_sebt_anterior_asymmetry(60.0, None))

    def test_sebt_anterior_asymmetry_reference_boundary(self):
        self.assertIn("4cm以下", classify_sebt_asymmetry_reference(4.0))
        self.assertIn("4cm超", classify_sebt_asymmetry_reference(4.1))

    def test_balance_lines_are_empty_when_everything_is_unmeasured(self):
        self.assertEqual(build_balance_assessment_lines(), [])

    def test_balance_lines_do_not_use_definitive_abnormality_terms(self):
        lines = build_balance_assessment_lines(
            tug_seconds=15.0,
            single_leg_right=3.0,
            sebt_right_composite=90.0,
            sebt_anterior_asymmetry=5.0,
            include_references=True,
        )
        text = "\n".join(lines)
        for prohibited_text in ("異常", "転倒リスクあり", "受傷リスクあり"):
            self.assertNotIn(prohibited_text, text)

    def test_initial_validation_requires_balance_only_when_requested(self):
        missing_items, _, _ = validate_ai_output(
            self.INITIAL_COMPLETE_OUTPUT,
            is_reevaluation=False,
            require_balance=False,
        )
        self.assertNotIn("バランス評価", missing_items)

        missing_items, _, _ = validate_ai_output(
            self.INITIAL_COMPLETE_OUTPUT,
            is_reevaluation=False,
            require_balance=True,
        )
        self.assertIn("バランス評価", missing_items)

        missing_items, _, _ = validate_ai_output(
            f"{self.INITIAL_COMPLETE_OUTPUT} バランス評価",
            is_reevaluation=False,
            require_balance=True,
        )
        self.assertNotIn("バランス評価", missing_items)

    def test_reevaluation_validation_is_unchanged_by_balance_requirement(self):
        missing_items, _, _ = validate_ai_output(
            OutputValidationTests.REEVALUATION_OUTPUT,
            is_reevaluation=True,
            require_balance=True,
        )
        self.assertNotIn("バランス評価", missing_items)
        self.assertNotIn("優先的問題点（3項目）", missing_items)
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
